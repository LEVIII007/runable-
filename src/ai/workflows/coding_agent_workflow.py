from langgraph.graph import END, StateGraph
from typing import Dict, Any, Optional
import uuid

from src.ai.states.coding_agent import CodingAgentState
from src.ai.nodes_and_edges.nodes.coding_agent_nodes import (
    initialize_agent_node,
    generate_code_node,
    execute_code_node,
    debug_code_node,
    analyze_results_node,
    should_continue_node,
    finalize_node
)
from src.config.logging_config import get_logger

logger = get_logger(__name__)


def create_coding_agent_workflow():
    """
    Create the main coding agent workflow using LangGraph.
    
    The workflow follows this pattern:
    1. Initialize -> Generate Code -> Execute Code -> Analyze Results
    2. If errors occur: Debug -> Generate Code (retry)
    3. If successful: Finalize and end
    
    Returns:
        Compiled LangGraph workflow
    """
    
    # Create the state graph
    workflow = StateGraph(CodingAgentState)
    
    # Add all nodes
    workflow.add_node("initialize", initialize_agent_node)
    workflow.add_node("generate_code", generate_code_node)
    workflow.add_node("execute_code", execute_code_node)
    workflow.add_node("debug_code", debug_code_node)
    workflow.add_node("analyze_results", analyze_results_node)
    workflow.add_node("finalize", finalize_node)
    
    # Set entry point
    workflow.set_entry_point("initialize")
    
    # Add edges from initialize
    workflow.add_edge("initialize", "generate_code")
    
    workflow.add_conditional_edges(
        "generate_code",
        should_continue_node,
        {
            "execute": "execute_code",
            "debug": "debug_code",
            "analyze": "analyze_results",
            "finish": "finalize",
            "generate": "generate_code"  # For retry
        }
    )
    
    workflow.add_conditional_edges(
        "execute_code",
        should_continue_node,
        {
            "analyze": "analyze_results",
            "debug": "debug_code",
            "finish": "finalize",
            "generate": "generate_code"
        }
    )
    
    workflow.add_conditional_edges(
        "debug_code",
        should_continue_node,
        {
            "generate": "generate_code",
            "finish": "finalize",
            "analyze": "analyze_results"
        }
    )
    
    workflow.add_conditional_edges(
        "analyze_results",
        should_continue_node,
        {
            "finish": "finalize",
            "generate": "generate_code",
            "debug": "debug_code"
        }
    )
    
    workflow.add_edge("finalize", END)
    
    compiled_workflow = workflow.compile()
    
    logger.info("Coding agent workflow compiled successfully")
    return compiled_workflow


def run_coding_task(task: str, max_iterations: int = 5, debug_mode: bool = True, job_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a coding task using the coding agent workflow.
    
    Args:
        task: The coding task description
        max_iterations: Maximum number of iterations allowed
        debug_mode: Whether to enable debug mode
        job_id: Optional job ID for workspace organization
        
    Returns:
        Final state and results
    """
    
    logger.info(f"Starting coding task: {task}")
    
    initial_state = CodingAgentState(
        task=task,
        messages=[],
        code_solutions=[],
        execution_results=[],
        current_iteration=0,
        max_iterations=max_iterations,
        error_count=0,
        max_errors=3,
        context=None,
        files_created=[],
        working_directory="",
        environment_setup={},
        debug_mode=debug_mode,
        tools_available=["python", "shell", "typescript", "filesystem"],
        session_id=job_id or str(uuid.uuid4()),
        final_output=None,
        should_continue=True,
        next_action="generate"
    )
    
    workflow = create_coding_agent_workflow()
    
    try:
        final_state = workflow.invoke(initial_state)
        logger.info("Coding task completed successfully")
        return {
            "success": True,
            "final_output": final_state.get("final_output"),
            "session_id": final_state.get("session_id"),
            "iterations": final_state.get("current_iteration"),
            "files_created": final_state.get("files_created", []),
            "execution_results": final_state.get("execution_results", []),
            "working_directory": final_state.get("working_directory")
        }
    except Exception as e:
        logger.error(f"Error running coding task: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "session_id": initial_state.get("session_id"),
            "iterations": initial_state.get("current_iteration", 0),
            "working_directory": initial_state.get("working_directory")
        }



