#!/bin/bash

# Check if date argument is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <date>"
    echo "Example: $0 20240912"
    exit 1
fi

# Get the date from command line argument
DATE=$1

# Source Snakefile
SOURCE_FILE=~/GitHub/invision-tools/Snakefile
SNAKEMAKE_PROFILE=~/GitHub/invision-tools/slurm-profile/

# Find all directories matching the provided date pattern
echo "Searching for directories starting with $DATE"
for dir in "$DATE"*; do
    if [ -d "$dir" ]; then
        echo "Processing directory: $dir"
        
        # Copy Snakefile
        cp "$SOURCE_FILE" "$dir/"
        
        # Change into directory and run snakemake
        (cd "$dir" && echo "Running snakemake in $dir" && nohup snakemake --profile "$SNAKEMAKE_PROFILE" > snakemake.log 2>&1 &)
        
        echo "Started snakemake in $dir"
    fi
done

echo "All directories processed"