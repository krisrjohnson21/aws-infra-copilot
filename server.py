"""
AWS Infrastructure Copilot - MCP Server
Query IAM, ECS, and S3 resources conversationally through Claude.
"""

# Import tools to register them with the MCP server
from tools import mcp
from tools import iam  # noqa: F401
from tools import ecs  # noqa: F401
from tools import s3  # noqa: F401
from tools import lambda_tools  # noqa: F401

if __name__ == "__main__":
    mcp.run()
