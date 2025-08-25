import time
import uuid
from typing import Dict, Any, Literal, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.ai.states.coding_agent import CodingAgentState, CodeSolution, ExecutionResult
from src.helpers.code_exec import get_executor, CodeExecutor
from src.helpers.context_manager import get_context_manager
from src.helpers.create_script import _create_run_script
from src.ai.llms.gemini import create_llm
from src.config.logging_config import get_logger
import re

logger = get_logger(__name__)


def initialize_agent_node(state: CodingAgentState) -> CodingAgentState:
    """Initialize the coding agent with default values and system setup"""
    
    logger.info("Initializing coding agent...")
    
    # Initialize session ID if not present
    if not state.get("session_id"):
        state["session_id"] = str(uuid.uuid4())
    
    # Initialize default values
    state.setdefault("current_iteration", 0)
    state.setdefault("max_iterations", 10)
    state.setdefault("error_count", 0)
    state.setdefault("max_errors", 5)
    state.setdefault("debug_mode", True)
    state.setdefault("should_continue", True)
    state.setdefault("next_action", "generate")
    state.setdefault("code_solutions", [])
    state.setdefault("execution_results", [])
    state.setdefault("files_created", [])
    state.setdefault("tools_available", ["python", "shell", "javascript", "filesystem"])
    state.setdefault("environment_setup", {})
    
    # Initialize working directory with job-specific executor
    session_id = state["session_id"]
    executor = get_executor(job_id=session_id)
    state["working_directory"] = executor.working_dir
    
    # Initialize messages with system prompt if empty
    if not state.get("messages"):
        system_prompt = SystemMessage(content="""You are an expert coding assistant focused on single-file solutions.

Your capabilities include:
- Execute Python code with full library support
- Run shell commands safely 
- Execute TypeScript/JavaScript code
- Read generated files for verification

IMPORTANT CONSTRAINTS:
- Focus on SINGLE FILE solutions only
- Do not create multiple files or complex project structures
- Keep solutions self-contained in one main file
- Avoid referencing external files or creating additional files

When given a coding task:
1. Break down the problem into logical steps
2. Generate a single, self-contained code solution   
3. Execute and test your code
4. Debug and iterate if errors occur
5. Provide clear explanations of your approach

Always structure your code with:
- Clear problem description
- Necessary imports
- Clean, executable code blocks in ONE file
- Error handling where appropriate

You have access to these tools: python execution, shell commands, TypeScript execution, file reading.
Use them strategically to complete the coding task efficiently with single-file solutions.""")
        
        state["messages"] = [system_prompt]
    
    return state


