"""
Script Name: server-azure.py
Description: MCP server implementation for Azure CLI integration. Provides programmatic
            access to Azure Cloud resources through Azure CLI commands with comprehensive
            support for compute, storage, networking, security, and resource management operations.
Author: JCallico
Date Created: 2025-04-21
Version: 0.1.0
Python Version: >= 3.13
Dependencies: 
    - mcp[cli]>=0.1.0
    - python-dotenv>=1.0.0
    - azure-cli>=2.57.0
License: MIT

Usage:
    Start the server:
    $ mcp run server-azure.py
    
    The server will be available at http://127.0.0.1:6274
"""

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
import subprocess
import os
from dotenv import load_dotenv
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Load environment variables from .env file
load_dotenv()

# Pass the Flask app instance to FastMCP
mcp = FastMCP("Azure")

@mcp.prompt()
def create_vm() -> List[base.Message]:
    return [
        base.UserMessage("Let's create a new virtual machine on Azure"),
        base.AssistantMessage("I can help with that. I can create VMs with various configurations:"),
        base.AssistantMessage("""
- Create new VMs with specific sizes and OS images
- Configure VM networking and storage
- Set up in any Azure region
- Handle both Windows and Linux VMs

Examples:
- Create a new Ubuntu VM in West US 2 with 2 cores and 8GB RAM
- Create a Windows VM with 16GB RAM
- Deploy a VM with custom networking
- Create a VM in an existing resource group"""),
        base.UserMessage("Create a Ubuntu VM in West US 2"),
        base.AssistantMessage("I'll help create a Ubuntu VM in West US 2. First, let me check your subscription details.")
    ]

@mcp.prompt()
def manage_infrastructure() -> List[base.Message]:
    return [
        base.UserMessage("I need to manage Azure infrastructure"),
        base.AssistantMessage("I can help with managing Azure infrastructure. Here's what I can do:"),
        base.AssistantMessage("""
- Virtual Machines and VM Scale Sets
    * Start, stop, restart, or delete VMs
    * Scale VM resources up or down
    * Configure VM networking and storage
- Storage Accounts and Containers
    * Create and manage storage accounts
    * Set up blob containers
    * Configure access and networking
- Virtual Networks and NSGs
    * Set up VNets and subnets
    * Configure NSG rules
    * Manage public IPs
- App Services and Function Apps
    * Deploy and manage web applications
    * Configure app settings and scaling
- Container Registries
    * Manage container images
    * Configure registry access

Examples:
- Start/stop a virtual machine
- Scale out a VM scale set to 5 instances
- Create a storage account with LRS redundancy
- Set up a virtual network with custom address space""")
    ]

@mcp.prompt()
def manage_security() -> List[base.Message]:
    return [
        base.UserMessage("I need to manage Azure security features"),
        base.AssistantMessage("I can help with Azure security features. Here's what I can do:"),
        base.AssistantMessage("""
- Key Vault management
    * Create and delete key vaults
    * Manage secrets
    * Configure access policies
- Role-based access control (RBAC)
    * List and create role assignments
    * Manage role definitions
    * Configure scoped permissions
- Managed Identities
    * List and manage identities
    * Configure identity assignments
- Service Principals
    * Create and manage service principals
    * Configure authentication

Examples:
- Create a new key vault
- List role assignments
- Create a role assignment for a user
- List managed identities
- Create a new service principal""")
    ]

@mcp.prompt()
def manage_monitoring() -> List[base.Message]:
    return [
        base.UserMessage("I need to monitor Azure resources"),
        base.AssistantMessage("I can help you monitor Azure resources. Here's what I can do:"),
        base.AssistantMessage("""
- Azure Monitor metrics
    * Resource utilization
    * Performance metrics
    * Custom metrics
- Log Analytics workspaces
    * Query logs
    * Set up workspaces
    * Configure data collection
- Resource health checks
    * Service health
    * Resource status
    * Diagnostic settings

Examples:
- Show metrics for a resource
- List log analytics workspaces
- Check resource health status
- Monitor VM performance
- Get web app metrics""")
    ]

