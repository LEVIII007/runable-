from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.ai.states.coding_agent import CodingAgentState, CodeSolution


def _create_run_script(latest_solution: 'CodeSolution', state: 'CodingAgentState') -> str:
    """Create a bash script to run the latest code solution"""
    
    # Get execution results for display
    execution_outputs = []
    for i, result in enumerate(state.get("execution_results", []), 1):
        if result.success:
            execution_outputs.append(f"=== Previous Execution {i} Output ===\n{result.output}")
        else:
            execution_outputs.append(f"=== Previous Execution {i} Error ===\n{result.output}")
    
    script_content = f"""#!/bin/bash

echo "======================================"
echo "🚀 CODING AGENT - EXECUTION RESULTS"
echo "======================================"
echo "Task: {state.get('task', 'N/A')}"
echo "Language: {latest_solution.language}"
echo "======================================"
echo

# Show previous execution results
echo "📋 Previous Execution Results:"
echo "{''.join(execution_outputs) if execution_outputs else 'No previous execution results.'}"
echo
echo "======================================"
echo "🔄 Running Latest Code Solution:"
echo "======================================"

# Run the latest code based on language
"""
    
    if latest_solution.language.lower() == "python":
        # Find the main Python file (usually solution_1.py)
        script_content += f"""
if [ -f "solution_1.py" ]; then
    echo "Running Python code: solution_1.py"
    echo "--------------------------------------"
    python3 solution_1.py
    echo "--------------------------------------"
    echo "✅ Python execution completed"
else
    echo "❌ Python file not found"
fi
"""
    elif latest_solution.language.lower() == "javascript":
        script_content += f"""
if [ -f "solution_1.js" ]; then
    echo "Running JavaScript code: solution_1.js"
    echo "--------------------------------------"
    node solution_1.js
    echo "--------------------------------------"
    echo "✅ JavaScript execution completed"
else
    echo "❌ JavaScript file not found"
fi
"""
    elif latest_solution.language.lower() == "shell":
        script_content += f"""
if [ -f "solution_1.sh" ]; then
    echo "Running Shell script: solution_1.sh"
    echo "--------------------------------------"
    chmod +x solution_1.sh
    ./solution_1.sh
    echo "--------------------------------------"
    echo "✅ Shell script execution completed"
else
    echo "❌ Shell script file not found"
fi
"""
    else:
        script_content += f"""
echo "Language {latest_solution.language} not supported for terminal execution"
"""
    
    script_content += f"""
echo
echo "======================================"
echo "📁 Files created in this session:"
for file in *; do
    if [ -f "$file" ]; then
        echo "  - $file"
    fi
done
echo "======================================"
echo "✨ Check result.txt for complete details"
echo "🌐 View files via VNC at localhost:6080"
echo "======================================"
"""
    
    return script_content 