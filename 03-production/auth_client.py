"""MCP Client có Authentication — kết nối tới auth_server.py qua HTTP.

Client truyền bearer token thông qua httpx.AsyncClient. MCP SDK tự gắn
token vào mọi request HTTP (POST, GET, DELETE) tới server.

Cách chạy (cần auth_server.py đang chạy ở terminal khác):
    cd 03-production
    python auth_server.py            # terminal 1
    python auth_client.py            # terminal 2
"""

from __future__ import annotations

import asyncio
import os

from dotenv import find_dotenv, load_dotenv
import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv(find_dotenv())

SERVER_URL = os.getenv("MCP_AUTH_SERVER_URL", f"http://localhost:{os.getenv('AUTH_PORT', '8001')}/mcp")
TOKEN = os.getenv("MCP_AUTH_TOKEN", "dev-token-abc123")



def extract_underlying_exception(exc: BaseException) -> BaseException:
    while hasattr(exc, "exceptions") and getattr(exc, "exceptions", None):
        exc = exc.exceptions[0]
    return exc


async def test_with_token(token: str | None, test_name: str) -> None:
    print(f"\n--- [Test Case] {test_name} ---")
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
        print(f"Gửi header: Authorization: Bearer {token}")
    else:
        print("Không gửi header Authorization (thiếu token)")

    http_client = httpx.AsyncClient(headers=headers)
    try:
        async with http_client:
            async with streamable_http_client(SERVER_URL, http_client=http_client) as streams:
                read, write = streams[0], streams[1]
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    print(f"✅ Kết nối thành công! Danh sách tools ({len(tools.tools)}):")
                    for t in tools.tools:
                        print(f"   - {t.name}: {t.description}")
                    result = await session.call_tool("get_weather", {"city": "Hanoi"})
                    print(f"   -> Kết quả gọi tool: {result.content[0].text}")
    except BaseException as e:
        exc = extract_underlying_exception(e)
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            text = exc.response.text.strip() or "Unauthorized"
            print(f"❌ Server từ chối đúng kỳ vọng! HTTP Status: {status} ({text})")
        else:
            print(f"❌ Chi tiết lỗi: {type(exc).__name__} - {exc}")




async def main() -> None:
    print("==================================================")
    print(f"Kiểm thử MCP Server Authentication tại: {SERVER_URL}")
    print("==================================================")

    # 1. Test với token đúng
    await test_with_token(TOKEN, "1. Token ĐÚNG (Hợp lệ)")

    # 2. Test khi thiếu token
    await test_with_token(None, "2. THIẾU Token (Không có header Authorization)")

    # 3. Test với token sai
    await test_with_token("wrong-invalid-token-999", "3. Token SAI (Không hợp lệ)")


if __name__ == "__main__":
    asyncio.run(main())

