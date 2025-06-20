"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example)

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""

import os
import json
from pathlib import Path
from typing import Annotated, Any, Callable, Dict, List, Optional, Union, cast

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_tavily import TavilySearch  # type: ignore[import-not-found]

from react_agent.configuration import Configuration

# Pinecone imports and config
try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None

load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Medical Pinecone Configuration
MEDICAL_PINECONE_INDEX_NAME = "anna-medical"
MEDICAL_DEFAULT_NAMESPACE = "anna-medical-namespace"

# Engineering Pinecone Configuration
ENGINEERING_PINECONE_INDEX_NAME = "engineering-index"
ENGINEERING_DEFAULT_NAMESPACE = "engineering-namespace"
# Engineering sparse index name for lexical retrieval
ENGINEERING_SPARSE_PINECONE_INDEX_NAME = "engineering-index-sparse"

_pinecone_client = None

def get_pinecone_client():
    """Get or initialize the Pinecone client instance.
    
    Returns:
        Pinecone client instance or None if not configured.
    """
    global _pinecone_client
    if _pinecone_client is None and PINECONE_API_KEY and Pinecone:
        _pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
    return _pinecone_client


async def search(query: str) -> Optional[dict[str, Any]]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    configuration = Configuration.from_context()
    wrapped = TavilySearch(max_results=configuration.max_search_results)
    return cast(dict[str, Any], await wrapped.ainvoke({"query": query}))


async def calculator(expression: str) -> float:
    """Evaluate a simple arithmetic expression.

    Args:
        expression: A string representing a simple arithmetic expression
            (e.g., "2 + 2", "10 * 5", "100 / 4").
            Supports addition (+), subtraction (-), multiplication (*), and division (/).

    Returns:
        The result of the calculation.
    """
    try:
        # A simple and relatively safe way to evaluate basic math expressions.
        # For production, consider a more robust math expression parser.
        allowed_chars = "0123456789+-*/(). "
        if not all(char in allowed_chars for char in expression):
            raise ValueError("Expression contains invalid characters.")
        # pylint: disable=eval-used
        result = eval(expression)
        return float(result)
    except Exception as e:
        return f"Error evaluating expression '{expression}': {e}"


async def calculate_slenderness_ratio(
    effective_length: float, 
    radius_of_gyration: float
) -> str:
    """Calculate slenderness ratio for structural steel members per AS 4100-1998.
    
    Args:
        effective_length: Effective length in mm
        radius_of_gyration: Radius of gyration in mm
        

    """
    if radius_of_gyration <= 0:
        return "Error: Radius of gyration must be positive"
    
    ratio = effective_length / radius_of_gyration
    
    if ratio <= 50:
        classification = "Short column"
    elif ratio <= 100:
        classification = "Intermediate column"
    else:
        classification = "Slender column"
    
    return f"""
SLENDERNESS CALCULATION (AS 4100-1998):
• Effective length (le): {effective_length:.1f} mm
• Radius of gyration (r): {radius_of_gyration:.1f} mm
• Slenderness ratio (le/r): {ratio:.2f}
• Classification: {classification}

DESIGN NOTES:
• AS 4100-1998 recommends le/r ≤ 200 for compression members
• Consider buckling effects for slender members
"""


