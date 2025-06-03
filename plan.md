# 🧠 Lab Workflow GUI App - Project Plan

## 📌 Goal
A modern, browser-based GUI to simplify a multi-step computational workflow for undergraduates in a biology lab. The app handles:

1. Transfer of video experiment folders to a NAS
2. Transfer of input folders to a campus HPC
3. SSH execution of a Snakemake workflow (SLURM-based)
4. Transfer of output results to OneDrive
5. Cleanup (delete input from HPC)

## 📂 Folder Structure

gui/
├── main.py # Entry point: starts the NiceGUI app
├── config.yaml # Stores paths, usernames, and settings
├── ssh_utils.py # SSH and SCP helper functions
├── file_ops.py # Local and remote file transfer logic
├── snakemake_runner.py # Code to trigger and monitor Snakemake jobs
├── onedrive_utils.py # Output sync via rclone
├── gui_components.py # Button definitions and UI logic
└── requirements.txt # Dependencies

## 🧰 Suggested Stack
| Role                      | Tech                                      |
|---------------------------|-------------------------------------------|
| GUI Framework             | nicegui                                   |
| SSH / SCP                 | paramiko or subprocess ssh/scp            |
| File Transfers            | rsync, shutil, or scp                     |
| OneDrive Sync             | rclone                                    |
| Workflow Execution        | subprocess (to call snakemake via ssh)    |
| Configuration Management  | PyYAML (config.yaml)                      |

## 🧩 Component Breakdown

### main.py
Starts the app, imports GUI logic, and runs the server.

### config.yaml
Stores system paths, usernames, and configuration info for reuse.

### ssh_utils.py
Handles SSH execution and SCP file transfers.

### file_ops.py
Manages local-to-NAS and local-to-HPC file transfers.

### snakemake_runner.py
Runs Snakemake via SSH on the HPC using SLURM profile.

### onedrive_utils.py
Transfers output results from HPC to OneDrive using rclone.

### gui_components.py
Defines NiceGUI buttons, progress indicators, and event handling.

## 📦 UV env management - pyproject.toml
nicegui
paramiko
pyyaml

## 🚀 Launch Instructions
```bash
uv sync
python main.py

💡 Copilot Prompts
ssh_utils.py: "Write a function that SSHes into a remote host and runs a command using Paramiko."
snakemake_runner.py: "Write a function that SSHes into an HPC, cds to a workflow folder, and runs Snakemake with a SLURM profile."
file_ops.py: "Use subprocess to run rsync or scp for uploading a directory to a remote host."
gui_components.py: "Add a NiceGUI button that runs a function and shows a progress bar."

"""