# Track token expiration
TOKEN_EXPIRES_AT = None
TOKEN_REFRESH_MARGIN = 300  # Refresh token 5 minutes before expiration

# Default timeout for long-running operations (in seconds)
DEFAULT_OPERATION_TIMEOUT = 60

async def run_azure_command(command_parts, timeout=None, check_status=False):
    """Run an Azure CLI command asynchronously and return the output."""
    try:
        # Set a larger buffer size for handling large responses
        process = await asyncio.create_subprocess_exec(
            *command_parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024 * 1024  # 1MB buffer size
        )
        
        if timeout:
            try:
                stdout = bytearray()
                stderr = bytearray()
                
                # Process output in chunks
                async def read_stream(stream, buffer):
                    while True:
                        chunk = await stream.read(32768)  # 32KB chunks
                        if not chunk:
                            break
                        buffer.extend(chunk)
                
                # Wait for both streams with timeout
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(process.stdout, stdout),
                        read_stream(process.stderr, stderr)
                    ),
                    timeout=timeout
                )
                
                await process.wait()
                
            except asyncio.TimeoutError:
                if check_status:
                    process.kill()
                    return json.dumps({
                        "status": "running",
                        "message": "Operation is still in progress. Please check status later.",
                        "error": None
                    })
                else:
                    process.kill()
                    return json.dumps({
                        "status": "timeout",
                        "message": f"Operation timed out after {timeout} seconds",
                        "error": "Operation took longer than expected"
                    })
        else:
            stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command_parts, stdout, stderr)

        try:
            # Attempt to decode and parse as JSON with a higher size limit
            return stdout.decode('utf-8')
        except UnicodeDecodeError:
            # Handle potential encoding issues
            return json.dumps({
                "status": "error",
                "message": "Unable to decode command output",
                "error": "Output encoding error"
            })

    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode() if hasattr(e.stderr, 'decode') else str(e.stderr)
        return json.dumps({
            "status": "error",
            "message": "Command execution failed",
            "error": error_message
        })

async def authenticate_with_service_principal():
    """Authenticate using a service principal and set the access token."""
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant_id = os.getenv("AZURE_TENANT_ID")

    if not client_id or not client_secret or not tenant_id:
        raise EnvironmentError("Missing environment variables for service principal authentication")

    try:
        # Authenticate using the service principal
        await run_azure_command([
            "az", "login",
            "--service-principal",
            "--username", client_id,
            "--password", client_secret,
            "--tenant", tenant_id
        ])

        # Get token with expiration info
        result = await run_azure_command(["az", "account", "get-access-token", "--output", "json"])
        token_info = json.loads(result)
        
        global TOKEN_EXPIRES_AT
        TOKEN_EXPIRES_AT = datetime.strptime(token_info['expiresOn'], "%Y-%m-%d %H:%M:%S.%f")
        
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to authenticate with service principal: {str(e)}")

async def ensure_valid_token():
    """Ensure we have a valid token, refreshing if needed."""
    global TOKEN_EXPIRES_AT
    
    if TOKEN_EXPIRES_AT is None or \
       datetime.now() + timedelta(seconds=TOKEN_REFRESH_MARGIN) >= TOKEN_EXPIRES_AT:
        await authenticate_with_service_principal()

@mcp.tool()
async def azure_cli(command: str, timeout: int = DEFAULT_OPERATION_TIMEOUT) -> str:
    """Run an Azure CLI command and return the output."""
    try:
        # Ensure we have a valid token before running any command
        await ensure_valid_token()
        
        # Remove 'az' prefix if present
        if command.startswith('az '):
            command = command[3:]
            
        # Ensure output is in JSON format if not explicitly set to table format
        if not any(fmt in command for fmt in ['--output', '-o']):
            command += " --output json"
        
        # Determine if this is a long-running operation that supports status checking
        check_status = any(op in command.lower() for op in [
            'create', 'delete', 'start', 'stop', 'restart', 'update',
            'scale', 'backup', 'restore', 'deploy'
        ])
        
        result = await run_azure_command(
            ["az"] + command.split(),
            timeout=timeout,
            check_status=check_status
        )
        
        try:
            if "--output table" not in command and "-o table" not in command:
                # Attempt to parse the result as JSON
                parsed_result = json.loads(result)
                return json.dumps(parsed_result)
            return result
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "Command output is not valid JSON",
                "output": result
            })
            
    except Exception as e:
        if "authentication failed" in str(e).lower():
            await authenticate_with_service_principal()
            return await azure_cli(command, timeout)  # Retry once
        return json.dumps({
            "status": "error",
            "message": "Command execution failed",
            "error": str(e)
        })