@tool
def search_engineering_database(
    query: Annotated[str, "Search query for AS 4100-1998 engineering documents"],
    top_k: Annotated[int, "Number of results to return (default: 5)"] = 5,
    namespace: Annotated[str, "Database namespace to search (default: aus-standards-namespace)"] = ENGINEERING_DEFAULT_NAMESPACE
) -> Dict[str, Any]:
    """Search the Pinecone vector database for AS 4100-1998 engineering documents and standards.
    
    Returns a structured dictionary containing the search results, including metadata and content for each hit.
    This tool searches through Australian Standards related to engineering, particularly AS 4100-1998.
    
    Use this tool to find:
    - Specific clauses and sections from AS 4100-1998
    - Design rules and formulas for steel structures
    - Material properties and specifications
    - Commentary and explanations related to the standard
    """
    # Check if Pinecone is configured
    if not PINECONE_API_KEY:
        return {
            "type": "database_search_error",
            "error": "PINECONE_API_KEY not found in environment variables. Please configure Pinecone access."
        }
    try:
        # Get Pinecone client
        pc = get_pinecone_client()
        if not pc:
            return {
                "type": "database_search_error",
                "error": "Failed to initialize Pinecone client."
            }
        # Get both dense and sparse Pinecone indexes
        index_dense = pc.Index(ENGINEERING_PINECONE_INDEX_NAME)
        index_sparse = pc.Index(ENGINEERING_SPARSE_PINECONE_INDEX_NAME)

        # Common search parameters for both searches
        search_params = {
            "namespace": namespace,
            "query": {
                "top_k": min(top_k, 10),
                "inputs": {"text": query}
            },
            "rerank": {
                "model": "bge-reranker-v2-m3",
                "top_n": min(top_k, 10),
                "rank_fields": ["chunk_text"]
            }
        }

        # Execute searches on both indexes
        dense_response = index_dense.search(**search_params)
        sparse_response = index_sparse.search(**search_params)

        # Combine and deduplicate hits
        combined_hits = dense_response.get("result", {}).get("hits", []) + \
                        sparse_response.get("result", {}).get("hits", [])

        # If no hits at all, return early (handled later in existing logic)
        if not combined_hits:
            pinecone_response = {"result": {"hits": []}}
        else:
            seen_keys: set[tuple[str, str]] = set()
            deduped_hits = []
            for hit in combined_hits:
                fields = hit.get("fields", {})
                # Uniqueness key: document + page number (falls back to chunk text hash)
                key = (
                    fields.get("source_document_id", ""),
                    str(fields.get("page_number", ""))
                )
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                deduped_hits.append(hit)

            # Sort by descending Pinecone score and truncate to top_k
            deduped_hits.sort(key=lambda h: h.get("_score", 0.0), reverse=True)
            deduped_hits = deduped_hits[: min(top_k, 10)]
            pinecone_response = {"result": {"hits": deduped_hits}}
        # Process results
        if not pinecone_response.get("result", {}).get("hits"):
            return {
                "type": "database_search_results",
                "query": query,
                "message": f"No relevant documents found for query: '{query}'",
                "results": []
            }
        # Format the results
        processed_results = []
        for hit in pinecone_response["result"]["hits"]:
            fields = hit.get("fields", {})
            result_item = {
                "source_document_id": fields.get("source_document_id", "Unknown Document"),
                "page_number": fields.get("page_number", "Unknown Page"),
                "score": hit.get("_score", 0.0),
                "content": fields.get("chunk_text", ""),
                "clauses_mentioned": fields.get("clauses_mentioned"),
                "tables_mentioned": fields.get("tables_mentioned"),
                "figures_mentioned": fields.get("figures_mentioned")
            }
            processed_results.append(result_item)
        return {
            "type": "database_search_results",
            "query": query,
            "count": len(processed_results),
            "results": processed_results
        }
    except Exception as e:
        return {
            "type": "database_search_error",
            "error": f"Error searching engineering database: {str(e)}",
            "details": "Please check your Pinecone configuration and try again."
        }


