"""
OneDrive integration using rclone
"""

import asyncio
import logging
import subprocess
from typing import List, Tuple, Optional
from ssh_utils import ssh_manager

logger = logging.getLogger(__name__)


class OneDriveManager:
    def __init__(self, remote_name: str = "onedrive"):
        self.remote_name = remote_name

    async def list_folders(self, base_path: str = "") -> List[str]:
        """List folders in OneDrive"""
        try:
            path = f"{self.remote_name}:{base_path}" if base_path else self.remote_name
            cmd = f"rclone lsd {path}"

            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                folders = []
                for line in stdout.decode().strip().split("\\n"):
                    if line.strip():
                        # rclone lsd output format: "        -1 2023-01-01 12:00:00        -1 FolderName"
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            folder_name = " ".join(parts[4:])
                            folders.append(folder_name)
                return folders
            else:
                logger.error(f"Failed to list OneDrive folders: {stderr.decode()}")
                return []

        except Exception as e:
            logger.error(f"Error listing OneDrive folders: {str(e)}")
            return []

    async def create_folder(self, folder_path: str) -> Tuple[bool, str]:
        """Create a folder in OneDrive"""
        try:
            full_path = f"{self.remote_name}:{folder_path}"
            cmd = f"rclone mkdir {full_path}"

            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"Successfully created OneDrive folder: {folder_path}")
                return True, f"Folder '{folder_path}' created successfully"
            else:
                error_msg = stderr.decode().strip()
                if "already exists" in error_msg.lower():
                    return True, f"Folder '{folder_path}' already exists"
                else:
                    logger.error(f"Failed to create OneDrive folder: {error_msg}")
                    return False, f"Failed to create folder: {error_msg}"

        except Exception as e:
            logger.error(f"Error creating OneDrive folder: {str(e)}")
            return False, f"Error creating folder: {str(e)}"

    async def upload_files(
        self, local_files: List[str], remote_folder: str
    ) -> Tuple[bool, str]:
        """Upload files to OneDrive folder"""
        try:
            uploaded = []
            failed = []

            for local_file in local_files:
                remote_path = f"{self.remote_name}:{remote_folder}/"
                cmd = f"rclone copy '{local_file}' {remote_path} --progress"

                process = await asyncio.create_subprocess_shell(
                    cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    uploaded.append(local_file)
                    logger.info(f"Successfully uploaded {local_file} to OneDrive")
                else:
                    failed.append(f"{local_file}: {stderr.decode().strip()}")
                    logger.error(f"Failed to upload {local_file}: {stderr.decode()}")

            if failed:
                return (
                    False,
                    f"Uploaded: {len(uploaded)}, Failed: {len(failed)}\\nErrors: {'; '.join(failed)}",
                )
            else:
                return True, f"Successfully uploaded {len(uploaded)} files to OneDrive"

        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return False, f"Upload failed: {str(e)}"

    async def check_rclone_config(self) -> Tuple[bool, str]:
        """Check if rclone is configured with OneDrive"""
        try:
            cmd = f"rclone config show {self.remote_name}"

            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                config_output = stdout.decode()
                if "onedrive" in config_output.lower():
                    return True, "OneDrive rclone configuration found"
                else:
                    return (
                        False,
                        f"Remote '{self.remote_name}' is not configured for OneDrive",
                    )
            else:
                return False, f"Remote '{self.remote_name}' not found in rclone config"

        except Exception as e:
            logger.error(f"Error checking rclone config: {str(e)}")
            return False, f"Error checking rclone configuration: {str(e)}"

    def is_configured(self) -> bool:
        """Synchronous check if OneDrive is configured"""
        try:
            result = subprocess.run(
                f"rclone config show {self.remote_name}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and "onedrive" in result.stdout.lower()
        except Exception:
            return False


# Global OneDrive manager instance
onedrive_manager = OneDriveManager()
