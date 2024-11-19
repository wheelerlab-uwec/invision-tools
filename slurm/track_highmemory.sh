#!/bin/bash

# ---- SLURM SETTINGS ---- #

# -- Job Specific -- #
#SBATCH --job-name="tracking"	# What is your job called?
#SBATCH --output=output-%j.txt	# Output file - Use %j to inject job id, like output-%j.txt
#SBATCH --error=error-%j.txt	# Error file - Use %j to inject job id, like error-%j.txt
#SBATCH --array=0-1

#SBATCH --partition=highmemory	# Which group of nodes do you want to use? Use "GPU" for graphics card support
#SBATCH --time=0-12:00:00	# What is the max time you expect the job to finish by? DD-HH:MM:SS

# -- Resource Requirements -- #
#SBATCH --mem=500G		# How much memory do you need?
#SBATCH --ntasks-per-node=64	# How many CPU cores do you want to use per node (max 64)?
#SBATCH --nodes=1		# How many nodes do you need to use at once?
##SBATCH --gpus=1		# Do you require a graphics card? How many (up to 3 per node)? Remove the first "#" to activate.

# -- Email Support -- #
#SBATCH --mail-type=END		# What notifications should be emailed about? (Options: NONE, ALL, BEGIN, END, FAIL, QUEUE) 

# ---- YOUR SCRIPT ---- #
module load python-libs
conda activate invision-env

export PYTHONUNBUFFERED=TRUE

python ~/GitHub/invision-tools/utils/tracking.py $PWD/00000${SLURM_ARRAY_TASK_ID}.mp4 $PWD/00000${SLURM_ARRAY_TASK_ID}
mv $PWD/00000${SLURM_ARRAY_TASK_ID}/00000${SLURM_ARRAY_TASK_ID}.hdf5 $PWD

# echo "Linking trajectories"
# python ~/GitHub/invision-tools/utils/link_trajectories.py $PWD --hdf5 
