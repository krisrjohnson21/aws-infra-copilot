"""
Lambda tools for AWS Infrastructure Copilot.
"""

from typing import Any

from botocore.exceptions import ClientError

from . import get_client, mcp

# Deprecated/EOL runtimes as of 2025
# Update this list as AWS deprecates more runtimes
# Source: https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
DEPRECATED_RUNTIMES = {
    "python2.7": "Deprecated since July 2022",
    "python3.6": "Deprecated since July 2022",
    "python3.7": "Deprecated since December 2023",
    "nodejs": "Deprecated (legacy)",
    "nodejs4.3": "Deprecated since April 2020",
    "nodejs4.3-edge": "Deprecated since April 2020",
    "nodejs6.10": "Deprecated since August 2019",
    "nodejs8.10": "Deprecated since March 2020",
    "nodejs10.x": "Deprecated since July 2021",
    "nodejs12.x": "Deprecated since March 2023",
    "nodejs14.x": "Deprecated since December 2023",
    "nodejs16.x": "Deprecated since June 2024",
    "ruby2.5": "Deprecated since July 2021",
    "ruby2.7": "Deprecated since December 2023",
    "java8": "Deprecated (Amazon Linux 1) - use java8.al2",
    "dotnetcore1.0": "Deprecated since July 2019",
    "dotnetcore2.0": "Deprecated since May 2019",
    "dotnetcore2.1": "Deprecated since January 2022",
    "dotnetcore3.1": "Deprecated since April 2023",
    "dotnet5.0": "Deprecated since May 2022",
    "dotnet6": "Deprecated since November 2024",
    "go1.x": "Deprecated since January 2024 - use provided.al2",
}

# Runtimes approaching EOL (warn about these)
APPROACHING_EOL_RUNTIMES = {
    "nodejs18.x": "EOL expected 2025",
    "python3.8": "EOL expected 2025",
    "python3.9": "EOL expected 2026",
    "java11": "EOL expected 2025",
    "dotnet7": "EOL expected 2025",
}