def generate_code_node(state: CodingAgentState) -> CodingAgentState:
    """Generate code solution for the given task"""
    
    logger.info("Generating code solution...")
    
    # Get current state
    messages = state["messages"]
    task = state["task"]
    current_iteration = state["current_iteration"]
    error_count = state["error_count"]
    
    # Check if we have previous errors to address
    has_errors = error_count > 0 and state["execution_results"]
    last_result = state["execution_results"][-1] if state["execution_results"] else None
    
    # Create the LLM with structured output
    llm = create_llm()
    
    # Get context from context manager
    context_manager = get_context_manager()
    session_id = state["session_id"]
    context_prompt = context_manager.build_context_prompt(session_id, max_tokens=4000)
    
    # Create prompt based on context
    if has_errors and last_result and not last_result.success:
        # Error fixing prompt
        user_prompt = f"""The previous code execution failed with this error:
        
Error: {last_result.output}

Please fix the error and provide a corrected solution for the task: {task}

{context_prompt}

Analyze the error, identify the issue, and provide a working solution."""
        
    else:
        # Initial or iterative prompt
        user_prompt = f"""Task: {task}

Current iteration: {current_iteration + 1}

{context_prompt}

Please provide a code solution. Consider:
1. What programming language is most appropriate?
2. What dependencies or setup might be needed?
3. Break the problem into logical steps
4. Provide clean, executable code

Structure your response with:
- Description of approach
- Import statements needed
- Main code implementation"""
    
    # Add user message
    messages.append(HumanMessage(content=user_prompt))
    
    try:
        # Generate response using LLM
        response = llm.invoke(messages)
        
        # Parse the response to extract code solution
        response_content = response.content
        
        # Try to extract code blocks from the response
        
        # Look for code blocks with language specifiers
        python_blocks = re.findall(r'```(?:python|py)\n(.*?)\n```', response_content, re.DOTALL | re.IGNORECASE)
        javascript_blocks = re.findall(r'```(?:javascript|js)\n(.*?)\n```', response_content, re.DOTALL | re.IGNORECASE)
        shell_blocks = re.findall(r'```(?:bash|shell|sh)\n(.*?)\n```', response_content, re.DOTALL | re.IGNORECASE)
        
        # Prefer language-specific blocks, fall back to generic
        if python_blocks:
            code_blocks = python_blocks
            detected_lang = "python"
        elif javascript_blocks:
            code_blocks = javascript_blocks
            detected_lang = "javascript"
        elif shell_blocks:
            code_blocks = shell_blocks
            detected_lang = "shell"
        else:
            # Look for any code blocks without language specifier
            code_blocks = re.findall(r'```\n(.*?)\n```', response_content, re.DOTALL)
            detected_lang = None
        
        # Extract imports and main code
        if code_blocks:
            full_code = code_blocks[0].strip()
            
            # Split imports from main code
            lines = full_code.split('\n')
            imports = []
            main_code = []
            
            for line in lines:
                if (line.strip().startswith('import ') or 
                    line.strip().startswith('from ') or
                    line.strip().startswith('#') and 'import' in line.lower()):
                    imports.append(line)
                else:
                    main_code.append(line)
            
            imports_str = '\n'.join(imports) if imports else "# No explicit imports found"
            main_code_str = '\n'.join(main_code) if main_code else full_code
            
            # Detect language based on code block markers first, then content analysis
            if detected_lang:
                language = detected_lang
            else:
                language = "python"  # Default
                
                # Analyze code content for language indicators
                if code_blocks:
                    code_content = code_blocks[0].lower()
                    if any(py_indicator in code_content for py_indicator in ['def ', 'import ', 'print(', 'if __name__']):
                        language = "python"
                    elif any(js_indicator in code_content for js_indicator in ['function ', 'const ', 'let ', 'console.log']):
                        language = "javascript"
                    elif any(sh_indicator in code_content for sh_indicator in ['#!/bin/', 'echo ', 'mkdir ', 'cd ', 'ls ']):
                        language = "shell"
                
                # Then check response content for explicit language mentions
                response_lower = response_content.lower()
                if any(keyword in response_lower for keyword in ['javascript', 'node.js', 'npm', 'js']):
                    language = "javascript"
                elif any(keyword in response_lower for keyword in ['bash script', 'shell script', 'command line', 'terminal']):
                    language = "shell"
        else:
            # No code blocks found, use entire response
            imports_str = "# No code blocks detected"
            main_code_str = response_content
            language = "python"
        
        code_solution = CodeSolution(
            prefix=f"Solution attempt {current_iteration + 1}: {response_content[:100]}...",
            imports=imports_str,
            code=main_code_str,
            language=language
        )
        
        # Add conversation context to context manager
        context_manager = get_context_manager()
        session_id = state["session_id"]
        context_manager.add_conversation_context(session_id, f"Generated solution: {response_content[:200]}...")
        
        # Add AI response to messages
        messages.append(AIMessage(content=response.content))
        
        # Update state
        state["messages"] = messages
        state["code_solutions"].append(code_solution)
        state["current_iteration"] += 1
        state["next_action"] = "execute"
        
    except Exception as e:
        logger.error(f"Error in code generation: {str(e)}")
        state["error_count"] += 1
        state["next_action"] = "debug" if state["error_count"] < state["max_errors"] else "finish"
    
    return state


