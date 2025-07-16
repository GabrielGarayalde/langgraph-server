"""Google Sheets calculator tool for LangGraph agent.

Phase 0 implementation using service account for quick MVP deployment.
All sheets are owned by gabriel.garayalde@gmail.com and shared with service account.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import gspread
from google.oauth2.service_account import Credentials


class SheetsCalculatorService:
    """Service for executing calculations via Google Sheets."""
    
    def __init__(self):
        """Initialize with service account credentials and load dynamic configs."""
        # Use backend credentials directory
        backend_dir = Path(__file__).parent.parent.parent
        self.credentials_path = backend_dir / "credentials" / "service_account.json"
        self.configs_dir = backend_dir / "configs" / "calculators"
        
        # Load calculator configurations dynamically
        self.calculator_configs = self._load_calculator_configs()
        
        self._authenticate()
    
    def _load_calculator_configs(self) -> Dict[str, Dict]:
        """Load all calculator configurations from JSON files."""
        configs = {}
        
        if not self.configs_dir.exists():
            print(f"Warning: Configs directory not found: {self.configs_dir}")
            return configs
        
        for config_file in self.configs_dir.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                calc_name = config_file.stem
                configs[calc_name] = {
                    "sheet_id": config.get("sheet_id"),
                    "inputs": config.get("inputs", {}),
                    "outputs": config.get("outputs", {}),
                    "title": config.get("title", calc_name),
                    "description": config.get("description", ""),
                    "standard": config.get("standard", "")
                }
                
            except Exception as e:
                print(f"Warning: Could not load config {config_file}: {e}")
        
        return configs
    
    def _authenticate(self):
        """Authenticate with Google Sheets API using service account."""
        if not self.credentials_path.exists():
            raise FileNotFoundError(f"Service account credentials not found at {self.credentials_path}")
        
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(str(self.credentials_path), scopes=scope)
        self.client = gspread.authorize(creds)
    
    def list_available_calculators(self) -> List[Dict[str, str]]:
        """List all available calculator types."""
        calculators = []
        for calc_name, config in self.calculator_configs.items():
            calculators.append({
                "name": calc_name,
                "title": config.get("title", calc_name),
                "description": config.get("description", ""),
                "standard": config.get("standard", ""),
                "sheet_id": config.get("sheet_id", ""),
                "inputs": list(config.get("inputs", {}).keys()),
                "outputs": list(config.get("outputs", {}).keys())
            })
        return calculators
    
    def execute_calculation(self, calculator_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a calculation on the specified Google Sheet."""
        # Validate calculator exists
        if calculator_name not in self.calculator_configs:
            available = list(self.calculator_configs.keys())
            return {
                "error": f"Calculator '{calculator_name}' not found",
                "available_calculators": available
            }
        
        config = self.calculator_configs[calculator_name]
        sheet_id = config.get("sheet_id")
        
        if not config:
            return {"error": f"No configuration found for calculator '{calculator_name}'"}
        
        try:
            # Open the sheet
            sheet = self.client.open_by_key(sheet_id).sheet1
            
            # Write inputs
            input_updates = []
            for param, value in inputs.items():
                if param in config["inputs"]:
                    cell = config["inputs"][param]
                    input_updates.append({
                        'range': cell,
                        'values': [[value]]
                    })
            
            if input_updates:
                sheet.batch_update(input_updates, value_input_option='USER_ENTERED')
            
            # Wait for calculations
            time.sleep(1.5)
            
            # Read outputs
            results = {}
            for param, cell in config["outputs"].items():
                try:
                    value = sheet.get(cell, value_render_option='FORMATTED_VALUE')
                    if value and value[0] and value[0][0]:
                        # Try to convert to float if numeric
                        try:
                            results[param] = float(value[0][0])
                        except ValueError:
                            results[param] = value[0][0]  # Keep as string
                    else:
                        results[param] = None
                except Exception as e:
                    results[param] = f"Error reading {cell}: {str(e)}"
            
            return {
                "calculator": calculator_name,
                "inputs": inputs,
                "results": results,
                "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            }
            
        except Exception as e:
            return {
                "error": f"Error executing calculation: {str(e)}",
                "calculator": calculator_name,
                "inputs": inputs
            }


# Initialize service (singleton)
_sheets_service = None

def get_sheets_service() -> SheetsCalculatorService:
    """Get or create the sheets calculator service."""
    global _sheets_service
    if _sheets_service is None:
        _sheets_service = SheetsCalculatorService()
    return _sheets_service


@tool
def sheets_calculate(
    calculator_name: str,
    inputs: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute engineering calculations using Google Sheets.
    
    This tool connects to pre-configured Google Sheets containing engineering formulas
    and calculations. Engineers maintain the formulas in the sheets while this tool
    handles input/output operations.
    
    Available calculators:
    - steel_beam: AS 4100 steel beam design
    - concrete_column: AS 3600 concrete column design
    - timber_design: AS 1720 timber member design
    
    Args:
        calculator_name: Name of the calculator to use
        inputs: Dictionary of input parameters (varies by calculator)
        
    Returns:
        Dictionary containing calculation results and any errors
    """
    try:
        service = get_sheets_service()
        return service.execute_calculation(calculator_name, inputs)
    except Exception as e:
        return {"error": str(e)}


@tool
def list_sheets_calculators() -> List[Dict[str, str]]:
    """List all available Google Sheets calculators.
    
    Returns information about each calculator including required inputs
    and available outputs.
    """
    try:
        service = get_sheets_service()
        return {"calculators": service.list_available_calculators()}
    except Exception as e:
        return {"error": str(e)}