@mcp.tool()
def list_lambda_functions(region: str = None) -> dict[str, Any]:
    """
    List all Lambda functions with runtime, memory, timeout, and last modified info.

    Args:
        region: AWS region (optional, uses default if not specified)
    """
    lambda_client = get_client("lambda") if not region else __import__("boto3").client("lambda", region_name=region)

    try:
        paginator = lambda_client.get_paginator("list_functions")
        functions = []

        for page in paginator.paginate():
            for func in page["Functions"]:
                runtime = func.get("Runtime", "N/A (container or custom)")
                
                # Check deprecation status
                deprecation_status = None
                if runtime in DEPRECATED_RUNTIMES:
                    deprecation_status = "DEPRECATED"
                elif runtime in APPROACHING_EOL_RUNTIMES:
                    deprecation_status = "APPROACHING_EOL"

                functions.append(
                    {
                        "name": func["FunctionName"],
                        "runtime": runtime,
                        "deprecation_status": deprecation_status,
                        "memory_mb": func.get("MemorySize"),
                        "timeout_seconds": func.get("Timeout"),
                        "code_size_mb": round(func.get("CodeSize", 0) / (1024 * 1024), 2),
                        "last_modified": func.get("LastModified"),
                        "description": func.get("Description", ""),
                    }
                )

        # Sort by deprecation status (deprecated first), then name
        functions.sort(key=lambda x: (x["deprecation_status"] is None, x["name"]))

        return {
            "function_count": len(functions),
            "functions": functions,
        }

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def find_deprecated_runtimes(include_approaching_eol: bool = True) -> dict[str, Any]:
    """
    Find all Lambda functions using deprecated or end-of-life runtimes.
    
    Args:
        include_approaching_eol: Also include runtimes approaching end-of-life (default: True)
    """
    lambda_client = get_client("lambda")

    try:
        paginator = lambda_client.get_paginator("list_functions")
        deprecated_functions = []
        approaching_eol_functions = []
        total_functions = 0

        for page in paginator.paginate():
            for func in page["Functions"]:
                total_functions += 1
                runtime = func.get("Runtime", "")
                
                if runtime in DEPRECATED_RUNTIMES:
                    deprecated_functions.append(
                        {
                            "name": func["FunctionName"],
                            "runtime": runtime,
                            "reason": DEPRECATED_RUNTIMES[runtime],
                            "last_modified": func.get("LastModified"),
                        }
                    )
                elif include_approaching_eol and runtime in APPROACHING_EOL_RUNTIMES:
                    approaching_eol_functions.append(
                        {
                            "name": func["FunctionName"],
                            "runtime": runtime,
                            "reason": APPROACHING_EOL_RUNTIMES[runtime],
                            "last_modified": func.get("LastModified"),
                        }
                    )

        result = {
            "total_functions_scanned": total_functions,
            "deprecated_count": len(deprecated_functions),
            "deprecated_functions": deprecated_functions,
        }

        if include_approaching_eol:
            result["approaching_eol_count"] = len(approaching_eol_functions)
            result["approaching_eol_functions"] = approaching_eol_functions

        # Summary by runtime
        runtime_summary = {}
        for func in deprecated_functions:
            rt = func["runtime"]
            runtime_summary[rt] = runtime_summary.get(rt, 0) + 1
        
        if runtime_summary:
            result["deprecated_runtime_summary"] = runtime_summary

        return result

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def get_lambda_function(function_name: str) -> dict[str, Any]:
    """
    Get detailed information about a specific Lambda function.

    Args:
        function_name: Name or ARN of the Lambda function
    """
    lambda_client = get_client("lambda")

    try:
        # Get function configuration
        config = lambda_client.get_function(FunctionName=function_name)
        func = config["Configuration"]
        
        runtime = func.get("Runtime", "N/A (container or custom)")
        
        # Check deprecation status
        deprecation_info = None
        if runtime in DEPRECATED_RUNTIMES:
            deprecation_info = {
                "status": "DEPRECATED",
                "message": DEPRECATED_RUNTIMES[runtime],
                "action_required": "Upgrade to a supported runtime immediately",
            }
        elif runtime in APPROACHING_EOL_RUNTIMES:
            deprecation_info = {
                "status": "APPROACHING_EOL",
                "message": APPROACHING_EOL_RUNTIMES[runtime],
                "action_required": "Plan upgrade to newer runtime",
            }

        # Get tags
        tags = config.get("Tags", {})

        # Get environment variables (names only for security)
        env_vars = list(func.get("Environment", {}).get("Variables", {}).keys())

        result = {
            "name": func["FunctionName"],
            "arn": func["FunctionArn"],
            "runtime": runtime,
            "deprecation_info": deprecation_info,
            "handler": func.get("Handler"),
            "role": func.get("Role", "").split("/")[-1],
            "memory_mb": func.get("MemorySize"),
            "timeout_seconds": func.get("Timeout"),
            "code_size_mb": round(func.get("CodeSize", 0) / (1024 * 1024), 2),
            "last_modified": func.get("LastModified"),
            "description": func.get("Description", ""),
            "state": func.get("State"),
            "architectures": func.get("Architectures", ["x86_64"]),
            "environment_variables": env_vars if env_vars else None,
            "vpc_config": func.get("VpcConfig", {}).get("VpcId"),
            "layers": [layer["Arn"].split(":")[-2] for layer in func.get("Layers", [])],
            "tags": tags if tags else None,
        }

        return result

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def list_lambda_runtimes() -> dict[str, Any]:
    """
    List all known Lambda runtimes with their deprecation status.
    Useful for understanding which runtimes are safe to use.
    """
    supported = [
        "python3.13", "python3.12", "python3.11", "python3.10",
        "nodejs22.x", "nodejs20.x",
        "java21", "java17",
        "ruby3.3", "ruby3.2",
        "dotnet8",
        "provided.al2023", "provided.al2",
    ]

    return {
        "supported_runtimes": supported,
        "approaching_eol": {rt: reason for rt, reason in APPROACHING_EOL_RUNTIMES.items()},
        "deprecated_runtimes": {rt: reason for rt, reason in DEPRECATED_RUNTIMES.items()},
        "recommendation": "Use the latest supported runtime for your language. Prefer Amazon Linux 2023 (al2023) based runtimes.",
    }
