# Agent Registration Client - README

This client provides a command-line interface to interact with both the the **Agent Engine** (managing deployed agents on Vertex AI Agent Engine) and **Agentspace** (managing agent metadata in Agentspace's Agent Gallery).

## Prerequisites

1.  **Google Cloud SDK (gcloud):**  Ensure you have the Google Cloud SDK installed and initialized.  You can download it from [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install).
2.  **Agent Pre-deployment (for Agent Registry):** For registering an agent with the Agentspace, the agent must be pre-deployed to Vertex AI Agent Engine. The Reasoning Engine ID (referred to as `adk_deployment_id` by this client) from this deployment will be required. This `adk_deployment_id` be found by inquiring the agents deployed to Vertex AI Agent Engine. 
3.  **Python 3.7+:**  Python 3.7 or a later version is required.  You can check your Python version with `python3 --version`.
4.  **Virtual Environment (Recommended):** It's highly recommended to use a virtual environment to isolate project dependencies. You can create and activate one like this:

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    # .venv\Scripts\activate  # On Windows
    ```

## Setup

1.  **Clone the repository:**  If you haven't already, clone the repository containing the client code.
2.  **Navigate to the directory:** Change your current directory to the location of the `as_registry_client.py` script.
3.  **Install dependencies:** Install the required Python packages.

    ```bash
     pip install google-cloud-aiplatform google-auth
    ```

## Configuration

The client resolves parameters with the following order of precedence (highest to lowest):

1.  **Command-line arguments:** Parameters passed directly when running the script.
2.  **Configuration file (`config.json`):** A JSON file (default name `config.json`, can be changed with the `--config` option) containing default parameter values. This is checked if the parameter is not found via CLI.
3.  **Interactive input:** If a required parameter is not found through any of the above methods, the client will prompt you for it.

**Example `config.json`:**
Create a file named `config.json` (or use `--config` to specify a different path):

    ```json
    {
        "project_id": "your-gcp-project-id-from-config",
        "location": "us-central1-from-config", 
        "app_id": "your-agentspace-app-id",
        "ars_display_name": "My Registered Agent Name from Config",
        "description": "Agent Description for Registry from Config",
        "tool_description": "Tool Description for Registry from Config",
        "adk_deployment_id": "your-reasoning-engine-id-from-agent-engine",
        "auth_id": "your-oauth-auth-id-if-any",
        "agent_id": "registered-agent-id-from-agentspace",
        "api_location": "global",
        "re_location": "global",
        "re_resource_name": "projects/your-gcp-project-id/locations/us-central1/agents/your-deployed-agent-engine-id",
        "re_resource_id": "your-deployed-agent-engine-id",
        "re_display_name": "My Deployed Agent Engine Name from Config"
    }
    ```
    *Note: `location` is for Vertex AI Agent Engine, while `api_location` and `re_location` are specific to the Agentspace API and reasoning engine and are typically configured via CLI or config.json.*

## Usage

The basic syntax for running the client is:

```bash
python as_registry_client.py [action] [options]
```

If you don't provide the `action` on the command line, the client will prompt you to enter it.

### Actions

The client supports actions for two main services:

**Agent Registry Service (ARS) Actions (for Agentspace Agent Gallery):**
*   `register_agent`: Registers a new agent.
*   `list_registry`: Lists registered agents.
*   `get_registered_agent`: Retrieves details for a specific registered agent by its AgentSpace ID.
*   `update_registered_agent`: Updates an existing agent registration.
*   `get_registered_agents_by_name`: Retrieves registered agents by their display name.
*   `unregister_agent`: Unregisters an agent.
*   `create_authorization`: Creates an OAuth authorization resource.
*   `delete_authorization`: Deletes an OAuth authorization resource.

**Agent Engine Manager (AEM) Actions (for Vertex AI Agent Engine):**
*   `list_deployed_agents`: Lists all agents deployed on Vertex AI Agent Engine.
*   `undeploy_agent`: Undeploys an agent from Vertex AI Agent Engine using its full resource name.
*   `get_deployed_agent`: Retrieves details of a specific deployed agent from Vertex AI Agent Engine by its resource ID.
*   `list_deployed_agents_by_name`: Lists deployed agents on Vertex AI Agent Engine by their display name.

### Options

The following options can be used to provide parameters:

**Common / Vertex AI Initialization:**
*   `--project_id <project_id>`: Google Cloud Project ID. Used for both services.
*   `--location <location>`: Google Cloud Location/Region for Vertex AI (e.g., `us-central1`). Used for Agent Engine Manager operations.

**Configuration:**
*   `--config <path>`: Specifies the path to the configuration file (defaults to `config.json`).

**For Agent Registry Service (ARS):**
*   `--app_id <app_id>`: The App ID (e.g., your Agentspace application ID).
*   `--agent_id <agent_id>`: The Agent ID assigned by the Agent Registry Service (used for `get_registered_agent`, `update_registered_agent`, `unregister_agent`).
*   `--ars_display_name <display_name>`: Agent display name for the registry (for `register_agent`, `update_registered_agent`, `get_registered_agents_by_name`).
*   `--description <description>`: Agent description for the registry.
*   `--tool_description <tool_description>`: Tool description for the registry.
*   `--adk_deployment_id <adk_deployment_id>`: The Reasoning Engine ID from the agent's deployment on Vertex AI Agent Engine. Example: if Reasoning Engine is `projects/PROJECT_ID/locations/LOCATION/reasoningEngines/RE_ID`, then this is `RE_ID`.
*   `--auth_id <auth_id>`: Authorization ID (for `register_agent`, `update_registered_agent`, `create_authorization`, `delete_authorization`).
*   `--icon_uri <icon_uri>`: URI for the agent's icon (optional).
*   `--oauth_client_id <client_id>`: OAuth Client ID for authorization.
*   `--oauth_client_secret <client_secret>`: OAuth Client Secret for authorization.
*   `--oauth_auth_uri <auth_uri>`: OAuth Authorization URI for authorization.
*   `--oauth_token_uri <token_uri>`: OAuth Token URI for authorization.
*   `--api_location <api_location>`: API location for the Agent Registry Service (default: `global`). See Discovery Engine locations.
*   `--re_location <re_location>`: Location of the Reasoning Engine and Authorizations (default: `global`).

**For Agent Engine Manager (AEM - Vertex AI Agent Engine):**
*   `--re_resource_name <resource_name>`: Full resource name of the deployed agent on Vertex AI (e.g., `projects/PROJECT_ID/locations/LOCATION/agents/AGENT_ID`). Required for `undeploy_agent`.
*   `--re_resource_id <resource_id>`: Resource ID of the deployed agent on Vertex AI. Required for `get_deployed_agent`.
*   `--re_display_name <display_name>`: Display name of the deployed agent on Vertex AI. Required for `list_deployed_agents_by_name`.

### Agent Engine Manager Examples

**1. List all deployed agents on Vertex AI Agent Engine:**

```bash
python as_registry_client.py list_deployed_agents --project_id your-gcp-project --location us-central1
```

**2. Get details of a specific deployed agent by its resource ID:**

```bash
python as_registry_client.py get_deployed_agent --project_id your-gcp-project --location us-central1 --re_resource_id your-deployed-agent-id
```

**3. List agents deployed to Vertex AI Agent Engine by their display name:**

```bash
python as_registry_client.py list_deployed_agents_by_name --project_id your-gcp-project --location us-central1 --re_display_name "My Deployed Agent Name"
```

**4. Undeploy an agent from Vertex AI Agent Engine using its full resource name:**

```bash
python as_registry_client.py undeploy_agent --project_id your-gcp-project --location us-central1 --re_resource_name projects/your-gcp-project/locations/us-central1/agents/your-deployed-agent-id
```


### Agentspace registration Examples

**1. Register an agent with Agentspace (interactive prompts for most fields):**

```bash
python as_registry_client.py register_agent --project_id your-gcp-project --app_id my-app
```

The client will prompt you for each required parameter.

**2. List agents (using command-line arguments):**

```bash
python as_registry_client.py list_registry --project_id your-project-id --app_id your-app-id --api_location global
```

**3. Get an agent by ID (using a configuration file and command-line argument):**

```bash
python as_registry_client.py get_registered_agent --agent_id your-agent-id --config my_config.json
```

This will load `project_id` and `app_id` from `my_config.json` and use the provided `agent_id`.

**4. Update an agent (partially, using a configuration file and command-line argument):**

```bash
python as_registry_client.py update_registered_agent --agent_id your-agent-id --display_name "New Agent Name"
```

**5. Get an agent by display name (using a configuration file and command-line argument):**

```bash
python as_registry_client.py get_registered_agents_by_name --display_name "Agent Name"  --config my_config.json   
```

**6. Unregister an agent from Agentspace (using a configuration file and command-line argument):**

```bash
python as_registry_client.py unregister_agent --agent_id your-agent-id --config my_config.json
```

This will update only the `display_name` of the agent with the specified ID, using other parameters from `config.json` or prompting the user if not found.