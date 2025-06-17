"""
SSH and SFTP utilities with Okta 2FA support
"""

import paramiko
import asyncio
import time
import logging
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SSHCredentials:
    username: str
    password: str
    host: str
    port: int = 22
    created_at: float = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

    def is_expired(self, timeout_hours: int = 24) -> bool:
        """Check if credentials are expired"""
        return (time.time() - self.created_at) > (timeout_hours * 3600)


class SSHManager:
    def __init__(self):
        self.credentials: Dict[str, SSHCredentials] = {}
        self.connections: Dict[str, paramiko.SSHClient] = {}

    async def authenticate(
        self, host: str, username: str, password: str, port: int = 22
    ) -> Tuple[bool, str]:
        """
        Authenticate with Okta 2FA push notification
        Returns (success, message)
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            logger.info(
                f"Attempting SSH connection to {host} on port {port} with username {username}"
            )
            print(
                f"DEBUG: Connecting to host='{host}', port={port}, username='{username}'"
            )

            # Attempt connection - this will trigger Okta push
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=90,  # Give time for 2FA approval
                auth_timeout=90,
                banner_timeout=30,
            )

            # Test connection with a simple command
            stdin, stdout, stderr = client.exec_command('echo "Connection test"')
            test_result = stdout.read().decode("utf-8").strip()

            if test_result == "Connection test":
                # Store credentials and connection
                self.credentials[host] = SSHCredentials(username, password, host, port)
                self.connections[host] = client
                logger.info(f"Successfully authenticated to {host}")
                return True, "Authentication successful"
            else:
                client.close()
                return False, "Connection test failed"

        except paramiko.AuthenticationException as e:
            logger.error(f"Authentication failed for {host}: {str(e)}")
            return (
                False,
                f"Authentication failed. Please check your credentials and approve the Okta push notification.",
            )
        except paramiko.SSHException as e:
            logger.error(f"SSH error for {host}: {str(e)}")
            return False, f"SSH connection error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error connecting to {host}: {str(e)}")
            return False, f"Connection error: {str(e)}"

    def get_connection(self, host: str) -> Optional[paramiko.SSHClient]:
        """Get existing SSH connection or None if expired/missing"""
        if host not in self.credentials or host not in self.connections:
            return None

        creds = self.credentials[host]
        if creds.is_expired():
            logger.info(f"Connection to {host} expired, cleaning up")
            self.cleanup_connection(host)
            return None

        # Test if connection is still alive
        try:
            transport = self.connections[host].get_transport()
            if transport and transport.is_active():
                return self.connections[host]
            else:
                logger.info(f"Connection to {host} is inactive, cleaning up")
                self.cleanup_connection(host)
                return None
        except Exception:
            self.cleanup_connection(host)
            return None

    def cleanup_connection(self, host: str):
        """Clean up expired or invalid connection"""
        if host in self.connections:
            try:
                self.connections[host].close()
            except Exception:
                pass
            del self.connections[host]

        if host in self.credentials:
            del self.credentials[host]

    async def execute_command(
        self, host: str, command: str, timeout: int = 300
    ) -> Tuple[bool, str, str]:
        """
        Execute command on remote host
        Returns (success, stdout, stderr)
        """
        client = self.get_connection(host)
        if not client:
            return False, "", "No valid connection to host. Please authenticate first."

        try:
            logger.debug(f"Executing command on {host}: {command}")
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)

            # Read outputs
            stdout_text = stdout.read().decode("utf-8")
            stderr_text = stderr.read().decode("utf-8")
            exit_code = stdout.channel.recv_exit_status()

            success = exit_code == 0
            if not success:
                logger.warning(
                    f"Command failed on {host} (exit code {exit_code}): {stderr_text}"
                )

            return success, stdout_text, stderr_text

        except Exception as e:
            logger.error(f"Command execution failed on {host}: {str(e)}")
            return False, "", f"Command execution failed: {str(e)}"

    def get_sftp_client(self, host: str) -> Optional[paramiko.SFTPClient]:
        """Get SFTP client for file operations"""
        client = self.get_connection(host)
        if not client:
            return None

        try:
            return client.open_sftp()
        except Exception as e:
            logger.error(f"Failed to open SFTP client for {host}: {str(e)}")
            return None

    def is_authenticated(self, host: str) -> bool:
        """Check if we have a valid connection to the host"""
        return self.get_connection(host) is not None

    def get_authenticated_hosts(self) -> list:
        """Get list of hosts we're currently authenticated to"""
        return [host for host in self.credentials.keys() if self.is_authenticated(host)]


# Global SSH manager instance
ssh_manager = SSHManager()
