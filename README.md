# invision-tools

To use the Snakefile:

1. `Snakefile` to the directory to be analyzed and `cd` to that directory.
2. Run `nohup snakemake --profile ~/GitHub/invision-tools/slurm-profile/ &`

Logs will be written to two locations:

- `nohup.out` will include the Snakemake logs, priting the rules that were submitted and the corresponding Slurm job ID.
- `logs/` will include two directories: `track` and `link`. Within the directories will include a log file for each mp4 for `track` and one log file for `link`. These files will include the output printed by `batch_track.py` and `link_trajectories.py`.