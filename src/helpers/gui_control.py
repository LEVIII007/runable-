import subprocess
import os
import time
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class GUIController:
    """Simple GUI controller for opening and displaying files on the VNC desktop"""
    
    def __init__(self, display: str = ":0"):
        self.display = display
        self.env = os.environ.copy()
        self.env["DISPLAY"] = self.display
        self._display_ready = None
        self._last_display_check = 0
    
    def _check_display_ready(self, force_check: bool = False) -> bool:
        """Check if X display is ready with caching and retry logic"""
        current_time = time.time()
        
        # Cache the result for 10 seconds unless forced
        if not force_check and self._display_ready is not None and (current_time - self._last_display_check) < 10:
            return self._display_ready
        
        try:
            # Try multiple display checks
            checks = [
                "xdpyinfo > /dev/null 2>&1",
                "xset q > /dev/null 2>&1",
                "xrandr > /dev/null 2>&1"
            ]
            
            for check_cmd in checks:
                result = subprocess.run(
                    check_cmd,
                    shell=True,
                    env=self.env,
                    capture_output=True,
                    timeout=3
                )
                if result.returncode == 0:
                    self._display_ready = True
                    self._last_display_check = current_time
                    logger.debug(f"X display {self.display} is ready")
                    return True
            
            # If all checks failed, try to start Xvfb if it's not running
            if not self._start_xvfb_if_needed():
                self._display_ready = False
                self._last_display_check = current_time
                logger.warning(f"X display {self.display} is not available")
                return False
                
        except Exception as e:
            logger.error(f"Error checking display: {e}")
            self._display_ready = False
            self._last_display_check = current_time
            return False
        
        return False
    
    def _start_xvfb_if_needed(self) -> bool:
        """Try to start Xvfb if it's not running"""
        try:
            # Check if Xvfb is already running
            check_result = subprocess.run(
                "pgrep Xvfb",
                shell=True,
                capture_output=True,
                timeout=5
            )
            
            if check_result.returncode == 0:
                logger.info("Xvfb is already running")
                return True
            
            # Try to start Xvfb
            logger.info("Attempting to start Xvfb...")
            start_result = subprocess.run(
                f"Xvfb {self.display} -screen 0 1280x800x24 -listen tcp -ac &",
                shell=True,
                capture_output=True,
                timeout=10
            )
            
            if start_result.returncode == 0:
                # Wait a moment for Xvfb to initialize
                time.sleep(2)
                logger.info("Xvfb started successfully")
                return True
            else:
                logger.error(f"Failed to start Xvfb: {start_result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting Xvfb: {e}")
            return False
    
    def _run_gui_command(self, command: str, retries: int = 2) -> Dict[str, Any]:
        """Execute a GUI command with proper DISPLAY environment and retry logic"""
        
        for attempt in range(retries + 1):
            try:
                # Check if display is ready
                if not self._check_display_ready(force_check=(attempt > 0)):
                    if attempt < retries:
                        logger.info(f"Display not ready, retrying in 2 seconds (attempt {attempt + 1}/{retries + 1})")
                        time.sleep(2)
                        continue
                    else:
                        return {
                            "success": False,
                            "output": f"X display {self.display} not available after {retries + 1} attempts",
                            "return_code": -2,
                            "suggestion": "Try accessing the VNC desktop at http://localhost:6080 to see if the display is working"
                        }
                
                logger.debug(f"Executing GUI command (attempt {attempt + 1}): {command}")
                result = subprocess.run(
                    command,
                    shell=True,
                    env=self.env,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout if result.returncode == 0 else result.stderr,
                    "return_code": result.returncode
                }
                
            except subprocess.TimeoutExpired:
                logger.error(f"GUI command timed out: {command}")
                if attempt < retries:
                    logger.info(f"Retrying command after timeout (attempt {attempt + 1}/{retries + 1})")
                    time.sleep(1)
                    continue
                else:
                    return {
                        "success": False,
                        "output": "GUI command timed out",
                        "return_code": -1
                    }
            except Exception as e:
                logger.error(f"GUI command error: {str(e)}")
                if attempt < retries:
                    logger.info(f"Retrying command after error (attempt {attempt + 1}/{retries + 1})")
                    time.sleep(1)
                    continue
                else:
                    return {
                        "success": False,
                        "output": f"GUI command error: {str(e)}",
                        "return_code": -1
                    }
        
        return {
            "success": False,
            "output": "All retry attempts failed",
            "return_code": -1
        }
    
    def open_file_in_editor(self, file_path: str, editor: str = "gedit") -> Dict[str, Any]:
        """Open a file in a text editor on the VNC display"""
        
        if not os.path.exists(file_path):
            return {
                "success": False,
                "output": f"File not found: {file_path}"
            }
        
        editors = {
            "gedit": "gedit",
            "xterm": "xterm -e vim",
            "terminal": "xterm -e nano"
        }
        
        if editor not in editors:
            editor = "gedit"
        
        # Try the primary editor first
        command = f"{editors[editor]} '{file_path}' &"
        result = self._run_gui_command(command)
        
        if result["success"]:
            time.sleep(2)
            logger.info(f"Successfully opened {file_path} in {editor}")
            return {
                "success": True,
                "output": f"Opened {file_path} in {editor}",
                "editor": editor,
                "file_path": file_path
            }
        else:
            # Try fallback editors
            fallback_editors = ["xterm", "terminal"] if editor == "gedit" else ["gedit"]
            
            for fallback_editor in fallback_editors:
                logger.warning(f"{editor} failed, trying {fallback_editor} as fallback")
                fallback_command = f"{editors[fallback_editor]} '{file_path}' &"
                fallback_result = self._run_gui_command(fallback_command)
                
                if fallback_result["success"]:
                    time.sleep(2)
                    logger.info(f"Successfully opened {file_path} in {fallback_editor}")
                    return {
                        "success": True,
                        "output": f"Opened {file_path} in {fallback_editor} (fallback)",
                        "editor": fallback_editor,
                        "file_path": file_path
                    }
            
            # If all editors fail, provide helpful error message
            error_msg = result.get("output", "unknown error")
            suggestion = result.get("suggestion", "")
            
            return {
                "success": False,
                "output": f"Failed to open {file_path} with any available editor: {error_msg}",
                "suggestion": suggestion or "Try accessing the VNC desktop at http://localhost:6080 to manually open the file"
            }
    
    def open_file_browser(self, directory: str = None) -> Dict[str, Any]:
        """Open file browser to show directory contents"""
        
        if directory and not os.path.exists(directory):
            return {
                "success": False,
                "output": f"Directory not found: {directory}"
            }
        
        file_managers = ["nautilus", "thunar", "pcmanfm", "xterm"]
        
        for fm in file_managers:
            if directory:
                command = f"{fm} '{directory}' &"
            else:
                command = f"{fm} &"
                
            result = self._run_gui_command(f"which {fm.split()[0]}")
            if result["success"]:
                gui_result = self._run_gui_command(command)
                if gui_result["success"]:
                    time.sleep(1)
                    return {
                        "success": True,
                        "output": f"Opened file browser ({fm}) for {directory or 'current directory'}",
                        "file_manager": fm,
                        "directory": directory
                    }
        
        return {
            "success": False,
            "output": "No file manager available"
        }
    
    def take_screenshot(self, output_path: str = None) -> Dict[str, Any]:
        """Take a screenshot of the current desktop"""
        
        if not output_path:
            output_path = f"/tmp/screenshot_{int(time.time())}.png"
        
        command = f"scrot '{output_path}'"
        result = self._run_gui_command(command)
        
        if result["success"]:
            return {
                "success": True,
                "output": f"Screenshot saved to {output_path}",
                "screenshot_path": output_path
            }
        else:
            return result
    
    def show_workspace_files(self, workspace_dir: str) -> Dict[str, Any]:
        """Open the workspace directory and key files for viewing"""
        
        if not os.path.exists(workspace_dir):
            return {
                "success": False,
                "output": f"Workspace directory not found: {workspace_dir}"
            }
        
        results = []
        
        browser_result = self.open_file_browser(workspace_dir)
        results.append(browser_result)
        
        code_extensions = ['.py', '.js', '.ts', '.html', '.css', '.json', '.md']
        opened_files = []
        
        for root, dirs, files in os.walk(workspace_dir):
            for file in files:
                if any(file.endswith(ext) for ext in code_extensions):
                    file_path = os.path.join(root, file)
                    if len(opened_files) < 3:
                        file_result = self.open_file_in_editor(file_path)
                        if file_result["success"]:
                            opened_files.append(file_path)
                            results.append(file_result)
        
        return {
            "success": True,
            "output": f"Opened workspace {workspace_dir} with {len(opened_files)} code files",
            "workspace_dir": workspace_dir,
            "opened_files": opened_files,
            "results": results
        }


