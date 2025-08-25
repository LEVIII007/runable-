from typing import TypedDict, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class CodeSolution(BaseModel):
    """Schema for code solutions from the coding assistant"""
    prefix: str = Field(description="Description of the problem and approach")
    imports: str = Field(description="Code block import statements")
    code: str = Field(description="Code block not including import statements")
    language: str = Field(description="Programming language (python, typescript, shell, etc.)")


class ExecutionResult(BaseModel):
    """Schema for code execution results"""
    success: bool = Field(description="Whether execution was successful")
    output: str = Field(description="Execution output or error message")
    execution_time: float = Field(description="Time taken for execution in seconds")


class CodingAgentState(TypedDict):
    """
    Represents the state of the Coding Agent Graph.
    
    Attributes:
        task: The main coding task description
        messages: Chat history with user questions and AI responses
        code_solutions: List of generated code solutions
        execution_results: Results from code executions
        current_iteration: Current iteration number
        max_iterations: Maximum allowed iterations
        error_count: Number of consecutive errors
        max_errors: Maximum allowed consecutive errors
        context: Additional context for the task
        files_created: List of files created during the session
        working_directory: Current working directory
        environment_setup: Environment configuration and dependencies
        debug_mode: Whether debug mode is enabled
        tools_available: List of available tools (shell, python, typescript, etc.)
        session_id: Unique session identifier
        final_output: Final result of the coding task
    """
    
    # Core task information
    task: str
    messages: List[BaseMessage]
    
    # Code generation and execution
    code_solutions: List[CodeSolution]
    execution_results: List[ExecutionResult]
    current_iteration: int
    max_iterations: int
    error_count: int
    max_errors: int
    
    # Context and state management
    context: Optional[str]
    files_created: List[str]
    working_directory: str
    environment_setup: Dict[str, Any]
    
    # Agent configuration
    debug_mode: bool
    tools_available: List[str]
    session_id: str
    
    # Results
    final_output: Optional[str]
    
    # Control flow
    should_continue: bool
    next_action: Optional[str]  # "generate", "execute", "debug", "finish" 