# Initialize authentication
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(authenticate_with_service_principal())

# Update all resource functions to be async
@mcp.resource("azure://compute/vm/list")
async def list_virtual_machines() -> str:
    """List all virtual machines in the current subscription."""
    return await azure_cli("vm list")

@mcp.resource("azure://compute/vm/show/{name}")
async def get_virtual_machine(name: str) -> str:
    """Get details of a specific virtual machine."""
    return await azure_cli(f"vm show --name {name}")

@mcp.resource("azure://compute/vm/start/{name}")
async def start_virtual_machine(name: str) -> str:
    """Start a virtual machine."""
    return await azure_cli(f"vm start --name {name}")

@mcp.resource("azure://compute/vm/stop/{name}")
async def stop_virtual_machine(name: str) -> str:
    """Stop a virtual machine."""
    return await azure_cli(f"vm stop --name {name}")

@mcp.resource("azure://compute/vmss/list")
async def list_vmss() -> str:
    """List all virtual machine scale sets."""
    return await azure_cli("vmss list")

@mcp.resource("azure://compute/aks/list")
async def list_aks_clusters() -> str:
    """List all AKS clusters."""
    return await azure_cli("aks list")

# Compute Operations - Extended
@mcp.resource("azure://compute/vm/delete/{name}")
async def delete_virtual_machine(name: str) -> str:
    """Delete a virtual machine."""
    return await azure_cli(f"vm delete --name {name} --yes")

@mcp.resource("azure://compute/vm/restart/{name}")
async def restart_virtual_machine(name: str) -> str:
    """Restart a virtual machine."""
    return await azure_cli(f"vm restart --name {name}")

@mcp.resource("azure://compute/vmss/scale/{name}/{capacity}")
async def scale_vmss(name: str, capacity: int) -> str:
    """Scale a virtual machine scale set to a specific capacity."""
    return await azure_cli(f"vmss scale --name {name} --new-capacity {capacity}")

@mcp.resource("azure://compute/vmss/update/{name}")
async def update_vmss(name: str) -> str:
    """Update instances in a virtual machine scale set."""
    return await azure_cli(f"vmss update-instances --name {name} --instance-ids *")

@mcp.resource("azure://compute/vm/create/{name}/{resource_group}")
async def create_virtual_machine(name: str, resource_group: str) -> str:
    """Create a new virtual machine.
    
    Args:
        name: Name of the VM
        resource_group: Resource group to create the VM in
    """
    command = f"vm create --name {name} --resource-group {resource_group}"
    command += " --image UbuntuLTS --size Standard_D2s_v3 --admin-username azureuser"
    return await azure_cli(command)

@mcp.resource("azure://compute/vm/create/{name}/{resource_group}/{image}")
async def create_virtual_machine_with_image(name: str, resource_group: str, image: str) -> str:
    """Create a new virtual machine with specified image.
    
    Args:
        name: Name of the VM
        resource_group: Resource group to create the VM in
        image: VM image to use
    """
    command = f"vm create --name {name} --resource-group {resource_group}"
    command += f" --image {image} --size Standard_D2s_v3 --admin-username azureuser"
    return await azure_cli(command)

