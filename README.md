# Pyenv GUI Manager

A Tkinter-based graphical user interface for managing `pyenv` Python versions. This tool provides an intuitive way to view, install, uninstall, and switch between Python versions managed by `pyenv` without needing to use the command line for every operation.

<img width="950" alt="image" src="https://github.com/user-attachments/assets/aa335848-82f8-4568-b2d8-5702878b7893" />


## Features

* **List Installed Versions:** Clearly displays all Python versions currently installed by `pyenv`.
* **Active Version Indicators:** Shows which versions are currently active (global `*`, local `>`).
* **View Available Versions:** Fetches and lists all Python versions available for installation via `pyenv install --list`.
* **Filter Available Versions:** Quickly find specific versions in the available list by **typing part of the version name or number into the filter field**. The list updates dynamically as you type.
* **Install Python Versions:** Select and install new Python versions from the available list with visual progress.
* **Uninstall Python Versions:** Easily remove installed Python versions.
* **Set Global Version:** Set the default global Python version recognized by `pyenv`.
* **Set Local Version:** Set a project-specific Python version (creates/updates `.python-version` in the current directory where the GUI is launched from, if `pyenv local` is supported and effective in that context).
* **GUI Shell Version Override:** Set a `PYENV_VERSION` specifically for the context of this GUI application. This allows you to run `pyenv` commands *within this GUI* as if a particular version is active via `PYENV_VERSION`, without affecting your actual shell's `PYENV_VERSION` environment variable.
* **Real-time Output Console:** Displays the output of `pyenv` commands as they execute, providing transparency and debugging information.
* **Asynchronous Operations:** Long-running tasks (like installations) are performed in separate threads, keeping the GUI responsive.
* **Progress Indication:** Uses a text spinner for fetching data and an indeterminate progress bar for installations.
* **Cross-Platform Theming:** Attempts to use native-looking themes (`vista` on Windows, `aqua` on macOS, `clam` on other systems).
* **Auto-detection:** Attempts to find the `pyenv` executable and `PYENV_ROOT`.

## Prerequisites

1.  **Python 3.x:** The script itself is written in Python 3.
2.  **Tkinter:** This is Python's standard GUI package.
    * On Windows and macOS, it's usually included with Python.
    * On Linux, you might need to install it separately (e.g., `sudo apt-get install python3-tk` on Debian/Ubuntu).
3.  **`pyenv`:**
    * `pyenv` must be installed and correctly configured in your system.
    * The `pyenv` command must be accessible in your system's `PATH`.
    * Your shell environment (`~/.bashrc`, `~/.zshrc`, etc.) should have the necessary `pyenv init` lines.
    * The GUI relies on `pyenv` for all Python version management operations.

## How to Run

1.  **Save the Code:** Save the Python script provided as a `.py` file (e.g., `pyenv_gui.py`).
2.  **Ensure Prerequisites:** Verify that Python 3, Tkinter, and a working `pyenv` installation are present.
3.  **Execute the Script:**
    Open your terminal or command prompt, navigate to the directory where you saved the file, and run:
    ```bash
    python pyenv_gui.py
    ```
    or
    ```bash
    python3 pyenv_gui.py
    ```

## UI Overview

* **Top Bar:**
    * **Current Versions:** Displays the detected `pyenv` global, local (if any), and the GUI-context shell override version.
    * **Status Indicator:** Shows a text spinner during data fetching or a progress bar during installations.
    * **Refresh All:** Button to reload all version lists and current version information.
* **Versions Pane (Left):**
    * **Installed Versions:**
        * Listbox showing currently installed Python versions.
        * `*` indicates the version active due to `PYENV_VERSION` (if set by GUI) or the global setting.
        * `>` indicates the version active due to a local `.python-version` file.
        * Buttons: `Uninstall`, `Set Global`, `Set Local`.
    * **Shell Version Override (GUI Context Only):**
        * Input field to specify a Python version.
        * `Set`: Applies this version to `PYENV_VERSION` for commands run *by this GUI instance*.
        * `Clear`: Clears the GUI-context `PYENV_VERSION` override.
    * **Available for Installation:**
        * **Filter:** An entry field labeled "Filter:". **Type part of a Python version name or number here (e.g., "3.10", "pypy", "miniconda") to dynamically filter the list below.**
        * Listbox showing versions available for installation based on the filter.
        * Button: `Install Selected`.
* **Output Console (Right):**
    * A scrolled text area displaying the output (stdout/stderr) from the `pyenv` commands executed by the GUI. This is useful for monitoring progress and diagnosing issues.

## How It Works

The application serves as a graphical front-end to the `pyenv` command-line tool.
* It discovers the `pyenv` executable and `PYENV_ROOT`.
* When you perform an action (e.g., "Install"), the GUI constructs the appropriate `pyenv` command (e.g., `pyenv install 3.9.7`).
* These commands are run in separate threads using Python's `subprocess` module to avoid freezing the GUI.
* Output from these commands is captured and displayed in the "Output Console".
* A `queue` is used for inter-thread communication to update the GUI safely from worker threads.
* The "Shell Version Override" works by setting the `PYENV_VERSION` environment variable specifically for the subprocesses launched by the GUI. This doesn't alter your system-wide or terminal-specific `PYENV_VERSION`.

## Known Limitations / Considerations

* **Initial `pyenv install --list`:** Fetching the list of all available versions can be slow, as `pyenv` itself needs to update its index. The GUI will be disabled during this fetch, with a spinner indicating activity.
* **Local Version Context:** "Set Local" will attempt to set the local version in the directory from which the `pyenv_gui.py` script was launched. Its effectiveness depends on `pyenv`'s standard behavior.
* **Error Handling:** While the GUI tries to catch and display errors from `pyenv` commands, complex `pyenv` or build issues might require looking at `pyenv`'s own logs or troubleshooting build dependencies manually.
* **`PYENV_ROOT` and `pyenv` executable:** The script tries its best to find these. If they are in very non-standard locations or `pyenv` is not in `PATH`, it might fail to initialize. Setting `PYENV_ROOT` as an environment variable can help.

## Contributing

Feel free to fork this project, submit issues, or suggest improvements!

## License

(You can add a license here, e.g., MIT License)
