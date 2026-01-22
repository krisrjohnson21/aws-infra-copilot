"""
AWS Infrastructure Copilot - Shared MCP instance and AWS client helpers.
"""

import boto3
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server (shared across all tool modules)
mcp = FastMCP("aws-infra-copilot")

# AWS clients (initialized lazily)
_clients = {}


def get_client(service_name: str):
    """Get or create an AWS client for the specified service."""
    if service_name not in _clients:
        _clients[service_name] = boto3.client(service_name)
    return _clients[service_name]