@tool
def search_medical_database(
    query: Annotated[str, "Search query for medical documents and literature"],
    top_k: Annotated[int, "Number of results to return (default: 5)"] = 5,
    namespace: Annotated[str, "Database namespace to search (default: anna-medical-namespace)"] = MEDICAL_DEFAULT_NAMESPACE
) -> Dict[str, Any]:
    """Search the Pinecone vector database for medical documents and literature.
    
    Returns a structured dictionary containing the search results, including metadata and content for each hit.
    This tool searches through medical literature, research papers, clinical guidelines, 
    drug information, and medical reference materials.
    
    Use this tool to find:
    - Medical research and clinical studies
    - Drug information and pharmacology
    - Medical procedures and protocols
    - Disease information and symptoms
    - Clinical guidelines and best practices
    - Medical terminology and definitions
    """
    # Check if Pinecone is configured
    if not PINECONE_API_KEY:
        return {
            "type": "database_search_error",
            "error": "PINECONE_API_KEY not found in environment variables. Please configure Pinecone access."
        }
    try:
        # Get Pinecone client
        pc = get_pinecone_client()
        if not pc:
            return {
                "type": "database_search_error",
                "error": "Failed to initialize Pinecone client."
            }
        # Get the index
        index = pc.Index(MEDICAL_PINECONE_INDEX_NAME)
        # Prepare the search parameters
        search_params = {
            "namespace": namespace,
            "query": {
                "top_k": min(top_k, 10),
                "inputs": {"text": query}
            },
            "rerank": {
                "model": "bge-reranker-v2-m3",
                "top_n": min(top_k, 10),
                "rank_fields": ["chunk_text"]
            }
        }
        # Execute the search
        pinecone_response = index.search(**search_params)
        # Process results
        if not pinecone_response.get("result", {}).get("hits"):
            return {
                "type": "database_search_results",
                "query": query,
                "message": f"No relevant medical documents found for query: '{query}'",
                "results": []
            }
        # Format the results
        processed_results = []
        for hit in pinecone_response["result"]["hits"]:
            fields = hit.get("fields", {})
            result_item = {
                "source_document_id": fields.get("source_document_id", "Unknown Document"),
                "page_number": fields.get("page_number", "Unknown Page"),
                "score": hit.get("_score", 0.0),
                "content": fields.get("chunk_text", ""),
            }
            processed_results.append(result_item)
        return {
            "type": "database_search_results",
            "query": query,
            "count": len(processed_results),
            "results": processed_results
        }
    except Exception as e:
        return {
            "type": "database_search_error",
            "error": f"Error searching medical database: {str(e)}",
            "details": "Please check your Pinecone configuration and try again."
        }


# Excel integration imports
try:
    import openpyxl
    from openpyxl import Workbook, load_workbook
    from openpyxl.utils import get_column_letter, column_index_from_string
except ImportError:
    openpyxl = None
    Workbook = None
    load_workbook = None

# Excel Configuration
EXCEL_SPREADSHEETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "company_spreadsheets")

@tool
def list_excel_files(directory_path: str = None) -> Dict[str, Any]:
    """List all Excel files in the company spreadsheets directory.
    
    Args:
        directory_path: Optional custom directory path. If not provided, uses default company_spreadsheets directory.
        
    Returns:
        Dictionary containing list of Excel files with their metadata.
    """
    if openpyxl is None:
        return {
            "type": "error",
            "error": "openpyxl not installed. Please install with: pip install openpyxl"
        }
    
    try:
        if directory_path is None:
            directory_path = EXCEL_SPREADSHEETS_DIR
        
        if not os.path.exists(directory_path):
            return {
                "type": "excel_files_list",
                "count": 0,
                "files": [],
                "message": f"Directory not found: {directory_path}"
            }
        
        excel_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.endswith(('.xlsx', '.xlsm')):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, directory_path)
                    
                    # Get sheet names
                    try:
                        wb = load_workbook(file_path, read_only=True)
                        sheet_names = wb.sheetnames
                        wb.close()
                    except Exception:
                        sheet_names = ["Unable to read"]
                    
                    excel_files.append({
                        "filename": file,
                        "relative_path": relative_path,
                        "full_path": file_path,
                        "sheet_names": sheet_names
                    })
        
        return {
            "type": "excel_files_list",
            "count": len(excel_files),
            "files": excel_files
        }
        
    except Exception as e:
        return {
            "type": "error",
            "error": f"Error listing Excel files: {str(e)}"
        }