@mcp.resource("azure://compute/vm/create/{name}/{resource_group}/{image}/{size}")
async def create_virtual_machine_with_size(name: str, resource_group: str, image: str, size: str) -> str:
    """Create a new virtual machine with specified image and size.
    
    Args:
        name: Name of the VM
        resource_group: Resource group to create the VM in
        image: VM image to use
        size: VM size (e.g. Standard_D2s_v3)
    """
    command = f"vm create --name {name} --resource-group {resource_group}"
    command += f" --image {image} --size {size} --admin-username azureuser"
    return await azure_cli(command)

@mcp.resource("azure://compute/vm/create/{name}/{resource_group}/{image}/{size}/{location}")
async def create_virtual_machine_with_location(name: str, resource_group: str, image: str, size: str, location: str) -> str:
    """Create a new virtual machine with all specifications.
    
    Args:
        name: Name of the VM
        resource_group: Resource group to create the VM in
        image: VM image to use
        size: VM size (e.g. Standard_D2s_v3)
        location: Azure region to create the VM in
    """
    command = f"vm create --name {name} --resource-group {resource_group}"
    command += f" --image {image} --size {size} --location {location} --admin-username azureuser"
    return await azure_cli(command)

# Storage Operations
@mcp.resource("azure://storage/account/list")
async def list_storage_accounts() -> str:
    """List all storage accounts."""
    return await azure_cli("storage account list")

@mcp.resource("azure://storage/account/show/{name}")
async def get_storage_account(name: str) -> str:
    """Get details of a storage account."""
    return await azure_cli(f"storage account show --name {name}")

@mcp.resource("azure://storage/container/list/{account_name}")
async def list_storage_containers(account_name: str) -> str:
    """List containers in a storage account."""
    return await azure_cli(f"storage container list --account-name {account_name}")

# Storage Operations - Extended
@mcp.resource("azure://storage/account/create/{name}/{resource_group}/{sku}")
async def create_storage_account(name: str, resource_group: str, sku: str = "Standard_LRS") -> str:
    """Create a new storage account."""
    return await azure_cli(f"storage account create --name {name} --resource-group {resource_group} --sku {sku}")

@mcp.resource("azure://storage/account/delete/{name}")
async def delete_storage_account(name: str) -> str:
    """Delete a storage account."""
    return await azure_cli(f"storage account delete --name {name} --yes")

@mcp.resource("azure://storage/container/create/{account_name}/{container_name}")
async def create_storage_container(account_name: str, container_name: str) -> str:
    """Create a container in a storage account."""
    return await azure_cli(f"storage container create --account-name {account_name} --name {container_name}")

@mcp.resource("azure://storage/container/delete/{account_name}/{container_name}")
async def delete_storage_container(account_name: str, container_name: str) -> str:
    """Delete a container from a storage account."""
    return await azure_cli(f"storage container delete --account-name {account_name} --name {container_name}")

# Networking Operations
@mcp.resource("azure://network/vnet/list")
async def list_virtual_networks() -> str:
    """List all virtual networks."""
    return await azure_cli("network vnet list")

@mcp.resource("azure://network/nsg/list")
async def list_network_security_groups() -> str:
    """List all network security groups."""
    return await azure_cli("network nsg list")

@mcp.resource("azure://network/public-ip/list")
async def list_public_ips() -> str:
    """List all public IP addresses."""
    return await azure_cli("network public-ip list")

# Database Operations
@mcp.resource("azure://sql/server/list")
async def list_sql_servers() -> str:
    """List all SQL servers."""
    return await azure_cli("sql server list")

@mcp.resource("azure://cosmos/list")
async def list_cosmos_accounts() -> str:
    """List all Cosmos DB accounts."""
    return await azure_cli("cosmos list")

# App Service Operations
@mcp.resource("azure://webapp/list")
async def list_web_apps() -> str:
    """List all web apps."""
    return await azure_cli("webapp list")

@mcp.resource("azure://webapp/show/{name}")
async def get_web_app(name: str) -> str:
    """Get details of a web app."""
    return await azure_cli(f"webapp show --name {name}")

@mcp.resource("azure://webapp/restart/{name}")
async def restart_web_app(name: str) -> str:
    """Restart a web app."""
    return await azure_cli(f"webapp restart --name {name}")

