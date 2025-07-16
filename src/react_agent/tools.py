"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example)

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""

import os
import json
from pathlib import Path
from typing import Annotated, Any, Callable, Dict, List, Optional, Union, cast
import base64
import asyncio
from io import BytesIO

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


@tool
def search_engineering_database(
    query: Annotated[str, "Search query for engineering documents and standards"],
    top_k: Annotated[int, "Number of results to return (default: 10)"] = 10,
    namespace: Annotated[str, "Database namespace to search (default: aus-standards-namespace)"] = ENGINEERING_DEFAULT_NAMESPACE,
    source_document_id: Annotated[Optional[str], "Optional filter – only return chunks from this document ID"] = None,
) -> Dict[str, Any]:
    """Search the Pinecone vector database for engineering documents and standards.
    
    Returns a structured dictionary containing the search results, including metadata and content for each hit.
    This tool searches through Australian Standards related to engineering.

    If *source_document_id* is supplied, the search is restricted to that document via a Pinecone metadata
    filter.
    
    Use this tool to find:
    - Specific clauses and sections from australian standards
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

        # Build the query dict with optional metadata filter
        query_dict: Dict[str, Any] = {
            "top_k": min(top_k, 10),
            "inputs": {"text": query},
        }
        if source_document_id:
            # Apply metadata filter
            query_dict["filter"] = {"source_document_id": source_document_id}

        # Common search parameters for both searches
        search_params = {
            "namespace": namespace,
            "query": query_dict,
            "rerank": {
                "model": "bge-reranker-v2-m3",
                "top_n": min(top_k, 10),
                "rank_fields": ["chunk_text"],
            },
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



# Google Generative AI imports
try:
    import google.generativeai as genai
    from PIL import Image
    import asyncio
except ImportError:
    genai = None
    Image = None
    asyncio = None



@tool
async def analyze_document_vision(
    document_id: str,
    page_number: int,
    query: str
) -> Dict[str, Any]:
    """Analyze a specific page image using Google's Gemini 2.5 Pro vision model.
    
    This tool loads a pre-processed page image from the page_images directory
    and uses Gemini's vision capabilities to analyze it based on the provided query.
    Useful for extracting information from diagrams, charts, tables, or complex
    layouts that require visual understanding.
    
    Args:
        document_id: Document identifier (e.g., 'as_4100_1998' or 'as_1170.0_2002')
        page_number: Page number to analyze (1-indexed)
        query: Specific question or analysis request for the page
    
    Returns:
        A dictionary containing the vision analysis results or error information
    """
    if genai is None or Image is None:
        return {
            "type": "error",
            "error": "Required libraries not installed. Please install: pip install google-generativeai pillow"
        }
    
    # Check for API key
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        return {
            "type": "error",
            "error": "GOOGLE_API_KEY environment variable not set"
        }
    
    try:
        # Configure Gemini
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Initialize the model - using gemini-2.5-pro which has vision capabilities
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Construct the image path
        # Images are stored in subdirectories: base_dir/document_id/page_X.png
        base_image_dir = r"C:\Users\gabri\Desktop\Engineering\aust_standards_digitilization\agentic_rag_v2\agent-chat-ui\public\data\page_images"
        
        # Build the path to the specific page image
        image_filename = f"page_{page_number}.png"
        image_path = os.path.join(base_image_dir, document_id, image_filename)
        
        # Check if the image exists
        if not os.path.exists(image_path):
            # Check if the document directory exists
            doc_dir = os.path.join(base_image_dir, document_id)
            if not os.path.exists(doc_dir):
                # List available document directories
                available_docs = []
                if os.path.exists(base_image_dir):
                    available_docs = [d for d in os.listdir(base_image_dir) 
                                    if os.path.isdir(os.path.join(base_image_dir, d))]
                
                return {
                    "type": "error",
                    "error": f"Document directory '{document_id}' not found",
                    "available_documents": available_docs,
                    "base_directory": base_image_dir
                }
            else:
                # List available pages for this document
                available_pages = []
                for file in os.listdir(doc_dir):
                    if file.startswith("page_") and file.endswith(".png"):
                        try:
                            page_num = int(file.replace("page_", "").replace(".png", ""))
                            available_pages.append(page_num)
                        except:
                            pass
                
                available_pages.sort()
                
                return {
                    "type": "error",
                    "error": f"Page {page_number} not found for document '{document_id}'",
                    "available_pages": available_pages,
                    "document_directory": doc_dir
                }
        
        # Load the image using asyncio.to_thread to avoid blocking
        img = await asyncio.to_thread(Image.open, image_path)
        
        # Get image metadata in a non-blocking way
        img_width = img.width
        img_height = img.height
        img_format = img.format
        img_mode = img.mode
        
        # Prepare the prompt
        prompt = f"""Please analyze this page image from a document and answer the following query:

Query: {query}

Additional context - this is page {page_number} of document '{document_id}'.
Please provide a detailed and accurate response based on what you can see in the image.
Focus on:
- Text content (including headers, paragraphs, and footnotes)
- Diagrams, charts, or technical drawings
- Tables and structured data
- Mathematical equations or formulas
- Any visual elements relevant to the query

Be specific and reference exact content from the image when answering."""

        # Generate response using vision model (this is already async)
        response = await asyncio.to_thread(model.generate_content, [prompt, img])
        
        # Extract the response text
        if response.text:
            analysis_result = response.text
        else:
            analysis_result = "No analysis could be generated from the image."
        
        return {
            "type": "vision_analysis_success",
            "document_id": document_id,
            "page_number": page_number,
            "query": query,
            "analysis": analysis_result,
            "image_path": image_path,
            "metadata": {
                "image_size": f"{img_width} x {img_height}",
                "image_format": img_format,
                "image_mode": img_mode
            }
        }
        
    except Exception as e:
        return {
            "type": "error",
            "error": f"Error during vision analysis: {str(e)}",
            "document_id": document_id,
            "page_number": page_number
        }


# Add your tools to this list. The ReAct agent will be able to invoke them.

@tool
async def get_document_page_text(
    document_id: str,
    page_number: int,
) -> Dict[str, Any]:
    """Retrieve markdown text for a specific page of a document.

    The preprocessing pipeline saves OCR-extracted text for every page as a
    ``.md`` file in the following structure::

        <base_dir>/<document_id>/<page_number>.md

    Example::
        as_1170.0_2002/1.md

    Args:
        document_id: Identifier of the source document (e.g., ``"as_1170.0_2002"``).
        page_number: 1-indexed page number.

    Returns:
        A dictionary with either the page text (``type = 'page_text_success'``)
        or helpful error information if the file cannot be found.
    """
    import asyncio  # local import avoids global dependency if asyncio missing

    base_text_dir = (
        r"C:\\Users\\gabri\\Desktop\\Engineering\\aust_standards_digitilization\\agentic_rag_v2\\agent-chat-ui\\public\\data\\page_text"
    )

    try:
        # Build expected file path
        file_path = os.path.join(base_text_dir, document_id, f"{page_number}.md")

        # Handle missing file or directory with informative errors
        if not os.path.exists(file_path):
            doc_dir = os.path.join(base_text_dir, document_id)
            if not os.path.isdir(doc_dir):
                available_docs = []
                if os.path.exists(base_text_dir):
                    available_docs = [d for d in os.listdir(base_text_dir) if os.path.isdir(os.path.join(base_text_dir, d))]
                return {
                    "type": "error",
                    "error": f"Document directory '{document_id}' not found",
                    "available_documents": available_docs,
                    "base_directory": base_text_dir,
                }

            # Directory exists, so list available page numbers for helpful feedback
            available_pages: list[int] = []
            for fname in os.listdir(doc_dir):
                if fname.endswith(".md"):
                    try:
                        available_pages.append(int(fname.replace(".md", "")))
                    except ValueError:
                        pass
            available_pages.sort()
            return {
                "type": "error",
                "error": f"Page {page_number} not found for document '{document_id}'",
                "available_pages": available_pages,
                "document_directory": doc_dir,
            }

        # Read markdown content in a separate thread to avoid blocking
        page_text = await asyncio.to_thread(lambda: Path(file_path).read_text(encoding="utf-8"))

        return {
            "type": "page_text_success",
            "document_id": document_id,
            "page_number": page_number,
            "text": page_text,
            "length": len(page_text),
            "path": file_path,
        }

    except Exception as e:  # noqa: BLE001
        return {
            "type": "error",
            "error": f"Error reading page text: {e}",
            "document_id": document_id,
            "page_number": page_number,
        }
# Import Google Sheets tools
from .sheets_tool import sheets_calculate, list_sheets_calculators

# The tools should be functions that accept a single string argument and return a string.
# The docstrings of the functions will be used to tell the LLM about the tool.
TOOLS: List[Callable[[Any], Any]] = [
    search, 
    calculator, 
    search_engineering_database, 
    sheets_calculate,  # Google Sheets calculator
    list_sheets_calculators,  # List available Google Sheets
    analyze_document_vision,
    get_document_page_text
]