@tool
def read_excel_sheet(file_path: str, sheet_name: str, cell_range: str) -> Dict[str, Any]:
    """Read data from an Excel sheet within a specified cell range.
    
    Args:
        file_path: Path to Excel file (relative to company_spreadsheets directory)
        sheet_name: Name of the worksheet to read from
        cell_range: Cell range to read (e.g., 'A1:C10' or 'B5')
        
    Returns:
        Dictionary containing the read data or error information.
    """
    if openpyxl is None:
        return {
            "type": "error",
            "error": "openpyxl not installed. Please install with: pip install openpyxl"
        }
    
    try:
        # Construct full file path
        if not os.path.isabs(file_path):
            full_path = os.path.join(EXCEL_SPREADSHEETS_DIR, file_path)
        else:
            full_path = file_path
        
        if not os.path.exists(full_path):
            return {
                "type": "error",
                "error": f"File not found: {full_path}"
            }
        
        # Load workbook and worksheet
        wb = load_workbook(full_path, read_only=True)
        
        if sheet_name not in wb.sheetnames:
            wb.close()
            return {
                "type": "error",
                "error": f"Sheet '{sheet_name}' not found. Available sheets: {wb.sheetnames}"
            }
        
        ws = wb[sheet_name]
        
        # Read the specified range
        if ':' in cell_range:
            # Range of cells
            cell_values = []
            for row in ws[cell_range]:
                if isinstance(row, tuple):
                    row_values = [cell.value for cell in row]
                else:
                    row_values = [row.value]
                cell_values.append(row_values)
        else:
            # Single cell
            cell_values = ws[cell_range].value
        
        wb.close()
        
        return {
            "type": "excel_read_success",
            "file_path": file_path,
            "sheet_name": sheet_name,
            "cell_range": cell_range,
            "data": cell_values
        }
        
    except Exception as e:
        return {
            "type": "error",
            "error": f"Error reading Excel file: {str(e)}"
        }

@tool
def write_excel_sheet(file_path: str, sheet_name: str, cell_range: str, data: Union[str, int, float, List]) -> Dict[str, Any]:
    """Write data to an Excel sheet at specified cell range.
    
    Args:
        file_path: Path to Excel file (relative to company_spreadsheets directory)
        sheet_name: Name of the worksheet to write to
        cell_range: Cell range to write to (e.g., 'A1' for single cell, 'A1:C3' for range)
        data: Data to write (single value or list of lists for ranges)
        
    Returns:
        Dictionary containing success/error information.
    """
    if openpyxl is None:
        return {
            "type": "error",
            "error": "openpyxl not installed. Please install with: pip install openpyxl"
        }
    
    try:
        # Construct full file path
        if not os.path.isabs(file_path):
            full_path = os.path.join(EXCEL_SPREADSHEETS_DIR, file_path)
        else:
            full_path = file_path
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Load or create workbook
        if os.path.exists(full_path):
            wb = load_workbook(full_path)
        else:
            wb = Workbook()
            # Remove default sheet if creating new workbook
            if 'Sheet' in wb.sheetnames and sheet_name != 'Sheet':
                wb.remove(wb['Sheet'])
        
        # Get or create worksheet
        if sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
        else:
            ws = wb.create_sheet(sheet_name)
        
        # Write data
        if ':' in cell_range:
            # Range of cells - data should be list of lists
            if not isinstance(data, list):
                return {
                    "type": "error",
                    "error": "For cell ranges, data must be a list of lists"
                }
            
            start_cell = cell_range.split(':')[0]
            for i, row_data in enumerate(data):
                if isinstance(row_data, list):
                    for j, cell_value in enumerate(row_data):
                        ws.cell(row=ws[start_cell].row + i, column=ws[start_cell].column + j, value=cell_value)
                else:
                    ws.cell(row=ws[start_cell].row + i, column=ws[start_cell].column, value=row_data)
        else:
            # Single cell
            ws[cell_range] = data
        
        # Save workbook
        wb.save(full_path)
        wb.close()
        
        return {
            "type": "excel_write_success",
            "file_path": file_path,
            "sheet_name": sheet_name,
            "cell_range": cell_range,
            "message": "Data written successfully"
        }
        
    except Exception as e:
        return {
            "type": "error",
            "error": f"Error writing to Excel file: {str(e)}"
        }

