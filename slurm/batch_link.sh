#!/bin/bash

# ---- SLURM SETTINGS ---- #

# -- Job Specific -- #
#SBATCH --job-name="linking"	# What is your job called?
#SBATCH --output=%A\_%a_output.txt	# Output file - Use %j to inject job id, like output-%j.txt
#SBATCH --error=%A\_%a_error.txt	# Error file - Use %j to inject job id, like error-%j.txt

#SBATCH --partition=week	# Which group of nodes do you want to use? Use "GPU" for graphics card support
#SBATCH --time=0-2:00:00	# What is the max time you expect the job to finish by? DD-HH:MM:SS

# -- Resource Requirements -- #
#SBATCH --mem=16G		# How much memory do you need?
#SBATCH --ntasks-per-node=16	# How many CPU cores do you want to use per node (max 64)?
#SBATCH --nodes=1		# How many nodes do you need to use at once?
##SBATCH --gpus=1		# Do you require a graphics card? How many (up to 3 per node)? Remove the first "#" to activate.

# -- Email Support -- #
#SBATCH --mail-type=END		# What notifications should be emailed about? (Options: NONE, ALL, BEGIN, END, FAIL, QUEUE) 

# ---- YOUR SCRIPT ---- #
module load python-libs
conda activate invision-env

# base_dir='/data/groups/wheelenj/mosquitoes/20240301-a01-MRB_20240301_144112.24568709'

export PYTHONUNBUFFERED=TRUE

python ~/GitHub/invision-tools/utils/link_trajectories.py $PWD --hdf5 
