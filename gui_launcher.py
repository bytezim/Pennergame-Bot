import sys
import os
import json
import logging
import threading
import subprocess
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import io

if hasattr(sys, "_MEIPASS"):
    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()
    try:
        if hasattr(sys.stdout, "buffer") and sys.stdout.buffer is not None:
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding="utf-8", errors="replace"
            )
        if hasattr(sys.stderr, "buffer") and sys.stderr.buffer is not None:
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, encoding="utf-8", errors="replace"
            )
    except (AttributeError, OSError):
        pass
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("gui_launcher")
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.scrolledtext as scrolledtext
import threading
import uvicorn
import aiohttp

sys.path.insert(0, str(Path(__file__).parent))
from src.db import close_db_connection

DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 1420
LOG_MAX_LINES = 10000


class ProcessManager:

    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.is_pyinstaller_bundle = hasattr(sys, "_MEIPASS")
        self._backend_thread = None
        self._frontend_thread = None
        self._backend_reader = None
        self._backend_output = []
        self._backend_lock = threading.Lock()
        self._uvicorn_server = None
        self._should_exit = threading.Event()

    def start_backend(self, port: int = 8000) -> bool:
        if self.is_pyinstaller_bundle:
            import os
            import io

            self._backend_reader = io.StringIO()

            def run_backend():
                try:
                    if hasattr(sys, "_MEIPASS"):
                        bundle_dir = sys._MEIPASS
                        os.chdir(bundle_dir)
                        if bundle_dir not in sys.path:
                            sys.path.insert(0, bundle_dir)
                    import logging as _logging

                    sys.stdout = self._backend_reader
                    sys.stderr = self._backend_reader
                    root = _logging.getLogger()
                    for h in root.handlers[:]:
                        try:
                            h.close()
                        except Exception:
                            pass
                        root.removeHandler(h)
                    fmt = _logging.Formatter(
                        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
                    )
                    sh = _logging.StreamHandler(self._backend_reader)
                    sh.setLevel(_logging.INFO)
                    sh.setFormatter(fmt)
                    root.addHandler(sh)
                    root.setLevel(_logging.INFO)
                    import uvicorn
                    from server import app

                    for h in root.handlers[:]:
                        if h is not sh:
                            try:
                                h.close()
                            except Exception:
                                pass
                            root.removeHandler(h)
                    config = uvicorn.Config(
                        app, host="127.0.0.1", port=port, log_level="info"
                    )
                    self._uvicorn_server = uvicorn.Server(config)
                    self._uvicorn_server.run()
                except Exception as e:
                    error_msg = f"Backend thread error: {e}"
                    try:
                        logger.error(error_msg)
                        import traceback

                        traceback.print_exc()
                    except Exception:
                        pass
                finally:
                    self._uvicorn_server = None

            self._backend_thread = threading.Thread(target=run_backend, daemon=True)
            self._backend_thread.start()
            time.sleep(3)
            return True
        if self.backend_process and self.backend_process.poll() is None:
            return True
        try:
            server_py = Path(__file__).parent / "server.py"
            cmd = [
                sys.executable,
                str(server_py),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ]
            self.backend_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            time.sleep(2)
            if self.backend_process.poll() is None:
                return True
            else:
                stdout, stderr = self.backend_process.communicate()
                logger.error("Backend failed to start: %s", stderr)
                return False
        except Exception as e:
            logger.error("Error starting backend: %s", e)
            return False

    def start_frontend(self, port: int = 1420) -> bool:
        if self.is_pyinstaller_bundle:

            def run_frontend():
                import logging as _logging

                for log_name in ("aiohttp.access", "aiohttp.server", "aiohttp.web"):
                    _log = _logging.getLogger(log_name)
                    for h in _log.handlers[:]:
                        try:
                            h.close()
                        except Exception:
                            pass
                        _log.removeHandler(h)
                    sh = _logging.StreamHandler(sys.stdout)
                    sh.setLevel(_logging.INFO)
                    _log.addHandler(sh)
                from web.serve import run_server

                run_server(port=port)

            self._frontend_thread = threading.Thread(target=run_frontend, daemon=True)
            self._frontend_thread.start()
            time.sleep(2)
            return True
        if self.frontend_process and self.frontend_process.poll() is None:
            return True
        try:
            dist_path = Path(__file__).parent / "web" / "dist"
            if not dist_path.exists():
                logger.error(
                    "Frontend build not found. Please build the frontend first with: npm run build"
                )
                return False
            serve_py = Path(__file__).parent / "web" / "serve.py"
            cmd = [sys.executable, str(serve_py), "--port", str(port)]
            self.frontend_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            time.sleep(2)
            if self.frontend_process.poll() is None:
                return True
            else:
                stdout, stderr = self.frontend_process.communicate()
                logger.error("Frontend failed to start: %s", stderr)
                return False
        except Exception as e:
            logger.error("Error starting frontend: %s", e)
            return False

    def stop_backend(self):
        if self.is_pyinstaller_bundle and self._uvicorn_server:
            try:
                if hasattr(self._uvicorn_server, "should_exit"):
                    self._uvicorn_server.should_exit = True
            except Exception as e:
                logger.error("Error signaling uvicorn shutdown: %s", e)
            if self._backend_thread and self._backend_thread.is_alive():
                self._backend_thread.join(timeout=8)
        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
            except Exception as e:
                logger.error("Error stopping backend: %s", e)
            finally:
                self.backend_process = None

    def stop_frontend(self):
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
            except Exception as e:
                logger.error("Error stopping frontend: %s", e)
            finally:
                self.frontend_process = None

    def stop_all(self):
        self.stop_backend()
        self.stop_frontend()

    def get_backend_logs(self) -> list:
        if self.is_pyinstaller_bundle and self._backend_reader:
            current_pos = self._backend_reader.tell()
            self._backend_reader.seek(0)
            content = self._backend_reader.read()
            self._backend_reader.seek(current_pos)
            lines = content.split("\n")
            with self._backend_lock:
                for line in lines:
                    if line.strip():
                        self._backend_output.append(line.strip())
            return list(self._backend_output)
        return []

    def is_backend_running(self) -> bool:
        if self.is_pyinstaller_bundle:
            return self._backend_thread is not None and self._backend_thread.is_alive()
        return self.backend_process and self.backend_process.poll() is None

    def is_frontend_running(self) -> bool:
        return self.frontend_process and self.frontend_process.poll() is None