def save_generated_code_to_files(code_solution: CodeSolution, executor: CodeExecutor, iteration: int) -> List[str]:
    """
    Save generated code to a single file in the workspace.
    
    Args:
        code_solution: The code solution to save
        executor: The code executor instance
        iteration: Current iteration number
        
    Returns:
        List containing the single file path that was created
    """
    created_files = []
    
    # Determine file extension
    file_extension = {
        "python": ".py",
        "javascript": ".js",
        "shell": ".sh"
    }.get(code_solution.language.lower(), ".py")
    
    # Look for specific filename mentions in the code or prefix
    
    # Check if the LLM specified a filename
    filename_patterns = [
        r'save (?:this |the )?(?:code )?(?:to |as |in )?["\']?([a-zA-Z0-9_.-]+\.(py|js|ts|sh|txt|json|yaml|yml|md))["\']?',
        r'(?:create|write) (?:a )?file (?:called |named )?["\']?([a-zA-Z0-9_.-]+\.(py|js|ts|sh|txt|json|yaml|yml|md))["\']?',
        r'filename?\s*[:=]\s*["\']?([a-zA-Z0-9_.-]+\.(py|js|ts|sh|txt|json|yaml|yml|md))["\']?'
    ]
    
    suggested_filename = None
    full_text = f"{code_solution.prefix} {code_solution.code}".lower()
    
    for pattern in filename_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            suggested_filename = match.group(1)
            break
    
    # Use suggested filename or create default
    if suggested_filename:
        filename = suggested_filename
    else:
        # Always use solution_1 to overwrite the same file on retry
        filename = f"solution_1{file_extension}"
    
    # Combine imports and code for saving
    if code_solution.language.lower() == "python" and code_solution.imports != "# No explicit imports found":
        full_code = f"{code_solution.imports}\n\n{code_solution.code}"
    else:
        full_code = code_solution.code
    
    # Save the main code file
    save_result = executor.create_file(filename, full_code)
    if save_result["success"]:
        created_files.append(save_result["file_path"])
        logger.info(f"Saved generated code to: {save_result['file_path']}")
    else:
        logger.warning(f"Failed to save code to file {filename}: {save_result['output']}")
    
    # Single file project - no additional file detection needed
    return created_files


def execute_code_node(state: CodingAgentState) -> CodingAgentState:
    """Execute the generated code and capture results"""
    
    logger.info("Executing generated code...")
    
    if not state["code_solutions"]:
        logger.error("No code solutions to execute")
        state["next_action"] = "generate"
        return state
    
    # Get the latest code solution
    latest_solution = state["code_solutions"][-1]
    session_id = state.get("session_id")
    executor = get_executor(job_id=session_id)
    
    try:
        start_time = time.time()
        
        # Save the generated code to files in the workspace
        iteration = state.get("current_iteration", 0)
        created_files = save_generated_code_to_files(latest_solution, executor, iteration)
        
        # Execute based on language
        if latest_solution.language.lower() == "python":
            full_code_for_execution = f"{latest_solution.imports}\n{latest_solution.code}"
            result = executor.execute_python(full_code_for_execution)
        elif latest_solution.language.lower() == "javascript":
            result = executor.execute_javascript(latest_solution.code)
        elif latest_solution.language.lower() == "shell":
            result = executor.execute_shell(latest_solution.code)
        else:
            full_code_for_execution = f"{latest_solution.imports}\n{latest_solution.code}"
            result = executor.execute_python(full_code_for_execution)
        
        execution_time = time.time() - start_time
        
        # Create execution result
        exec_result = ExecutionResult(
            success=result["success"],
            output=result["output"],
            execution_time=execution_time
        )
        
        state["execution_results"].append(exec_result)
        
        all_created_files = executor.get_created_files()
        if all_created_files:
            state["files_created"].extend(all_created_files)
            logger.info(f"Total files in workspace: {len(all_created_files)}")
        
        context_manager = get_context_manager()
        
        main_file_path = created_files[0] if created_files else None
        context_manager.add_code_context(
            session_id, 
            latest_solution.code, 
            latest_solution.language,
            file_path=main_file_path
        )
        
        context_manager.add_execution_result(session_id, exec_result)
        
        if exec_result.success:
            state["next_action"] = "analyze"
        else:
            state["error_count"] += 1
            if state["error_count"] >= state["max_errors"]:
                state["next_action"] = "finish"
            else:
                state["next_action"] = "debug"
                
    except Exception as e:
        logger.error(f"Error during code execution: {str(e)}")
        state["error_count"] += 1
        state["next_action"] = "debug" if state["error_count"] < state["max_errors"] else "finish"
    
    return state


