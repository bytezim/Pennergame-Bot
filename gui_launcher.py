#!/usr/bin/env python3
"""
PennerBot GUI Launcher
"""

import sys
import json
import threading
import subprocess
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Handle encoding for bundled executables
import io

# Ensure stdout/stderr can handle Unicode in bundled apps
if hasattr(sys, '_MEIPASS'):
    try:
        if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer is not None:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer is not None:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass


# GUI imports
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.scrolledtext as scrolledtext

# Threading imports for in-process server execution
import threading
import uvicorn
import aiohttp

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import database cleanup function
from src.db import close_db_connection

# Default ports
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 1420
LOG_MAX_LINES = 10000

class ProcessManager:
    """Simple process manager"""
    
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.is_pyinstaller_bundle = hasattr(sys, '_MEIPASS')
        self._backend_thread = None
        self._frontend_thread = None
        self._backend_reader = None  # StringIO for bundle mode
        self._backend_output = []  # List to capture backend output in bundle mode
        self._backend_lock = threading.Lock()
        
    def start_backend(self, port: int = 8000) -> bool:
        """Start the FastAPI backend"""
        if self.is_pyinstaller_bundle:
            # Run backend in a thread for bundle mode
            import os
            import io
            import logging
            
            # Create pipes for capturing output
            self._backend_reader = io.StringIO()
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            
            def run_backend():
                # Redirect stdout/stderr to capture logs
                sys.stdout = self._backend_reader
                sys.stderr = self._backend_reader
                
                try:
                    # Change to bundle directory for proper module resolution
                    if hasattr(sys, '_MEIPASS'):
                        bundle_dir = sys._MEIPASS
                        os.chdir(bundle_dir)
                        if bundle_dir not in sys.path:
                            sys.path.insert(0, bundle_dir)
                    
                    # Import and run server directly (not via string reference)
                    import uvicorn
                    from server import app
                    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
                except Exception as e:
                    error_msg = f"Backend thread error: {e}"
                    try:
                        print(error_msg)
                        import traceback
                        traceback.print_exc()
                    except:
                        pass
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
            
            self._backend_thread = threading.Thread(target=run_backend, daemon=True)
            self._backend_thread.start()
            
            # Wait for server to start
            time.sleep(3)
            return True
        
        # Development mode: spawn subprocess
        if self.backend_process and self.backend_process.poll() is None:
            return True
        
        try:
            server_py = Path(__file__).parent / "server.py"
            cmd = [sys.executable, str(server_py),
                   "--host", "127.0.0.1", "--port", str(port)]
            
            self.backend_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            time.sleep(2)
            if self.backend_process.poll() is None:
                return True
            else:
                stdout, stderr = self.backend_process.communicate()
                print(f"Backend failed to start: {stderr}")
                return False
                
        except Exception as e:
            print(f"Error starting backend: {e}")
            return False
    
    def start_frontend(self, port: int = 1420) -> bool:
        """Start the frontend server"""
        if self.is_pyinstaller_bundle:
            # Run frontend in a thread for bundle mode
            def run_frontend():
                from web.serve import run_server
                run_server(port=port)
            
            self._frontend_thread = threading.Thread(target=run_frontend, daemon=True)
            self._frontend_thread.start()
            
            # Wait for server to start
            time.sleep(2)
            return True
        
        # Development mode: spawn subprocess
        if self.frontend_process and self.frontend_process.poll() is None:
            return True
        
        try:
            dist_path = Path(__file__).parent / "web" / "dist"
            if not dist_path.exists():
                print("Frontend build not found. Please build the frontend first with: npm run build")
                return False
            
            serve_py = Path(__file__).parent / "web" / "serve.py"
            cmd = [sys.executable, str(serve_py), "--port", str(port)]
            
            self.frontend_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            time.sleep(2)
            if self.frontend_process.poll() is None:
                return True
            else:
                stdout, stderr = self.frontend_process.communicate()
                print(f"Frontend failed to start: {stderr}")
                return False
                
        except Exception as e:
            print(f"Error starting frontend: {e}")
            return False
    
    def stop_backend(self):
        """Stop the backend process"""
        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
            except Exception as e:
                print(f"Error stopping backend: {e}")
            finally:
                self.backend_process = None
    
    def stop_frontend(self):
        """Stop the frontend process"""
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
            except Exception as e:
                print(f"Error stopping frontend: {e}")
            finally:
                self.frontend_process = None
    
    def stop_all(self):
        """Stop all processes"""
        self.stop_backend()
        self.stop_frontend()
    
    def get_backend_logs(self) -> list:
        """Get captured backend logs (for bundle mode)"""
        if self.is_pyinstaller_bundle and self._backend_reader:
            # Read new content from StringIO
            current_pos = self._backend_reader.tell()
            self._backend_reader.seek(0)
            content = self._backend_reader.read()
            self._backend_reader.seek(current_pos)
            
            # Parse lines and add to output list
            lines = content.split('\n')
            with self._backend_lock:
                for line in lines:
                    if line.strip():
                        self._backend_output.append(line.strip())
            
            # Return only new lines (lines not yet returned)
            return list(self._backend_output)
        return []
    
    def is_backend_running(self) -> bool:
        """Check if backend is running"""
        if self.is_pyinstaller_bundle:
            # Check if thread is alive
            return self._backend_thread is not None and self._backend_thread.is_alive()
        return self.backend_process and self.backend_process.poll() is None
    
    def is_frontend_running(self) -> bool:
        """Check if frontend is running"""
        return self.frontend_process and self.frontend_process.poll() is None

