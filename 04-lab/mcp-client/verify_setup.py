#!/usr/bin/env python3
"""
Verification script for Weather Agent setup
Checks if all components are configured correctly
"""
import os
import sys
from pathlib import Path

def check_environment():
    """Check if .env file exists and is configured"""
    print("🔍 Checking environment configuration...")
    
    from dotenv import find_dotenv, load_dotenv
    dotenv_path = find_dotenv()
    if not dotenv_path:
        print("❌ .env file not found")
        print("   Create .env at project root or cwd with GOOGLE_API_KEY / GEMINI_API_KEY")
        return False
    
    load_dotenv(dotenv_path)
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key or api_key in ["your_google_api_key_here", "your_gemini_api_key_here"]:
        print("❌ GOOGLE_API_KEY / GEMINI_API_KEY not configured in .env")
        print("   Get key from: https://aistudio.google.com/apikey")
        return False
    
    # Ensure GOOGLE_API_KEY is in environment for ADK
    os.environ["GOOGLE_API_KEY"] = api_key
    print(f"✅ Google/Gemini API key configured ({api_key[:10]}...)")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        ("google.adk", "Google ADK"),
        ("google.generativeai", "Google Generative AI"),
        ("mcp", "MCP"),
        ("fastmcp", "FastMCP"),
        ("dotenv", "python-dotenv"),
        ("httpx", "httpx"),
    ]
    
    all_installed = True
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} not installed")
            all_installed = False
    
    if not all_installed:
        print("\n   Install with: uv sync")
        print("   Or: pip install google-adk google-generativeai mcp fastmcp python-dotenv httpx")
    
    return all_installed

def check_agent_structure():
    """Check if agent directory structure is correct"""
    print("\n🔍 Checking agent structure...")
    
    script_dir = Path(__file__).parent
    required_files = [
        script_dir / "weather_agent/agent.py",
        script_dir / "weather_agent/__init__.py",
    ]
    
    all_exist = True
    for path in required_files:
        if path.exists():
            print(f"✅ {path.name}")
        else:
            print(f"❌ {path} not found")
            all_exist = False
    
    return all_exist

def check_mcp_server():
    """Check if MCP server is accessible"""
    print("\n🔍 Checking MCP server connectivity...")
    
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")
    
    try:
        import httpx
        import asyncio
        
        async def test_connection():
            headers = {"Accept": "text/event-stream, application/json, text/plain, */*"}
            async with httpx.AsyncClient(headers=headers) as client:
                response = await client.get(server_url, timeout=10.0)
                return response.status_code
        
        status_code = asyncio.run(test_connection())
        
        if status_code in [200, 400, 404, 405, 406]:  # FastMCP streamable-http endpoints return 200/400/404/405/406 on GET probe
            print(f"✅ MCP server reachable at {server_url} (HTTP {status_code})")
            return True
        else:
            print(f"⚠️  MCP server returned unexpected status {status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Cannot reach MCP server ({server_url}): {e}")
        print("   Make sure the MCP server is running (e.g. `cd 04-lab/mcp-server && uv run python weather.py`)")
        return False

def check_agent_import():
    """Try to import the agent"""
    print("\n🔍 Checking agent import...")
    
    try:
        # Suppress warnings during import
        import warnings
        warnings.filterwarnings("ignore")
        
        from weather_agent import root_agent
        print(f"✅ Agent imported successfully: {root_agent.name}")
        print(f"   Model: {root_agent.model}")
        return True
    except Exception as e:
        print(f"❌ Failed to import agent: {e}")
        return False

def main():
    """Run all verification checks"""
    print("=" * 60)
    print("Weather Agent Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        check_environment(),
        check_dependencies(),
        check_agent_structure(),
        check_mcp_server(),
        check_agent_import(),
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✅ All checks passed!")
        print("\n🚀 Ready to start!")
        print("   Run: ./start_agent.sh")
        print("   Or:  uv run adk web")
        print("\n📍 Then open: http://localhost:8000")
        return 0
    else:
        print("❌ Some checks failed")
        print("\n⚠️  Fix the issues above and run this script again")
        return 1

if __name__ == "__main__":
    sys.exit(main())

