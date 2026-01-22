# AWS Infrastructure Copilot

An MCP server that lets you query AWS IAM and ECS resources conversationally through Claude.

## Features

**IAM Tools**
- List IAM users
- Find users with stale credentials
- List roles and trust policies
- Check admin access
- List access keys and age

**ECS Tools**
- List clusters
- List services in a cluster
- Get service status
- List running tasks
- Describe task definitions
- Find Fargate tasks scheduled for retirement

**S3 Tools**
- List buckets with region and creation date
- Get bucket size and object count
- Check public access settings
- Find objects across buckets by name
- Check encryption configuration

**Lambda Tools**
- List functions with runtime and deprecation status
- Find functions using deprecated runtimes
- Get detailed function info
- List all runtimes with deprecation status

## Setup

### Prerequisites

- Python 3.10+
- AWS credentials configured (`~/.aws/credentials` or environment variables)
- Claude Desktop (for testing)

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure Claude Desktop

Add this to your Claude Desktop config:
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

**Important:** Use the full path to the Python binary inside your virtual environment. Using just `python` won't work because Claude Desktop launches the process directly, not from a shell with your venv activated.

```json
{
  "mcpServers": {
    "aws-infra-copilot": {
      "command": "/full/path/to/aws-infra-copilot/venv/bin/python",
      "args": ["/full/path/to/aws-infra-copilot/server.py"]
    }
  }
}
```

For example, if your project is at `~/projects/aws-infra-copilot`:

```json
{
  "mcpServers": {
    "aws-infra-copilot": {
      "command": "/Users/yourname/projects/aws-infra-copilot/venv/bin/python",
      "args": ["/Users/yourname/projects/aws-infra-copilot/server.py"]
    }
  }
}
```

If you use named AWS profiles instead of default credentials, add the `env` block:

```json
{
  "mcpServers": {
    "aws-infra-copilot": {
      "command": "/Users/yourname/projects/aws-infra-copilot/venv/bin/python",
      "args": ["/Users/yourname/projects/aws-infra-copilot/server.py"],
      "env": {
        "AWS_PROFILE": "your-profile-name"
      }
    }
  }
}
```

After saving, restart Claude Desktop completely. You should see a hammer icon indicating tools are available.

### Running Standalone (for testing)

```bash
python server.py
```

## Example Questions

- "List all IAM users"
- "Which users haven't rotated credentials in 90 days?"
- "Who has AdministratorAccess?"
- "What ECS clusters exist?"
- "Show me services in the production cluster"
- "Is the api-service healthy?"
- "Are any Fargate tasks being retired soon?"
- "What S3 buckets do I have?"
- "Which buckets are publicly accessible?"
- "Find which bucket contains config.yaml"
- "Are all my buckets encrypted?"
- "List my Lambda functions"
- "Which Lambda functions are using deprecated runtimes?"
- "What runtimes are currently supported?"

## Development

To add new tools, create a new file in `tools/` and import it in `server.py`. See existing tool files for patterns.

## Building as a Desktop Extension

You can package this server as a Desktop Extension (`.mcpb`) for one-click installation:

```bash
# Install the MCPB CLI
npm install -g @anthropic-ai/mcpb

# Package the extension
mcpb pack
```

This creates `aws-infra-copilot.mcpb` which users can double-click to install in Claude Desktop.