class LogCapture:

    def __init__(self, max_lines: int = LOG_MAX_LINES):
        self.log_lines: List[Dict[str, Any]] = []
        self.max_lines = max_lines
        self.subscribers: List[callable] = []

    def add_subscriber(self, callback: callable):
        self.subscribers.append(callback)

    def remove_subscriber(self, callback: callable):
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def add_log_entry(
        self, level: str, message: str, timestamp: Optional[datetime] = None
    ):
        if timestamp is None:
            timestamp = datetime.now()
        entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "formatted": f"[{timestamp.strftime('%H:%M:%S')}] {level}: {message}",
        }
        self.log_lines.append(entry)
        if len(self.log_lines) > self.max_lines:
            self.log_lines = self.log_lines[-self.max_lines :]
        for callback in self.subscribers:
            try:
                callback(entry)
            except Exception:
                pass


class SimpleGUI:

    def __init__(self):
        self.process_manager = ProcessManager()
        self.log_capture = LogCapture()
        self.root = None
        self.log_text = None
        self.status_var = None
        self.log_thread = None
        self.running = False
        self.setup_gui()
        self.setup_log_capture()
        self.auto_start_services()
        self.status_var.set("Starting services...")

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("PennerBot")
        if hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "web", "dist", "favicon.ico")
        else:
            icon_path = "web/dist/favicon.ico"
        try:
            self.root.iconbitmap(icon_path)
        except tk.TclError:
            pass
        self.root.geometry("800x600+100+100")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_theme()
        self.status_var = tk.StringVar(value="Initializing...")
        self.create_header()
        self.create_log_display()
        self.create_footer()
        self.root.bind("<Control-r>", lambda e: self.open_frontend_browser())

    def setup_theme(self):
        self.root.configure(bg="#1e1e1e")
        self.colors = {
            "bg_primary": "#1e1e1e",
            "bg_secondary": "#252526",
            "text_primary": "#d4d4d4",
            "text_secondary": "#858585",
            "accent_blue": "#007acc",
            "success": "#4ec9b0",
            "danger": "#f44747",
            "warning": "#ffcc00",
        }
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Simple.TButton",
            background=self.colors["bg_secondary"],
            foreground=self.colors["text_primary"],
            borderwidth=0,
            focuscolor="none",
            font=("Segoe UI", 9),
        )
        style.map("Simple.TButton", background=[("active", self.colors["accent_blue"])])
        style.configure(
            "Simple.TFrame", background=self.colors["bg_primary"], borderwidth=0
        )
        style.configure(
            "Simple.TLabel",
            background=self.colors["bg_primary"],
            foreground=self.colors["text_primary"],
            font=("Segoe UI", 9),
        )

    def create_header(self):
        header_frame = tk.Frame(self.root, bg=self.colors["bg_secondary"], height=30)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)
        title_label = tk.Label(
            header_frame,
            text="PennerBot",
            font=("Segoe UI", 12, "bold"),
            fg=self.colors["accent_blue"],
            bg=self.colors["bg_secondary"],
        )
        title_label.pack(side=tk.LEFT, padx=10, pady=5)
        controls_frame = tk.Frame(header_frame, bg=self.colors["bg_secondary"])
        controls_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        browser_btn = tk.Button(
            controls_frame,
            text="🌐 Open Frontend",
            command=self.open_frontend_browser,
            bg=self.colors["accent_blue"],
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            bd=0,
            padx=10,
            pady=2,
            cursor="hand2",
        )
        browser_btn.pack(side=tk.RIGHT, padx=2)
        status_frame = tk.Frame(controls_frame, bg=self.colors["bg_secondary"])
        status_frame.pack(side=tk.RIGHT, padx=(0, 10))
        status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            fg=self.colors["text_secondary"],
            bg=self.colors["bg_secondary"],
            font=("Segoe UI", 8),
        )
        status_label.pack(side=tk.LEFT)

    def create_log_display(self):
        log_frame = tk.Frame(self.root, bg=self.colors["bg_primary"])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 9),
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            selectbackground=self.colors["accent_blue"],
            selectforeground=self.colors["text_primary"],
            insertbackground=self.colors["accent_blue"],
            relief="flat",
            bd=2,
            padx=10,
            pady=5,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.tag_configure("INFO", foreground=self.colors["text_primary"])
        self.log_text.tag_configure("WARNING", foreground=self.colors["warning"])
        self.log_text.tag_configure("ERROR", foreground=self.colors["danger"])
        self.log_text.tag_configure("DEBUG", foreground=self.colors["text_secondary"])
        self.log_text.tag_configure("BOT", foreground=self.colors["success"])

    def create_footer(self):
        footer_frame = tk.Frame(self.root, bg=self.colors["bg_secondary"], height=20)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)
        copyright_label = tk.Label(
            footer_frame,
            text="v0.0.4",
            fg=self.colors["text_secondary"],
            bg=self.colors["bg_secondary"],
            font=("Segoe UI", 7),
        )
        copyright_label.pack(side=tk.RIGHT, padx=5, pady=2)

    def setup_log_capture(self):

        def log_reader():
            last_content_len = 0
            while self.running:
                try:
                    if not self.process_manager.is_pyinstaller_bundle:
                        if self.process_manager.is_backend_running():
                            backend = self.process_manager.backend_process
                            if backend and backend.stdout:
                                for line in iter(backend.stdout.readline, ""):
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
                                        break
                        else:
                            time.sleep(0.1)
                    else:
                        if self.process_manager._backend_reader:
                            current_pos = self.process_manager._backend_reader.tell()
                            self.process_manager._backend_reader.seek(0)
                            content = self.process_manager._backend_reader.read()
                            self.process_manager._backend_reader.seek(current_pos)
                            if len(content) > last_content_len:
                                new_content = content[last_content_len:]
                                last_content_len = len(content)
                                for line in new_content.split("\n"):
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
                        time.sleep(0.1)
                except Exception as e:
                    error_msg = f"Error reading logs: {e}"
                    self.log_capture.add_log_entry("ERROR", error_msg)
                    time.sleep(1)

        self.running = True
        self.log_thread = threading.Thread(target=log_reader, daemon=True)
        self.log_thread.start()
        self.log_capture.add_subscriber(self.on_log_update)
        welcome_msg = "PennerBot GUI Launcher Ready"
        self.log_capture.add_log_entry("INFO", welcome_msg)
        if self.process_manager.is_pyinstaller_bundle:
            bundle_msg = "Running in PyInstaller bundle mode"
            self.log_capture.add_log_entry("INFO", bundle_msg)
        else:
            dev_msg = "Running in development mode"
            self.log_capture.add_log_entry("INFO", dev_msg)

    def on_log_update(self, entry: Dict[str, Any]):
        self.root.after(0, self.add_log_to_display, entry)

    def add_log_to_display(self, entry: Dict[str, Any]):
        try:
            self.log_text.config(state=tk.NORMAL)
            tag = entry.get("level", "INFO").lower()
            self.log_text.insert(tk.END, entry["formatted"] + "\n", tag)
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        except Exception as e:
            error_msg = f"Error adding log to display: {e}"
            self.log_capture.add_log_entry("ERROR", error_msg)

    def auto_start_services(self):

        def start_services():
            try:
                self.root.after(0, lambda: self.status_var.set("Starting services..."))
                if not self.process_manager.start_backend(DEFAULT_BACKEND_PORT):
                    self.root.after(
                        0, lambda: self.status_var.set("Failed to start backend")
                    )
                    error_msg = "Failed to start backend service"
                    self.log_capture.add_log_entry("ERROR", error_msg)
                    return
                if not self.process_manager.start_frontend(DEFAULT_FRONTEND_PORT):
                    self.root.after(
                        0, lambda: self.status_var.set("Failed to start frontend")
                    )
                    error_msg = "Failed to start frontend service"
                    self.log_capture.add_log_entry("ERROR", error_msg)
                    return
                self.root.after(0, lambda: self.status_var.set("Services running"))

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

        threading.Thread(target=start_services, daemon=True).start()

    def open_frontend_browser(self):
        try:
            webbrowser.open(f"http://127.0.0.1:{DEFAULT_FRONTEND_PORT}")
        except Exception as e:
            error_msg = f"Could not open browser: {e}"
            self.log_capture.add_log_entry("ERROR", error_msg)

    def on_closing(self):
        self.safe_exit()

    def safe_exit(self):
        self.running = False
        self.process_manager.stop_backend()
        self.process_manager.stop_frontend()
        close_db_connection()
        if self.root:
            self.root.quit()
            self.root.destroy()

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.safe_exit()


def main():
    try:
        logger.info("=" * 60)
        logger.info("PennerBot GUI Launcher")
        logger.info("=" * 60)
        gui = SimpleGUI()
        gui.run()
    except Exception as e:
        logger.error("Critical error in GUI launcher: %s", e)
        import traceback

        traceback.print_exc()
        input("\nPress Enter to exit...")
    finally:
        try:
            if "gui" in locals():
                gui.process_manager.stop_backend()
                gui.process_manager.stop_frontend()
            close_db_connection()
        except Exception:
            pass


if __name__ == "__main__":
    main()
