"""
IAM tools for AWS Infrastructure Copilot.
"""

from datetime import datetime, timezone
from typing import Any

from botocore.exceptions import ClientError

from . import get_client, mcp


@mcp.tool()
def list_iam_users() -> dict[str, Any]:
    """
    List all IAM users in the AWS account.
    Returns user names, creation dates, and password last used dates.
    """
    iam = get_client("iam")

    try:
        paginator = iam.get_paginator("list_users")
        users = []

        for page in paginator.paginate():
            for user in page["Users"]:
                users.append(
                    {
                        "username": user["UserName"],
                        "user_id": user["UserId"],
                        "created": user["CreateDate"].isoformat(),
                        "password_last_used": (
                            user.get("PasswordLastUsed").isoformat()
                            if user.get("PasswordLastUsed")
                            else "Never"
                        ),
                    }
                )

        return {"user_count": len(users), "users": users}

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def list_users_with_stale_credentials(days: int = 90) -> dict[str, Any]:
    """
    Find IAM users with access keys that haven't been rotated in the specified number of days.

    Args:
        days: Number of days to consider credentials stale (default: 90)
    """
    iam = get_client("iam")
    now = datetime.now(timezone.utc)
    stale_users = []

    try:
        paginator = iam.get_paginator("list_users")

        for page in paginator.paginate():
            for user in page["Users"]:
                username = user["UserName"]
                keys_response = iam.list_access_keys(UserName=username)

                for key in keys_response["AccessKeyMetadata"]:
                    key_age = (now - key["CreateDate"]).days

                    if key_age > days:
                        stale_users.append(
                            {
                                "username": username,
                                "access_key_id": key["AccessKeyId"],
                                "key_age_days": key_age,
                                "status": key["Status"],
                                "created": key["CreateDate"].isoformat(),
                            }
                        )

        return {
            "threshold_days": days,
            "stale_credential_count": len(stale_users),
            "users": stale_users,
        }

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def list_users_with_admin_access() -> dict[str, Any]:
    """
    Find IAM users who have AdministratorAccess policy attached directly or through groups.
    """
    iam = get_client("iam")
    admin_users = []
    admin_policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"

    try:
        paginator = iam.get_paginator("list_users")

        for page in paginator.paginate():
            for user in page["Users"]:
                username = user["UserName"]
                has_admin = False
                admin_source = []

                # Check directly attached policies
                attached = iam.list_attached_user_policies(UserName=username)
                for policy in attached["AttachedPolicies"]:
                    if policy["PolicyArn"] == admin_policy_arn:
                        has_admin = True
                        admin_source.append("direct_attachment")

                # Check group memberships
                groups = iam.list_groups_for_user(UserName=username)
                for group in groups["Groups"]:
                    group_policies = iam.list_attached_group_policies(
                        GroupName=group["GroupName"]
                    )
                    for policy in group_policies["AttachedPolicies"]:
                        if policy["PolicyArn"] == admin_policy_arn:
                            has_admin = True
                            admin_source.append(f"group:{group['GroupName']}")

                if has_admin:
                    admin_users.append(
                        {
                            "username": username,
                            "admin_source": admin_source,
                        }
                    )

        return {"admin_user_count": len(admin_users), "users": admin_users}

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def list_iam_roles(path_prefix: str = "/") -> dict[str, Any]:
    """
    List IAM roles, optionally filtered by path prefix.

    Args:
        path_prefix: Filter roles by path (default: "/" for all roles)
    """
    iam = get_client("iam")

    try:
        paginator = iam.get_paginator("list_roles")
        roles = []

        for page in paginator.paginate(PathPrefix=path_prefix):
            for role in page["Roles"]:
                roles.append(
                    {
                        "role_name": role["RoleName"],
                        "role_id": role["RoleId"],
                        "path": role["Path"],
                        "created": role["CreateDate"].isoformat(),
                        "description": role.get("Description", ""),
                    }
                )

        return {"role_count": len(roles), "roles": roles}

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def get_role_trust_policy(role_name: str) -> dict[str, Any]:
    """
    Get the trust policy for a specific IAM role. Shows who/what can assume this role.

    Args:
        role_name: The name of the IAM role
    """
    iam = get_client("iam")

    try:
        response = iam.get_role(RoleName=role_name)
        role = response["Role"]

        return {
            "role_name": role["RoleName"],
            "trust_policy": role["AssumeRolePolicyDocument"],
        }

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def list_access_keys(username: str = None) -> dict[str, Any]:
    """
    List access keys for a specific user or all users.

    Args:
        username: Specific user to check (optional, defaults to all users)
    """
    iam = get_client("iam")
    now = datetime.now(timezone.utc)
    all_keys = []

    try:
        if username:
            users = [{"UserName": username}]
        else:
            paginator = iam.get_paginator("list_users")
            users = []
            for page in paginator.paginate():
                users.extend(page["Users"])

        for user in users:
            uname = user["UserName"]
            keys_response = iam.list_access_keys(UserName=uname)

            for key in keys_response["AccessKeyMetadata"]:
                key_age = (now - key["CreateDate"]).days

                # Get last used info
                last_used_response = iam.get_access_key_last_used(
                    AccessKeyId=key["AccessKeyId"]
                )
                last_used = last_used_response.get("AccessKeyLastUsed", {})

                all_keys.append(
                    {
                        "username": uname,
                        "access_key_id": key["AccessKeyId"],
                        "status": key["Status"],
                        "created": key["CreateDate"].isoformat(),
                        "age_days": key_age,
                        "last_used": (
                            last_used.get("LastUsedDate").isoformat()
                            if last_used.get("LastUsedDate")
                            else "Never"
                        ),
                        "last_used_service": last_used.get("ServiceName", "N/A"),
                    }
                )

        return {"key_count": len(all_keys), "access_keys": all_keys}

    except ClientError as e:
        return {"error": str(e)}
