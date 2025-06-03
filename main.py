"""
Script Name: main.py
Description: Main entry point for the Azure MCP Server package.
            Starts the MCP server for Azure CLI integration.
Author: JCallico
Date Created: 2025-04-21
Version: 0.1.0
Python Version: >= 3.13
Dependencies: 
    - mcp[cli]>=1.6.0
    - python-dotenv>=1.0.0
License: MIT
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the Azure MCP server."""
    try:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        server_path = script_dir / "server-azure.py"
        
        # Check if server-azure.py exists
        if not server_path.exists():
            print(f"Error: server-azure.py not found at {server_path}")
            sys.exit(1)
        
        print("Starting Azure MCP Server...")
        print(f"Server file: {server_path}")
        print("The server will be available at http://127.0.0.1:6274")
        print("Press Ctrl+C to stop the server")
        print("-" * 50)
        
        # Use relative path to mcp command in virtual environment
        mcp_path = script_dir / ".venv" / "bin" / "mcp"
        
        # Check if mcp command exists at the expected location
        if not mcp_path.exists():
            print(f"Error: mcp command not found at {mcp_path}")
            print("Please ensure the virtual environment is set up and mcp[cli] is installed")
            sys.exit(1)
        
        # Start the MCP server using the relative mcp command
        result = subprocess.run([
            str(mcp_path), "run", str(server_path)
        ], cwd=script_dir)
        
        sys.exit(result.returncode)
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except FileNotFoundError:
        print("Error: 'mcp' command not found. Please ensure mcp[cli] is installed:")
        print("  pip install 'mcp[cli]>=1.6.0'")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
