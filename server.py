import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import logging
import json
from inspect import signature, _empty
from langchain_core.tools import BaseTool # For type checking

# Create the FastAPI app
app = FastAPI(
    title="Agent Tools Info Server",
    version="1.0",
    description="A simple API server to provide metadata about the agent's tools.",
)

# Add a logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Import your compiled LangGraph agent
from src.react_agent.graph import graph as engineering_agent_graph
from src.react_agent.tools import TOOLS as graph_tools  # Import lazily to prevent circular deps.

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET"], # Allow only GET
    allow_headers=["*"],
)

# Helper function from Memory: 6ff5551b-f75c-47ea-ac98-42dfe836f4ae
# Used to parse potentially complex message content structures
def parse_message_content(content):
    if not content:
        return ""
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and 'text' in part:
                text_parts.append(part['text'])
            elif isinstance(part, str):
                text_parts.append(part)
            # Handle common AIMessageChunk content part structure
            elif isinstance(part, dict) and part.get('type') == 'text' and 'text' in part:
                text_parts.append(part['text'])
            # Add other specific part handling if necessary
        return ''.join(text_parts)
    elif isinstance(content, str):
        return content
    else:
        # Fallback for other types, convert to string
        return str(content)

# --------------------
# Info endpoint for frontend
# --------------------
@app.get("/tools_info", response_model=dict)
async def get_info():
    """Return basic metadata about the running LangGraph application, including available tools.

    The agent-chat UI expects this endpoint to provide a `tools` key containing an
    array of tool specifications (name, description, parameters).  We derive this
    information directly from the `tools` list that is defined in
    `src.react_agent.tools`.
    """
    try:
        tool_specs = []
        for tool_func in graph_tools:
            params_spec = {}
            if isinstance(tool_func, BaseTool):
                # It's a LangChain BaseTool object (e.g., StructuredTool or @tool decorated)
                t_name = tool_func.name
                t_desc = tool_func.description
                if hasattr(tool_func, 'args_schema') and tool_func.args_schema:
                    schema_method = getattr(tool_func.args_schema, 'model_json_schema', getattr(tool_func.args_schema, 'schema', None))
                    if schema_method:
                        try:
                            schema = schema_method()
                            schema_props = schema.get("properties", {})
                            required_params = schema.get("required", [])
                            for param_name, param_info in schema_props.items():
                                params_spec[param_name] = {
                                    "type": param_info.get("type", "any"),
                                    "description": param_info.get("description", ""),
                                    "required": param_name in required_params
                                }
                        except Exception as e:
                            logger.warning(f"Could not get schema for BaseTool {getattr(tool_func, 'name', 'unknown')}: {e}")
                    else:
                        logger.warning(f"BaseTool {getattr(tool_func, 'name', 'unknown')} has args_schema but no schema() or model_json_schema() method.")
                else:
                    logger.info(f"BaseTool {getattr(tool_func, 'name', 'unknown')} does not have an args_schema.")
            elif callable(tool_func):
                # It's a raw Python function
                t_name = tool_func.__name__
                t_desc = (tool_func.__doc__ or "").strip()
                try:
                    sig = signature(tool_func)
                    for param_name, param in sig.parameters.items():
                        # Skip *args/**kwargs and common LangChain runtime params if they appear
                        if param.kind in (param.VAR_KEYWORD, param.VAR_POSITIONAL) or \
                           param_name in ("config", "callbacks", "run_manager"):
                            continue
                        param_type = str(param.annotation) if param.annotation != _empty else "any"
                        # Clean up <class 'xxx'> representation
                        if param_type.startswith("<class '") and param_type.endswith("'>"):
                            param_type = param_type[8:-2]
                        params_spec[param_name] = {
                            "type": param_type,
                            "description": "",  # Raw function signatures don't easily provide per-param descriptions
                            "required": param.default == _empty
                        }
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not get signature for raw function {t_name}: {e}")
            else:
                logger.warning(f"Skipping item in TOOLS list as it is not a BaseTool or callable: {type(tool_func)}")
                continue

            tool_specs.append({
                "name": t_name,
                "description": t_desc,
                "parameters": params_spec,
            })

        return {
            "status": "success",
            "tools": tool_specs,
        }
    except Exception as exc:  # pragma: no cover – ensures the server keeps running if this fails.
        logger.error("Failed to import tools from graph.py: %s", exc, exc_info=True)
        return {"status": "error", "message": f"Could not load tools: {exc}"}

if __name__ == "__main__":
    # Run the server on port 3024
    uvicorn.run(app, host="127.0.0.1", port=3024, log_level="info")