class LogCapture:
    """Simple log capture"""
    
    def __init__(self, max_lines: int = LOG_MAX_LINES):
        self.log_lines: List[Dict[str, Any]] = []
        self.max_lines = max_lines
        self.subscribers: List[callable] = []
        
    def add_subscriber(self, callback: callable):
        """Add a callback for new log entries"""
        self.subscribers.append(callback)
    
    def remove_subscriber(self, callback: callable):
        """Remove a callback"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def add_log_entry(self, level: str, message: str, timestamp: Optional[datetime] = None):
        """Add a new log entry"""
        if timestamp is None:
            timestamp = datetime.now()
            
        entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "formatted": f"[{timestamp.strftime('%H:%M:%S')}] {level}: {message}"
        }
        
        # Add to lines list
        self.log_lines.append(entry)
        
        # Maintain max lines
        if len(self.log_lines) > self.max_lines:
            self.log_lines = self.log_lines[-self.max_lines:]
        
        # Notify subscribers
        for callback in self.subscribers:
            try:
                callback(entry)
            except Exception:
                pass

class SimpleGUI:
    """GUI"""
    
    def __init__(self):
        self.process_manager = ProcessManager()
        self.log_capture = LogCapture()
        
        # GUI elements
        self.root = None
        self.log_text = None
        self.status_var = None
        
        # Threading
        self.log_thread = None
        self.running = False
        
        # Setup
        self.setup_gui()
        self.setup_log_capture()

        # Auto-start services on launch
        self.auto_start_services()
        self.status_var.set("Starting services...")
    
    def setup_gui(self):
        """Setup the minimal GUI"""
        self.root = tk.Tk()
        self.root.title("PennerBot")
        self.root.geometry("800x600+100+100")
        
        # Remove window decorations that add padding
        self.root.resizable(True, True)
        
        # Protocol for window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Apply simple dark theme
        self.setup_theme()
        
        # Variables
        self.status_var = tk.StringVar(value="Initializing...")
        
        # Create minimal interface
        self.create_header()
        self.create_log_display()
        self.create_footer()
        
        # Bind events
        self.root.bind('<Control-r>', lambda e: self.open_frontend_browser())
    
    def setup_theme(self):
        """Setup simple dark theme"""
        # Configure root window
        self.root.configure(bg='#1e1e1e')
        
        # Simple color scheme
        self.colors = {
            'bg_primary': '#1e1e1e',
            'bg_secondary': '#252526',
            'text_primary': '#d4d4d4',
            'text_secondary': '#858585',
            'accent_blue': '#007acc',
            'success': '#4ec9b0',
            'danger': '#f44747',
            'warning': '#ffcc00'
        }
        
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Simple button style
        style.configure('Simple.TButton',
                       background=self.colors['bg_secondary'],
                       foreground=self.colors['text_primary'],
                       borderwidth=0,
                       focuscolor='none',
                       font=('Segoe UI', 9))
        style.map('Simple.TButton',
                 background=[('active', self.colors['accent_blue'])])
        
        # Simple frame style
        style.configure('Simple.TFrame',
                       background=self.colors['bg_primary'],
                       borderwidth=0)
        
        # Simple label style
        style.configure('Simple.TLabel',
                       background=self.colors['bg_primary'],
                       foreground=self.colors['text_primary'],
                       font=('Segoe UI', 9))
    
    def create_header(self):
        """Create minimal header"""
        header_frame = tk.Frame(self.root, bg=self.colors['bg_secondary'], height=30)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(header_frame, text="PennerBot",
                              font=('Segoe UI', 12, 'bold'),
                              fg=self.colors['accent_blue'],
                              bg=self.colors['bg_secondary'])
        title_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Controls on the right
        controls_frame = tk.Frame(header_frame, bg=self.colors['bg_secondary'])
        controls_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Browser button
        browser_btn = tk.Button(controls_frame, text="🌐 Open Frontend",
                               command=self.open_frontend_browser,
                               bg=self.colors['accent_blue'],
                               fg='white',
                               font=('Segoe UI', 9),
                               relief='flat',
                               bd=0,
                               padx=10, pady=2,
                               cursor='hand2')
        browser_btn.pack(side=tk.RIGHT, padx=2)
        
        # Status indicator
        status_frame = tk.Frame(controls_frame, bg=self.colors['bg_secondary'])
        status_frame.pack(side=tk.RIGHT, padx=(0, 10))
        
        status_label = tk.Label(status_frame, textvariable=self.status_var,
                               fg=self.colors['text_secondary'],
                               bg=self.colors['bg_secondary'],
                               font=('Segoe UI', 8))
        status_label.pack(side=tk.LEFT)
    
    def create_log_display(self):
        """Create minimal log display area"""
        # Main log frame with no wasted space
        log_frame = tk.Frame(self.root, bg=self.colors['bg_primary'])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create minimal scrolled text widget
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 9),
            bg=self.colors['bg_secondary'],
            fg=self.colors['text_primary'],
            selectbackground=self.colors['accent_blue'],
            selectforeground=self.colors['text_primary'],
            insertbackground=self.colors['accent_blue'],
            relief='flat',
            bd=2,
            padx=10,
            pady=5
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for log levels
        self.log_text.tag_configure("INFO", foreground=self.colors['text_primary'])
        self.log_text.tag_configure("WARNING", foreground=self.colors['warning'])
        self.log_text.tag_configure("ERROR", foreground=self.colors['danger'])
        self.log_text.tag_configure("DEBUG", foreground=self.colors['text_secondary'])
        self.log_text.tag_configure("BOT", foreground=self.colors['success'])
    
    def create_footer(self):
        """Create minimal footer"""
        footer_frame = tk.Frame(self.root, bg=self.colors['bg_secondary'], height=20)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)
        
        # Copyright info
        copyright_label = tk.Label(footer_frame, text="v0.0.4",
                                  fg=self.colors['text_secondary'],
                                  bg=self.colors['bg_secondary'],
                                  font=('Segoe UI', 7))
        copyright_label.pack(side=tk.RIGHT, padx=5, pady=2)
    
    def setup_log_capture(self):
        """Setup log capture from backend process"""
        def log_reader():
            """Background thread to read logs from backend"""
            last_content_len = 0
            while self.running:
                try:
                    # Development mode: prefer blocking read from subprocess stdout
                    if not self.process_manager.is_pyinstaller_bundle:
                        if self.process_manager.is_backend_running():
                            backend = self.process_manager.backend_process
                            # Use iterator to block on readline and process lines immediately
                            if backend and backend.stdout:
                                for line in iter(backend.stdout.readline, ''):
                                    if not self.running:
                                        break
                                    if line:
                                        level = "INFO"
                                        message = line.strip()

                                        if "ERROR" in message or "❌" in message:
                                            level = "ERROR"
                                        elif "WARNING" in message or "⚠️" in message:
                                            level = "WARNING"
                                        elif "DEBUG" in message:
                                            level = "DEBUG"
                                        elif "[BOT]" in message or "Bot" in message:
                                            level = "BOT"

                                        self.log_capture.add_log_entry(level, message)
                                    else:
                                        # EOF reached
                                        break
                        else:
                            # Backend not running: short sleep to avoid busy-loop
                            time.sleep(0.1)

                    else:
                        # Bundle mode: poll the StringIO capture more frequently
                        if self.process_manager._backend_reader:
                            current_pos = self.process_manager._backend_reader.tell()
                            self.process_manager._backend_reader.seek(0)
                            content = self.process_manager._backend_reader.read()
                            self.process_manager._backend_reader.seek(current_pos)

                            # Get only new content
                            if len(content) > last_content_len:
                                new_content = content[last_content_len:]
                                last_content_len = len(content)

                                # Parse and add each new line
                                for line in new_content.split('\n'):
                                    if line.strip():
                                        level = "INFO"
                                        message = line.strip()

                                        if "ERROR" in message or "❌" in message:
                                            level = "ERROR"
                                        elif "WARNING" in message or "⚠️" in message:
                                            level = "WARNING"
                                        elif "DEBUG" in message:
                                            level = "DEBUG"
                                        elif "[BOT]" in message or "Bot" in message:
                                            level = "BOT"

                                        self.log_capture.add_log_entry(level, message)

                        # Poll more frequently in bundle mode
                        time.sleep(0.1)

                except Exception as e:
                    # Log errors to GUI
                    error_msg = f"Error reading logs: {e}"
                    self.log_capture.add_log_entry("ERROR", error_msg)
                    time.sleep(1)
        
        self.running = True
        self.log_thread = threading.Thread(target=log_reader, daemon=True)
        self.log_thread.start()
        
        # Subscribe to log updates
        self.log_capture.add_subscriber(self.on_log_update)
        
        # Add a welcome message to show the interface is working
        welcome_msg = "PennerBot GUI Launcher Ready"
        self.log_capture.add_log_entry("INFO", welcome_msg)
        
        # Add mode information
        if self.process_manager.is_pyinstaller_bundle:
            bundle_msg = "Running in PyInstaller bundle mode"
            self.log_capture.add_log_entry("INFO", bundle_msg)
        else:
            dev_msg = "Running in development mode"
            self.log_capture.add_log_entry("INFO", dev_msg)
    
    def on_log_update(self, entry: Dict[str, Any]):
        """Handle new log entry"""
        # Schedule GUI update in main thread
        self.root.after(0, self.add_log_to_display, entry)
    
    def add_log_to_display(self, entry: Dict[str, Any]):
        """Add log entry to display"""
        try:
            self.log_text.config(state=tk.NORMAL)
            
            # Insert log line with styling
            tag = entry.get("level", "INFO").lower()
            self.log_text.insert(tk.END, entry["formatted"] + "\n", tag)
            
            # Auto-scroll to bottom
            self.log_text.see(tk.END)
            
            self.log_text.config(state=tk.DISABLED)
            
        except Exception as e:
            # Log errors to GUI
            error_msg = f"Error adding log to display: {e}"
            self.log_capture.add_log_entry("ERROR", error_msg)
    
    def auto_start_services(self):
        """Auto-start backend and frontend services"""
        def start_services():
            try:
                self.root.after(0, lambda: self.status_var.set("Starting services..."))
                
                # Start backend
                if not self.process_manager.start_backend(DEFAULT_BACKEND_PORT):
                    self.root.after(0, lambda: self.status_var.set("Failed to start backend"))
                    error_msg = "Failed to start backend service"
                    self.log_capture.add_log_entry("ERROR", error_msg)
                    return
                
                # Start frontend
                if not self.process_manager.start_frontend(DEFAULT_FRONTEND_PORT):
                    self.root.after(0, lambda: self.status_var.set("Failed to start frontend"))
                    error_msg = "Failed to start frontend service"
                    self.log_capture.add_log_entry("ERROR", error_msg)
                    return
                
                self.root.after(0, lambda: self.status_var.set("Services running"))
                
                # Open browser after a delay
                def open_browser():
                    try:
                        webbrowser.open(f"http://127.0.0.1:{DEFAULT_FRONTEND_PORT}")
                    except Exception as e:
                        error_msg = f"Could not open browser: {e}"
                        self.log_capture.add_log_entry("ERROR", error_msg)
                
                time.sleep(3)
                threading.Thread(target=open_browser, daemon=True).start()
                
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
                error_msg = f"Error in auto-start services: {e}"
                self.log_capture.add_log_entry("ERROR", error_msg)
        
        # Start in separate thread to avoid blocking GUI
        threading.Thread(target=start_services, daemon=True).start()
    
    def open_frontend_browser(self):
        """Open frontend in browser"""
        try:
            webbrowser.open(f"http://127.0.0.1:{DEFAULT_FRONTEND_PORT}")
        except Exception as e:
            error_msg = f"Could not open browser: {e}"
            self.log_capture.add_log_entry("ERROR", error_msg)
    
    def on_closing(self):
        """Handle window closing"""
        self.safe_exit()
    
    def safe_exit(self):
        """Safely exit the application"""
        self.running = False
        
        # Stop processes
        self.process_manager.stop_all()
        
        # Close database connection properly (merges WAL, removes shm/wal files)
        close_db_connection()
        
        # Destroy GUI
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Run the GUI application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.safe_exit()

def main():
    """Main entry point"""
    try:
        print("=" * 60)
        print("PennerBot GUI Launcher")
        print("=" * 60)
        
        # Create and run GUI
        gui = SimpleGUI()
        
        # Run GUI
        gui.run()
        
    except Exception as e:
        print(f"Critical error in GUI launcher: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
    finally:
        # Ensure clean shutdown
        try:
            if 'gui' in locals():
                gui.process_manager.stop_all()
            # Close database connection properly
            close_db_connection()
        except:
            pass

if __name__ == "__main__":
    main()