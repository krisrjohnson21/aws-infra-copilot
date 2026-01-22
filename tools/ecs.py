"""
ECS tools for AWS Infrastructure Copilot.
"""

from datetime import datetime, timezone, timedelta
from typing import Any

from botocore.exceptions import ClientError

from . import get_client, mcp


@mcp.tool()
def list_ecs_clusters() -> dict[str, Any]:
    """
    List all ECS clusters in the AWS account.
    """
    ecs = get_client("ecs")

    try:
        cluster_arns = []
        paginator = ecs.get_paginator("list_clusters")

        for page in paginator.paginate():
            cluster_arns.extend(page["clusterArns"])

        if not cluster_arns:
            return {"cluster_count": 0, "clusters": []}

        # Get cluster details
        clusters_response = ecs.describe_clusters(clusters=cluster_arns)
        clusters = []

        for cluster in clusters_response["clusters"]:
            clusters.append(
                {
                    "name": cluster["clusterName"],
                    "status": cluster["status"],
                    "running_tasks": cluster["runningTasksCount"],
                    "pending_tasks": cluster["pendingTasksCount"],
                    "active_services": cluster["activeServicesCount"],
                    "registered_instances": cluster["registeredContainerInstancesCount"],
                }
            )

        return {"cluster_count": len(clusters), "clusters": clusters}

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def list_ecs_services(cluster_name: str) -> dict[str, Any]:
    """
    List all services in an ECS cluster.

    Args:
        cluster_name: Name of the ECS cluster
    """
    ecs = get_client("ecs")

    try:
        service_arns = []
        paginator = ecs.get_paginator("list_services")

        for page in paginator.paginate(cluster=cluster_name):
            service_arns.extend(page["serviceArns"])

        if not service_arns:
            return {"cluster": cluster_name, "service_count": 0, "services": []}

        # Get service details (API allows max 10 at a time)
        services = []
        for i in range(0, len(service_arns), 10):
            batch = service_arns[i : i + 10]
            services_response = ecs.describe_services(
                cluster=cluster_name, services=batch
            )

            for service in services_response["services"]:
                services.append(
                    {
                        "name": service["serviceName"],
                        "status": service["status"],
                        "desired_count": service["desiredCount"],
                        "running_count": service["runningCount"],
                        "pending_count": service["pendingCount"],
                        "launch_type": service.get("launchType", "EC2"),
                        "task_definition": service["taskDefinition"].split("/")[-1],
                    }
                )

        return {"cluster": cluster_name, "service_count": len(services), "services": services}

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def get_ecs_service_status(cluster_name: str, service_name: str) -> dict[str, Any]:
    """
    Get detailed status of a specific ECS service including recent deployments.

    Args:
        cluster_name: Name of the ECS cluster
        service_name: Name of the service
    """
    ecs = get_client("ecs")

    try:
        response = ecs.describe_services(cluster=cluster_name, services=[service_name])

        if not response["services"]:
            return {"error": f"Service '{service_name}' not found in cluster '{cluster_name}'"}

        service = response["services"][0]

        # Format deployments
        deployments = []
        for dep in service.get("deployments", []):
            deployments.append(
                {
                    "id": dep["id"],
                    "status": dep["status"],
                    "desired_count": dep["desiredCount"],
                    "running_count": dep["runningCount"],
                    "pending_count": dep["pendingCount"],
                    "created": dep["createdAt"].isoformat(),
                    "task_definition": dep["taskDefinition"].split("/")[-1],
                }
            )

        # Format recent events (last 5)
        events = []
        for event in service.get("events", [])[:5]:
            events.append(
                {
                    "timestamp": event["createdAt"].isoformat(),
                    "message": event["message"],
                }
            )

        return {
            "cluster": cluster_name,
            "service_name": service["serviceName"],
            "status": service["status"],
            "desired_count": service["desiredCount"],
            "running_count": service["runningCount"],
            "pending_count": service["pendingCount"],
            "launch_type": service.get("launchType", "EC2"),
            "task_definition": service["taskDefinition"].split("/")[-1],
            "deployments": deployments,
            "recent_events": events,
        }

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def list_ecs_tasks(cluster_name: str, service_name: str = None) -> dict[str, Any]:
    """
    List running tasks in a cluster, optionally filtered by service.

    Args:
        cluster_name: Name of the ECS cluster
        service_name: Filter by service name (optional)
    """
    ecs = get_client("ecs")

    try:
        list_params = {"cluster": cluster_name, "desiredStatus": "RUNNING"}
        if service_name:
            list_params["serviceName"] = service_name

        task_arns = []
        paginator = ecs.get_paginator("list_tasks")

        for page in paginator.paginate(**list_params):
            task_arns.extend(page["taskArns"])

        if not task_arns:
            return {"cluster": cluster_name, "task_count": 0, "tasks": []}

        # Get task details (API allows max 100 at a time)
        tasks = []
        for i in range(0, len(task_arns), 100):
            batch = task_arns[i : i + 100]
            tasks_response = ecs.describe_tasks(cluster=cluster_name, tasks=batch)

            for task in tasks_response["tasks"]:
                tasks.append(
                    {
                        "task_id": task["taskArn"].split("/")[-1],
                        "task_definition": task["taskDefinitionArn"].split("/")[-1],
                        "status": task["lastStatus"],
                        "health_status": task.get("healthStatus", "UNKNOWN"),
                        "launch_type": task.get("launchType", "EC2"),
                        "cpu": task.get("cpu", "N/A"),
                        "memory": task.get("memory", "N/A"),
                        "started_at": (
                            task["startedAt"].isoformat()
                            if task.get("startedAt")
                            else "Not started"
                        ),
                    }
                )

        return {"cluster": cluster_name, "task_count": len(tasks), "tasks": tasks}

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def describe_task_definition(task_definition: str) -> dict[str, Any]:
    """
    Get details of an ECS task definition including container images, CPU, and memory.

    Args:
        task_definition: Task definition name or ARN (e.g., "my-task:1" or just "my-task" for latest)
    """
    ecs = get_client("ecs")

    try:
        response = ecs.describe_task_definition(taskDefinition=task_definition)
        task_def = response["taskDefinition"]

        containers = []
        for container in task_def["containerDefinitions"]:
            containers.append(
                {
                    "name": container["name"],
                    "image": container["image"],
                    "cpu": container.get("cpu", "N/A"),
                    "memory": container.get("memory", "N/A"),
                    "memory_reservation": container.get("memoryReservation", "N/A"),
                    "essential": container.get("essential", True),
                    "port_mappings": container.get("portMappings", []),
                }
            )

        return {
            "family": task_def["family"],
            "revision": task_def["revision"],
            "status": task_def["status"],
            "task_role": task_def.get("taskRoleArn", "None").split("/")[-1],
            "execution_role": task_def.get("executionRoleArn", "None").split("/")[-1],
            "network_mode": task_def.get("networkMode", "bridge"),
            "cpu": task_def.get("cpu", "N/A"),
            "memory": task_def.get("memory", "N/A"),
            "containers": containers,
        }

    except ClientError as e:
        return {"error": str(e)}


