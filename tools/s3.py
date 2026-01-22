"""
S3 tools for AWS Infrastructure Copilot.
"""

from typing import Any

from botocore.exceptions import ClientError

from . import get_client, mcp


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / 1024**2:.2f} MB"
    elif size_bytes < 1024**4:
        return f"{size_bytes / 1024**3:.2f} GB"
    else:
        return f"{size_bytes / 1024**4:.2f} TB"


@mcp.tool()
def list_s3_buckets() -> dict[str, Any]:
    """
    List all S3 buckets in the AWS account with region and creation date.
    """
    s3 = get_client("s3")

    try:
        response = s3.list_buckets()
        buckets = []

        for bucket in response["Buckets"]:
            bucket_name = bucket["Name"]

            # Get bucket region
            try:
                location = s3.get_bucket_location(Bucket=bucket_name)
                region = location["LocationConstraint"] or "us-east-1"
            except ClientError:
                region = "unknown"

            buckets.append(
                {
                    "name": bucket_name,
                    "region": region,
                    "created": bucket["CreationDate"].isoformat(),
                }
            )

        return {"bucket_count": len(buckets), "buckets": buckets}

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def get_bucket_size(bucket_name: str) -> dict[str, Any]:
    """
    Get the total size and object count for an S3 bucket.
    Note: This iterates through all objects, so may be slow for very large buckets.

    Args:
        bucket_name: Name of the S3 bucket
    """
    s3 = get_client("s3")

    try:
        paginator = s3.get_paginator("list_objects_v2")
        total_size = 0
        object_count = 0

        for page in paginator.paginate(Bucket=bucket_name):
            if "Contents" in page:
                for obj in page["Contents"]:
                    total_size += obj["Size"]
                    object_count += 1

        return {
            "bucket": bucket_name,
            "object_count": object_count,
            "total_size_bytes": total_size,
            "total_size_human": _human_readable_size(total_size),
        }

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def check_bucket_public_access(bucket_name: str = None) -> dict[str, Any]:
    """
    Check public access settings for a specific bucket or all buckets.
    Identifies buckets that may be publicly accessible.

    Args:
        bucket_name: Specific bucket to check (optional, defaults to all buckets)
    """
    s3 = get_client("s3")

    try:
        if bucket_name:
            bucket_names = [bucket_name]
        else:
            response = s3.list_buckets()
            bucket_names = [b["Name"] for b in response["Buckets"]]

        results = []

        for name in bucket_names:
            bucket_info = {"bucket": name, "public_access_blocked": True, "issues": []}

            # Check public access block configuration
            try:
                pab = s3.get_public_access_block(Bucket=name)
                config = pab["PublicAccessBlockConfiguration"]

                if not config.get("BlockPublicAcls", False):
                    bucket_info["issues"].append("BlockPublicAcls is disabled")
                    bucket_info["public_access_blocked"] = False
                if not config.get("IgnorePublicAcls", False):
                    bucket_info["issues"].append("IgnorePublicAcls is disabled")
                    bucket_info["public_access_blocked"] = False
                if not config.get("BlockPublicPolicy", False):
                    bucket_info["issues"].append("BlockPublicPolicy is disabled")
                    bucket_info["public_access_blocked"] = False
                if not config.get("RestrictPublicBuckets", False):
                    bucket_info["issues"].append("RestrictPublicBuckets is disabled")
                    bucket_info["public_access_blocked"] = False

            except ClientError as e:
                if "NoSuchPublicAccessBlockConfiguration" in str(e):
                    bucket_info["issues"].append("No public access block configured")
                    bucket_info["public_access_blocked"] = False
                else:
                    bucket_info["issues"].append(f"Error checking: {str(e)}")

            results.append(bucket_info)

        # Summary
        public_buckets = [r for r in results if not r["public_access_blocked"]]

        return {
            "buckets_checked": len(results),
            "potentially_public_count": len(public_buckets),
            "buckets": results,
        }

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def find_object(object_name: str, exact_match: bool = False) -> dict[str, Any]:
    """
    Search across all S3 buckets to find which bucket(s) contain an object.
    Can search by exact name or partial match.

    Args:
        object_name: The object key/name to search for
        exact_match: If True, only match exact object keys. If False, match objects containing the search term.
    """
    s3 = get_client("s3")

    try:
        response = s3.list_buckets()
        bucket_names = [b["Name"] for b in response["Buckets"]]

        matches = []
        buckets_searched = 0
        buckets_with_errors = []

        for bucket_name in bucket_names:
            buckets_searched += 1

            try:
                paginator = s3.get_paginator("list_objects_v2")

                for page in paginator.paginate(Bucket=bucket_name):
                    if "Contents" not in page:
                        continue

                    for obj in page["Contents"]:
                        key = obj["Key"]

                        if exact_match:
                            is_match = key == object_name
                        else:
                            is_match = object_name.lower() in key.lower()

                        if is_match:
                            matches.append(
                                {
                                    "bucket": bucket_name,
                                    "key": key,
                                    "size": _human_readable_size(obj["Size"]),
                                    "last_modified": obj["LastModified"].isoformat(),
                                }
                            )

                            # Limit results to prevent overwhelming output
                            if len(matches) >= 50:
                                return {
                                    "search_term": object_name,
                                    "exact_match": exact_match,
                                    "match_count": len(matches),
                                    "truncated": True,
                                    "message": "Results limited to 50 matches",
                                    "buckets_searched": buckets_searched,
                                    "matches": matches,
                                }

            except ClientError as e:
                buckets_with_errors.append({"bucket": bucket_name, "error": str(e)})

        return {
            "search_term": object_name,
            "exact_match": exact_match,
            "match_count": len(matches),
            "truncated": False,
            "buckets_searched": buckets_searched,
            "buckets_with_errors": buckets_with_errors if buckets_with_errors else None,
            "matches": matches,
        }

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def get_bucket_encryption(bucket_name: str = None) -> dict[str, Any]:
    """
    Check encryption configuration for a specific bucket or all buckets.

    Args:
        bucket_name: Specific bucket to check (optional, defaults to all buckets)
    """
    s3 = get_client("s3")

    try:
        if bucket_name:
            bucket_names = [bucket_name]
        else:
            response = s3.list_buckets()
            bucket_names = [b["Name"] for b in response["Buckets"]]

        results = []

        for name in bucket_names:
            bucket_info = {"bucket": name, "encryption_enabled": False, "encryption_type": None}

            try:
                encryption = s3.get_bucket_encryption(Bucket=name)
                rules = encryption.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])

                if rules:
                    bucket_info["encryption_enabled"] = True
                    sse = rules[0].get("ApplyServerSideEncryptionByDefault", {})
                    bucket_info["encryption_type"] = sse.get("SSEAlgorithm", "Unknown")
                    if sse.get("KMSMasterKeyID"):
                        bucket_info["kms_key_id"] = sse["KMSMasterKeyID"]

            except ClientError as e:
                if "ServerSideEncryptionConfigurationNotFoundError" in str(e):
                    bucket_info["encryption_enabled"] = False
                    bucket_info["encryption_type"] = "None"
                else:
                    bucket_info["error"] = str(e)

            results.append(bucket_info)

        # Summary
        encrypted_count = sum(1 for r in results if r["encryption_enabled"])
        unencrypted = [r["bucket"] for r in results if not r["encryption_enabled"] and "error" not in r]

        return {
            "buckets_checked": len(results),
            "encrypted_count": encrypted_count,
            "unencrypted_count": len(unencrypted),
            "unencrypted_buckets": unencrypted if unencrypted else None,
            "buckets": results,
        }

    except ClientError as e:
        return {"error": str(e)}
