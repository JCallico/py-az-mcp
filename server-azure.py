from mcp.server.fastmcp import FastMCP
import subprocess
import os
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Pass the Flask app instance to FastMCP
mcp = FastMCP("Azure")

def authenticate_with_service_principal():
    """Authenticate using a service principal and set the access token."""
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant_id = os.getenv("AZURE_TENANT_ID")

    if not client_id or not client_secret or not tenant_id:
        raise EnvironmentError("Missing environment variables for service principal authentication: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID")

    try:
        # Authenticate using the service principal
        subprocess.run([
            "az", "login",
            "--service-principal",
            "--username", client_id,
            "--password", client_secret,
            "--tenant", tenant_id
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Retrieve the access token
        command = "az account get-access-token --query accessToken -o tsv"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        global ACCESS_TOKEN
        ACCESS_TOKEN = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError("Failed to authenticate with service principal")

# Authenticate when the server starts
authenticate_with_service_principal()

@mcp.tool()
def azure_cli(command: str) -> str:
    """Run an Azure CLI command and return the output."""
    try:
        # Ensure output is in JSON format
        if not command.endswith(" --output json"):
            command += " --output json"
            
        result = subprocess.run(
            ["az"] + command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        
        # Try to parse the output as JSON to validate it
        try:
            json.loads(result.stdout)
            return result.stdout
        except json.JSONDecodeError:
            return json.dumps({"error": "Command output is not valid JSON", "output": result.stdout})
            
    except subprocess.CalledProcessError as e:
        return json.dumps({"error": str(e.stderr)})

# Compute Operations
@mcp.resource("azure://compute/vm/list")
def list_virtual_machines() -> str:
    """List all virtual machines in the current subscription."""
    return azure_cli("vm list")

@mcp.resource("azure://compute/vm/show/{name}")
def get_virtual_machine(name: str) -> str:
    """Get details of a specific virtual machine."""
    return azure_cli(f"vm show --name {name}")

@mcp.resource("azure://compute/vm/start/{name}")
def start_virtual_machine(name: str) -> str:
    """Start a virtual machine."""
    return azure_cli(f"vm start --name {name}")

@mcp.resource("azure://compute/vm/stop/{name}")
def stop_virtual_machine(name: str) -> str:
    """Stop a virtual machine."""
    return azure_cli(f"vm stop --name {name}")

@mcp.resource("azure://compute/vmss/list")
def list_vmss() -> str:
    """List all virtual machine scale sets."""
    return azure_cli("vmss list")

@mcp.resource("azure://compute/aks/list")
def list_aks_clusters() -> str:
    """List all AKS clusters."""
    return azure_cli("aks list")

# Compute Operations - Extended
@mcp.resource("azure://compute/vm/delete/{name}")
def delete_virtual_machine(name: str) -> str:
    """Delete a virtual machine."""
    return azure_cli(f"vm delete --name {name} --yes")

@mcp.resource("azure://compute/vm/restart/{name}")
def restart_virtual_machine(name: str) -> str:
    """Restart a virtual machine."""
    return azure_cli(f"vm restart --name {name}")

@mcp.resource("azure://compute/vmss/scale/{name}/{capacity}")
def scale_vmss(name: str, capacity: int) -> str:
    """Scale a virtual machine scale set to a specific capacity."""
    return azure_cli(f"vmss scale --name {name} --new-capacity {capacity}")

@mcp.resource("azure://compute/vmss/update/{name}")
def update_vmss(name: str) -> str:
    """Update instances in a virtual machine scale set."""
    return azure_cli(f"vmss update-instances --name {name} --instance-ids *")

# Storage Operations
@mcp.resource("azure://storage/account/list")
def list_storage_accounts() -> str:
    """List all storage accounts."""
    return azure_cli("storage account list")

@mcp.resource("azure://storage/account/show/{name}")
def get_storage_account(name: str) -> str:
    """Get details of a storage account."""
    return azure_cli(f"storage account show --name {name}")

@mcp.resource("azure://storage/container/list/{account_name}")
def list_storage_containers(account_name: str) -> str:
    """List containers in a storage account."""
    return azure_cli(f"storage container list --account-name {account_name}")

# Storage Operations - Extended
@mcp.resource("azure://storage/account/create/{name}/{resource_group}/{sku}")
def create_storage_account(name: str, resource_group: str, sku: str = "Standard_LRS") -> str:
    """Create a new storage account."""
    return azure_cli(f"storage account create --name {name} --resource-group {resource_group} --sku {sku}")

@mcp.resource("azure://storage/account/delete/{name}")
def delete_storage_account(name: str) -> str:
    """Delete a storage account."""
    return azure_cli(f"storage account delete --name {name} --yes")

@mcp.resource("azure://storage/container/create/{account_name}/{container_name}")
def create_storage_container(account_name: str, container_name: str) -> str:
    """Create a container in a storage account."""
    return azure_cli(f"storage container create --account-name {account_name} --name {container_name}")

@mcp.resource("azure://storage/container/delete/{account_name}/{container_name}")
def delete_storage_container(account_name: str, container_name: str) -> str:
    """Delete a container from a storage account."""
    return azure_cli(f"storage container delete --account-name {account_name} --name {container_name}")

# Networking Operations
@mcp.resource("azure://network/vnet/list")
def list_virtual_networks() -> str:
    """List all virtual networks."""
    return azure_cli("network vnet list")

@mcp.resource("azure://network/nsg/list")
def list_network_security_groups() -> str:
    """List all network security groups."""
    return azure_cli("network nsg list")

@mcp.resource("azure://network/public-ip/list")
def list_public_ips() -> str:
    """List all public IP addresses."""
    return azure_cli("network public-ip list")

# Database Operations
@mcp.resource("azure://sql/server/list")
def list_sql_servers() -> str:
    """List all SQL servers."""
    return azure_cli("sql server list")

@mcp.resource("azure://cosmos/list")
def list_cosmos_accounts() -> str:
    """List all Cosmos DB accounts."""
    return azure_cli("cosmos list")

# App Service Operations
@mcp.resource("azure://webapp/list")
def list_web_apps() -> str:
    """List all web apps."""
    return azure_cli("webapp list")

@mcp.resource("azure://webapp/show/{name}")
def get_web_app(name: str) -> str:
    """Get details of a web app."""
    return azure_cli(f"webapp show --name {name}")

@mcp.resource("azure://webapp/restart/{name}")
def restart_web_app(name: str) -> str:
    """Restart a web app."""
    return azure_cli(f"webapp restart --name {name}")

# App Service Operations - Extended
@mcp.resource("azure://webapp/create/{name}/{resource_group}/{plan}")
def create_web_app(name: str, resource_group: str, plan: str) -> str:
    """Create a new web app."""
    return azure_cli(f"webapp create --name {name} --resource-group {resource_group} --plan {plan}")

@mcp.resource("azure://webapp/delete/{name}")
def delete_web_app(name: str) -> str:
    """Delete a web app."""
    return azure_cli(f"webapp delete --name {name} --yes")

@mcp.resource("azure://webapp/stop/{name}")
def stop_web_app(name: str) -> str:
    """Stop a web app."""
    return azure_cli(f"webapp stop --name {name}")

@mcp.resource("azure://webapp/start/{name}")
def start_web_app(name: str) -> str:
    """Start a web app."""
    return azure_cli(f"webapp start --name {name}")

@mcp.resource("azure://webapp/deployment/list/{name}")
def list_web_app_deployments(name: str) -> str:
    """List deployments for a web app."""
    return azure_cli(f"webapp deployment list --name {name}")

# Monitor Operations
@mcp.resource("azure://monitor/metrics/list/{resource_id}")
def list_metrics(resource_id: str) -> str:
    """List available metrics for a resource."""
    return azure_cli(f"monitor metrics list --resource {resource_id}")

@mcp.resource("azure://monitor/log-analytics/workspace/list")
def list_log_analytics_workspaces() -> str:
    """List all Log Analytics workspaces."""
    return azure_cli("monitor log-analytics workspace list")

# Key Vault Operations
@mcp.resource("azure://keyvault/list")
def list_key_vaults() -> str:
    """List all Key Vaults."""
    return azure_cli("keyvault list")

@mcp.resource("azure://keyvault/secret/list/{vault_name}")
def list_key_vault_secrets(vault_name: str) -> str:
    """List secrets in a Key Vault."""
    return azure_cli(f"keyvault secret list --vault-name {vault_name}")

# Key Vault Operations - Extended
@mcp.resource("azure://keyvault/create/{name}/{resource_group}")
def create_key_vault(name: str, resource_group: str) -> str:
    """Create a new key vault."""
    return azure_cli(f"keyvault create --name {name} --resource-group {resource_group}")

@mcp.resource("azure://keyvault/delete/{name}")
def delete_key_vault(name: str) -> str:
    """Delete a key vault."""
    return azure_cli(f"keyvault delete --name {name}")

@mcp.resource("azure://keyvault/secret/set/{vault_name}/{secret_name}/{value}")
def set_key_vault_secret(vault_name: str, secret_name: str, value: str) -> str:
    """Set a secret in a key vault."""
    return azure_cli(f"keyvault secret set --vault-name {vault_name} --name {secret_name} --value {value}")

@mcp.resource("azure://keyvault/secret/delete/{vault_name}/{secret_name}")
def delete_key_vault_secret(vault_name: str, secret_name: str) -> str:
    """Delete a secret from a key vault."""
    return azure_cli(f"keyvault secret delete --vault-name {vault_name} --name {secret_name}")

# Resource Group Operations
@mcp.resource("azure://group/list")
def list_resource_groups() -> str:
    """List all resource groups."""
    return azure_cli("group list")

@mcp.resource("azure://group/show/{name}")
def get_resource_group(name: str) -> str:
    """Get details of a resource group."""
    return azure_cli(f"group show --name {name}")

# Resource Group Operations - Extended
@mcp.resource("azure://group/create/{name}/{location}")
def create_resource_group(name: str, location: str) -> str:
    """Create a new resource group."""
    return azure_cli(f"group create --name {name} --location {location}")

@mcp.resource("azure://group/delete/{name}")
def delete_resource_group(name: str) -> str:
    """Delete a resource group."""
    return azure_cli(f"group delete --name {name} --yes")

@mcp.resource("azure://group/lock/create/{name}")
def create_resource_group_lock(name: str) -> str:
    """Create a delete lock for a resource group."""
    return azure_cli(f"group lock create --name DoNotDelete --resource-group {name} --lock-type CanNotDelete")

# Container Registry Operations
@mcp.resource("azure://acr/list")
def list_container_registries() -> str:
    """List all container registries."""
    return azure_cli("acr list")

@mcp.resource("azure://acr/repository/list/{registry_name}")
def list_acr_repositories(registry_name: str) -> str:
    """List repositories in a container registry."""
    return azure_cli(f"acr repository list --name {registry_name}")

# Container Registry Operations - Extended
@mcp.resource("azure://acr/create/{name}/{resource_group}/{sku}")
def create_container_registry(name: str, resource_group: str, sku: str = "Basic") -> str:
    """Create a new container registry."""
    return azure_cli(f"acr create --name {name} --resource-group {resource_group} --sku {sku}")

@mcp.resource("azure://acr/delete/{name}")
def delete_container_registry(name: str) -> str:
    """Delete a container registry."""
    return azure_cli(f"acr delete --name {name} --yes")

@mcp.resource("azure://acr/update/{name}/{sku}")
def update_container_registry(name: str, sku: str) -> str:
    """Update a container registry SKU."""
    return azure_cli(f"acr update --name {name} --sku {sku}")

# Function App Operations
@mcp.resource("azure://functionapp/list")
def list_function_apps() -> str:
    """List all function apps."""
    return azure_cli("functionapp list")

@mcp.resource("azure://functionapp/show/{name}")
def get_function_app(name: str) -> str:
    """Get details of a function app."""
    return azure_cli(f"functionapp show --name {name}")

# Function App Operations - Extended
@mcp.resource("azure://functionapp/delete/{name}")
def delete_function_app(name: str) -> str:
    """Delete a function app."""
    return azure_cli(f"functionapp delete --name {name} --yes")

@mcp.resource("azure://functionapp/restart/{name}")
def restart_function_app(name: str) -> str:
    """Restart a function app."""
    return azure_cli(f"functionapp restart --name {name}")

@mcp.resource("azure://functionapp/stop/{name}")
def stop_function_app(name: str) -> str:
    """Stop a function app."""
    return azure_cli(f"functionapp stop --name {name}")

@mcp.resource("azure://functionapp/start/{name}")
def start_function_app(name: str) -> str:
    """Start a function app."""
    return azure_cli(f"functionapp start --name {name}")

# Identity Operations
@mcp.resource("azure://identity/list")
def list_managed_identities() -> str:
    """List all managed identities."""
    return azure_cli("identity list")

# Role Operations
@mcp.resource("azure://role/definition/list")
def list_role_definitions() -> str:
    """List all role definitions."""
    return azure_cli("role definition list")

@mcp.resource("azure://role/assignment/list")
def list_role_assignments() -> str:
    """List all role assignments."""
    return azure_cli("role assignment list")

# Role Operations - Extended
@mcp.resource("azure://role/assignment/create/{principal_id}/{role}/{scope}")
def create_role_assignment(principal_id: str, role: str, scope: str) -> str:
    """Create a role assignment."""
    return azure_cli(f"role assignment create --assignee {principal_id} --role {role} --scope {scope}")

@mcp.resource("azure://role/assignment/delete/{principal_id}/{role}/{scope}")
def delete_role_assignment(principal_id: str, role: str, scope: str) -> str:
    """Delete a role assignment."""
    return azure_cli(f"role assignment delete --assignee {principal_id} --role {role} --scope {scope}")

# Subscription Operations
@mcp.resource("azure://account/list")
def list_subscriptions() -> str:
    """List all subscriptions."""
    return azure_cli("account list")

@mcp.resource("azure://account/show")
def show_current_subscription() -> str:
    """Show the current subscription."""
    return azure_cli("account show")

if __name__ == "__main__":
    mcp.run()
