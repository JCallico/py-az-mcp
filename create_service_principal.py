"""
Script Name: create_service_principal.py
Description: Utility script for creating and configuring an Azure Service Principal
            with necessary permissions for the Azure MCP Server. Handles interactive
            authentication and creates the required environment configuration.
Author: JCallico
Date Created: 2025-04-21
Version: 0.1.0
Python Version: >= 3.13
Dependencies:
    - azure-cli>=2.57.0
License: MIT

Usage:
    $ python create_service_principal.py
    
    This will:
    1. Authenticate you with Azure interactively
    2. Create a new Service Principal with Contributor role
    3. Generate a .env file with required credentials
"""

import subprocess
import json

def authenticate_user_and_get_subscription() -> str:
    """Authenticate the user interactively and retrieve the subscription ID."""
    try:
        # Run the Azure CLI command to authenticate the user interactively
        subprocess.run(["az", "login"], check=True)

        # Retrieve the current subscription ID
        result = subprocess.run(
            ["az", "account", "show", "--query", "id", "-o", "tsv"],
            capture_output=True,
            text=True,
            check=True
        )

        subscription_id = result.stdout.strip()
        return subscription_id

    except subprocess.CalledProcessError as e:
        print(f"Error during authentication or retrieving subscription ID: {e.stderr}")
        return ""

def create_service_principal(subscription_id: str) -> dict:
    """Create a new Azure service principal and return its credentials."""
    try:
        # Run the Azure CLI command to create a service principal
        result = subprocess.run(
            [
                "az", "ad", "sp", "create-for-rbac",
                "--name", "mcp-server-azure",
                "--role", "Contributor",
                "--scopes", f"/subscriptions/{subscription_id}",
                "--sdk-auth"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the JSON output
        credentials = json.loads(result.stdout)

        # Extract and return the required fields
        return {
            "client_id": credentials["clientId"],
            "client_secret": credentials["clientSecret"],
            "tenant_id": credentials["tenantId"]
        }

    except subprocess.CalledProcessError as e:
        print(f"Error creating service principal: {e.stderr}")
        return {}

def write_env_file(credentials: dict, subscription_id: str):
    """Write credentials to .env file."""
    env_content = f"""AZURE_CLIENT_ID={credentials['client_id']}
AZURE_CLIENT_SECRET={credentials['client_secret']}
AZURE_TENANT_ID={credentials['tenant_id']}
AZURE_SUBSCRIPTION_ID={subscription_id}
"""
    with open('.env', 'w') as f:
        f.write(env_content)
    print("Created .env file with credentials")

if __name__ == "__main__":
    print("Authenticating user interactively...")
    subscription_id = authenticate_user_and_get_subscription()

    if subscription_id:
        print(f"Authenticated successfully. Subscription ID: {subscription_id}")
        print("Creating service principal...")
        credentials = create_service_principal(subscription_id)

        if credentials:
            print("Service Principal created successfully:")
            print(f"Client ID: {credentials['client_id']}")
            print(f"Client Secret: {credentials['client_secret']}")
            print(f"Tenant ID: {credentials['tenant_id']}")
            
            # Write credentials to .env file
            write_env_file(credentials, subscription_id)
        else:
            print("Failed to create service principal.")
    else:
        print("Failed to authenticate or retrieve subscription ID.")