_gui_controller: Optional[GUIController] = None

def get_gui_controller() -> GUIController:
    """Get or create the global GUI controller instance"""
    global _gui_controller
    if _gui_controller is None:
        _gui_controller = GUIController()
    return _gui_controller


@tool
def open_file_on_screen(file_path: str, editor: str = "gedit") -> str:
    """
    Open a code file in a text editor on the VNC display screen.
    
    Args:
        file_path: Path to the file to open
        editor: Text editor to use (gedit, nano, vim, code)
        
    Returns:
        Result of opening the file
    """
    controller = get_gui_controller()
    result = controller.open_file_in_editor(file_path, editor)
    
    if result["success"]:
        return f"✅ {result['output']} - Users can now see the file via VNC at localhost:6080"
    else:
        return f"❌ {result['output']}"


@tool
def show_workspace_on_screen(workspace_dir: str) -> str:
    """
    Open the workspace directory and display key code files on screen.
    
    Args:
        workspace_dir: Path to the workspace directory
        
    Returns:
        Result of opening workspace files
    """
    controller = get_gui_controller()
    result = controller.show_workspace_files(workspace_dir)
    
    if result["success"]:
        opened_files = "\n".join(f"  - {f}" for f in result.get("opened_files", []))
        return f"✅ {result['output']}\n\nOpened files:\n{opened_files}\n\nUsers can see the workspace via VNC at localhost:6080"
    else:
        return f"❌ {result['output']}"


@tool
def take_desktop_screenshot(output_path: str = None) -> str:
    """
    Take a screenshot of the current desktop display.
    
    Args:
        output_path: Optional path to save screenshot (default: /tmp/screenshot_<timestamp>.png)
        
    Returns:
        Result of taking screenshot
    """
    controller = get_gui_controller()
    result = controller.take_screenshot(output_path)
    
    if result["success"]:
        return f"✅ {result['output']}"
    else:
        return f"❌ {result['output']}"



GUI_TOOLS = [
    open_file_on_screen,
    show_workspace_on_screen,
    take_desktop_screenshot
] 