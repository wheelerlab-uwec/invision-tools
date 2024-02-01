#!/bin/bash

# ---- SLURM SETTINGS ---- #

# -- Job Specific -- #
#SBATCH --job-name="tracking"	# What is your job called?
#SBATCH --output=%A\_%a_output.txt	# Output file - Use %j to inject job id, like output-%j.txt
#SBATCH --error=%A\_%a_error.txt	# Error file - Use %j to inject job id, like error-%j.txt
#SBATCH --array=0-1

#SBATCH --partition=highmemory	# Which group of nodes do you want to use? Use "GPU" for graphics card support
#SBATCh --time=0-12:00:00	# What is the max time you expect the job to finish by? DD-HH:MM:SS

# -- Resource Requirements -- #
#SBATCH --mem=500G		# How much memory do you need?
#SBATCH --ntasks-per-node=64	# How many CPU cores do you want to use per node (max 64)?
#SBATCH --nodes=1		# How many nodes do you need to use at once?
##SBATCH --gpus=1		# Do you require a graphics card? How many (up to 3 per node)? Remove the first "#" to activate.

# -- Email Support -- #
#SBATCH --mail-type=END		# What notifications should be emailed about? (Options: NONE, ALL, BEGIN, END, FAIL, QUEUE) 

# ---- YOUR SCRIPT ---- #
module load python-libs
module load R/4.3.1
conda init bash
conda activate invision-env

export PYTHONUNBUFFERED=TRUE

# track all files
python ~/GitHub/invision-tools/utils/tracking.py /data/groups/wheelenj/miracidia/20240125/liver_vs_intestine_apw_20240125_143509.24568709/00000${SLURM_ARRAY_TASK_ID}.mp4 /data/groups/wheelenj/miracidia/20240125/liver_vs_intestine_apw_20240125_143509.24568709/00000${SLURM_ARRAY_TASK_ID} 

# link trajectories
python ~/GitHub/invision-tools/utils/link_trajectories.py /data/groups/wheelenj/miracidia/20240125/liver_vs_intestine_apw_20240125_143509.24568709/ --hdf5

# plot
# Rscript ~/GitHub/invision-tools/plot/plot_tracks.R /data/groups/wheelenj/miracidia/20240125/liver_vs_intestine_apw_20240125_143509.24568744/liver_vs_intestine_apw_20240125_143509_tracks.pkl.gz ~/GitHub/invision-tools/utils/link_trajectories.py /data/groups/wheelenj/miracidia/20240125/liver_vs_intestine_apw_20240125_143509.24568709/liver_vs_intestine_apw_20240125_143509_tracks.pkl.gz