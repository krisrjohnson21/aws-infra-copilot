"""
Quick test script to verify AWS connectivity and tool functions work.
Run this directly: python test_tools.py
"""

import json


def print_result(name: str, result: dict):
    """Pretty print a tool result."""
    print(f"\n{'='*60}")
    print(f"✓ {name}")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))


def main():
    print("Testing AWS Infrastructure Copilot Tools")
    print("=" * 60)

    # Test AWS credentials first
    print("\n1. Testing AWS credentials...")
    try:
        import boto3

        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        print(f"   ✓ Connected as: {identity['Arn']}")
        print(f"   ✓ Account: {identity['Account']}")
    except Exception as e:
        print(f"   ✗ AWS credential error: {e}")
        print("   Make sure your AWS credentials are configured.")
        print("   Run: aws configure")
        return

    # Import our tools from the new module structure
    from tools.iam import (
        list_iam_users,
        list_users_with_stale_credentials,
        list_users_with_admin_access,
    )
    from tools.ecs import list_ecs_clusters
    from tools.s3 import (
        list_s3_buckets,
        check_bucket_public_access,
        get_bucket_encryption,
    )

    # Test IAM tools
    print("\n2. Testing IAM tools...")

    try:
        result = list_iam_users()
        if "error" in result:
            print(f"   ✗ list_iam_users error: {result['error']}")
        else:
            print(f"   ✓ list_iam_users: Found {result['user_count']} users")
    except Exception as e:
        print(f"   ✗ list_iam_users exception: {e}")

    try:
        result = list_users_with_stale_credentials(days=90)
        if "error" in result:
            print(f"   ✗ list_users_with_stale_credentials error: {result['error']}")
        else:
            print(f"   ✓ list_users_with_stale_credentials: Found {result['stale_credential_count']} stale credentials")
    except Exception as e:
        print(f"   ✗ list_users_with_stale_credentials exception: {e}")

    try:
        result = list_users_with_admin_access()
        if "error" in result:
            print(f"   ✗ list_users_with_admin_access error: {result['error']}")
        else:
            print(f"   ✓ list_users_with_admin_access: Found {result['admin_user_count']} admin users")
    except Exception as e:
        print(f"   ✗ list_users_with_admin_access exception: {e}")

    # Test ECS tools
    print("\n3. Testing ECS tools...")

    try:
        result = list_ecs_clusters()
        if "error" in result:
            print(f"   ✗ list_ecs_clusters error: {result['error']}")
        else:
            print(f"   ✓ list_ecs_clusters: Found {result['cluster_count']} clusters")
            if result["clusters"]:
                for cluster in result["clusters"]:
                    print(f"      - {cluster['name']} ({cluster['running_tasks']} running tasks)")
    except Exception as e:
        print(f"   ✗ list_ecs_clusters exception: {e}")

    # Test S3 tools
    print("\n4. Testing S3 tools...")

    try:
        result = list_s3_buckets()
        if "error" in result:
            print(f"   ✗ list_s3_buckets error: {result['error']}")
        else:
            print(f"   ✓ list_s3_buckets: Found {result['bucket_count']} buckets")
            if result["buckets"]:
                for bucket in result["buckets"][:5]:  # Show first 5
                    print(f"      - {bucket['name']} ({bucket['region']})")
                if len(result["buckets"]) > 5:
                    print(f"      ... and {len(result['buckets']) - 5} more")
    except Exception as e:
        print(f"   ✗ list_s3_buckets exception: {e}")

    try:
        result = check_bucket_public_access()
        if "error" in result:
            print(f"   ✗ check_bucket_public_access error: {result['error']}")
        else:
            print(f"   ✓ check_bucket_public_access: {result['potentially_public_count']} potentially public buckets")
    except Exception as e:
        print(f"   ✗ check_bucket_public_access exception: {e}")

    try:
        result = get_bucket_encryption()
        if "error" in result:
            print(f"   ✗ get_bucket_encryption error: {result['error']}")
        else:
            print(f"   ✓ get_bucket_encryption: {result['encrypted_count']}/{result['buckets_checked']} buckets encrypted")
    except Exception as e:
        print(f"   ✗ get_bucket_encryption exception: {e}")

    # Test Lambda tools
    print("\n5. Testing Lambda tools...")

    from tools.lambda_tools import (
        list_lambda_functions,
        find_deprecated_runtimes,
    )

    try:
        result = list_lambda_functions()
        if "error" in result:
            print(f"   ✗ list_lambda_functions error: {result['error']}")
        else:
            print(f"   ✓ list_lambda_functions: Found {result['function_count']} functions")
            deprecated = [f for f in result["functions"] if f.get("deprecation_status") == "DEPRECATED"]
            approaching_eol = [f for f in result["functions"] if f.get("deprecation_status") == "APPROACHING_EOL"]
            if deprecated:
                print(f"      ⚠ {len(deprecated)} using deprecated runtimes:")
                for f in deprecated:
                    print(f"         - {f['name']} ({f['runtime']})")
            if approaching_eol:
                print(f"      ⚠ {len(approaching_eol)} approaching EOL:")
                for f in approaching_eol:
                    print(f"         - {f['name']} ({f['runtime']})")
    except Exception as e:
        print(f"   ✗ list_lambda_functions exception: {e}")

    try:
        result = find_deprecated_runtimes()
        if "error" in result:
            print(f"   ✗ find_deprecated_runtimes error: {result['error']}")
        else:
            print(f"   ✓ find_deprecated_runtimes: {result['deprecated_count']} deprecated, {result.get('approaching_eol_count', 0)} approaching EOL")
            if result.get("deprecated_functions"):
                print("      Deprecated:")
                for f in result["deprecated_functions"]:
                    print(f"         - {f['name']} ({f['runtime']}): {f['reason']}")
            if result.get("approaching_eol_functions"):
                print("      Approaching EOL:")
                for f in result["approaching_eol_functions"]:
                    print(f"         - {f['name']} ({f['runtime']}): {f['reason']}")
    except Exception as e:
        print(f"   ✗ find_deprecated_runtimes exception: {e}")

    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)
    print("\nIf all tests passed, your MCP server should work with Claude Desktop.")
    print("See README.md for Claude Desktop configuration instructions.")


if __name__ == "__main__":
    main()
