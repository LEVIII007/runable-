import subprocess
import tempfile
import os
import time
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
import shlex
from langchain_core.tools import tool
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class CodeExecutionError(Exception):
    """Custom exception for code execution errors"""
    pass


class CodeExecutor:
    """Safe code execution environment with sandboxing capabilities"""
    
    def __init__(self, working_dir: Optional[str] = None, timeout: int = 30, job_id: Optional[str] = None, auto_open_files: bool = True):
        if job_id:
            workspace_base = Path("workspace")
            workspace_base.mkdir(exist_ok=True)
            self.working_dir = str(workspace_base / job_id)
        else:
            self.working_dir = working_dir or tempfile.mkdtemp()
            
        self.timeout = timeout
        self.files_created = []
        self.auto_open_files = auto_open_files
        
        # Ensure working directory exists and is writable
        working_path = Path(self.working_dir)
        working_path.mkdir(parents=True, exist_ok=True)
        
        # Verify the directory is writable in Docker environment
        if not os.access(self.working_dir, os.W_OK):
            raise RuntimeError(f"Working directory is not writable: {self.working_dir}")
        
    def _run_command(self, command: str, shell: bool = True) -> Dict[str, Any]:
        """Execute a shell command with timeout and safety checks"""
        start_time = time.time()
        
        try:
            dangerous_patterns = ['rm -rf /', 'dd if=', 'mkfs', 'fdisk', 'format', ':(){ :|:& };:']
            for pattern in dangerous_patterns:
                if pattern in command.lower():
                    raise CodeExecutionError(f"Dangerous command detected: {pattern}")
            
            if not shell:
                command_list = shlex.split(command)
            else:
                command_list = command
                
            result = subprocess.run(
                command_list,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                shell=shell
            )
            
            execution_time = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout if result.returncode == 0 else result.stderr,
                "return_code": result.returncode,
                "execution_time": execution_time
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": f"Command timed out after {self.timeout} seconds",
                "return_code": -1,
                "execution_time": self.timeout
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Execution error: {str(e)}",
                "return_code": -1,
                "execution_time": time.time() - start_time
            }
    
    def execute_python(self, code: str, keep_temp_file: bool = False) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            # Create temp file name and full path
            temp_filename = f"temp_python_{uuid.uuid4().hex[:8]}.py"
            python_file = os.path.join(self.working_dir, temp_filename)
            
            with open(python_file, 'w') as f:
                f.write(code)
            
            if keep_temp_file:
                self.files_created.append(python_file)
            
            # Use just the filename since we're running from the working directory
            result = subprocess.run(
                [
                    'python3', temp_filename
                ],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            execution_time = time.time() - start_time
            
            if not keep_temp_file and os.path.exists(python_file):
                os.remove(python_file)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout if result.returncode == 0 else result.stderr,
                "execution_time": execution_time
            }
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            if not keep_temp_file and 'python_file' in locals() and os.path.exists(python_file):
                os.remove(python_file)
            return {
                "success": False,
                "output": f"Python execution timed out after {self.timeout} seconds",
                "execution_time": execution_time
            }
        except Exception as e:
            execution_time = time.time() - start_time
            if not keep_temp_file and 'python_file' in locals() and os.path.exists(python_file):
                os.remove(python_file)
            return {
                "success": False,
                "output": f"Python execution error: {str(e)}",
                "execution_time": execution_time
            }
    
    def execute_javascript(self, code: str) -> Dict[str, Any]:
        """Execute JavaScript code directly with Node.js"""
        start_time = time.time()
        
        try:
            # Create temp file name and full path
            temp_filename = f"temp_{uuid.uuid4().hex[:8]}.js"
            js_file = os.path.join(self.working_dir, temp_filename)
            
            with open(js_file, 'w') as f:
                f.write(code)
            
            # Use just the filename since _run_command runs from working_dir
            exec_result = self._run_command(f"node {temp_filename}")
            
            if os.path.exists(js_file):
                os.remove(js_file)
            
            return {
                "success": exec_result["success"],
                "output": exec_result["output"],
                "execution_time": time.time() - start_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "output": f"JavaScript execution error: {str(e)}",
                "execution_time": time.time() - start_time
            }
    
    def execute_shell(self, command: str) -> Dict[str, Any]:
        """Execute shell command with safety checks"""
        return self._run_command(command, shell=True)
    
    def create_file(self, filename: str, content: str) -> Dict[str, Any]:
        """Create a file in the working directory"""
        try:
            file_path = os.path.join(self.working_dir, filename)
            
            # Log the file creation attempt for debugging
            logger.info(f"🔧 Creating file: {file_path}")
            logger.info(f"📁 Working dir: {self.working_dir}")
            logger.info(f"✅ Working dir exists: {os.path.exists(self.working_dir)}")
            logger.info(f"✏️  Working dir writable: {os.access(self.working_dir, os.W_OK)}")
            
            # Check permissions more thoroughly
            import stat
            if os.path.exists(self.working_dir):
                st = os.stat(self.working_dir)
                logger.info(f"📊 Working dir permissions: {oct(st.st_mode)}")
                logger.info(f"👤 Working dir owner: uid={st.st_uid}, gid={st.st_gid}")
                logger.info(f"🔍 Current process: uid={os.getuid()}, gid={os.getgid()}")
            
            # Only create directories if the filename contains a path separator
            # This prevents trying to create the working directory itself
            dir_path = os.path.dirname(file_path)
            if dir_path != self.working_dir:
                logger.info(f"📂 Creating subdirectory: {dir_path}")
                os.makedirs(dir_path, exist_ok=True)
                # Set permissions on created subdirectory
                os.chmod(dir_path, 0o755)
            
            # Set umask for this process to ensure readable files
            old_umask = os.umask(0o022)
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                
                # Explicitly set file permissions
                os.chmod(file_path, 0o644)
            finally:
                os.umask(old_umask)
            
            # Verify file was actually created and has content
            if not os.path.exists(file_path):
                raise RuntimeError(f"File was not created: {file_path}")
            
            file_size = os.path.getsize(file_path)
            if file_size == 0 and len(content) > 0:
                raise RuntimeError(f"File was created but is empty: {file_path}")
            
            self.files_created.append(file_path)
            logger.info(f"✅ Successfully created file: {file_path} ({file_size} bytes)")
            
            # Auto-open file in gedit if enabled
            if self.auto_open_files:
                try:
                    # Set environment variables like in supervisor config
                    env = os.environ.copy()
                    env["DISPLAY"] = ":0"
                    env["GDK_BACKEND"] = "x11"
                    env["HOME"] = "/home/agent"
                    
                    # Run gedit command with proper environment
                    gedit_result = subprocess.run(
                        f"gedit '{file_path}' &",
                        shell=True,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if gedit_result.returncode == 0:
                        return {
                            "success": True,
                            "output": f"File created: {file_path} ({file_size} bytes) and opened in gedit",
                            "file_path": file_path,
                            "opened_in_gedit": True
                        }
                    else:
                        logger.warning(f"gedit command failed: {gedit_result.stderr}")
                except Exception as e:
                    logger.warning(f"Failed to auto-open file in gedit: {e}")
            
            return {
                "success": True,
                "output": f"File created: {file_path} ({file_size} bytes)",
                "file_path": file_path,
                "opened_in_gedit": False
            }
        except Exception as e:
            logger.error(f"❌ Failed to create file {filename}: {str(e)}")
            import traceback
            logger.error(f"📍 Full traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "output": f"Failed to create file: {str(e)}"
            }
    
    def get_created_files(self) -> List[str]:
        """Get list of files created during execution"""
        return self.files_created.copy()
    
    def clear_file_tracking(self):
        """Clear the list of tracked files"""
        self.files_created.clear()
    
    def read_file(self, filename: str) -> Dict[str, Any]:
        """Read a file from the working directory"""
        try:
            file_path = os.path.join(self.working_dir, filename)
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            return {
                "success": True,
                "output": content,
                "file_path": file_path
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Failed to read file: {str(e)}"
            }
    
    def list_files(self, path: str = ".") -> Dict[str, Any]:
        """List files in the working directory or specified path"""
        try:
            target_path = os.path.join(self.working_dir, path)
            files = []
            
            for item in os.listdir(target_path):
                item_path = os.path.join(target_path, item)
                is_dir = os.path.isdir(item_path)
                files.append({
                    "name": item,
                    "type": "directory" if is_dir else "file",
                    "path": item_path
                })
            
            return {
                "success": True,
                "output": f"Found {len(files)} items",
                "files": files
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Failed to list files: {str(e)}"
            }
    



_executor = None
_job_executors = {}

def get_executor(job_id: Optional[str] = None, auto_open_files: bool = True) -> CodeExecutor:
    """Get or create code executor instance - job-specific if job_id provided"""
    global _executor, _job_executors
    
    if job_id:
        if job_id not in _job_executors:
            _job_executors[job_id] = CodeExecutor(job_id=job_id, auto_open_files=auto_open_files)
        return _job_executors[job_id]
    else:
        if _executor is None:
            _executor = CodeExecutor(auto_open_files=auto_open_files)
        return _executor

def get_job_files(job_id: str) -> List[str]:
    """Get list of files created for a specific job"""
    if job_id in _job_executors:
        return _job_executors[job_id].get_created_files()
    return []

def cleanup_job_executor(job_id: str):
    """Clean up executor for a completed job"""
    global _job_executors
    if job_id in _job_executors:
        del _job_executors[job_id]



@tool
def execute_python_code(code: str) -> str:
    """
    Execute Python code and return the result.
    
    Args:
        code: Python code to execute
        
    Returns:
        Execution result as string
    """
    executor = get_executor()
    result = executor.execute_python(code)
    
    if result["success"]:
        return f"✅ Execution successful (took {result['execution_time']:.2f}s):\n{result['output']}"
    else:
        return f"❌ Execution failed (took {result['execution_time']:.2f}s):\n{result['output']}"


@tool  
def execute_shell_command(command: str) -> str:
    """
    Execute a shell command and return the result.
    
    Args:
        command: Shell command to execute
        
    Returns:
        Execution result as string
    """
    executor = get_executor()
    result = executor.execute_shell(command)
    
    if result["success"]:
        return f"✅ Command successful (took {result['execution_time']:.2f}s):\n{result['output']}"
    else:
        return f"❌ Command failed (took {result['execution_time']:.2f}s):\n{result['output']}"


@tool
def execute_javascript_code(code: str) -> str:
    """
    Execute JavaScript code directly with Node.js.
    
    Args:
        code: JavaScript code to execute
        
    Returns:
        Execution result as string
    """
    executor = get_executor()
    result = executor.execute_javascript(code)
    
    if result["success"]:
        return f"✅ JavaScript execution successful (took {result['execution_time']:.2f}s):\n{result['output']}"
    else:
        return f"❌ JavaScript execution failed (took {result['execution_time']:.2f}s):\n{result['output']}"


@tool
def create_file_tool(filename: str, content: str) -> str:
    """
    Create a file with the specified content.
    
    Args:
        filename: Name of the file to create
        content: Content to write to the file
        
    Returns:
        Result of file creation
    """
    executor = get_executor()
    result = executor.create_file(filename, content)
    
    if result["success"]:
        response = f"✅ {result['output']}"
        if result.get("opened_in_gedit", False):
            response += " - File automatically opened in gedit and visible via VNC at localhost:6080"
        return response
    else:
        return f"❌ {result['output']}"


@tool
def read_file_tool(filename: str) -> str:
    """
    Read the contents of a file.
    
    Args:
        filename: Name of the file to read
        
    Returns:
        File contents or error message
    """
    executor = get_executor()
    result = executor.read_file(filename)
    
    if result["success"]:
        return f"✅ File contents:\n{result['output']}"
    else:
        return f"❌ {result['output']}"


@tool
def list_files_tool(path: str = ".") -> str:
    """
    List files and directories in the specified path.
    
    Args:
        path: Path to list (default: current directory)
        
    Returns:
        List of files and directories
    """
    executor = get_executor()
    result = executor.list_files(path)
    
    if result["success"]:
        files_info = []
        for file_info in result["files"]:
            files_info.append(f"{file_info['type'].upper()}: {file_info['name']}")
        
        return f"✅ Files in {path}:\n" + "\n".join(files_info)
    else:
        return f"❌ {result['output']}"





CODING_TOOLS = [
    execute_python_code,
    execute_shell_command, 
    execute_javascript_code,
    create_file_tool,
    read_file_tool,
    list_files_tool
]