# App Service Operations - Extended
@mcp.resource("azure://webapp/create/{name}/{resource_group}/{plan}")
async def create_web_app(name: str, resource_group: str, plan: str) -> str:
    """Create a new web app."""
    return await azure_cli(f"webapp create --name {name} --resource-group {resource_group} --plan {plan}")

@mcp.resource("azure://webapp/delete/{name}")
async def delete_web_app(name: str) -> str:
    """Delete a web app."""
    return await azure_cli(f"webapp delete --name {name} --yes")

@mcp.resource("azure://webapp/stop/{name}")
async def stop_web_app(name: str) -> str:
    """Stop a web app."""
    return await azure_cli(f"webapp stop --name {name}")

@mcp.resource("azure://webapp/start/{name}")
async def start_web_app(name: str) -> str:
    """Start a web app."""
    return await azure_cli(f"webapp start --name {name}")

@mcp.resource("azure://webapp/deployment/list/{name}")
async def list_web_app_deployments(name: str) -> str:
    """List deployments for a web app."""
    return await azure_cli(f"webapp deployment list --name {name}")

# Monitor Operations
@mcp.resource("azure://monitor/metrics/list/{resource_id}")
async def list_metrics(resource_id: str) -> str:
    """List available metrics for a resource."""
    return await azure_cli(f"monitor metrics list --resource {resource_id}")

@mcp.resource("azure://monitor/log-analytics/workspace/list")
async def list_log_analytics_workspaces() -> str:
    """List all Log Analytics workspaces."""
    return await azure_cli("monitor log-analytics workspace list")

# Key Vault Operations
@mcp.resource("azure://keyvault/list")
async def list_key_vaults() -> str:
    """List all Key Vaults."""
    return await azure_cli("keyvault list")

@mcp.resource("azure://keyvault/secret/list/{vault_name}")
async def list_key_vault_secrets(vault_name: str) -> str:
    """List secrets in a Key Vault."""
    return await azure_cli(f"keyvault secret list --vault-name {vault_name}")

# Key Vault Operations - Extended
@mcp.resource("azure://keyvault/create/{name}/{resource_group}")
async def create_key_vault(name: str, resource_group: str) -> str:
    """Create a new key vault."""
    return await azure_cli(f"keyvault create --name {name} --resource-group {resource_group}")

@mcp.resource("azure://keyvault/delete/{name}")
async def delete_key_vault(name: str) -> str:
    """Delete a key vault."""
    return await azure_cli(f"keyvault delete --name {name}")

@mcp.resource("azure://keyvault/secret/set/{vault_name}/{secret_name}/{value}")
async def set_key_vault_secret(vault_name: str, secret_name: str, value: str) -> str:
    """Set a secret in a key vault."""
    return await azure_cli(f"keyvault secret set --vault-name {vault_name} --name {secret_name} --value {value}")

@mcp.resource("azure://keyvault/secret/delete/{vault_name}/{secret_name}")
async def delete_key_vault_secret(vault_name: str, secret_name: str) -> str:
    """Delete a secret from a key vault."""
    return await azure_cli(f"keyvault secret delete --vault-name {vault_name} --name {secret_name}")

# Resource Group Operations
@mcp.resource("azure://group/list")
async def list_resource_groups() -> str:
    """List all resource groups."""
    return await azure_cli("group list")

@mcp.resource("azure://group/show/{name}")
async def get_resource_group(name: str) -> str:
    """Get details of a resource group."""
    return await azure_cli(f"group show --name {name}")

# Resource Group Operations - Extended
@mcp.resource("azure://group/create/{name}/{location}")
async def create_resource_group(name: str, location: str) -> str:
    """Create a new resource group."""
    return await azure_cli(f"group create --name {name} --location {location}")

@mcp.resource("azure://group/delete/{name}")
async def delete_resource_group(name: str) -> str:
    """Delete a resource group."""
    return await azure_cli(f"group delete --name {name} --yes")

