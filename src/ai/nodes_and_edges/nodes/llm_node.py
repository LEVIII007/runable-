from langchain_core.messages import AIMessage

from src.ai.llms.gemini import create_llm
from src.ai.states.theises import AgentState

async def llm_node(state: AgentState):
    llm = create_llm()

    if not state.get("messages"):
        state["messages"] = []

    state["messages"].append(state["prompt"])

    response = await llm.ainvoke(state["prompt"].messages)

    state["messages"].append(AIMessage(content=response.content))
    state["answer"] = response.content
    return state