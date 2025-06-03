"""
Snakemake workflow execution on HPC with SLURM
"""

import asyncio
import logging
import time
from typing import List, Tuple, Dict
from ssh_utils import ssh_manager

logger = logging.getLogger(__name__)


class SnakemakeRunner:
    def __init__(self):
        self.job_ids: Dict[str, str] = {}  # experiment_name -> slurm_job_id
        self.job_status: Dict[str, str] = {}  # experiment_name -> status

    async def submit_workflow(
        self,
        experiment_names: List[str],
        hpc_host: str,
        project_path: str,
        workflow_path: str,
        conda_env: str = "invision",
    ) -> Tuple[bool, str]:
        """
        Submit Snakemake workflows for multiple experiments
        """
        try:
            submitted = []
            failed = []

            for exp_name in experiment_names:
                success, job_id, error = await self._submit_single_workflow(
                    exp_name, hpc_host, project_path, workflow_path, conda_env
                )

                if success:
                    self.job_ids[exp_name] = job_id
                    self.job_status[exp_name] = "SUBMITTED"
                    submitted.append(exp_name)
                    logger.info(f"Submitted Snakemake job {job_id} for {exp_name}")
                else:
                    failed.append(f"{exp_name}: {error}")
                    logger.error(f"Failed to submit job for {exp_name}: {error}")

            if failed:
                return (
                    False,
                    f"Submitted: {len(submitted)}, Failed: {len(failed)}\\nErrors: {'; '.join(failed)}",
                )
            else:
                return True, f"Successfully submitted {len(submitted)} Snakemake jobs"

        except Exception as e:
            logger.error(f"Workflow submission error: {str(e)}")
            return False, f"Submission failed: {str(e)}"

    async def _submit_single_workflow(
        self,
        exp_name: str,
        hpc_host: str,
        project_path: str,
        workflow_path: str,
        conda_env: str,
    ) -> Tuple[bool, str, str]:
        """Submit a single Snakemake workflow and return job ID"""

        # Build the Snakemake command
        exp_path = f"{project_path}/{exp_name}"

        # Create a SLURM script for this experiment
        slurm_script = f"""#!/bin/bash
#SBATCH --job-name=invision_{exp_name}
#SBATCH --output={exp_path}/slurm_%j.out
#SBATCH --error={exp_path}/slurm_%j.err
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --partition=general

# Load conda environment
source ~/.bashrc
conda activate {conda_env}

# Change to experiment directory
cd {exp_path}

# Run Snakemake with SLURM profile
snakemake \\
    --snakefile {workflow_path}/Snakefile \\
    --profile {workflow_path}/slurm-profile \\
    --config experiment_path={exp_path} \\
    --cores 4 \\
    --jobs 10 \\
    --rerun-incomplete \\
    --keep-going

echo "Snakemake workflow completed for {exp_name}"
"""

        script_path = f"{exp_path}/run_snakemake.sh"

        # Create the script on HPC
        create_script_cmd = f"""
        mkdir -p {exp_path} && 
        cat > {script_path} << 'EOF'
{slurm_script}
EOF
        chmod +x {script_path}
        """

        success, stdout, stderr = await ssh_manager.execute_command(
            hpc_host, create_script_cmd
        )
        if not success:
            return False, "", f"Failed to create SLURM script: {stderr}"

        # Submit the job
        submit_cmd = f"cd {exp_path} && sbatch {script_path}"
        success, stdout, stderr = await ssh_manager.execute_command(
            hpc_host, submit_cmd
        )

        if success:
            # Extract job ID from sbatch output
            # Output format: "Submitted batch job 12345"
            lines = stdout.strip().split("\\n")
            for line in lines:
                if "Submitted batch job" in line:
                    job_id = line.split()[-1]
                    return True, job_id, ""

            return False, "", f"Could not extract job ID from: {stdout}"
        else:
            return False, "", f"sbatch failed: {stderr}"

    async def check_job_status(self, hpc_host: str) -> Dict[str, str]:
        """
        Check status of all submitted jobs
        Returns dict of experiment_name -> status
        """
        try:
            if not self.job_ids:
                return {}

            # Get status of all jobs
            job_id_list = " ".join(self.job_ids.values())
            status_cmd = f"squeue -j {job_id_list} --format='%i %T' --noheader"

            success, stdout, stderr = await ssh_manager.execute_command(
                hpc_host, status_cmd
            )

            if not success:
                logger.warning(f"Failed to check job status: {stderr}")
                return self.job_status

            # Parse squeue output
            running_jobs = {}
            for line in stdout.strip().split("\\n"):
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        job_id, status = parts[0], parts[1]
                        running_jobs[job_id] = status

            # Update status for each experiment
            for exp_name, job_id in self.job_ids.items():
                if job_id in running_jobs:
                    self.job_status[exp_name] = running_jobs[job_id]
                else:
                    # Job not in queue, check if completed successfully
                    completed_status = await self._check_completed_job(
                        hpc_host, exp_name, job_id
                    )
                    self.job_status[exp_name] = completed_status

            return self.job_status

        except Exception as e:
            logger.error(f"Error checking job status: {str(e)}")
            return self.job_status

    async def _check_completed_job(
        self, hpc_host: str, exp_name: str, job_id: str
    ) -> str:
        """Check if a completed job was successful"""
        try:
            # Check sacct for job completion status
            sacct_cmd = f"sacct -j {job_id} --format=State --noheader --parsable2"
            success, stdout, stderr = await ssh_manager.execute_command(
                hpc_host, sacct_cmd
            )

            if success and stdout.strip():
                states = stdout.strip().split("\\n")
                # Look for final state (usually the last one or the one containing COMPLETED/FAILED)
                for state in states:
                    state = state.strip()
                    if state in ["COMPLETED", "FAILED", "CANCELLED", "TIMEOUT"]:
                        return state

                # If no definitive state, assume completed
                return "COMPLETED"
            else:
                # Fallback: check if output files exist
                return await self._check_output_files(hpc_host, exp_name)

        except Exception as e:
            logger.error(f"Error checking completed job {job_id}: {str(e)}")
            return "UNKNOWN"

    async def _check_output_files(self, hpc_host: str, exp_name: str) -> str:
        """Check if expected output files exist"""
        try:
            base_name = exp_name.split(".")[0]  # Remove camera ID
            expected_files = [f"{base_name}.pdf", f"{base_name}_tracks.pkl.gz"]

            project_path = "/data/groups/wheelenj"  # This should come from config
            exp_path = f"{project_path}/{exp_name}"

            for file_name in expected_files:
                check_cmd = f"ls {exp_path}/{file_name}"
                success, stdout, stderr = await ssh_manager.execute_command(
                    hpc_host, check_cmd
                )
                if not success:
                    return "FAILED"

            return "COMPLETED"

        except Exception:
            return "UNKNOWN"

    def get_completed_experiments(self) -> List[str]:
        """Get list of experiments that have completed successfully"""
        return [exp for exp, status in self.job_status.items() if status == "COMPLETED"]

    def get_failed_experiments(self) -> List[str]:
        """Get list of experiments that failed"""
        return [
            exp
            for exp, status in self.job_status.items()
            if status in ["FAILED", "CANCELLED", "TIMEOUT"]
        ]

    def get_running_experiments(self) -> List[str]:
        """Get list of experiments still running"""
        return [
            exp
            for exp, status in self.job_status.items()
            if status in ["RUNNING", "PENDING", "SUBMITTED"]
        ]

    def clear_completed(self):
        """Remove completed experiments from tracking"""
        completed = self.get_completed_experiments()
        for exp in completed:
            if exp in self.job_ids:
                del self.job_ids[exp]
            if exp in self.job_status:
                del self.job_status[exp]


# Global Snakemake runner instance
snakemake_runner = SnakemakeRunner()
