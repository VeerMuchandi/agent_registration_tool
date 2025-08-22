import subprocess
import json
import logging
import google.auth
import google.auth.transport.requests

# Scopes define the level of access you are requesting.
# For this example, we are using the default cloud-platform scope.
# You may need to specify more granular scopes depending on your needs.
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

def get_access_token():
    """Gets the access token from the environment."""
    try:
        # google.auth.default() automatically finds the credentials
        # from the environment (e.g., a service account key).
        credentials, project_id = google.auth.default(scopes=SCOPES)

        # Refresh the credentials to get an access token.
        # Provide a transport object for refreshing.
        credentials.refresh(google.auth.transport.requests.Request())

        return credentials.token
    except Exception as e:
        print(f"An error occurred in get_access_token: {e}")
        import traceback
        traceback.print_exc() # This will print the full stack trace
        return None

def get_project_number(project_id: str) -> str:
    """Gets the project number for a given project ID using gcloud."""
    if not project_id:
        logging.error("Project ID is required to get project number.")
        return None
    try:
        command = ["gcloud", "projects", "describe", project_id, "--format=value(projectNumber)"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        project_number = result.stdout.strip()
        if not project_number:
            logging.error(f"Project number for project ID {project_id} is empty.")
            return None
        return project_number
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logging.error(f"Failed to get project number for project ID {project_id}: {e}")
        return None

# --- Constants for URL construction ---
BASE_API_URL = "https://{location_prefix}discoveryengine.googleapis.com/v1alpha"
DEFAULT_LOCATION = "global"
DEFAULT_COLLECTION = "default_collection"
DEFAULT_ASSISTANT = "default_assistant"

def _check_required_params(params, required):
    missing = [param for param in required if not params.get(param)]
    if missing:
        raise ValueError(f"Missing required parameters: {', '.join(missing)}")

def _build_discovery_engine_url(project_id: str, app_id: str, agent_id: str = None, api_location: str = DEFAULT_LOCATION) -> str:
    """Helper function to construct the Discovery Engine API URL for agents."""
    location_prefix = ""
    if api_location != "global":
        location_prefix = api_location + "-"
    url = BASE_API_URL.format(location_prefix=location_prefix)
    base_path = f"{url}/projects/{project_id}/locations/{api_location}/collections/{DEFAULT_COLLECTION}/engines/{app_id}/assistants/{DEFAULT_ASSISTANT}/agents"
    if agent_id:
        return f"{base_path}/{agent_id}"
    return base_path

def _build_authorization_url(project_id: str, auth_id: str, api_location: str = DEFAULT_LOCATION) -> str:
    """Helper function to construct the Discovery Engine API URL for authorizations."""
    location_prefix = ""
    if api_location != "global":
        location_prefix = api_location + "-"
    url = BASE_API_URL.format(location_prefix=location_prefix)
    # Note the query parameter `authorizationId`
    base_path = f"{url}/projects/{project_id}/locations/{api_location}/authorizations?authorizationId={auth_id}"
    return base_path

def create_agent(project_id, app_id, display_name, description, tool_description, adk_deployment_id, auth_id, icon_uri=None, re_location="global", api_location="global"):
    """
    Creates a new agent in the Agent Registry.

    Args:
        project_id (str): Google Cloud Project ID.
        app_id (str): App ID for the Discovery Engine.
        display_name (str): Display name of the agent.
        description (str): Description of the agent.
        tool_description (str): Tool description for the agent.
        adk_deployment_id (str): Reasoning Engine ID.
        auth_id (str): Authorization ID.
        icon_uri (str, optional): Icon URI for the agent. Defaults to None.
        re_location (str, optional): Location of the Reasoning Engine. Defaults to "global".
        api_location (str, optional): API location for the Discovery Engine service and Authorizations. Defaults to "global".

    Returns:
        dict: A dictionary containing the status code, stdout, and stderr of the curl command.
    """
  
    
    _check_required_params(locals(), ["project_id", "app_id", "display_name", "description", "tool_description", "adk_deployment_id"])
    access_token = get_access_token()
    if not access_token:
        logging.error("Failed to obtain access token for create_agent.")
        return {
            "status_code": 401, # Unauthorized
            "stdout": "",
            "stderr": "Failed to obtain access token.",
            "error": "Authentication failed: Could not retrieve access token."
        }

    project_number_for_auth = None
    if auth_id:
        project_number_for_auth = get_project_number(project_id)
        if not project_number_for_auth:
            return {
                "status_code": 400,
                "stdout": "",
                "stderr": f"Could not retrieve project number for project ID {project_id}.",
                "error": f"Could not retrieve project number for project ID {project_id}."
            }

    url = _build_discovery_engine_url(project_id, app_id, api_location=api_location)

    # Prepare the request body
    data = {
        "displayName": display_name,
        "description": description,
        "adk_agent_definition": {
            "tool_settings": {
                "tool_description": tool_description
            },
            "provisioned_reasoning_engine": {
                "reasoning_engine": f"projects/{project_id}/locations/{re_location}/reasoningEngines/{adk_deployment_id}"
            },
            "authorizations": [f"projects/{project_number_for_auth}/locations/{api_location}/authorizations/{auth_id}"] if auth_id else [],
        }

    }

    if icon_uri:
        data["icon"] = {"uri": icon_uri}

    # Prepare the curl command
    command = [
        "curl", "-X", "POST",
        "-H", f"Authorization: Bearer {access_token}",
        "-H", "Content-Type: application/json",
        "-H", f"X-Goog-User-Project: {project_id}",
        url,
        "-d", json.dumps(data)
    ]

    logging.info(f"Create Agent Command: {command}")

    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        try:
            agent_data = json.loads(result.stdout)
            logging.debug(f"Create Agent Response: {agent_data}")
            return {"status_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "agent": agent_data}
        except json.JSONDecodeError:
            return {"status_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "error": "Could not decode JSON response."}
    else:
        logging.error(f"Create Agent Error: {result.returncode}, {result.stderr}")

    return {"status_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def list_agents(project_id, app_id, api_location="global"):
    """
    Lists agents in the Agent Registry for a given project and app.

    Args:
        project_id (str): Google Cloud Project ID.
        app_id (str): App ID for the Discovery Engine.
        api_location (str, optional): API location for the Discovery Engine service. Defaults to "global".

    Returns:
        dict: A dictionary containing a list of agents or an error message.
    """
    _check_required_params(locals(), ["project_id", "app_id"])

    access_token=get_access_token()
    if not access_token:
        logging.error(f"Failed to obtain access token for list_agents (project_id: {project_id}, app_id: {app_id}).")
        return {
            "status_code": 401, # Unauthorized
            "stdout": "",
            "stderr": "Failed to obtain access token.",
            "error": "Authentication failed: Could not retrieve access token."
        }


    url = _build_discovery_engine_url(project_id, app_id, api_location=api_location)

    # Prepare the curl command
    command = [
        "curl", "-X", "GET",
        "-H", f"Authorization: Bearer {access_token}",
        "-H", "Content-Type: application/json",
        "-H", f"X-Goog-User-Project: {project_id}",
        url
    ]

    logging.debug(f"List Agents Command: {command}")
    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True)

    # Return the output as a list of agents
    if result.returncode == 0:
        try:
            agents_data = json.loads(result.stdout)
            logging.debug(f"List Agents Response: {agents_data}")
            if "agents" in agents_data:
                return {"agents": agents_data["agents"]}
            else:
                return {"agents": []}
        except json.JSONDecodeError:
            return {"error": "Could not decode JSON response.", "stderr": result.stderr}
    else:
        return {"error": "Error during agent listing", "stderr": result.stderr}

def get_agent(project_id, app_id, agent_id, api_location="global"):
    """
    Retrieves details for a specific agent from the Agent Registry.

    Args:
        project_id (str): Google Cloud Project ID.
        app_id (str): App ID for the Discovery Engine.
        agent_id (str): ID of the agent to retrieve.
        api_location (str, optional): API location for the Discovery Engine service. Defaults to "global".

    Returns:
        dict: A dictionary containing the agent details or an error message.
    """
    _check_required_params(locals(), ["project_id", "app_id", "agent_id"])

    access_token=get_access_token()
    if not access_token:
        logging.error(f"Failed to obtain access token for get_agent (project_id: {project_id}, app_id: {app_id}, agent_id: {agent_id}).")
        return {
            "status_code": 401, # Unauthorized
            "stdout": "",
            "stderr": "Failed to obtain access token.",
            "error": "Authentication failed: Could not retrieve access token."
        }

    
    url = _build_discovery_engine_url(project_id, app_id, agent_id, api_location=api_location)

    # Prepare the curl command
    command = [
        "curl", "-X", "GET",
        "-H", f"Authorization: Bearer {access_token}",
        "-H", "Content-Type: application/json",
        "-H", f"X-Goog-User-Project: {project_id}",
        url
    ]

    logging.debug(f"Get Agent Command: {command}")
    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        try:
            agent_data = json.loads(result.stdout)
            logging.debug(f"Get Agent Response: {agent_data}")
            return {"agent_details": agent_data}
        except json.JSONDecodeError:
            return {"error": "Could not decode JSON response.", "stderr": result.stderr}
    else:
        return {"error": f"Error: {result.returncode} - {result.stderr}"}


def update_agent(project_id, app_id, agent_id, display_name, description, tool_description, adk_deployment_id, auth_id, icon_uri=None, re_location="global", api_location="global"):
    """
    Updates an existing agent in the Agent Registry.

    Args:
        project_id (str): Google Cloud Project ID.
        app_id (str): App ID for the Discovery Engine.
        agent_id (str): ID of the agent to update.
        display_name (str): New display name for the agent (leave blank to keep current).
        description (str): New description for the agent (leave blank to keep current).
        tool_description (str): New tool description (leave blank to keep current).
        adk_deployment_id (str): New Reasoning Engine ID (leave blank to keep current).
        auth_id (str, optional): New Authorization ID (leave blank to keep current).
        icon_uri (str, optional): New icon URI (leave blank to keep current).
        re_location (str, optional): Location of the Reasoning Engine if it is being updated. Defaults to "global".
        api_location (str, optional): API location for the Discovery Engine service and Authorizations. Defaults to "global".
    
    Returns:    
        dict: A dictionary containing the status code, stdout, stderr, and optionally the updated agent details or an error message.
    """
    _check_required_params(locals(), ["project_id", "app_id", "agent_id"]) # Check primary IDs first

    # First get the agent
    get_result = get_agent(project_id, app_id, agent_id, api_location=api_location)
    if "agent_details" not in get_result:
        return {"error": f"Could not retrieve agent details: {get_result.get('error', '')}"}
    
    existing_agent = get_result["agent_details"]

    # Prepare updated data. Use existing values as defaults.
    updated_data = {
        "displayName": display_name or existing_agent.get("displayName", ""),
        "description": description or existing_agent.get("description", ""),
    }

    #Handle adk_agent_definition.
    existing_adk = existing_agent.get("adkAgentDefinition", {})
    updated_adk = {}

    #Tool settings
    existing_tool = existing_adk.get("toolSettings", {})
    updated_adk["tool_settings"] = {
        "tool_description": tool_description or existing_tool.get("toolDescription", "")
    }

    #Reasoning engine
    existing_reasoning_engine_info = existing_adk.get("provisionedReasoningEngine", {})
    if adk_deployment_id: # If a new ADK deployment ID is provided, update it with the new re_location
        updated_adk["provisionedReasoningEngine"] = {
            "reasoning_engine": f"projects/{project_id}/locations/{re_location}/reasoningEngines/{adk_deployment_id}"
        }
    elif existing_reasoning_engine_info: # Otherwise, keep the existing one
        updated_adk["provisionedReasoningEngine"] = existing_reasoning_engine_info

    #Authorizations
    existing_auths = existing_adk.get("authorizations", [])
    if auth_id: # If a new auth ID is provided, update it with the new re_location
        project_number_for_auth = get_project_number(project_id)
        if not project_number_for_auth:
            return {
                "status_code": 400,
                "stdout": "",
                "stderr": f"Could not retrieve project number for project ID {project_id}.",
                "error": f"Could not retrieve project number for project ID {project_id}."
            }
        updated_adk["authorizations"] = [f"projects/{project_number_for_auth}/locations/{api_location}/authorizations/{auth_id}"]
    else: # Otherwise, keep the existing ones
        updated_adk["authorizations"] = existing_auths


    existing_icon = existing_agent.get("icon")
    if icon_uri:  # If new icon URI is provided
        updated_data["icon"] = {"uri": icon_uri}
    elif existing_icon:  # If no new URI, retain the existing icon
        updated_data["icon"] = existing_icon

    updated_data["adk_agent_definition"] = updated_adk

    url = _build_discovery_engine_url(project_id, app_id, agent_id, api_location=api_location)

    # Get access token
    #access_token = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip()
    access_token=get_access_token()
    if not access_token:
        logging.error(f"Failed to obtain access token for update_agent (project_id: {project_id}, app_id: {app_id}, agent_id: {agent_id}).")
        return {
            "status_code": 401, # Unauthorized
            "stdout": "",
            "stderr": "Failed to obtain access token.",
            "error": "Authentication failed: Could not retrieve access token."
        }



    # Prepare the curl command
    logging.debug(f"Updated Data: {json.dumps(updated_data, indent=2)}")
    command = [
        "curl", "-X", "PATCH",
        "-H", f"Authorization: Bearer {access_token}",
        "-H", "Content-Type: application/json",
        "-H", f"X-Goog-User-Project: {project_id}",
        url,
        "-d", json.dumps(updated_data, indent=2)
    ]

    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True)

    # Return results as JSON
    response = {"status_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    if result.returncode == 0:
        try:
            updated_agent = json.loads(result.stdout)
            response["updated_agent"] = updated_agent
        except json.JSONDecodeError:
            response["error"] = "Could not decode JSON response for updated agent."
    return response

def get_agent_by_display_name(project_id, app_id, display_name, api_location="global"):
    """
    Retrieves an agent from the Agent Registry by its display name.

    Args:
        project_id (str): Google Cloud Project ID.
        app_id (str): App ID for the Discovery Engine.
        display_name (str): Display name of the agent to retrieve.
        api_location (str, optional): API location for the Discovery Engine service. Defaults to "global".

    Returns:
        dict: A dictionary containing the agent details or a message indicating the agent was not found.
    """
    _check_required_params(locals(), ["project_id", "app_id", "display_name"])
    list_result = list_agents(project_id, app_id, api_location=api_location)
    if "error" in list_result:
        return list_result

    agents = list_result.get("agents", [])
    for agent in agents:
        if agent.get("displayName") == display_name:
            return {"agent": agent}

    return {"message": f"Agent with display name '{display_name}' not found."}


def delete_agent(project_id, app_id, agent_id, api_location="global"):
    """
    Deletes an agent from the Agent Registry.

    Args:
        project_id (str): Google Cloud Project ID.
        app_id (str): App ID for the Discovery Engine.
        agent_id (str): ID of the agent to delete.
        api_location (str, optional): API location for the Discovery Engine service. Defaults to "global".

    Returns:
        dict: A dictionary containing the status code, stdout, and stderr of the curl command,
              or an error message.
    """
    _check_required_params(locals(), ["project_id", "app_id", "agent_id"])

    #access_token = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True).stdout.strip()
    access_token=get_access_token()
    if not access_token:
        logging.error(f"Failed to obtain access token for delete_agent (project_id: {project_id}, app_id: {app_id}, agent_id: {agent_id}).")
        return {
            "status_code": 401, # Unauthorized
            "stdout": "",
            "stderr": "Failed to obtain access token.",
            "error": "Authentication failed: Could not retrieve access token."
        }


    url = _build_discovery_engine_url(project_id, app_id, agent_id, api_location=api_location)

    # Prepare the curl command
    command = [
        "curl", "-X", "DELETE",
        # Although DELETE often doesn't need this, it's good practice
        "-H", f"Authorization: Bearer {access_token}",
        "-H", "Content-Type: application/json",  # Although DELETE often doesn't need this, it's good practice
        "-H", f"X-Goog-User-Project: {project_id}",
        url
    ]

    logging.info(f"Delete Agent Command: {command}")

    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        logging.info(f"Agent {agent_id} deleted successfully.")
        return {"status_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "message": f"Agent {agent_id} deleted successfully."}
    else:
        logging.error(f"Error deleting agent {agent_id}: {result.returncode}, {result.stderr}")
        return {"status_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "error": f"Error deleting agent: {result.stderr}"}

def delete_authorization(project_id, auth_id, api_location="global"):
    """
    Deletes an authorization resource from Discovery Engine.

    Args:
        project_id (str): Google Cloud Project ID.
        auth_id (str): The ID for this authorization to delete.
        api_location (str, optional): API location for the Discovery Engine service. Defaults to "global".

    Returns:
        dict: A dictionary containing the status code, stdout, and stderr of the curl command.
    """
    _check_required_params(locals(), ["project_id", "auth_id"])
    access_token = get_access_token()
    if not access_token:
        logging.error("Failed to obtain access token for delete_authorization.")
        return {
            "status_code": 401, # Unauthorized
            "stdout": "",
            "stderr": "Failed to obtain access token.",
            "error": "Authentication failed: Could not retrieve access token."
        }

    location_prefix = ""
    if api_location != "global":
        location_prefix = api_location + "-"
    api_url = BASE_API_URL.format(location_prefix=location_prefix)
    url = f"{api_url}/projects/{project_id}/locations/{api_location}/authorizations/{auth_id}"

    command = ["curl", "-X", "DELETE", "-H", f"Authorization: Bearer {access_token}", "-H", "Content-Type: application/json", "-H", f"X-Goog-User-Project: {project_id}", url]

    logging.info(f"Delete Authorization Command: {command}")
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        logging.info(f"Authorization {auth_id} deleted successfully.")
        return {"status_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "message": f"Authorization {auth_id} deleted successfully."}
    else:
        logging.error(f"Error deleting authorization {auth_id}: {result.returncode}, {result.stderr}")
        return {"status_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "error": f"Error deleting authorization: {result.stderr}"}

def create_authorization(project_id, auth_id, oauth_client_id, oauth_client_secret, oauth_auth_uri, oauth_token_uri, api_location="global"):
    """
    Creates a new authorization resource in Discovery Engine.

    Args:
        project_id (str): Google Cloud Project ID.
        auth_id (str): The ID for this authorization.
        oauth_client_id (str): The OAuth 2.0 client ID.
        oauth_client_secret (str): The OAuth 2.0 client secret.
        oauth_auth_uri (str): The authorization URI for the OAuth 2.0 provider.
        oauth_token_uri (str): The token URI for the OAuth 2.0 provider.
        api_location (str, optional): API location for the Discovery Engine service. Defaults to "global".

    Returns:
        dict: A dictionary containing the status code, stdout, and stderr of the curl command.
    """
    _check_required_params(locals(), ["project_id", "auth_id", "oauth_client_id", "oauth_client_secret", "oauth_auth_uri", "oauth_token_uri"])
    access_token = get_access_token()
    if not access_token:
        logging.error("Failed to obtain access token for create_authorization.")
        return {
            "status_code": 401, # Unauthorized
            "stdout": "",
            "stderr": "Failed to obtain access token.",
            "error": "Authentication failed: Could not retrieve access token."
        }

    url = _build_authorization_url(project_id, auth_id, api_location=api_location)

    # Prepare the request body
    data = {
        "name": f"projects/{project_id}/locations/{api_location}/authorizations/{auth_id}",
        "serverSideOauth2": {
            "clientId": oauth_client_id,
            "clientSecret": oauth_client_secret,
            "authorizationUri": oauth_auth_uri,
            "tokenUri": oauth_token_uri
        }
    }

    # Prepare the curl command
    command = [
        "curl", "-X", "POST",
        "-H", f"Authorization: Bearer {access_token}",
        "-H", "Content-Type: application/json",
        "-H", f"X-Goog-User-Project: {project_id}",
        url,
        "-d", json.dumps(data)
    ]

    logging.info(f"Create Authorization Command: {command}")

    # Execute the command
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        try:
            auth_data = json.loads(result.stdout)
            logging.debug(f"Create Authorization Response: {auth_data}")
            return {"status_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "authorization": auth_data}
        except json.JSONDecodeError:
            return {"status_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "error": "Could not decode JSON response."}
    else:
        logging.error(f"Create Authorization Error: {result.returncode}, {result.stderr}")

    return {"status_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}