@mcp.tool()
def list_fargate_retirements(days: int = 14) -> dict[str, Any]:
    """
    Find Fargate tasks scheduled for retirement due to AWS maintenance.
    Requires AWS Business or Enterprise support plan for Health API access.

    Args:
        days: Number of days to look ahead (default: 14)
    """
    try:
        # Health API must be called in us-east-1
        import boto3
        health = boto3.client("health", region_name="us-east-1")
    except Exception as e:
        return {"error": f"Failed to create Health client: {str(e)}"}

    now = datetime.now(timezone.utc)
    end_time = now + timedelta(days=days)

    try:
        # Query for ECS-related scheduled maintenance events
        event_filter = {
            "services": ["ECS"],
            "eventTypeCategories": ["scheduledChange"],
            "eventStatusCodes": ["open", "upcoming"],
        }

        events = []
        paginator = health.get_paginator("describe_events")

        for page in paginator.paginate(filter=event_filter):
            for event in page["events"]:
                # Check if event is within our time window
                event_start = event.get("startTime")
                if event_start and event_start <= end_time:
                    events.append(event)

        if not events:
            return {
                "days_checked": days,
                "retirement_count": 0,
                "message": "No Fargate task retirements scheduled in the specified time window",
                "retirements": [],
            }

        # Get affected entities for each event
        retirements = []
        for event in events:
            event_arn = event["arn"]
            
            try:
                affected = health.describe_affected_entities(
                    filter={"eventArns": [event_arn]}
                )
                
                for entity in affected.get("entities", []):
                    entity_value = entity.get("entityValue", "")
                    
                    # Filter for Fargate tasks (task ARNs contain "/task/")
                    if "/task/" in entity_value or "fargate" in event.get("eventTypeCode", "").lower():
                        retirements.append(
                            {
                                "task_arn": entity_value,
                                "event_type": event.get("eventTypeCode"),
                                "status": entity.get("statusCode"),
                                "scheduled_start": event.get("startTime").isoformat() if event.get("startTime") else None,
                                "scheduled_end": event.get("endTime").isoformat() if event.get("endTime") else None,
                                "description": event.get("eventTypeCode", "").replace("_", " ").title(),
                            }
                        )
            except ClientError as e:
                # Continue if we can't get details for a specific event
                continue

        # Group by cluster for easier reading
        by_cluster = {}
        for ret in retirements:
            # Extract cluster from task ARN
            # Format: arn:aws:ecs:region:account:task/cluster-name/task-id
            arn_parts = ret["task_arn"].split("/")
            cluster = arn_parts[1] if len(arn_parts) > 1 else "unknown"
            
            if cluster not in by_cluster:
                by_cluster[cluster] = []
            by_cluster[cluster].append(ret)

        return {
            "days_checked": days,
            "retirement_count": len(retirements),
            "retirements_by_cluster": by_cluster,
            "retirements": retirements,
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "SubscriptionRequiredException":
            return {
                "error": "AWS Health API requires Business or Enterprise support plan",
                "suggestion": "Upgrade your AWS support plan or check the AWS Health Dashboard in the console manually",
            }
        return {"error": str(e)}
