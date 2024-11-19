import glob
import os
from pathlib import Path

os.environ["PYTHONUNBUFFERED"] = "1"

configfile: "config.yaml"

VIDEOS = [os.path.basename(x) for x in glob.glob(config["workdir"] + "*.mp4")]
STEMS = [Path(x).stem for x in VIDEOS]

# print(VIDEOS, STEMS)

rule all:
    input:
        config["workdir"] + config["experiment"] + "_tracks.pkl.gz",
        config["workdir"] + config["experiment"] + ".pdf",
        expand("{stem}.hdf5", stem=STEMS)

rule track:
    input: "{stem}.mp4"
    output: "{stem}.hdf5"
    params: 
        workdir = config["workdir"],
        stem = "{stem}"
    threads: 64
    shell: "python ~/GitHub/invision-tools/utils/tracking.py {params.workdir}{input} {params.workdir}{params.stem} && \
            mv {params.workdir}{params.stem}/{output} {params.workdir}"

rule link:
    input: expand("{stem}.hdf5", stem=STEMS)
    output: 
        config["workdir"] + config["experiment"] + "_tracks.pkl.gz",
        config["workdir"] + config["experiment"] + ".pdf"
    params: workdir = config["workdir"]
    threads: 64
    shell: "python ~/GitHub/invision-tools/utils/link_trajectories.py {params.workdir} --hdf5"