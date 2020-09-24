########################################################
# This is the Dockerfile for a Docker image to extract #
# raw physio data (from a CMRR DICOM file, '.puls' and #
# '.resp' Siemens files or '.acq' file) to BIDS physio #
########################################################

ARG DEBIAN_VERSION=buster
ARG BASE_PYTHON_VERSION=3.8
# (don't use simply PYTHON_VERSION because it's an env variable)

# Use an official Python runtime as a parent image
FROM python:${BASE_PYTHON_VERSION}-slim-${DEBIAN_VERSION}

RUN pip install --upgrade pip

###   Install SR-Research libraries   ###

## get needed linux packages:
#  - gnupg2 (for adding SRResearch_key)
#  - software-properties-common (adding of sr-support to the trusted sites)
#  - curl
#  - gcc (to make libraries)
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y \
        gnupg2 \
        software-properties-common \
        curl \
        gcc \
    && apt-get clean -y && apt-get autoclean -y && apt-get autoremove -y

# Install SR Research for Eyelink
# https://www.sr-support.com/forum/downloads/eyelink-display-software/46-eyelink-developers-kit-for-linux-linux-display-software
RUN curl -L "http://download.sr-support.com/software/dists/SRResearch/SRResearch_key" \
        | apt-key add - \
    && add-apt-repository "deb http://download.sr-support.com/software SRResearch main" \
    && apt-get update \
    && apt-get install -y eyelink-display-software \
    && apt-get clean -y && apt-get autoclean -y && apt-get autoremove -y

# install required python packages:
RUN pip install cython \
        pandas \
        h5py

###   Install pyedfread   ###
# from GitHub:
ENV INSTALL_FOLDER=/src/pyedfread/
RUN mkdir -p ${INSTALL_FOLDER} \
    && curl -sSL https://github.com/nwilming/pyedfread/archive/master.tar.gz | tar xz -C ${INSTALL_FOLDER} \
            --strip-components=1 \
            --exclude='SUB001.*' \
    && cd ${INSTALL_FOLDER} \
    && sed -i -e "s/cython: profile=True/cython: profile=True, language_level=2/" pyedfread/edfread.pyx \
    && python setup.py install

###

## install python packages required by bidsphysio:
RUN pip install pydicom==1.4.1 \
		numpy==1.18.1  \
		etelemetry==0.1.2 \
        bioread>=1.0.4 \
    	pytest \
        bids

### copy module:
ENV INSTALL_FOLDER=/src/bidsphysio
COPY . ${INSTALL_FOLDER}
RUN pip install ${INSTALL_FOLDER}[all]

ENTRYPOINT ["/bin/bash"]

