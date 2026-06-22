import asyncio
import os
import sys
import logging
from typing import Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("SwarmMCPClient")

class SwarmMCPClient:
    """
    Client manager that launches local MCP servers and routes tool requests.
    Supports connecting to any local MCP Server.
    """
    def __init__(self, server_script: str = "mcp_browser_server.py"):
        workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = os.environ.copy()
        env["PYTHONPATH"] = workspace_root + os.pathsep + env.get("PYTHONPATH", "")
        
        self.server_params = StdioServerParameters(
            command=sys.executable,
            args=[os.path.join(os.path.dirname(__file__), server_script)],
            env=env
        )
        self.stdio_transport = None
        self.read_stream = None
        self.write_stream = None
        self.session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        logger.info("Connecting to MCP Browser Server subprocess...")
        self.stdio_transport = stdio_client(self.server_params)
        self.read_stream, self.write_stream = await self.stdio_transport.__aenter__()
        self.session = ClientSession(self.read_stream, self.write_stream)
        await self.session.__aenter__()
        # Handshake initialization
        await self.session.initialize()
        logger.info("MCP Browser Server initialized successfully.")

    async def disconnect(self):
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
        if self.stdio_transport:
            await self.stdio_transport.__aexit__(None, None, None)
            self.stdio_transport = None
        logger.info("MCP Browser Server disconnected.")

    async def call_tool(self, name: str, arguments: dict):
        if not self.session:
            await self.connect()
        res = await self.session.call_tool(name, arguments)
        return res
