"""
Python Execution Tools for Unreal MCP.

This module provides tools for executing Python scripts directly in Unreal Engine.
"""

import logging
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_python_tools(mcp: FastMCP):
    """Register Python execution tools with the MCP server."""

    @mcp.tool()
    def execute_python(ctx: Context, code: str) -> Dict[str, Any]:
        """
        Execute Python code directly in Unreal Engine.

        The code runs inside the UE editor with access to the `unreal` Python module.
        Output (stdout/stderr) is captured and returned.

        Args:
            code: Python code string to execute

        Returns:
            Dict containing success status and captured output
        """
        from unreal_mcp_server import get_unreal_connection

        try:
            unreal = get_unreal_connection()
            if not unreal:
                logger.error("Failed to connect to Unreal Engine")
                return {
                    "success": False,
                    "message": "Failed to connect to Unreal Engine",
                }

            logger.info(f"Executing Python code ({len(code)} chars)")
            response = unreal.send_command("execute_python", {"code": code})

            if not response:
                logger.error("No response from Unreal Engine")
                return {"success": False, "message": "No response from Unreal Engine"}

            return response

        except Exception as e:
            error_msg = f"Error executing Python: {e}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

    @mcp.tool()
    def execute_python_file(ctx: Context, file_path: str) -> Dict[str, Any]:
        """
        Execute a Python script file in Unreal Engine.

        The script runs inside the UE editor with access to the `unreal` Python module.

        Args:
            file_path: Absolute path to the Python file to execute

        Returns:
            Dict containing success status and captured output
        """
        from unreal_mcp_server import get_unreal_connection

        try:
            unreal = get_unreal_connection()
            if not unreal:
                logger.error("Failed to connect to Unreal Engine")
                return {
                    "success": False,
                    "message": "Failed to connect to Unreal Engine",
                }

            logger.info(f"Executing Python file: {file_path}")
            response = unreal.send_command(
                "execute_python_file", {"file_path": file_path}
            )

            if not response:
                logger.error("No response from Unreal Engine")
                return {"success": False, "message": "No response from Unreal Engine"}

            return response

        except Exception as e:
            error_msg = f"Error executing Python file: {e}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

    logger.info("Python execution tools registered successfully")