def debug_code_node(state: CodingAgentState) -> CodingAgentState:
    """Debug failed code execution and prepare for retry"""
    
    logger.info("Debugging code execution...")
    
    if not state["execution_results"]:
        state["next_action"] = "generate"
        return state
    
    latest_result = state["execution_results"][-1]
    
    if latest_result.success:
        state["next_action"] = "analyze"
        return state
    
    debug_message = HumanMessage(content=f"""
Code execution failed with the following error:

{latest_result.output}

Please analyze the error and provide a corrected solution. Consider:
1. Syntax errors
2. Missing imports or dependencies
3. Logic errors
4. Environment issues

Provide a fixed version of the code.""")
    
    state["messages"].append(debug_message)
    state["next_action"] = "generate"
    
    return state


def analyze_results_node(state: CodingAgentState) -> CodingAgentState:
    """Analyze execution results and determine next steps"""
    
    logger.info("Analyzing execution results...")
    
    if not state["execution_results"]:
        state["next_action"] = "generate"
        return state
    
    latest_result = state["execution_results"][-1]
    
    if latest_result.success:
        analysis_message = HumanMessage(content=f"""
The code executed successfully! 

Output:
{latest_result.output}

Please provide a summary of:
1. What the code accomplished
2. Key results or insights
3. Any recommendations for improvement or next steps
4. Whether the original task has been completed

Execution time: {latest_result.execution_time:.2f} seconds""")
        
        state["messages"].append(analysis_message)
        
        llm = create_llm()
        try:
            response = llm.invoke(state["messages"])
            state["messages"].append(AIMessage(content=response.content))
            state["final_output"] = response.content
            state["next_action"] = "finish"
        except Exception as e:
            logger.error(f"Error in analysis: {str(e)}")
            state["final_output"] = f"Task completed successfully. Output: {latest_result.output}"
            state["next_action"] = "finish"
    else:
        state["next_action"] = "debug"
    
    return state


def should_continue_node(state: CodingAgentState) -> Literal["generate", "execute", "debug", "analyze", "finish"]:
    """Determine the next action based on current state"""
    
    current_iteration = state["current_iteration"]
    max_iterations = state["max_iterations"]
    error_count = state["error_count"]
    max_errors = state["max_errors"]
    next_action = state.get("next_action", "generate")
    
    # Check termination conditions
    if current_iteration >= max_iterations:
        logger.info("Maximum iterations reached")
        return "finish"
    
    if error_count >= max_errors:
        logger.info("Maximum errors reached")
        return "finish"
    
    if next_action == "finish":
        return "finish"
    
    return next_action


