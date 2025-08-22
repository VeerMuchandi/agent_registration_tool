import argparse
import json
import os
import logging

# Import functions from both service modules
from as_agent_registry_service import (
    create_agent as ars_create_agent,
    list_agents as ars_list_agents,
    get_agent as ars_get_agent,
    update_agent as ars_update_agent,
    delete_agent as ars_delete_agent,
    get_agent_by_display_name as ars_get_agent_by_display_name,
    create_authorization as ars_create_authorization,
    delete_authorization as ars_delete_authorization,
)
import agent_engine_manager # For Vertex AI Agent Engine specific operations

# Configure logging for the client
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = "config.json"

def load_config(config_file):
    if not config_file:
        return {}
    config_path = os.path.expanduser(config_file)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Could not decode JSON from config file {config_path}: {e}")
            return {}
    return {}

def get_parameter(name, config, args, prompt=None, required=False, default=None):
    """
    Retrieves a parameter value with a defined order of precedence:
    1. Command-line arguments (args)
    2. Config file (config)
    3. User prompt (if prompt is specified)
    4. Default value (if default is specified)
    """
    value_sources = [] # For debugging which source was used

    # 1. Command-line arguments
    cli_value = getattr(args, name, None)
    if cli_value is not None:
        logger.debug(f"Parameter '{name}' from CLI: '{cli_value}'")
        return cli_value

    # 2. Config file
    if name in config:
        logger.debug(f"Parameter '{name}' from config file: '{config[name]}'")
        return config[name]

    # 3. User prompt
    if prompt:
        user_input = input(f"{prompt}: ").strip()
        if user_input:
            logger.debug(f"Parameter '{name}' from prompt: '{user_input}'")
            return user_input
        elif default is None and required: # If prompt is skipped and no default, and it's required
             raise ValueError(f"Parameter '{name}' is required but was not provided via prompt.")


    # 4. Default value
    if default is not None:
        logger.debug(f"Parameter '{name}' from default: '{default}'")
        return default

    if required:
        raise ValueError(f"Parameter '{name}' is required but not found via CLI, config, or prompt.")

    return None

