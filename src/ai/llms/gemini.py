import os
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config.settings import GOOGLE_API_KEY


def create_llm(model_name: str = "gemini-2.0-flash", with_tools: bool = False):
    """
    Factory function to create and configure the LLM model with the provided tools.

    Args:
        model_name (str): The name of the language model to use.
        with_tools (bool): Whether to bind tools to the model.

    Returns:
        ChatGoogleGenerativeAI: The configured LLM instance.
    """
    try:
        # Use init_chat_model for better compatibility
        model = init_chat_model(f"google_genai:{model_name}", api_key=GOOGLE_API_KEY)
        
        # If tools are requested, bind them
        if with_tools:
            from src.helpers.code_exec import CODING_TOOLS
            model = model.bind_tools(CODING_TOOLS)
        
        return model
    except Exception as e:
        # Fallback to direct ChatGoogleGenerativeAI initialization
        print(f"Warning: init_chat_model failed, using direct initialization: {e}")
        model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.1
        )
        
        if with_tools:
            from src.helpers.code_exec import CODING_TOOLS
            model = model.bind_tools(CODING_TOOLS)
        
        return model