def finalize_node(state: CodingAgentState) -> CodingAgentState:
    """Finalize the coding session and prepare output"""
    
    logger.info("Finalizing coding session...")
    
    state["should_continue"] = False
    
    # Ensure all files from executor are captured
    session_id = state.get("session_id")
    executor = None
    if session_id:
        executor = get_executor(job_id=session_id)
        final_files = executor.get_created_files()
        # Merge with any files already tracked in state
        all_files = list(set(state.get("files_created", []) + final_files))
        state["files_created"] = all_files
        logger.info(f"Final file count: {len(all_files)}")
    
    # If no final output set, create a summary
    if not state.get("final_output"):
        if state["execution_results"] and state["execution_results"][-1].success:
            latest_result = state["execution_results"][-1]
            state["final_output"] = f"""
Task completed successfully!

Final Output:
{latest_result.output}

Execution Summary:
- Total iterations: {state['current_iteration']}
- Files created: {len(state['files_created'])}
- Working directory: {state.get('working_directory', 'N/A')}
- Execution time: {latest_result.execution_time:.2f} seconds

Created files:
{chr(10).join(f"- {f}" for f in state['files_created']) if state['files_created'] else "- No files created"}
"""
        else:
            state["final_output"] = f"""
Task completed with errors after {state['current_iteration']} iterations.
Error count: {state['error_count']}

Please review the execution history for details.
"""
    
    # Create result.txt file with LLM's final response and code output
    if executor and state.get("final_output"):
        try:
            # Gather code outputs from execution results
            code_outputs = []
            for i, result in enumerate(state.get("execution_results", []), 1):
                if result.success:
                    code_outputs.append(f"=== Execution {i} Output ===\n{result.output}\n")
                else:
                    code_outputs.append(f"=== Execution {i} Error ===\n{result.output}\n")
            
            # Prepare result.txt content
            result_content = f"""# Coding Agent Results
## Task: {state.get('task', 'N/A')}

## LLM Final Response
{state['final_output']}

## Code Execution Outputs
{''.join(code_outputs) if code_outputs else 'No code execution outputs available.'}

## Generated Code Solutions
"""
            
            # Add code solutions to the result
            for i, solution in enumerate(state.get("code_solutions", []), 1):
                result_content += f"""
### Solution {i} ({solution.language})
```{solution.language}
{solution.imports if solution.imports != "# No explicit imports found" else ""}
{solution.code}
```
"""
            
            # Add session information
            result_content += f"""
## Session Information
- Session ID: {session_id}
- Working Directory: {state.get('working_directory', 'N/A')}
- Total Iterations: {state.get('current_iteration', 0)}
- Error Count: {state.get('error_count', 0)}
- Files Created: {len(state.get('files_created', []))}

## Created Files List
{chr(10).join(f"- {f}" for f in state.get('files_created', [])) if state.get('files_created') else "- No files created"}
"""
            
            # Create the result.txt file
            result_file_creation = executor.create_file("result.txt", result_content)
            if result_file_creation["success"]:
                logger.info("✅ Successfully created result.txt file")
                # Add result.txt to the list of created files
                if "result.txt" not in state["files_created"]:
                    state["files_created"].append(result_file_creation["file_path"])
            else:
                logger.warning(f"❌ Failed to create result.txt: {result_file_creation['output']}")
            
            # Launch xterm to show code execution results
            _launch_xterm_with_results(executor, state)
                
        except Exception as e:
            logger.error(f"Error creating result.txt file: {str(e)}")
    
    return state


def _launch_xterm_with_results(executor: CodeExecutor, state: CodingAgentState):
    """Launch xterm terminal to display code execution results"""
    try:
        # Get the latest successful code solution
        latest_solution = None
        if state.get("code_solutions"):
            latest_solution = state["code_solutions"][-1]
        
        if not latest_solution:
            logger.warning("No code solution found to run in xterm")
            return
        
        # Create a script to run the code and keep terminal open
        script_content = _create_run_script(latest_solution, state)
        
        # Save the run script
        script_file_creation = executor.create_file("run_code.sh", script_content)
        if not script_file_creation["success"]:
            logger.warning(f"Failed to create run script: {script_file_creation['output']}")
            return
        
        # Make the script executable
        import os
        script_path = script_file_creation["file_path"]
        os.chmod(script_path, 0o755)
        
        # Launch xterm with the script
        import subprocess
        env = os.environ.copy()
        env["DISPLAY"] = ":0"
        env["HOME"] = "/home/agent"
        
        # Create xterm command to run the script and keep terminal open
        xterm_command = [
            'xterm',
            '-geometry', '80x24+100+100',
            '-title', 'Code Execution Results',
            '-e', 'bash', '-c',
            f'cd "{executor.working_dir}" && ./run_code.sh; echo; echo "Press any key to close..."; read -n 1'
        ]
        
        # Launch xterm in background
        xterm_process = subprocess.Popen(
            xterm_command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start
        import time
        time.sleep(0.5)
        
        # Check if it started successfully
        poll_result = xterm_process.poll()
        if poll_result is None or poll_result == 0:
            logger.info("✅ Successfully launched xterm with code execution results")
        else:
            # Get error output if available
            try:
                _, stderr = xterm_process.communicate(timeout=1)
                logger.warning(f"xterm launch failed: {stderr}")
            except subprocess.TimeoutExpired:
                logger.warning(f"xterm launch failed with return code: {poll_result}")
            
    except Exception as e:
        logger.error(f"Error launching xterm: {str(e)}")