@mcp.resource("azure://group/lock/create/{name}")
async def create_resource_group_lock(name: str) -> str:
    """Create a delete lock for a resource group."""
    return await azure_cli(f"group lock create --name DoNotDelete --resource-group {name} --lock-type CanNotDelete")

# Container Registry Operations
@mcp.resource("azure://acr/list")
async def list_container_registries() -> str:
    """List all container registries."""
    return await azure_cli("acr list")

@mcp.resource("azure://acr/repository/list/{registry_name}")
async def list_acr_repositories(registry_name: str) -> str:
    """List repositories in a container registry."""
    return await azure_cli(f"acr repository list --name {registry_name}")

# Container Registry Operations - Extended
@mcp.resource("azure://acr/create/{name}/{resource_group}/{sku}")
async def create_container_registry(name: str, resource_group: str, sku: str = "Basic") -> str:
    """Create a new container registry."""
    return await azure_cli(f"acr create --name {name} --resource-group {resource_group} --sku {sku}")

@mcp.resource("azure://acr/delete/{name}")
async def delete_container_registry(name: str) -> str:
    """Delete a container registry."""
    return await azure_cli(f"acr delete --name {name} --yes")

@mcp.resource("azure://acr/update/{name}/{sku}")
async def update_container_registry(name: str, sku: str) -> str:
    """Update a container registry SKU."""
    return await azure_cli(f"acr update --name {name} --sku {sku}")

# Function App Operations
@mcp.resource("azure://functionapp/list")
async def list_function_apps() -> str:
    """List all function apps."""
    return await azure_cli("functionapp list")

@mcp.resource("azure://functionapp/show/{name}")
async def get_function_app(name: str) -> str:
    """Get details of a function app."""
    return await azure_cli(f"functionapp show --name {name}")

# Function App Operations - Extended
@mcp.resource("azure://functionapp/delete/{name}")
async def delete_function_app(name: str) -> str:
    """Delete a function app."""
    return await azure_cli(f"functionapp delete --name {name} --yes")

@mcp.resource("azure://functionapp/restart/{name}")
async def restart_function_app(name: str) -> str:
    """Restart a function app."""
    return await azure_cli(f"functionapp restart --name {name}")

@mcp.resource("azure://functionapp/stop/{name}")
async def stop_function_app(name: str) -> str:
    """Stop a function app."""
    return await azure_cli(f"functionapp stop --name {name}")

@mcp.resource("azure://functionapp/start/{name}")
async def start_function_app(name: str) -> str:
    """Start a function app."""
    return await azure_cli(f"functionapp start --name {name}")

# Identity Operations
@mcp.resource("azure://identity/list")
async def list_managed_identities() -> str:
    """List all managed identities."""
    return await azure_cli("identity list")

# Role Operations
@mcp.resource("azure://role/definition/list")
async def list_role_definitions() -> str:
    """List all role definitions."""
    return await azure_cli("role definition list")

@mcp.resource("azure://role/assignment/list")
async def list_role_assignments() -> str:
    """List all role assignments."""
    return await azure_cli("role assignment list")

# Role Operations - Extended
@mcp.resource("azure://role/assignment/create/{principal_id}/{role}/{scope}")
async def create_role_assignment(principal_id: str, role: str, scope: str) -> str:
    """Create a role assignment."""
    return await azure_cli(f"role assignment create --assignee {principal_id} --role {role} --scope {scope}")

@mcp.resource("azure://role/assignment/delete/{principal_id}/{role}/{scope}")
async def delete_role_assignment(principal_id: str, role: str, scope: str) -> str:
    """Delete a role assignment."""
    return await azure_cli(f"role assignment delete --assignee {principal_id} --role {role} --scope {scope}")

# Subscription Operations
@mcp.resource("azure://account/list")
async def list_subscriptions() -> str:
    """List all subscriptions."""
    return await azure_cli("account list")

@mcp.resource("azure://account/show")
async def show_current_subscription() -> str:
    """Show the current subscription."""
    return await azure_cli("account show")

if __name__ == "__main__":
    mcp.run()
