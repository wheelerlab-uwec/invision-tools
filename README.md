# invision-tools

To use the Snakefile:

1. Copy the `Snakefile` to the directory to be analyzed and `cd` to that directory.
2. Run `nohup snakemake --profile ~/GitHub/invision-tools/slurm-profile/ &`

To start Snakemake workflows for all videos from a single date:

1. Copy `run_snakemake.sh` to the parent directory of the videos (i.e., `/data/groups/wheelenj/miracidia` if it is not already present.
2. `cd` to the directory.
3. Run `./run_snakemake.sh {date}` where `date` is the date prefix of the videos to be analyzed.

Logs will be written to two locations:

- `nohup.out` or `snakemake.logs` will include the Snakemake logs, priting the rules that were submitted and the corresponding Slurm job ID.
- `logs/` will include two directories: `track` and `link`. Within the directories will include a log file for each mp4 for `track` and one log file for `link`. These files will include the output printed by `batch_track.py` and `link_trajectories.py`.
