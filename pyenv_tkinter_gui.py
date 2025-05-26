import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import subprocess
import threading
import queue
import os
import sys
import shutil
import re # For parsing progress if we attempt it later

class PyenvGUI:
    def __init__(self, master):
        self.master = master
        self.is_successfully_initialized = False

        self.gui_queue = queue.Queue()
        self.animating = False # For text-based status animation
        self.animation_index = 0
        self.ANIMATION_CHARS = ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"]

        # --- Style Configuration ---
        self.style = ttk.Style()
        if sys.platform == "win32":
            self.style.theme_use('vista')
        elif sys.platform == "darwin":
            self.style.theme_use('aqua') # 'aqua' or 'clam' often work well
        else:
            self.style.theme_use('clam') # Default for other platforms

        # General widget styling for a cleaner look
        self.style.configure("TFrame", padding=5)
        self.style.configure("TLabelFrame", padding=(10, 5), relief=tk.GROOVE)
        self.style.configure("TButton", padding=(8, 4), font=('Helvetica', 10))
        self.style.configure("Header.TLabel", font=('Helvetica', 12, 'bold'))
        self.style.configure("Status.TLabel", font=('Helvetica', 9))
        self.style.configure("Small.TLabel", font=('Helvetica', 9))
        self.style.configure("Error.TLabel", foreground="red", font=('Helvetica', 9))

        # Determine pyenv paths
        self.pyenv_executable_path = self._determine_pyenv_executable_path()
        self.pyenv_root_path = self._determine_pyenv_root_path()

        if not self.pyenv_executable_path or not self.is_pyenv_installed():
            # Error message box is shown by is_pyenv_installed or the check above
            return

        master.title("Pyenv Manager")
        master.geometry("950x750") # Slightly larger default size

        # --- Main Application Frame ---
        main_app_frame = ttk.Frame(master, padding=(10, 10, 10, 10))
        main_app_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Bar (Current Versions, Refresh, Status, Progress) ---
        self.top_bar_frame = ttk.Frame(main_app_frame, padding=(0, 0, 0, 10))
        self.top_bar_frame.pack(fill=tk.X)

        self.current_versions_frame = ttk.Frame(self.top_bar_frame)
        self.current_versions_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.current_global_label = ttk.Label(self.current_versions_frame, text="Global: N/A", style="Small.TLabel")
        self.current_global_label.pack(side=tk.LEFT, padx=(0,10))
        self.current_local_label = ttk.Label(self.current_versions_frame, text="Local: N/A", style="Small.TLabel")
        self.current_local_label.pack(side=tk.LEFT, padx=(0,10))

        self.refresh_all_button = ttk.Button(self.top_bar_frame, text="Refresh All", command=self.refresh_all_data, style="Accent.TButton")
        self.refresh_all_button.pack(side=tk.RIGHT, padx=(5,0))
        
        # Status Label and Progress Bar will share space on the right
        self.status_container = ttk.Frame(self.top_bar_frame)
        self.status_container.pack(side=tk.RIGHT, padx=(10,5), fill=tk.X)

        self.status_label = ttk.Label(self.status_container, text="", style="Status.TLabel", width=15, anchor=tk.E) # Anchor East
        self.status_label.pack(side=tk.RIGHT) # Will be hidden when progress bar is shown

        self.progress_bar = ttk.Progressbar(self.status_container, orient='horizontal', mode='indeterminate', length=150)
        # self.progress_bar will be packed/unpacked by its control methods

        # --- Main Content Area (PanedWindow) ---
        self.paned_window = ttk.PanedWindow(main_app_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Left Pane: Versions Lists
        self.versions_pane = ttk.Frame(self.paned_window, padding=5)
        self.paned_window.add(self.versions_pane, weight=2) # Give it a weight

        # Installed versions
        installed_frame = ttk.LabelFrame(self.versions_pane, text="Installed Versions")
        installed_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.installed_versions_list = tk.Listbox(installed_frame, height=12, exportselection=False, relief=tk.SOLID, borderwidth=1)
        self.installed_versions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=5)
        installed_scrollbar = ttk.Scrollbar(installed_frame, orient=tk.VERTICAL, command=self.installed_versions_list.yview)
        installed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,5), pady=5)
        self.installed_versions_list.config(yscrollcommand=installed_scrollbar.set)
        
        installed_actions_frame = ttk.Frame(installed_frame, padding=(5,5,5,0))
        installed_actions_frame.pack(fill=tk.X)
        self.uninstall_button = ttk.Button(installed_actions_frame, text="Uninstall", command=self.uninstall_selected_version)
        self.uninstall_button.pack(side=tk.LEFT, padx=(0,3))
        self.set_global_button = ttk.Button(installed_actions_frame, text="Set Global", command=self.set_global_selected_version)
        self.set_global_button.pack(side=tk.LEFT, padx=3)
        self.set_local_button = ttk.Button(installed_actions_frame, text="Set Local", command=self.set_local_selected_version)
        self.set_local_button.pack(side=tk.LEFT, padx=3)

        # Available versions
        available_frame = ttk.LabelFrame(self.versions_pane, text="Available for Installation")
        available_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        filter_controls_frame = ttk.Frame(available_frame, padding=(5,5,5,0))
        filter_controls_frame.pack(fill=tk.X)
        ttk.Label(filter_controls_frame, text="Filter:", style="Small.TLabel").pack(side=tk.LEFT, padx=(0,5), pady=(0,5))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", self.filter_available_versions)
        filter_entry = ttk.Entry(filter_controls_frame) # Removed textvariable for now, will set it after style
        filter_entry.configure(textvariable=self.filter_var) # Set after potential style applied by theme
        filter_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, pady=(0,5))

        self.available_versions_list = tk.Listbox(available_frame, height=15, exportselection=False, relief=tk.SOLID, borderwidth=1)
        self.available_versions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=5)
        available_scrollbar = ttk.Scrollbar(available_frame, orient=tk.VERTICAL, command=self.available_versions_list.yview)
        available_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,5), pady=5)
        self.available_versions_list.config(yscrollcommand=available_scrollbar.set)
        
        self.install_button = ttk.Button(available_frame, text="Install Selected", command=self.install_selected_version, style="Accent.TButton")
        self.install_button.pack(fill=tk.X, padx=5, pady=(5,5))

        self._all_available_versions = []

        # Right Pane: Output Console
        self.output_console_frame = ttk.LabelFrame(self.paned_window, text="Output Console")
        self.paned_window.add(self.output_console_frame, weight=3) # Give it more weight

        self.output_text = scrolledtext.ScrolledText(self.output_console_frame, wrap=tk.WORD, height=10, relief=tk.SOLID, borderwidth=1, state=tk.DISABLED,
                                                     font=('Monaco', 10) if sys.platform == 'darwin' else ('Consolas', 10)) # Monospaced font
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Accent button style (example)
        self.style.configure("Accent.TButton", font=('Helvetica', 10, 'bold'), foreground="white")
        if sys.platform == "darwin":
             self.style.map("Accent.TButton", background=[('active', '#007AFF'), ('!disabled', '#007AFF')], foreground=[('!disabled', 'white')])
        else: # A generic blue
             self.style.map("Accent.TButton", background=[('active', '#005fcc'), ('!disabled', '#007bff')], foreground=[('!disabled', 'white')])


        self.refresh_all_data()
        self.process_gui_queue()
        self.is_successfully_initialized = True


    # --- Progress Bar Control Methods ---
    def start_progress_indeterminate(self):
        if self.progress_bar.winfo_exists():
            self.status_label.pack_forget() # Hide text status
            self.progress_bar.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
            self.progress_bar.start(15) # Speed of indeterminate animation

    def stop_progress(self):
        if self.progress_bar.winfo_exists():
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.status_label.pack(side=tk.RIGHT, padx=5) # Re-show text status

    # ... (Methods _determine_pyenv_executable_path, _determine_pyenv_root_path, _get_pyenv_env, is_pyenv_installed
    #      _get_command_with_absolute_path, start_animation, stop_animation, _animate, _run_pyenv_command_threaded
    #      _execute_command_worker, _fetch_data_worker, load_current_versions, process_gui_queue, set_ui_state,
    #      _start_fetch_op, _end_fetch_op, load_installed_versions, load_available_versions, refresh_all_data,
    #      filter_available_versions, and action handlers like install_selected_version etc.
    #      should be taken from your last working version, with modifications to _execute_command_worker
    #      for progress bar calls)

    def _determine_pyenv_executable_path(self):
        pyenv_exe = shutil.which("pyenv")
        return pyenv_exe

    def _determine_pyenv_root_path(self):
        pyenv_root_env = os.environ.get('PYENV_ROOT')
        if self.pyenv_executable_path:
            try:
                proc = subprocess.run([self.pyenv_executable_path, "root"],
                                      capture_output=True, text=True, check=True, timeout=5)
                pyenv_root_from_cmd = proc.stdout.strip()
                if pyenv_root_from_cmd: return pyenv_root_from_cmd
            except Exception: pass
        if pyenv_root_env: return pyenv_root_env
        return os.path.expanduser("~/.pyenv")

    def _get_pyenv_env(self):
        shims_path = os.path.join(self.pyenv_root_path, "shims")
        current_env = os.environ.copy()
        current_env["PATH"] = shims_path + os.pathsep + current_env.get("PATH", "")
        current_env["PYENV_ROOT"] = self.pyenv_root_path
        if "PYENV_SHELL" not in current_env:
            current_env["PYENV_SHELL"] = os.path.basename(os.environ.get("SHELL", "bash"))
        return current_env

    def is_pyenv_installed(self):
        if not self.pyenv_executable_path: return False
        pyenv_env = self._get_pyenv_env()
        if not os.path.exists(self.pyenv_executable_path) or not os.access(self.pyenv_executable_path, os.X_OK): return False
        try:
            command = [self.pyenv_executable_path, "--version"]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, universal_newlines=True, env=pyenv_env)
            stdout, _ = process.communicate(timeout=10)
            return process.returncode == 0 and "pyenv" in stdout.lower()
        except Exception:
            return False

    def _get_command_with_absolute_path(self, command_args):
        if command_args and command_args[0] == "pyenv":
            if not self.pyenv_executable_path: raise ValueError("pyenv_executable_path is not set")
            return [self.pyenv_executable_path] + command_args[1:]
        return command_args

    def start_animation(self): # Text spinner
        if not self.animating:
            self.animating = True; self.animation_index = 0
            self._animate()

    def stop_animation(self): # Text spinner
        self.animating = False
        if self.status_label.winfo_exists(): self.status_label.config(text="")

    def _animate(self): # Text spinner
        if self.animating:
            if self.status_label.winfo_exists():
                self.status_label.config(text=self.ANIMATION_CHARS[self.animation_index % len(self.ANIMATION_CHARS)])
            self.animation_index += 1
            if self.master.winfo_exists(): self.master.after(100, self._animate)

    def _run_pyenv_command_threaded(self, command_args, success_message=None, error_message=None, on_complete_action=None, requires_selection_from=None, pass_version_to_complete_action=True):
        version_to_act_on = None
        if not command_args or command_args[0] != "pyenv":
            self.gui_queue.put(("append_output", f"Internal Error: Command does not start with 'pyenv': {command_args}\n"))
            return
        final_command_args = list(command_args)
        if requires_selection_from:
            if not requires_selection_from.winfo_exists(): return
            selected_indices = requires_selection_from.curselection()
            if not selected_indices:
                if self.master.winfo_exists(): messagebox.showwarning("Selection Required", "Please select a version from the list.")
                return
            selected_item_text = requires_selection_from.get(selected_indices[0]).strip()
            version_to_act_on = selected_item_text.lstrip('*> ').split(" ")[0]
            if "version_placeholder" in final_command_args:
                final_command_args = [arg.replace("version_placeholder", version_to_act_on) for arg in final_command_args]
            else: final_command_args.append(version_to_act_on)
        
        # Determine if this is an install command for progress bar
        is_install_command = "install" in final_command_args and "--list" not in final_command_args
        
        if not is_install_command: # Only use text spinner if not an install command
            self.start_animation()
        self.set_ui_state(tk.DISABLED)
        
        thread = threading.Thread(target=self._execute_command_worker,
                                  args=(final_command_args, success_message, error_message, on_complete_action, 
                                        version_to_act_on if pass_version_to_complete_action else None, 
                                        is_install_command)) # Pass install command flag
        thread.daemon = True
        thread.start()

    def _execute_command_worker(self, command_args, success_msg, error_msg, on_complete_action, 
                                data_for_complete_action=None, is_install_command=False): # Added is_install_command
        pyenv_env = self._get_pyenv_env()
        full_command = self._get_command_with_absolute_path(command_args)

        if is_install_command:
            self.gui_queue.put(("progress_start_indeterminate", None))
        
        try:
            self.gui_queue.put(("append_output", f"Executing: {' '.join(full_command)}\n"))
            process = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, universal_newlines=True, bufsize=1, env=pyenv_env)
            for line in iter(process.stdout.readline, ''):
                if not line and process.poll() is not None: break
                self.gui_queue.put(("append_output", line))
                # Later: Add regex parsing here for install progress percentage and send to queue
            process.stdout.close()
            return_code = process.wait()
            if return_code == 0:
                if success_msg: self.gui_queue.put(("append_output", f"\n{success_msg}\n"))
                if on_complete_action:
                    payload = (data_for_complete_action, True) if data_for_complete_action is not None else True
                    self.gui_queue.put((on_complete_action, payload))
            else:
                err_output = f"\nError: Command failed with code {return_code}.\n"
                if error_msg: err_output += f"{error_msg}\n"
                self.gui_queue.put(("append_output", err_output))
                if on_complete_action:
                    payload = (data_for_complete_action, False) if data_for_complete_action is not None else False
                    self.gui_queue.put((on_complete_action, payload))
        except FileNotFoundError:
            self.gui_queue.put(("append_output", f"Error: Executable '{full_command[0]}' not found during execution.\n"))
        except Exception as e:
            self.gui_queue.put(("append_output", f"An unexpected error occurred executing {' '.join(full_command)}: {e}\n"))
        finally:
            if is_install_command:
                self.gui_queue.put(("progress_stop", None))
            self.gui_queue.put(("task_done", None)) # General task cleanup signal

    def _fetch_data_worker(self, command_args, queue_message_type):
        pyenv_env = self._get_pyenv_env()
        full_command = self._get_command_with_absolute_path(command_args)
        try:
            self.gui_queue.put(("append_output", f"Fetching: {' '.join(full_command)}\n"))
            process = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, universal_newlines=True, env=pyenv_env)
            stdout, stderr = process.communicate(timeout=60)
            if process.returncode == 0:
                lines = stdout.strip().split('\n')
                if queue_message_type == "update_available_list": # Debug output for GUI console
                    self.gui_queue.put(("append_output", f"DEBUG (GUI): `install --list` raw lines received: {len(lines)}\n"))
                    # if lines: # Only show if there are lines, to reduce noise if it's empty
                    #     self.gui_queue.put(("append_output", f"DEBUG (GUI): First 10 raw lines from `install --list`:\n{chr(10).join(lines[:10])}\n"))
                if queue_message_type == "update_installed_list":
                    cleaned_lines = [line.replace("*", "").replace(">", "").strip().split(" ")[0] for line in lines if line.strip()]
                    self._last_installed_versions_data = cleaned_lines
                    self.gui_queue.put((queue_message_type, cleaned_lines))
                else:
                    self.gui_queue.put((queue_message_type, lines))
            else:
                self.gui_queue.put(("append_output", f"Error fetching data with {' '.join(full_command)} (Code: {process.returncode}):\nSTDERR: {stderr}\nSTDOUT: {stdout}\n"))
                self.gui_queue.put((queue_message_type, []))
        except Exception as e:
            self.gui_queue.put(("append_output", f"Error during data fetch ({' '.join(full_command)}): {e}\n"))
            self.gui_queue.put((queue_message_type, []))
        finally:
            self.gui_queue.put(("fetch_op_done", queue_message_type))

    def load_current_versions(self):
        self._start_fetch_op()
        pyenv_env = self._get_pyenv_env()
        pyenv_exe = self.pyenv_executable_path
        if not pyenv_exe:
            self.gui_queue.put(("append_output", "Error: Pyenv executable path not determined for load_current_versions.\n"))
            self.gui_queue.put(("fetch_op_done", "update_current_versions"))
            return
        def worker():
            versions = {}
            try:
                cmd_global = [pyenv_exe, "global"]; global_ver_proc = subprocess.run(cmd_global, capture_output=True, text=True, check=False, env=pyenv_env, timeout=5)
                versions['global'] = global_ver_proc.stdout.strip() if global_ver_proc.returncode == 0 and global_ver_proc.stdout.strip() else ("N/A (or system)" if global_ver_proc.stdout.strip() != "system" else "system")
                cmd_local = [pyenv_exe, "local"]; local_ver_proc = subprocess.run(cmd_local, capture_output=True, text=True, check=False, env=pyenv_env, timeout=5)
                versions['local'] = local_ver_proc.stdout.strip() if local_ver_proc.returncode == 0 and local_ver_proc.stdout.strip() else "N/A"
                self.gui_queue.put(("update_current_versions", versions))
            except Exception as e:
                self.gui_queue.put(("append_output", f"Error fetching current versions: {e}\n")); self.gui_queue.put(("update_current_versions", {'global': 'Error', 'local': 'Error'}))
            finally: self.gui_queue.put(("fetch_op_done", "update_current_versions"))
        threading.Thread(target=worker, daemon=True).start()

    def process_gui_queue(self):
        try:
            while True:
                if not self.master.winfo_exists(): return
                message_type, data = self.gui_queue.get_nowait()

                if message_type == "append_output":
                    if self.output_text.winfo_exists():
                        self.output_text.config(state=tk.NORMAL); self.output_text.insert(tk.END, data); self.output_text.see(tk.END); self.output_text.config(state=tk.DISABLED)
                
                elif message_type == "update_installed_list":
                    if self.installed_versions_list.winfo_exists():
                        self.installed_versions_list.delete(0, tk.END)
                        current_global = getattr(self, '_current_global_version_cache', '')
                        current_local = getattr(self, '_current_local_version_cache', '')
                        for version in data:
                            prefix = ""
                            if version == current_global: prefix += "*"
                            if version == current_local: prefix += ">"
                            self.installed_versions_list.insert(tk.END, f"{prefix}{' ' if prefix else ''}{version}")
                
                elif message_type == "update_available_list":
                    # self.gui_queue.put(("append_output", f"DEBUG (GUI): process_gui_queue processing 'update_available_list'. Raw data items: {len(data)}\n"))
                    processed_versions = []
                    for v_line in data:
                        v_stripped = v_line.strip()
                        if v_stripped and not v_stripped.lower().startswith("available versions:") and not v_stripped.startswith(("Fetching", "Latest", "Only", "Usage:", "==", "-")):
                            if v_stripped and (v_stripped[0].isdigit() or any(v_stripped.startswith(p) for p in ["jython", "ironpython", "graalpython", "micropython", "pypy", "stackless", "anaconda", "miniconda", "miniforge", "mambaforge"])):
                                processed_versions.append(v_stripped)
                    self._all_available_versions = processed_versions
                    # self.gui_queue.put(("append_output", f"DEBUG (GUI): process_gui_queue after filtering, {len(self._all_available_versions)} versions.\n"))
                    # if self._all_available_versions: self.gui_queue.put(("append_output", f"DEBUG (GUI): First 5 processed available versions:\n{chr(10).join(self._all_available_versions[:5])}\n"))
                    # else: self.gui_queue.put(("append_output", "DEBUG (GUI): No available versions found after filtering.\n"))
                    self.filter_available_versions()
                
                elif message_type == "update_current_versions":
                    self._current_global_version_cache = data.get('global', 'N/A')
                    self._current_local_version_cache = data.get('local', 'N/A')
                    if self.current_global_label.winfo_exists(): self.current_global_label.config(text=f"Global: {self._current_global_version_cache}")
                    if self.current_local_label.winfo_exists(): self.current_local_label.config(text=f"Local: {self._current_local_version_cache}")
                    if hasattr(self, '_last_installed_versions_data') and self.installed_versions_list.winfo_exists():
                         self.gui_queue.put(("update_installed_list", self._last_installed_versions_data))
                
                elif message_type == 'progress_start_indeterminate':
                    if self.progress_bar.winfo_exists():
                        self.status_label.pack_forget() 
                        self.progress_bar.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True) # expand to fill space
                        self.progress_bar.start(10) 
                elif message_type == 'progress_stop':
                    if self.progress_bar.winfo_exists():
                        self.progress_bar.stop()
                        self.progress_bar.pack_forget()
                        self.status_label.pack(side=tk.RIGHT, padx=5)
                
                elif message_type == "task_done": pass
                elif message_type == "fetch_op_done": self._end_fetch_op()
                
                # Installation/Uninstallation/Set Version complete messages
                elif message_type in ["installation_complete", "uninstallation_complete", "set_version_complete"]:
                    item, success = data # item is version string or action type
                    action_verb = message_type.split("_")[0] # "installation", "uninstallation", "set"
                    
                    if message_type == "set_version_complete": # 'item' here is not used for the message
                        log_msg = f"Version set operation {'successful' if success else 'failed'}.\n"
                    else: # for install/uninstall, 'item' is the version name
                        log_msg = f"{action_verb.capitalize()} of {item} {'successful' if success else 'failed'}.\n"
                    
                    self.gui_queue.put(("append_output", log_msg))
                    self.load_installed_versions(); self.load_current_versions()
                    if message_type == "installation_complete" and success: # Refresh available if install was successful
                        self.load_available_versions()


        except queue.Empty: pass
        finally:
            if self.master.winfo_exists(): self.master.after(100, self.process_gui_queue)

    def set_ui_state(self, state):
        widgets_to_toggle = [
            self.refresh_all_button, self.uninstall_button, self.set_global_button,
            self.set_local_button, self.install_button,
            self.installed_versions_list, self.available_versions_list]
        if self.versions_pane.winfo_exists():
            available_frame = next((c for c in self.versions_pane.winfo_children() if isinstance(c, ttk.LabelFrame) and "Available" in c.cget("text")), None)
            if available_frame:
                filter_controls_frame = next((c for c in available_frame.winfo_children() if isinstance(c, ttk.Frame)), None)
                if filter_controls_frame:
                    filter_entry_widget = next((gc for gc in filter_controls_frame.winfo_children() if isinstance(gc, ttk.Entry)), None)
                    if filter_entry_widget: widgets_to_toggle.append(filter_entry_widget)
        for widget in widgets_to_toggle:
            try:
                if widget.winfo_exists(): widget.config(state=state)
            except tk.TclError: pass

    _fetch_ops_pending = 0
    _fetch_lock = threading.Lock()

    def _start_fetch_op(self):
        with self._fetch_lock:
            if self._fetch_ops_pending == 0:
                if self.master.winfo_exists(): 
                    # Don't use text spinner if progress bar will be used for this op
                    is_general_fetch = True # Assume general fetch unless specific op (like install) handles its own indicator
                    # This logic needs refinement if install also uses _start_fetch_op
                    # For now, install commands directly trigger progress_bar, other fetches use text spinner via this.
                    
                    # A better way: _run_pyenv_command_threaded should handle its own indicators
                    # and _start_fetch_op is for generic data loading.
                    self.start_animation() # Text spinner for general fetches
                    self.set_ui_state(tk.DISABLED)
            self._fetch_ops_pending += 1

    def _end_fetch_op(self):
        with self._fetch_lock:
            if self._fetch_ops_pending > 0: self._fetch_ops_pending -= 1
            if self._fetch_ops_pending == 0:
                if self.master.winfo_exists(): 
                    self.stop_animation() # Stop text spinner
                    self.set_ui_state(tk.NORMAL)

    def load_installed_versions(self):
        self._start_fetch_op()
        threading.Thread(target=self._fetch_data_worker, args=(["pyenv", "versions", "--bare"], "update_installed_list"), daemon=True).start()

    def load_available_versions(self):
        self._start_fetch_op() # This will show text spinner
        if self.master.winfo_exists():
            self.gui_queue.put(("append_output", "Fetching available versions (this may take a moment)...\n"))
        threading.Thread(target=self._fetch_data_worker, args=(["pyenv", "install", "--list"], "update_available_list"), daemon=True).start()

    def refresh_all_data(self):
        if not self.master.winfo_exists() or not self.output_text.winfo_exists(): return
        self.output_text.config(state=tk.NORMAL); self.output_text.delete(1.0, tk.END); self.output_text.config(state=tk.DISABLED)
        self.gui_queue.put(("append_output", "Refreshing all data...\n"))
        self.load_current_versions(); self.load_installed_versions(); self.load_available_versions()

    def filter_available_versions(self, *args): # This populates the listbox based on _all_available_versions and filter
        if not self.available_versions_list.winfo_exists(): return
        filter_text = self.filter_var.get().lower()
        self.available_versions_list.delete(0, tk.END)
        items_added = 0
        if not filter_text:
            for version in self._all_available_versions:
                self.available_versions_list.insert(tk.END, version); items_added+=1
        else:
            for version in self._all_available_versions:
                if filter_text in version.lower():
                    self.available_versions_list.insert(tk.END, version); items_added+=1
        # print(f"CONSOLE_DEBUG: filter_available_versions: Populated listbox with {items_added} items. Filter: '{filter_text}'")


    def install_selected_version(self):
        self._run_pyenv_command_threaded(
            ["pyenv", "install", "-v", "version_placeholder"], # -v for verbose
            success_message="Installation process completed.", error_message="Installation failed.",
            on_complete_action="installation_complete", requires_selection_from=self.available_versions_list)

    def uninstall_selected_version(self):
        if not self.installed_versions_list.winfo_exists(): return
        selected_indices = self.installed_versions_list.curselection()
        if not selected_indices:
            if self.master.winfo_exists(): messagebox.showwarning("Selection Required", "Please select an installed version.")
            return
        selected_item_text = self.installed_versions_list.get(selected_indices[0]).strip()
        version_to_uninstall = selected_item_text.lstrip('*> ').split(" ")[0]
        if self.master.winfo_exists() and messagebox.askyesno("Confirm Uninstall", f"Uninstall '{version_to_uninstall}'?"):
            self._run_pyenv_command_threaded(["pyenv", "uninstall", "-f"],
                success_message=f"Uninstalled {version_to_uninstall}.", error_message=f"Failed to uninstall {version_to_uninstall}.",
                on_complete_action="uninstallation_complete", requires_selection_from=self.installed_versions_list)

    def set_global_selected_version(self):
        self._run_pyenv_command_threaded(["pyenv", "global"],
            success_message="Global version set.", error_message="Failed to set global version.",
            on_complete_action="set_version_complete", requires_selection_from=self.installed_versions_list)

    def set_local_selected_version(self):
        self._run_pyenv_command_threaded(["pyenv", "local"],
            success_message=f"Local version set for: {os.getcwd()}", error_message="Failed to set local version.",
            on_complete_action="set_version_complete", requires_selection_from=self.installed_versions_list)

if __name__ == "__main__":
    root = tk.Tk()
    PyenvGUI._fetch_ops_pending = 0 # Class variable reset
    print("--- Python Script Starting ---")
    app = PyenvGUI(root)
    if app.is_successfully_initialized:
        print("CONSOLE_DEBUG: PyenvGUI initialized successfully. Starting mainloop.")
        try: root.mainloop()
        except Exception as e: print(f"CONSOLE_DEBUG: Fatal error during Tkinter mainloop: {e}")
        finally:
             if root.winfo_exists(): # Ensure window is destroyed if mainloop exits unexpectedly
                try: messagebox.showerror("Fatal Error", f"A critical error occurred: {e}\nThe application will now close.")
                except tk.TclError: pass # If root is too far gone
                root.destroy()
    else:
        print("CONSOLE_DEBUG: PyenvGUI initialization failed. The application will now exit.")
        if root.winfo_exists(): root.destroy()
        sys.exit(1)
