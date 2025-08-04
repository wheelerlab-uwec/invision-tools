import glob
import os
from pathlib import Path

os.environ["PYTHONUNBUFFERED"] = "1"

work = str(Path.cwd()) + '/'
experiment_cam = work.rsplit('/',2)[-2]
experiment = experiment_cam.rsplit('.', 1)[0]

VIDEOS = [os.path.basename(x) for x in glob.glob(work + "*.mp4")]
STEMS = [Path(x).stem for x in VIDEOS]

rule all:
    input:
        work + experiment + "_tracks.feather",
        # work + experiment + ".pdf",
        expand("{stem}.hdf5", stem=STEMS)

rule track:
    input: "{stem}.mp4"
    output: "{stem}.hdf5"
    params: 
        workdir = work,
        stem = "{stem}"
    threads: 64
    shell: "python ~/GitHub/invision-tools/utils/tracking.py {params.workdir}{input} {params.workdir}{params.stem} && \
            mv {params.workdir}{params.stem}/{output} {params.workdir}"

rule link:
    input: expand("{stem}.hdf5", stem=STEMS)
    output: 
        work + experiment + "_tracks.feather",
        # work + experiment + ".pdf"
    params: workdir = work
    threads: 64
    shell: "python ~/GitHub/invision-tools/utils/link_trajectories.py {params.workdir} --hdf5"