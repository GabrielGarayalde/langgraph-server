"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example)

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""

import os
from typing import Annotated, Any, Callable, Dict, List, Optional, cast

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
PINECONE_INDEX_NAME = "anna-medical"
DEFAULT_NAMESPACE = "anna-medical-namespace"
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
    namespace: Annotated[str, "Database namespace to search (default: corpus-data)"] = DEFAULT_NAMESPACE
) -> Dict[str, Any]:
    """Search the Pinecone vector database for AS 4100-1998 engineering documents and standards.
    
    Returns a structured dictionary containing the search results, including metadata and content for each hit.
    This tool searches through digitized Australian Steel Standards (AS 4100-1998) documents
    including tables, clauses, design requirements, and engineering specifications.
    
    Use this tool to find:
    - Specific clauses and requirements from AS 4100-1998
    - Design tables and capacity factors
    - Load combinations and safety factors
    - Material properties and specifications
    - Design procedures and calculations
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
        index = pc.Index(PINECONE_INDEX_NAME)
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

# Add your tools to this list. The ReAct agent will be able to invoke them.
# The tools should be functions that accept a single string argument and return a string.
# The docstrings of the functions will be used to tell the LLM about the tool.
TOOLS: List[Callable[[Any], Any]] = [search, calculator, calculate_slenderness_ratio, search_engineering_database]
