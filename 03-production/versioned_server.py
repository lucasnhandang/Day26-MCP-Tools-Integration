"""MCP Server có Versioning — minh hoạ backward compatibility.

Khi tool thay đổi schema (thêm/bớt tham số, đổi kiểu trả về), client cũ
sẽ bị break nếu không có chiến lược versioning. Ví dụ này minh hoạ 3 kỹ thuật:

  1. Tool mới song song (get_weather_v2) — giữ tool cũ cho client legacy
  2. Tham số optional với default — thêm tính năng mà không break client cũ
  3. Server version trong metadata — client kiểm tra version trước khi gọi

Cách chạy:
    pip install -r ../requirements.txt
    python versioned_server.py
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from dotenv import find_dotenv, load_dotenv
import httpx

load_dotenv(find_dotenv())

from mcp.server.mcpserver import MCPServer

SERVER_VERSION = "2.0.0"
WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY")

mcp = MCPServer(
    "weather-v2",
    instructions=f"Weather MCP Server v{SERVER_VERSION}. "
    "Hỗ trợ get_weather (v1, backward compat) và get_weather_v2 (chi tiết hơn).",
)

_MOCK_DB = {
    "Hanoi": {
        "temp": 29,
        "condition": "trời mưa",
        "humidity": 82,
        "wind_speed": 12,
        "forecast": [
            {"day": "tomorrow", "temp": 27, "condition": "mưa nhẹ"},
            {"day": "day_after", "temp": 31, "condition": "nắng"},
        ],
    },
    "Danang": {
        "temp": 30,
        "condition": "nhiều mây",
        "humidity": 78,
        "wind_speed": 10,
        "forecast": [
            {"day": "tomorrow", "temp": 32, "condition": "nắng"},
            {"day": "day_after", "temp": 29, "condition": "mưa rào"},
        ],
    },
}


def _fetch_weatherapi(endpoint: str, params: dict[str, str]) -> dict | None:
    if not WEATHERAPI_KEY:
        return None
    params["key"] = WEATHERAPI_KEY
    url = f"https://api.weatherapi.com/v1/{endpoint}"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


# ── Tool v1 (giữ nguyên cho backward compatibility) ──────────────────
@mcp.tool()
def get_weather(city: str) -> str:
    """[v1] Lấy thời tiết hiện tại — trả chuỗi đơn giản. Deprecated, dùng get_weather_v2."""
    real_data = _fetch_weatherapi("current.json", {"q": city, "aqi": "no"})
    if real_data:
        cur = real_data["current"]
        loc = real_data["location"]
        return f"{loc['name']}: {cur['temp_c']}°C, {cur['condition']['text']}"

    data = _MOCK_DB.get(city)
    if data:
        return f"{city}: {data['temp']}°C, {data['condition']}"
    return f"{city}: 28°C, không có dữ liệu chi tiết"


# ── Tool v2 (thêm tính năng, không break v1) ─────────────────────────
@mcp.tool()
def get_weather_v2(
    city: str,
    include_forecast: bool = False,
    units: str = "celsius",
) -> str:
    """[v2] Lấy thời tiết chi tiết — JSON, hỗ trợ forecast và đơn vị đo.

    Args:
        city: Tên thành phố (ví dụ: Hanoi, Danang)
        include_forecast: Có trả thêm dự báo các ngày tới không (mặc định: False)
        units: Đơn vị nhiệt độ — "celsius" hoặc "fahrenheit" (mặc định: celsius)
    """
    days = "3" if include_forecast else "1"
    real_data = _fetch_weatherapi("forecast.json", {"q": city, "days": days, "aqi": "no"})
    if real_data:
        cur = real_data["current"]
        loc = real_data["location"]
        temp = cur["temp_f"] if units == "fahrenheit" else cur["temp_c"]
        result: dict = {
            "api_version": "2.0",
            "source": "WeatherAPI.com (live)",
            "city": loc["name"],
            "region": loc["region"],
            "country": loc["country"],
            "temp": temp,
            "units": units,
            "condition": cur["condition"]["text"],
            "humidity": cur["humidity"],
            "wind_speed_kmh": cur["wind_kph"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if include_forecast and "forecast" in real_data:
            result["forecast"] = [
                {
                    "date": d["date"],
                    "maxtemp": d["day"]["maxtemp_f"] if units == "fahrenheit" else d["day"]["maxtemp_c"],
                    "mintemp": d["day"]["mintemp_f"] if units == "fahrenheit" else d["day"]["mintemp_c"],
                    "condition": d["day"]["condition"]["text"],
                    "chance_of_rain": d["day"].get("daily_chance_of_rain", 0),
                }
                for d in real_data["forecast"]["forecastday"]
            ]
        return json.dumps(result, ensure_ascii=False)

    data = _MOCK_DB.get(city)
    if not data:
        return json.dumps(
            {"city": city, "error": "không có dữ liệu", "api_version": "2.0"},
            ensure_ascii=False,
        )

    temp = data["temp"]
    if units == "fahrenheit":
        temp = round(temp * 9 / 5 + 32, 1)

    result_mock: dict = {
        "api_version": "2.0",
        "source": "mock_db",
        "city": city,
        "temp": temp,
        "units": units,
        "condition": data["condition"],
        "humidity": data["humidity"],
        "wind_speed_kmh": data["wind_speed"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if include_forecast:
        result_mock["forecast"] = data["forecast"]

    return json.dumps(result_mock, ensure_ascii=False)


# ── Resource: server metadata (client dùng để kiểm tra version) ──────
@mcp.resource("server://info")
def server_info() -> str:
    """Metadata của server — version, supported tools, deprecation notices."""
    return json.dumps(
        {
            "name": "weather-v2",
            "version": SERVER_VERSION,
            "deprecated_tools": ["get_weather"],
            "migration_guide": "Chuyển từ get_weather sang get_weather_v2. "
            "Tham số 'city' giữ nguyên, thêm include_forecast và units.",
        },
        ensure_ascii=False,
    )


if __name__ == "__main__":
    mcp.run()

