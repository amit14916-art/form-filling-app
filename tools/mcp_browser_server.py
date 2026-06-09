import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from mcp.server.fastmcp import FastMCP
from tools.browser_worker import StealthBrowserWorker

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCPBrowserServer")

# Create FastMCP server
mcp = FastMCP("StealthBrowser")

# Singleton worker instance managed by the server
_global_worker = None

def get_worker():
    global _global_worker
    if _global_worker is None:
        _global_worker = StealthBrowserWorker()
    return _global_worker

@mcp.tool()
async def browser_navigate(url: str) -> str:
    """
    Launches a stealth browser context (if not active) and navigates to the target URL.
    """
    worker = get_worker()
    try:
        page = await worker.init_session()
        # Condition on about:blank or mock urls
        if url and url != "about:blank" and not url.startswith("data:"):
            logger.info(f"[MCPBrowserServer] Navigating to {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_load_state("networkidle")
        else:
            logger.info(f"[MCPBrowserServer] Skipping navigation for URL: {url}")
        
        current_url = page.url
        return f"SUCCESS: Navigated successfully. Current page URL: {current_url}"
    except Exception as e:
        return f"ERROR: Failed navigation: {str(e)}"

@mcp.tool()
async def browser_fill_form(url: str, form_data: dict, task_id: str = None) -> dict:
    """
    Navigates to URL, maps fields, solves captcha if present, handles OTP polling loops up to 60s,
    types data character-by-character with human delays, and runs QA evaluations before submission.
    """
    worker = get_worker()
    from main import orchestrator
    broker = orchestrator.broker if orchestrator else None
    
    try:
        res = await worker.execute_form_fill(
            url=url,
            form_data=form_data,
            qa_agents=orchestrator.qa_agents if orchestrator else [],
            current_step={"action": "fill_form", "inputs": form_data},
            task_id=task_id,
            broker=broker
        )
        return {
            "success": res.get("success", False),
            "confidence": res.get("confidence", 0.0),
            "final_dom": res.get("final_dom", ""),
            "screenshot_len": len(res.get("screenshot_bytes", b""))
        }
    except Exception as e:
        return {"success": False, "error": f"Form execution error: {str(e)}"}

@mcp.tool()
async def browser_close() -> str:
    """
    Closes the active browser and playwright context safely.
    """
    global _global_worker
    if _global_worker is not None:
        try:
            await _global_worker.close_session()
            _global_worker = None
            return "SUCCESS: Browser session closed."
        except Exception as e:
            return f"ERROR: Close error: {str(e)}"
    return "SUCCESS: No active browser session found."

if __name__ == "__main__":
    mcp.run()
