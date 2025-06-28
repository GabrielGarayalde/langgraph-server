"""Utility & helper functions."""

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage


def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)

    if provider == "google":
        return ChatGoogleGenerativeAI(model=model, temperature=0)
    elif provider == "anthropic":
        return ChatAnthropic(model_name=model, temperature=0, streaming=True)
    else:
        raise ValueError(
            f"Unsupported chat model provider: '{provider}'. "
            "Supported providers are 'google' and 'anthropic'."
        )