@tool
def execute_excel_calculation(file_path: str, input_data: Dict[str, Union[str, int, float]], 
                            output_cells: List[str], sheet_name: str = None) -> Dict[str, Any]:
    """Execute a calculation in Excel by writing input values and reading output values.
    
    This function writes input values to specified cells, triggers Excel's calculation engine,
    and then reads the results from output cells.
    
    Args:
        file_path: Path to Excel file (relative to company_spreadsheets directory)
        input_data: Dictionary mapping cell references to input values (e.g., {'A1': 10, 'B1': 20})
        output_cells: List of cell references to read results from (e.g., ['C1', 'D1'])
        sheet_name: Name of the worksheet (optional, uses first sheet if not specified)
        
    Returns:
        Dictionary containing input values, output values, and calculation results.
    """
    if openpyxl is None:
        return {
            "type": "error",
            "error": "openpyxl not installed. Please install with: pip install openpyxl"
        }
    
    try:
        # Construct full file path
        if not os.path.isabs(file_path):
            full_path = os.path.join(EXCEL_SPREADSHEETS_DIR, file_path)
        else:
            full_path = file_path
        
        if not os.path.exists(full_path):
            return {
                "type": "error",
                "error": f"File not found: {full_path}"
            }
        
        # Load workbook
        wb = load_workbook(full_path)
        
        # Get worksheet
        if sheet_name:
            if sheet_name not in wb.sheetnames:
                wb.close()
                return {
                    "type": "error",
                    "error": f"Sheet '{sheet_name}' not found. Available sheets: {wb.sheetnames}"
                }
            ws = wb[sheet_name]
        else:
            ws = wb.active
        
        # Write input values
        for cell_ref, value in input_data.items():
            ws[cell_ref] = value
        
        # Force recalculation by setting calculation mode
        wb.calculation.calcMode = 'auto'
        
        # Save to trigger calculation
        wb.save(full_path)
        wb.close()
        
        # Try to use xlwings for calculation if available
        try:
            import xlwings as xw
            
            # Open with xlwings to force calculation
            app = xw.App(visible=False)
            book = app.books.open(full_path)
            
            # Force calculation
            book.app.calculate()
            
            # Read output values
            sheet = book.sheets[sheet_name] if sheet_name else book.sheets[0]
            output_values = {}
            for cell_ref in output_cells:
                output_values[cell_ref] = sheet.range(cell_ref).value
            
            # Close and cleanup
            book.close()
            app.quit()
            
        except ImportError:
            # Fallback: reload workbook and try manual formula evaluation
            wb = load_workbook(full_path)
            ws = wb[sheet_name] if sheet_name else wb.active
            
            output_values = {}
            for cell_ref in output_cells:
                cell_value = ws[cell_ref].value
                
                # If it's a formula, try to evaluate it manually
                if isinstance(cell_value, str) and cell_value.startswith('='):
                    try:
                        evaluated_value = _evaluate_formula(cell_value, ws)
                        output_values[cell_ref] = evaluated_value
                    except Exception:
                        output_values[cell_ref] = cell_value  # Return formula if evaluation fails
                else:
                    output_values[cell_ref] = cell_value
            
            wb.close()
        
        return {
            "type": "excel_calculation_success",
            "file_path": file_path,
            "sheet_name": sheet_name or "default",
            "inputs": input_data,
            "outputs": output_values,
            "message": "Calculation completed successfully"
        }
        
    except Exception as e:
        return {
            "type": "error",
            "error": f"Error executing Excel calculation: {str(e)}"
        }

# Add your tools to this list. The ReAct agent will be able to invoke them.
# The tools should be functions that accept a single string argument and return a string.
# The docstrings of the functions will be used to tell the LLM about the tool.
TOOLS: List[Callable[[Any], Any]] = [
    search, 
    calculator, 
    calculate_slenderness_ratio, 
    search_engineering_database, 
    search_medical_database,
    list_excel_files,
    read_excel_sheet,
    write_excel_sheet,
    execute_excel_calculation
]
