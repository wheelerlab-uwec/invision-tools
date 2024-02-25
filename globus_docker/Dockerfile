FROM amd64/ubuntu:22.04

LABEL maintainer="wheelenj@uwec.edu"

# install dependencies
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y --no-install-recommends gnupg ca-certificates wget=1.21.2-2ubuntu1 python3=3.10.6-1~22.04 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


RUN wget --progress=dot:giga https://downloads.globus.org/globus-connect-server/stable/installers/repo/deb/globus-repo_latest_all.deb && \
    dpkg -i globus-repo_latest_all.deb && \
    apt-key add /usr/share/globus-repo/RPM-GPG-KEY-Globus && \
    apt-get update && \
    apt-get install -y globus-connect-server54