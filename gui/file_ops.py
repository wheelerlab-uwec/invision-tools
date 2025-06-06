"""
File transfer operations between local, NAS, and HPC systems
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import shutil
import paramiko
from ssh_utils import ssh_manager

logger = logging.getLogger(__name__)


class FileTransferManager:
    def __init__(self):
        pass

    async def transfer_to_nas(
        self, local_paths: List[str], nas_host: str, nas_base_path: str
    ) -> Tuple[bool, str]:
        """
        Transfer experiment folders from local computer to NAS via SFTP
        """
        try:
            sftp = ssh_manager.get_sftp_client(nas_host)
            if not sftp:
                return False, "No SFTP connection to NAS. Please authenticate first."

            transferred = []
            failed = []

            for local_path in local_paths:
                if not os.path.exists(local_path):
                    failed.append(f"{local_path}: Local path does not exist")
                    continue

                folder_name = os.path.basename(local_path)
                remote_path = f"{nas_base_path}/{folder_name}"

                try:
                    # Create remote directory
                    try:
                        sftp.mkdir(remote_path)
                    except IOError:
                        # Directory might already exist
                        pass

                    # Transfer all files in the folder
                    await self._sftp_upload_recursive(sftp, local_path, remote_path)
                    transferred.append(folder_name)
                    logger.info(f"Successfully transferred {folder_name} to NAS")

                except Exception as e:
                    failed.append(f"{folder_name}: {str(e)}")
                    logger.error(f"Failed to transfer {folder_name} to NAS: {str(e)}")

            sftp.close()

            if failed:
                return (
                    False,
                    f"Transferred: {len(transferred)}, Failed: {len(failed)}\\nErrors: {'; '.join(failed)}",
                )
            else:
                return (
                    True,
                    f"Successfully transferred {len(transferred)} folders to NAS",
                )

        except Exception as e:
            logger.error(f"NAS transfer error: {str(e)}")
            return False, f"NAS transfer failed: {str(e)}"

    async def transfer_nas_to_hpc(
        self,
        experiment_names: List[str],
        nas_host: str,
        nas_base_path: str,
        hpc_host: str,
        hpc_project_path: str,
    ) -> Tuple[bool, str]:
        """
        Transfer experiment folders from NAS to HPC using rsync over SSH
        """
        try:
            # Build rsync command for each experiment
            transferred = []
            failed = []

            for exp_name in experiment_names:
                nas_path = f"{nas_base_path}/{exp_name}/"
                hpc_path = f"{hpc_project_path}/{exp_name}/"

                # Use SSH credentials from manager
                creds = ssh_manager.credentials.get(hpc_host)
                if not creds:
                    failed.append(f"{exp_name}: No HPC credentials")
                    continue

                # Create rsync command that uses SSH
                rsync_cmd = f"""
                rsync -avz --progress \\
                -e "ssh -o StrictHostKeyChecking=no" \\
                {creds.username}@{nas_host}:{nas_path} \\
                {creds.username}@{hpc_host}:{hpc_path}
                """

                success, stdout, stderr = await ssh_manager.execute_command(
                    hpc_host, f"mkdir -p {hpc_path} && {rsync_cmd}", timeout=1800
                )

                if success:
                    transferred.append(exp_name)
                    logger.info(f"Successfully transferred {exp_name} from NAS to HPC")
                else:
                    failed.append(f"{exp_name}: {stderr}")
                    logger.error(f"Failed to transfer {exp_name}: {stderr}")

            if failed:
                return (
                    False,
                    f"Transferred: {len(transferred)}, Failed: {len(failed)}\\nErrors: {'; '.join(failed)}",
                )
            else:
                return (
                    True,
                    f"Successfully transferred {len(transferred)} experiments to HPC",
                )

        except Exception as e:
            logger.error(f"NAS to HPC transfer error: {str(e)}")
            return False, f"Transfer failed: {str(e)}"

    async def transfer_hpc_to_onedrive(
        self,
        experiment_names: List[str],
        hpc_host: str,
        hpc_project_path: str,
        onedrive_path: str,
    ) -> Tuple[bool, str]:
        """
        Transfer output files from HPC to OneDrive using rclone
        """
        try:
            transferred = []
            failed = []

            for exp_name in experiment_names:
                # Expected output files
                base_name = exp_name.split(".")[0]  # Remove camera ID if present
                pdf_file = f"{base_name}.pdf"
                pkl_file = f"{base_name}_tracks.pkl.gz"
                metadata_file = "metadata.yaml"

                hpc_exp_path = f"{hpc_project_path}/{exp_name}"
                onedrive_exp_path = f"{onedrive_path}/{exp_name}"

                # Create OneDrive folder and transfer files
                commands = [
                    f"rclone mkdir onedrive:{onedrive_exp_path}",
                    f"rclone copy {hpc_exp_path}/{pdf_file} onedrive:{onedrive_exp_path}/ --progress",
                    f"rclone copy {hpc_exp_path}/{pkl_file} onedrive:{onedrive_exp_path}/ --progress",
                    f"rclone copy {hpc_exp_path}/{metadata_file} onedrive:{onedrive_exp_path}/ --progress",
                ]

                all_success = True
                error_msgs = []

                for cmd in commands:
                    success, stdout, stderr = await ssh_manager.execute_command(
                        hpc_host, cmd, timeout=600
                    )
                    if not success and "not found" not in stderr.lower():
                        all_success = False
                        error_msgs.append(stderr.strip())

                if all_success:
                    transferred.append(exp_name)
                    logger.info(
                        f"Successfully transferred {exp_name} outputs to OneDrive"
                    )
                else:
                    failed.append(f"{exp_name}: {'; '.join(error_msgs)}")
                    logger.error(
                        f"Failed to transfer {exp_name} outputs: {'; '.join(error_msgs)}"
                    )

            if failed:
                return (
                    False,
                    f"Transferred: {len(transferred)}, Failed: {len(failed)}\\nErrors: {'; '.join(failed)}",
                )
            else:
                return (
                    True,
                    f"Successfully transferred {len(transferred)} experiment outputs to OneDrive",
                )

        except Exception as e:
            logger.error(f"HPC to OneDrive transfer error: {str(e)}")
            return False, f"Transfer failed: {str(e)}"

    async def cleanup_hpc_inputs(
        self, experiment_names: List[str], hpc_host: str, hpc_project_path: str
    ) -> Tuple[bool, str]:
        """
        Delete input experiment folders from HPC after successful processing
        """
        try:
            cleaned = []
            failed = []

            for exp_name in experiment_names:
                hpc_exp_path = f"{hpc_project_path}/{exp_name}"

                # Only delete input files, keep outputs
                delete_cmd = f"""
                cd {hpc_exp_path} && \\
                find . -name "*.mp4" -delete && \\
                find . -name "*.avi" -delete && \\
                find . -name "*.mov" -delete && \\
                echo "Cleaned input files for {exp_name}"
                """

                success, stdout, stderr = await ssh_manager.execute_command(
                    hpc_host, delete_cmd
                )

                if success:
                    cleaned.append(exp_name)
                    logger.info(f"Successfully cleaned input files for {exp_name}")
                else:
                    failed.append(f"{exp_name}: {stderr}")
                    logger.error(f"Failed to clean {exp_name}: {stderr}")

            if failed:
                return (
                    False,
                    f"Cleaned: {len(cleaned)}, Failed: {len(failed)}\\nErrors: {'; '.join(failed)}",
                )
            else:
                return (
                    True,
                    f"Successfully cleaned input files for {len(cleaned)} experiments",
                )

        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
            return False, f"Cleanup failed: {str(e)}"

    async def _sftp_upload_recursive(
        self, sftp: paramiko.SFTPClient, local_path: str, remote_path: str
    ):
        """Recursively upload files and directories via SFTP"""
        if os.path.isfile(local_path):
            sftp.put(local_path, remote_path)
        else:
            try:
                sftp.mkdir(remote_path)
            except IOError:
                pass  # Directory might already exist

            for item in os.listdir(local_path):
                local_item = os.path.join(local_path, item)
                remote_item = f"{remote_path}/{item}"
                await self._sftp_upload_recursive(sftp, local_item, remote_item)

    def list_local_experiments(self, base_path: str) -> List[str]:
        """List available experiment folders in the local directory"""
        try:
            if not os.path.exists(base_path):
                return []

            experiments = []
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if os.path.isdir(item_path) and self._is_experiment_folder(item):
                    experiments.append(item)

            return sorted(experiments)
        except Exception as e:
            logger.error(f"Error listing local experiments: {str(e)}")
            return []

    async def list_nas_experiments(
        self, nas_host: str, nas_base_path: str, limit: int = 50
    ) -> List[str]:
        """List available experiment folders on the NAS (optimized with caching and batch operations)"""
        try:
            sftp = ssh_manager.get_sftp_client(nas_host)
            if not sftp:
                logger.error("No SFTP client available")
                return []

            experiments = []
            try:
                print(f"DEBUG: Listing directory: {nas_base_path} (limit: {limit})")

                # Use listdir_attr to get file attributes in one call (much faster)
                try:
                    items_with_attrs = sftp.listdir_attr(nas_base_path)
                    print(
                        f"DEBUG: Found {len(items_with_attrs)} total items with attributes"
                    )

                    # Sort by name (reverse for most recent first)
                    items_with_attrs.sort(key=lambda x: x.filename, reverse=True)
                    candidates = []

                    for attr in items_with_attrs:
                        if len(candidates) >= limit:
                            break

                        folder_name = attr.filename

                        # Quick pre-filter
                        if not self._quick_experiment_filter(folder_name):
                            continue

                        # Check if it's a directory using the attribute info
                        import stat as stat_module

                        if attr.st_mode and stat_module.S_ISDIR(attr.st_mode):
                            if self._is_experiment_folder(folder_name):
                                candidates.append(folder_name)
                                print(f"DEBUG: Added experiment: {folder_name}")

                    experiments = candidates

                except Exception as e:
                    print(
                        f"DEBUG: listdir_attr failed ({e}), falling back to listdir with stat calls"
                    )
                    # Fallback to regular listdir if listdir_attr fails
                    items = sftp.listdir(nas_base_path)
                    items.sort(reverse=True)

                    candidates = []
                    checked = 0

                    for item in items:
                        if len(candidates) >= limit or checked >= limit * 2:
                            break

                        # Quick pre-filter
                        if not self._quick_experiment_filter(item):
                            continue

                        # Check if it's a directory
                        try:
                            remote_path = f"{nas_base_path}/{item}"
                            stat_info = sftp.stat(remote_path)
                            import stat as stat_module

                            if stat_info.st_mode and stat_module.S_ISDIR(
                                stat_info.st_mode
                            ):
                                if self._is_experiment_folder(item):
                                    candidates.append(item)
                                    print(f"DEBUG: Added experiment: {item}")
                        except:
                            pass  # Skip items we can't stat
                        finally:
                            checked += 1

                    experiments = candidates

                print(f"DEBUG: Found {len(experiments)} experiments")
                print(f"DEBUG: Returning experiments type: {type(experiments)}")
                print(f"DEBUG: Sample returned experiments: {experiments[:2] if len(experiments) >= 2 else experiments}")
                
                # Additional debug: check each experiment item type
                for i, exp in enumerate(experiments[:3]):  # Check first 3
                    print(f"DEBUG: experiments[{i}] = {repr(exp)} (type: {type(exp)})")
                
                return experiments

            except IOError as e:
                logger.error(f"Error accessing NAS directory {nas_base_path}: {str(e)}")
                print(f"DEBUG: Directory access error: {e}")
                return []

        except Exception as e:
            logger.error(f"Error listing NAS experiments: {str(e)}")
            print(f"DEBUG: General error: {e}")
            return []

    def _quick_experiment_filter(self, folder_name: str) -> bool:
        """Quick pre-filter to skip obvious non-experiment folders"""
        # Skip hidden files and common system folders
        if folder_name.startswith(".") or folder_name.startswith("@"):
            return False

        # Skip common non-experiment folders
        skip_patterns = [
            "backup",
            "temp",
            "tmp",
            "archive",
            "old",
            "test",
            "config",
            "system",
        ]
        if any(pattern in folder_name.lower() for pattern in skip_patterns):
            return False

        # Must contain at least one digit (experiments have dates/times)
        if not any(c.isdigit() for c in folder_name):
            return False

        return True

    def _is_experiment_folder(self, folder_name: str) -> bool:
        """Check if folder name matches experiment pattern"""
        print(f"DEBUG: Checking folder pattern for: '{folder_name}'")

        # Pattern: user_generated_date_time.camera_id
        # Example: 20250522a01sao_20250522_141848.24568709
        # More flexible pattern matching

        # Check for basic underscore structure
        if "_" not in folder_name:
            print(f"DEBUG: No underscores found in '{folder_name}'")
            return False

        parts = folder_name.split("_")
        print(f"DEBUG: Split into parts: {parts}")

        if len(parts) >= 3:
            # Check if last part has camera ID after dot
            last_part = parts[-1]
            if "." in last_part:
                print(f"DEBUG: Found dot in last part '{last_part}' - matches pattern")
                return True

        # Also accept any folder that looks like a date-based experiment
        # Check if folder contains date patterns (YYYYMMDD)
        import re

        if re.search(r"\d{8}", folder_name):
            print(
                f"DEBUG: Found date pattern in '{folder_name}' - accepting as experiment"
            )
            return True

        print(f"DEBUG: '{folder_name}' does not match experiment pattern")
        return False


# Global file transfer manager instance
file_manager = FileTransferManager()