def main():
    parser = argparse.ArgumentParser(description="Unified Agent Registry and Engine Client")
    parser.add_argument(
        "action", nargs='?',
        choices=[
            # AS Agent Registry Service actions
            "register_agent", "list_registry", "get_registered_agent",
            "update_registered_agent", "get_registered_agents_by_name", "unregister_agent",
            "create_authorization", "delete_authorization",
            # Agent Engine Manager actions
            "list_deployed_agents", "undeploy_agent", "get_deployed_agent", "list_deployed_agents_by_name"
        ],
        help="Action to perform. Refer to specific action help for required parameters.",
    )

    # Common parameters / Vertex AI Init
    parser.add_argument("--project_id", help="Google Cloud Project ID. Used for both services.")
    parser.add_argument("--location", help="Google Cloud Location/Region for Vertex AI (e.g., us-central1). Used for Agent Engine.")

    # Parameters for AS Agent Registry Service
    parser.add_argument("--config", help=f"Path to the config file (default: {DEFAULT_CONFIG_FILE})", default=DEFAULT_CONFIG_FILE)
    parser.add_argument("--app_id", help="App ID (for AS Agent Registry Service)")
    parser.add_argument("--agent_id", help="Agent ID (for AS Agent Registry Service: get, update, unregister)")
    parser.add_argument("--ars_display_name", help="Agent display name (for AS Agent Registry Service: register, update, get_by_name)")
    parser.add_argument("--description", help="Agent description (for AS Agent Registry Service: register, update)")
    parser.add_argument("--tool_description", help="Tool description (for AS Agent Registry Service: register, update)")
    parser.add_argument("--adk_deployment_id", help="ADK deployment ID (for AS Agent Registry Service: register, update)")
    parser.add_argument("--auth_id", help="Authorization ID (for AS Agent Registry Service: register, update, create_authorization, delete_authorization)")
    parser.add_argument("--icon_uri", help="Icon URI for the agent (for AS Agent Registry Service: register, update)")
    parser.add_argument("--oauth_client_id", help="OAuth Client ID for authorization")
    parser.add_argument("--oauth_client_secret", help="OAuth Client Secret for authorization")
    parser.add_argument("--oauth_auth_uri", help="OAuth Authorization URI for authorization")
    parser.add_argument("--oauth_token_uri", help="OAuth Token URI for authorization")
    parser.add_argument("--api_location", help="API location for AS Agent Registry Service (default: global)")
    parser.add_argument("--re_location", help="Reasoning Engine location for AS Agent Registry Service (default: global)")

    # Parameters for Agent Engine Manager
    parser.add_argument("--re_resource_name", help="Full Resource Name for Agent Engine (e.g., projects/.../agents/AGENT_ID). Required for 'undeploy_agent'.")
    parser.add_argument("--re_resource_id", help="Resource ID for Agent Engine. Required for 'get_deployed_agent'.")
    parser.add_argument("--re_display_name", help="Display name for Agent Engine. Required for 'list_deployed_agents_by_name'.")


    args = parser.parse_args()
    config = load_config(args.config)

    action = args.action
    if not action:
        action = input(
            "Enter action to perform:\n"
            "  list_deployed_agents\n"
            "  get_deployed_agent\n"
            "  list_deployed_agents_by_name\n"
            "  undeploy_agent\n"
            "  register_agent\n"
            "  list_registry\n"
            "  get_registered_agent\n"
            "  update_registered_agent\n"
            "  get_registered_agents_by_name\n"
            "  unregister_agent\n"
            "  create_authorization\n"
            "  delete_authorization\n"
            "Action: "
        ).strip()

    try:
        # --- Initialize Vertex AI (for agent_engine_manager) ---
        # These parameters are fundamental for agent_engine_manager
        # For as_agent_registry_service, project_id is also used but passed directly.
        if action in ["list_deployed_agents", "undeploy_agent", "get_deployed_agent", "list_deployed_agents_by_name"]:
            project_id_for_init = get_parameter("project_id", config, args, prompt="Enter Google Cloud Project ID (for Vertex AI init)", required=True)
            location_for_init = get_parameter("location", config, args, prompt="Enter Vertex AI Location (e.g., us-central1, optional)", required=False)
            
            if not project_id_for_init: # Should be caught by required=True in get_parameter
                logger.error("Project ID is required for Agent Engine operations.")
                return

            logger.info(f"Initializing Vertex AI with Project ID: {project_id_for_init}, Location: {location_for_init or 'Default'}")
            agent_engine_manager.initialize_vertex_ai(project_id_for_init, location_for_init)
        # --- End Vertex AI Initialization ---

        # --- AS Agent Registry Service Actions ---
        if action == "register_agent":
            project_id = get_parameter("project_id", config, args, "Enter Google Cloud Project ID", required=True)
            app_id = get_parameter("app_id", config, args, "Enter App ID", required=True)
            ars_display_name = get_parameter("ars_display_name", config, args, "Enter agent display name", required=True)
            description = get_parameter("description", config, args, "Enter agent description", required=True)
            tool_description = get_parameter("tool_description", config, args, "Enter tool description", required=True)
            adk_deployment_id = get_parameter("adk_deployment_id", config, args, "Enter ADK deployment ID", required=True)
            auth_id = get_parameter("auth_id", config, args, "Enter authorization ID (optional)") 
            re_location = get_parameter("re_location", config, args, "Enter Reasoning Engine location (optional, default: global)", default="global")
            api_location = get_parameter("api_location", config, args, "Enter API location (optional, default: global)", default="global")
            icon_uri = get_parameter("icon_uri", config, args, "Enter icon URI (optional)")

            result = ars_create_agent(
                project_id, app_id, ars_display_name, description, tool_description,
                adk_deployment_id, auth_id, icon_uri,
                re_location=re_location, api_location=api_location
            )
            print(json.dumps(result, indent=2))

        elif action == "list_registry":
            project_id = get_parameter("project_id", config, args, "Enter Google Cloud Project ID", required=True)
            app_id = get_parameter("app_id", config, args, "Enter App ID", required=True)
            api_location = get_parameter("api_location", config, args, "Enter API location (optional, default: global)", default="global")
            result = ars_list_agents(project_id, app_id, api_location=api_location)
            print(json.dumps(result, indent=2))

        elif action == "get_registered_agent":
            project_id = get_parameter("project_id", config, args, "Enter Google Cloud Project ID", required=True)
            app_id = get_parameter("app_id", config, args, "Enter App ID", required=True)
            agent_id = get_parameter("agent_id", config, args, "Enter Agent ID", required=True)
            api_location = get_parameter("api_location", config, args, "Enter API location (optional, default: global)", default="global")
            result = ars_get_agent(project_id, app_id, agent_id, api_location=api_location)
            print(json.dumps(result, indent=2))

        elif action == "update_registered_agent":
            project_id = get_parameter("project_id", config, args, "Enter Google Cloud Project ID", required=True)
            app_id = get_parameter("app_id", config, args, "Enter App ID", required=True)
            agent_id = get_parameter("agent_id", config, args, "Enter Agent ID to update", required=True) # This was the highlighted line
            ars_display_name = get_parameter("ars_display_name", config, args, "Enter new display name (leave blank to keep current)")
            description = get_parameter("description", config, args, "Enter new description (leave blank to keep current)")
            tool_description = get_parameter("tool_description", config, args, "Enter new tool description (leave blank to keep current)")
            adk_deployment_id = get_parameter("adk_deployment_id", config, args, "Enter new ADK deployment ID (leave blank to keep current)")
            auth_id = get_parameter("auth_id", config, args, "Enter new authorization ID (leave blank to keep current)")
            re_location = get_parameter("re_location", config, args, "Enter new Reasoning Engine location (optional, default: global)", default="global")
            api_location = get_parameter("api_location", config, args, "Enter API location (optional, default: global)", default="global")
            icon_uri = get_parameter("icon_uri", config, args, "Enter new icon URI (leave blank to keep current)")

            result = ars_update_agent(
                project_id, app_id, agent_id, ars_display_name, description, tool_description,
                adk_deployment_id, auth_id, icon_uri,
                re_location=re_location, api_location=api_location
            )
            print(json.dumps(result, indent=2))

        elif action == "get_registered_agents_by_name":
            project_id = get_parameter("project_id", config, args, "Enter Google Cloud Project ID", required=True)
            app_id = get_parameter("app_id", config, args, "Enter App ID", required=True)
            ars_display_name = get_parameter("ars_display_name", config, args, "Enter agent display name to search for", required=True)
            api_location = get_parameter("api_location", config, args, "Enter API location (optional, default: global)", default="global")
            result = ars_get_agent_by_display_name(project_id, app_id, ars_display_name, api_location=api_location)
            print(json.dumps(result, indent=2))

        elif action == "unregister_agent":
            project_id = get_parameter("project_id", config, args, "Enter Google Cloud Project ID", required=True)
            app_id = get_parameter("app_id", config, args, "Enter App ID", required=True)
            agent_id = get_parameter("agent_id", config, args, "Enter Agent ID to unregister", required=True) # This was the highlighted line
            api_location = get_parameter("api_location", config, args, "Enter API location (optional, default: global)", default="global")

            confirmation = input(f"Are you sure you want to unregister agent '{agent_id}' from App '{app_id}'? (yes/no): ")
            if confirmation.lower() == "yes":
                result = ars_delete_agent(project_id, app_id, agent_id, api_location=api_location)
                print(json.dumps(result, indent=2))
            else:
                print("Unregistering agent cancelled.")

        elif action == "create_authorization":
            project_id = get_parameter("project_id", config, args, "Enter Google Cloud Project ID", required=True)
            auth_id = get_parameter("auth_id", config, args, "Enter Authorization ID to create", required=True)
            oauth_client_id = get_parameter("oauth_client_id", config, args, "Enter OAuth Client ID", required=True)
            oauth_client_secret = get_parameter("oauth_client_secret", config, args, "Enter OAuth Client Secret", required=True)
            oauth_auth_uri = get_parameter("oauth_auth_uri", config, args, "Enter OAuth Authorization URI", required=True)
            oauth_token_uri = get_parameter("oauth_token_uri", config, args, "Enter OAuth Token URI", required=True)
            api_location = get_parameter("api_location", config, args, "Enter API location (optional, default: global)", default="global")

            result = ars_create_authorization(
                project_id, auth_id, oauth_client_id, oauth_client_secret,
                oauth_auth_uri, oauth_token_uri, api_location=api_location
            )
            print(json.dumps(result, indent=2))

        elif action == "delete_authorization":
            project_id = get_parameter("project_id", config, args, "Enter Google Cloud Project ID", required=True)
            auth_id = get_parameter("auth_id", config, args, "Enter Authorization ID to delete", required=True)
            api_location = get_parameter("api_location", config, args, "Enter API location (optional, default: global)", default="global")

            confirmation = input(f"Are you sure you want to delete authorization '{auth_id}'? (yes/no): ")
            if confirmation.lower() == "yes":
                result = ars_delete_authorization(project_id, auth_id, api_location=api_location)
                print(json.dumps(result, indent=2))
            else:
                print("Deleting authorization cancelled.")

        # --- Agent Engine Manager Actions ---
        elif action == "list_deployed_agents":
            result = agent_engine_manager.list_agents()
            print(json.dumps(json.loads(result), indent=2) if isinstance(result, str) else json.dumps(result, indent=2))


        elif action == "undeploy_agent":
            re_resource_name = get_parameter(
                "re_resource_name", config, args,
                prompt="Enter resource name of the agent to undeploy (e.g., projects/PROJECT_ID/locations/LOCATION/agents/AGENT_ID)",
                required=True
            )
            confirmation = input(f"Are you sure you want to undeploy agent with resource name '{re_resource_name}'? (yes/no): ")
            if confirmation.lower() == "yes":
                result = agent_engine_manager.delete_agent(re_resource_name)
                print(json.dumps({"message": result}, indent=2) if isinstance(result, str) else json.dumps(result, indent=2))
            else:
                print("Undeployment cancelled.")

        elif action == "get_deployed_agent":
            re_resource_id = get_parameter(
                "re_resource_id", config, args,
                prompt="Enter resource ID of the agent to get",
                required=True
            )
            result = agent_engine_manager.get_agent(re_resource_id)
            print(json.dumps(json.loads(result), indent=2) if isinstance(result, str) else json.dumps(result, indent=2))


        elif action == "list_deployed_agents_by_name":
            re_display_name = get_parameter(
                "re_display_name", config, args,
                prompt="Enter display name of the agent to list for Agent Engine",
                required=True
            )
            result = agent_engine_manager.list_agents_by_display_name(re_display_name)
            print(json.dumps(json.loads(result), indent=2) if isinstance(result, str) else json.dumps(result, indent=2))

        else:
            logger.error(f"Invalid action: {action}")
            parser.print_help()

    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
    except RuntimeError as re:
        logger.error(f"SDK Initialization or Runtime error: {re}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main()