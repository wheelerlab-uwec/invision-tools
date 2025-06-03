"""
NiceGUI components for the lab workflow interface
"""

import asyncio
import logging
from typing import List, Optional
from nicegui import ui, app
import yaml
from pathlib import Path

from ssh_utils import ssh_manager
from file_ops import file_manager
from snakemake_runner import snakemake_runner
from onedrive_utils import onedrive_manager

logger = logging.getLogger(__name__)

# Load configuration
config_path = Path(__file__).parent / "config.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

print(f"DEBUG: Loaded config NAS host: {config['nas']['host']}")
print(f"DEBUG: Config path: {config_path}")
print(f"DEBUG: Full NAS config: {config['nas']}")


class WorkflowGUI:
    def __init__(self):
        self.selected_experiments: List[str] = []
        self.local_experiment_path = ""
        self.selected_project = ""
        self.onedrive_output_path = ""
        self.workflow_status = {}

        # UI elements (will be set in create_interface)
        self.status_card = None
        self.experiment_table = None
        self.progress_log = None

    async def create_interface(self):
        """Create the main workflow interface"""

        # Page styling
        ui.add_head_html(
            '<style>body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }</style>'
        )

        with ui.column().classes("w-full max-w-6xl mx-auto p-4"):
            # Header
            with ui.row().classes("w-full justify-between items-center mb-6"):
                ui.label("🧠 Lab Workflow Manager").classes("text-3xl font-bold")
                self.status_card = ui.card().classes("p-2")
                with self.status_card:
                    ui.label("Not Connected").classes("text-sm text-red-500")

            # Authentication Section
            await self._create_auth_section()

            ui.separator().classes("my-6")

            # Experiment Selection Section
            await self._create_experiment_section()

            ui.separator().classes("my-6")

            # Workflow Control Section
            await self._create_workflow_section()

            ui.separator().classes("my-6")

            # Progress and Monitoring Section
            await self._create_monitoring_section()

    async def _create_auth_section(self):
        """Create authentication section"""
        with ui.card().classes("w-full p-4"):
            ui.label("🔐 Authentication").classes("text-xl font-semibold mb-4")

            with ui.row().classes("w-full gap-4"):
                # NAS Authentication
                with ui.column().classes("flex-1"):
                    ui.label("NAS Connection").classes("font-medium")
                    nas_username = ui.input(
                        "Username", value="wheelenjadmin", placeholder="wheelenjadmin"
                    ).classes("w-full")
                    nas_password = ui.input(
                        "Password", password=True, password_toggle_button=True
                    ).classes("w-full")
                    nas_connect_btn = ui.button(
                        "Connect to NAS",
                        on_click=lambda: self._authenticate_nas(
                            nas_username.value, nas_password.value
                        ),
                    )
                    nas_status = ui.label("Not connected").classes(
                        "text-sm text-gray-500"
                    )

                # HPC Authentication
                with ui.column().classes("flex-1"):
                    ui.label("HPC Connection").classes("font-medium")
                    hpc_username = ui.input(
                        "Username", placeholder="your-username"
                    ).classes("w-full")
                    hpc_password = ui.input(
                        "Password", password=True, password_toggle_button=True
                    ).classes("w-full")
                    hpc_connect_btn = ui.button(
                        "Connect to HPC",
                        on_click=lambda: self._authenticate_hpc(
                            hpc_username.value, hpc_password.value
                        ),
                    )
                    hpc_status = ui.label("Not connected").classes(
                        "text-sm text-gray-500"
                    )

        # Store references for status updates
        self.nas_status = nas_status
        self.hpc_status = hpc_status

    async def _create_experiment_section(self):
        """Create experiment selection section"""
        with ui.card().classes("w-full p-4"):
            ui.label("📁 Experiment Selection").classes("text-xl font-semibold mb-4")

            # Source selection
            with ui.row().classes("w-full gap-4 mb-4"):
                ui.label("Source:").classes("self-center")
                self.source_select = ui.select(["Local", "NAS"], value="Local").classes(
                    "w-32"
                )
                self.local_path_input = ui.input(
                    "Local Experiment Folder", placeholder="/path/to/experiments"
                ).classes("flex-1")
                ui.button("Browse Local", on_click=self._browse_local_folder)
                ui.button("Browse NAS", on_click=self._browse_nas_experiments)
                ui.button("Refresh", on_click=self._refresh_experiments)

            # Project selection
            with ui.row().classes("w-full gap-4 mb-4"):
                ui.label("HPC Project:").classes("self-center")
                self.project_select = ui.select(
                    config["hpc"]["available_projects"],
                    value=config["hpc"]["available_projects"][0],
                ).classes("flex-1")

            # Search/filter experiments
            with ui.row().classes("w-full gap-4 mb-4"):
                ui.label("Filter:").classes("self-center")
                self.search_input = ui.input(
                    "Search experiments...",
                    placeholder="Type to filter experiments by name",
                ).classes("flex-1")
                ui.button("Apply Filter", on_click=self._apply_filter)
                ui.button("Clear", on_click=self._clear_filter)

            # Experiment table
            self.experiment_table = ui.table(
                columns=[
                    {
                        "name": "select",
                        "label": "Select",
                        "field": "select",
                        "align": "center",
                    },
                    {
                        "name": "name",
                        "label": "Experiment Name",
                        "field": "name",
                        "align": "left",
                    },
                    {
                        "name": "size",
                        "label": "Size",
                        "field": "size",
                        "align": "right",
                    },
                    {
                        "name": "status",
                        "label": "Status",
                        "field": "status",
                        "align": "center",
                    },
                ],
                rows=[],
                selection="multiple",
            ).classes("w-full")

            with ui.row().classes("w-full justify-between mt-4"):
                ui.button("Select All", on_click=self._select_all_experiments)
                ui.button("Clear Selection", on_click=self._clear_selection)
                self.selection_label = ui.label("0 experiments selected").classes(
                    "self-center"
                )

    async def _create_workflow_section(self):
        """Create workflow control section"""
        with ui.card().classes("w-full p-4"):
            ui.label("⚙️ Workflow Control").classes("text-xl font-semibold mb-4")

            # OneDrive path selection
            with ui.row().classes("w-full gap-4 mb-4"):
                self.onedrive_path_input = ui.input(
                    "OneDrive Output Folder",
                    placeholder="Lab/ProcessedExperiments/YYYY-MM-DD",
                ).classes("flex-1")
                ui.button("Create Folder", on_click=self._create_onedrive_folder)

            # Workflow buttons
            with ui.row().classes("w-full gap-4"):
                self.step1_btn = ui.button(
                    "1. Transfer to NAS", on_click=self._step1_transfer_to_nas
                ).classes("flex-1")
                self.step2_btn = ui.button(
                    "2. Transfer to HPC", on_click=self._step2_transfer_to_hpc
                ).classes("flex-1")
                self.step3_btn = ui.button(
                    "3. Submit Workflows", on_click=self._step3_submit_workflows
                ).classes("flex-1")
                self.step4_btn = ui.button(
                    "4. Transfer Outputs", on_click=self._step4_transfer_outputs
                ).classes("flex-1")
                self.step5_btn = ui.button(
                    "5. Cleanup", on_click=self._step5_cleanup
                ).classes("flex-1")

            with ui.row().classes("w-full gap-4 mt-4"):
                self.run_all_btn = ui.button(
                    "🚀 Run Complete Workflow", on_click=self._run_complete_workflow
                ).classes("w-full bg-green-500")
                self.stop_btn = ui.button(
                    "⏹️ Stop", on_click=self._stop_workflow
                ).classes("bg-red-500")

    async def _create_monitoring_section(self):
        """Create progress monitoring section"""
        with ui.card().classes("w-full p-4"):
            ui.label("📊 Progress Monitor").classes("text-xl font-semibold mb-4")

            # Progress indicators
            with ui.row().classes("w-full gap-4 mb-4"):
                self.overall_progress = ui.linear_progress(value=0).classes("flex-1")
                ui.button("Refresh Status", on_click=self._refresh_status)

            # Log area
            self.progress_log = ui.log().classes(
                "w-full h-64 bg-gray-100 p-4 font-mono text-sm"
            )

    # Authentication methods
    async def _authenticate_nas(self, username: str, password: str):
        """Authenticate to NAS"""
        if not username or not password:
            ui.notify("Please enter username and password", type="warning")
            return

        self.nas_status.text = "Connecting..."
        self.nas_status.classes("text-yellow-500")

        try:
            success, message = await ssh_manager.authenticate(
                config["nas"]["host"], username, password, config["nas"]["port"]
            )

            if success:
                self.nas_status.text = f"Connected as {username}"
                self.nas_status.classes("text-green-500")
                ui.notify("Connected to NAS successfully", type="positive")
                await self._update_connection_status()
            else:
                self.nas_status.text = f"Failed: {message}"
                self.nas_status.classes("text-red-500")
                ui.notify(f"NAS connection failed: {message}", type="negative")

        except Exception as e:
            self.nas_status.text = f"Error: {str(e)}"
            self.nas_status.classes("text-red-500")
            ui.notify(f"NAS connection error: {str(e)}", type="negative")

    async def _authenticate_hpc(self, username: str, password: str):
        """Authenticate to HPC"""
        if not username or not password:
            ui.notify("Please enter username and password", type="warning")
            return

        self.hpc_status.text = "Connecting... (Check your device for Okta push)"
        self.hpc_status.classes("text-yellow-500")

        try:
            success, message = await ssh_manager.authenticate(
                config["hpc"]["host"], username, password, config["hpc"]["port"]
            )

            if success:
                self.hpc_status.text = f"Connected as {username}"
                self.hpc_status.classes("text-green-500")
                ui.notify("Connected to HPC successfully", type="positive")
                await self._update_connection_status()
            else:
                self.hpc_status.text = f"Failed: {message}"
                self.hpc_status.classes("text-red-500")
                ui.notify(f"HPC connection failed: {message}", type="negative")

        except Exception as e:
            self.hpc_status.text = f"Error: {str(e)}"
            self.hpc_status.classes("text-red-500")
            ui.notify(f"HPC connection error: {str(e)}", type="negative")

    async def _update_connection_status(self):
        """Update overall connection status"""
        nas_connected = ssh_manager.is_authenticated(config["nas"]["host"])
        hpc_connected = ssh_manager.is_authenticated(config["hpc"]["host"])

        if nas_connected and hpc_connected:
            with self.status_card:
                self.status_card.clear()
                ui.label("✅ All Systems Connected").classes("text-sm text-green-500")
        elif nas_connected or hpc_connected:
            with self.status_card:
                self.status_card.clear()
                ui.label("⚠️ Partially Connected").classes("text-sm text-yellow-500")
        else:
            with self.status_card:
                self.status_card.clear()
                ui.label("❌ Not Connected").classes("text-sm text-red-500")

    # Experiment selection methods
    async def _browse_local_folder(self):
        """Browse for local experiment folder"""
        # In a real implementation, this would open a file dialog
        # For now, we'll use a simple input
        ui.notify("Please enter the path to your experiment folder", type="info")

    async def _browse_nas_experiments(self):
        """Browse and list experiments on the NAS"""
        if not ssh_manager.is_authenticated(config["nas"]["host"]):
            ui.notify("Please authenticate to NAS first", type="warning")
            return

        # Show loading spinner
        with ui.dialog() as loading_dialog, ui.card():
            ui.label("Loading experiments from NAS...")
            ui.spinner(size="lg")

        loading_dialog.open()

        try:
            self.source_select.value = "NAS"

            # Get experiments with limit for faster loading
            limit = 100  # Increased from 50 for better coverage
            experiments = await file_manager.list_nas_experiments(
                config["nas"]["host"], config["nas"]["base_path"], limit=limit
            )

            loading_dialog.close()

            if not experiments:
                ui.notify("No experiments found on NAS", type="info")
                return

            # Debug: First try a simple test row
            # print(f"DEBUG: Found {len(experiments)} experiments from NAS")
            # print(f"DEBUG: Sample experiments: {experiments[:5]}")

            # Update table with NAS experiments
            rows = []
            for i, exp in enumerate(experiments):
                rows.append(
                    {
                        "id": i,  # Required for NiceGUI table selection
                        "select": False,
                        "name": exp,
                        "size": "Unknown",  # Could query actual size
                        "status": "On NAS",
                    }
                )

            # print(f"DEBUG: Created {len(rows)} table rows")
            # print(f"DEBUG: Sample row: {rows[0] if rows else 'No rows'}")

            # Store all experiments for filtering
            print(f"DEBUG: About to store {len(rows)} rows")
            print(f"DEBUG: Type of rows: {type(rows)}")
            print(f"DEBUG: Sample rows: {rows[:2] if len(rows) >= 2 else rows}")
            
            self._store_all_experiments(rows)

            # Update the table using the proper NiceGUI method
            print(f"DEBUG: About to update table with {len(rows)} rows")
            print(f"DEBUG: Table type: {type(self.experiment_table)}")
            print(
                f"DEBUG: Current table rows count: {len(self.experiment_table.rows) if hasattr(self.experiment_table, 'rows') else 'No rows attr'}"
            )

            # Simple direct assignment (most reliable for NiceGUI)
            self.experiment_table.rows[:] = rows
            self.experiment_table.update()

            # Debug logging
            # print(f"DEBUG: Table rows after update: {len(self.experiment_table.rows)}")
            # print(
            #     f"DEBUG: First row in table: {self.experiment_table.rows[0] if self.experiment_table.rows else 'No rows'}"
            )

            # Double-check table state
            if len(self.experiment_table.rows) == 0:
                # print("DEBUG: Table still empty, trying alternative method")
                # Clear and rebuild
                self.experiment_table.rows.clear()
                for row in rows:
                    self.experiment_table.rows.append(row)
                self.experiment_table.update()

            # Show success message with info about pagination
            if len(experiments) == limit:
                ui.notify(
                    f"Showing first {len(experiments)} experiments from NAS.",
                    type="positive",
                )
            else:
                ui.notify(
                    f"Found {len(experiments)} experiments on NAS", type="positive"
                )

        except Exception as e:
            loading_dialog.close()
            ui.notify(f"Error browsing NAS: {str(e)}", type="negative")
            logger.error(f"NAS browsing error: {e}")

    async def _refresh_experiments(self):
        """Refresh the list of available experiments"""
        source = self.source_select.value

        if source == "Local":
            if not self.local_path_input.value:
                ui.notify(
                    "Please specify a local experiment folder path", type="warning"
                )
                return

            try:
                experiments = file_manager.list_local_experiments(
                    self.local_path_input.value
                )

                # Update table
                rows = []
                for i, exp in enumerate(experiments):
                    rows.append(
                        {
                            "id": i,  # Required for NiceGUI table selection
                            "select": False,
                            "name": exp,
                            "size": "Unknown",  # Could calculate actual size
                            "status": "Local",
                        }
                    )

                # Store all experiments for filtering and update table
                self._store_all_experiments(rows)
                self.experiment_table.rows = rows
                self.experiment_table.update()

                print(
                    f"DEBUG: Refresh - Set table rows to {len(rows)} local experiments"
                )
                ui.notify(
                    f"Found {len(experiments)} local experiments", type="positive"
                )

            except Exception as e:
                ui.notify(f"Error listing local experiments: {str(e)}", type="negative")

        elif source == "NAS":
            if not ssh_manager.is_authenticated(config["nas"]["host"]):
                ui.notify("Please authenticate to NAS first", type="warning")
                return

            try:
                experiments = await file_manager.list_nas_experiments(
                    config["nas"]["host"], config["nas"]["base_path"]
                )

                # Update table
                rows = []
                for i, exp in enumerate(experiments):
                    rows.append(
                        {
                            "id": i,  # Required for NiceGUI table selection
                            "select": False,
                            "name": exp,
                            "size": "Unknown",  # Could query actual size
                            "status": "On NAS",
                        }
                    )

                # Store all experiments for filtering and update table
                self._store_all_experiments(rows)
                self.experiment_table.rows = rows
                self.experiment_table.update()

                print(f"DEBUG: Refresh - Set table rows to {len(rows)} NAS experiments")
                ui.notify(
                    f"Found {len(experiments)} experiments on NAS", type="positive"
                )

            except Exception as e:
                ui.notify(f"Error listing NAS experiments: {str(e)}", type="negative")

    def _select_all_experiments(self):
        """Select all experiments"""
        for row in self.experiment_table.rows:
            row["select"] = True
        self.experiment_table.update()
        self._update_selection_count()

    def _clear_selection(self):
        """Clear all selections"""
        for row in self.experiment_table.rows:
            row["select"] = False
        self.experiment_table.update()
        self._update_selection_count()

    def _update_selection_count(self):
        """Update selection count label"""
        selected = len([row for row in self.experiment_table.rows if row["select"]])
        self.selection_label.text = f"{selected} experiments selected"

    def _get_selected_experiments(self) -> List[str]:
        """Get list of selected experiment names"""
        return [row["name"] for row in self.experiment_table.rows if row["select"]]

    # Workflow step methods
    async def _step1_transfer_to_nas(self):
        """Step 1: Transfer experiments to NAS"""
        selected = self._get_selected_experiments()
        if not selected:
            ui.notify("Please select experiments to transfer", type="warning")
            return

        if not ssh_manager.is_authenticated(config["nas"]["host"]):
            ui.notify("Please authenticate to NAS first", type="warning")
            return

        self.progress_log.push(
            f"🔄 Starting transfer of {len(selected)} experiments to NAS..."
        )

        try:
            local_paths = [f"{self.local_path_input.value}/{exp}" for exp in selected]
            success, message = await file_manager.transfer_to_nas(
                local_paths, config["nas"]["host"], config["nas"]["base_path"]
            )

            if success:
                self.progress_log.push(f"✅ {message}")
                ui.notify("Transfer to NAS completed", type="positive")
            else:
                self.progress_log.push(f"❌ {message}")
                ui.notify("Transfer to NAS failed", type="negative")

        except Exception as e:
            error_msg = f"Transfer to NAS error: {str(e)}"
            self.progress_log.push(f"❌ {error_msg}")
            ui.notify(error_msg, type="negative")

    async def _step2_transfer_to_hpc(self):
        """Step 2: Transfer experiments from NAS to HPC"""
        selected = self._get_selected_experiments()
        if not selected:
            ui.notify("Please select experiments to transfer", type="warning")
            return

        if not all(
            [
                ssh_manager.is_authenticated(config["nas"]["host"]),
                ssh_manager.is_authenticated(config["hpc"]["host"]),
            ]
        ):
            ui.notify("Please authenticate to both NAS and HPC first", type="warning")
            return

        self.progress_log.push(
            f"🔄 Starting transfer of {len(selected)} experiments from NAS to HPC..."
        )

        try:
            project = self.project_select.value
            hpc_project_path = f"{config['hpc']['base_path']}/{project}"

            success, message = await file_manager.transfer_nas_to_hpc(
                selected,
                config["nas"]["host"],
                config["nas"]["base_path"],
                config["hpc"]["host"],
                hpc_project_path,
            )

            if success:
                self.progress_log.push(f"✅ {message}")
                ui.notify("Transfer to HPC completed", type="positive")
            else:
                self.progress_log.push(f"❌ {message}")
                ui.notify("Transfer to HPC failed", type="negative")

        except Exception as e:
            error_msg = f"Transfer to HPC error: {str(e)}"
            self.progress_log.push(f"❌ {error_msg}")
            ui.notify(error_msg, type="negative")

    async def _step3_submit_workflows(self):
        """Step 3: Submit Snakemake workflows"""
        selected = self._get_selected_experiments()
        if not selected:
            ui.notify("Please select experiments to process", type="warning")
            return

        if not ssh_manager.is_authenticated(config["hpc"]["host"]):
            ui.notify("Please authenticate to HPC first", type="warning")
            return

        self.progress_log.push(
            f"🔄 Submitting Snakemake workflows for {len(selected)} experiments..."
        )

        try:
            project = self.project_select.value
            project_path = f"{config['hpc']['base_path']}/{project}"
            workflow_path = config["hpc"]["snakemake"]["workflow_path"]
            conda_env = config["hpc"]["snakemake"]["conda_env"]

            success, message = await snakemake_runner.submit_workflow(
                selected, config["hpc"]["host"], project_path, workflow_path, conda_env
            )

            if success:
                self.progress_log.push(f"✅ {message}")
                ui.notify("Workflows submitted successfully", type="positive")
            else:
                self.progress_log.push(f"❌ {message}")
                ui.notify("Workflow submission failed", type="negative")

        except Exception as e:
            error_msg = f"Workflow submission error: {str(e)}"
            self.progress_log.push(f"❌ {error_msg}")
            ui.notify(error_msg, type="negative")

    async def _step4_transfer_outputs(self):
        """Step 4: Transfer outputs to OneDrive"""
        if not self.onedrive_path_input.value:
            ui.notify("Please specify OneDrive output folder", type="warning")
            return

        # Get completed experiments
        completed = snakemake_runner.get_completed_experiments()
        if not completed:
            ui.notify("No completed experiments to transfer", type="warning")
            return

        self.progress_log.push(
            f"🔄 Transferring outputs for {len(completed)} experiments to OneDrive..."
        )

        try:
            project = self.project_select.value
            project_path = f"{config['hpc']['base_path']}/{project}"

            success, message = await file_manager.transfer_hpc_to_onedrive(
                completed,
                config["hpc"]["host"],
                project_path,
                self.onedrive_path_input.value,
            )

            if success:
                self.progress_log.push(f"✅ {message}")
                ui.notify("Output transfer completed", type="positive")
            else:
                self.progress_log.push(f"❌ {message}")
                ui.notify("Output transfer failed", type="negative")

        except Exception as e:
            error_msg = f"Output transfer error: {str(e)}"
            self.progress_log.push(f"❌ {error_msg}")
            ui.notify(error_msg, type="negative")

    async def _step5_cleanup(self):
        """Step 5: Cleanup input files from HPC"""
        completed = snakemake_runner.get_completed_experiments()
        if not completed:
            ui.notify("No experiments to clean up", type="warning")
            return

        self.progress_log.push(
            f"🔄 Cleaning up input files for {len(completed)} experiments..."
        )

        try:
            project = self.project_select.value
            project_path = f"{config['hpc']['base_path']}/{project}"

            success, message = await file_manager.cleanup_hpc_inputs(
                completed, config["hpc"]["host"], project_path
            )

            if success:
                self.progress_log.push(f"✅ {message}")
                ui.notify("Cleanup completed", type="positive")
                # Clear completed experiments from tracking
                snakemake_runner.clear_completed()
            else:
                self.progress_log.push(f"❌ {message}")
                ui.notify("Cleanup failed", type="negative")

        except Exception as e:
            error_msg = f"Cleanup error: {str(e)}"
            self.progress_log.push(f"❌ {error_msg}")
            ui.notify(error_msg, type="negative")

    async def _run_complete_workflow(self):
        """Run the complete workflow"""
        selected = self._get_selected_experiments()
        if not selected:
            ui.notify("Please select experiments to process", type="warning")
            return

        self.progress_log.push(
            f"🚀 Starting complete workflow for {len(selected)} experiments..."
        )

        # Run steps sequentially
        await self._step1_transfer_to_nas()
        await asyncio.sleep(1)
        await self._step2_transfer_to_hpc()
        await asyncio.sleep(1)
        await self._step3_submit_workflows()

        # Start monitoring loop for outputs
        ui.timer(30, self._monitor_and_transfer_outputs)

    async def _monitor_and_transfer_outputs(self):
        """Monitor workflows and transfer outputs when ready"""
        try:
            # Check job status
            status_dict = await snakemake_runner.check_job_status(config["hpc"]["host"])

            # Transfer any newly completed experiments
            completed = snakemake_runner.get_completed_experiments()
            if completed:
                await self._step4_transfer_outputs()
                await asyncio.sleep(2)
                await self._step5_cleanup()

        except Exception as e:
            logger.error(f"Monitor error: {str(e)}")

    def _stop_workflow(self):
        """Stop the current workflow"""
        ui.notify("Workflow stopped", type="info")

    async def _create_onedrive_folder(self):
        """Create OneDrive folder"""
        if not self.onedrive_path_input.value:
            ui.notify("Please enter folder path", type="warning")
            return

        success, message = await onedrive_manager.create_folder(
            self.onedrive_path_input.value
        )
        if success:
            ui.notify(message, type="positive")
        else:
            ui.notify(message, type="negative")

    async def _refresh_status(self):
        """Refresh workflow status"""
        try:
            if ssh_manager.is_authenticated(config["hpc"]["host"]):
                status_dict = await snakemake_runner.check_job_status(
                    config["hpc"]["host"]
                )

                # Update progress log with current status
                running = snakemake_runner.get_running_experiments()
                completed = snakemake_runner.get_completed_experiments()
                failed = snakemake_runner.get_failed_experiments()

                self.progress_log.push(
                    f"📊 Status - Running: {len(running)}, Completed: {len(completed)}, Failed: {len(failed)}"
                )

                if status_dict:
                    for exp, status in status_dict.items():
                        self.progress_log.push(f"   {exp}: {status}")

        except Exception as e:
            self.progress_log.push(f"❌ Status refresh error: {str(e)}")

    def _apply_filter(self):
        """Apply search filter to experiments"""
        search_term = self.search_input.value.lower() if self.search_input.value else ""

        if not hasattr(self, "all_experiments") or not self.all_experiments:
            ui.notify("No experiments to filter", type="info")
            return

        if not search_term:
            # Show all experiments if no search term
            filtered_rows = self.all_experiments.copy()
        else:
            # Filter experiments based on search term
            filtered_rows = [
                row
                for row in self.all_experiments
                if search_term in row["name"].lower()
            ]

        self.experiment_table.rows = filtered_rows
        ui.notify(
            f"Showing {len(filtered_rows)} of {len(self.all_experiments)} experiments",
            type="info",
        )

    def _clear_filter(self):
        """Clear the search filter and show all experiments"""
        self.search_input.value = ""
        if hasattr(self, "all_experiments") and self.all_experiments:
            self.experiment_table.rows = self.all_experiments.copy()
            ui.notify(
                f"Showing all {len(self.all_experiments)} experiments", type="info"
            )

    def _store_all_experiments(self, rows):
        """Store all experiment rows for filtering purposes"""
        print(f"DEBUG: _store_all_experiments called with type: {type(rows)}")
        print(f"DEBUG: _store_all_experiments rows content: {rows[:2] if hasattr(rows, '__len__') and len(rows) >= 2 else rows}")
        
        if isinstance(rows, list):
            self.all_experiments = rows.copy()
        else:
            print(f"WARNING: Expected list but got {type(rows)}, converting to empty list")
            self.all_experiments = []
        return rows


# Global GUI instance
workflow_gui = WorkflowGUI()


async def create_main_interface():
    """Create and return the main interface"""
    await workflow_gui.create_interface()
