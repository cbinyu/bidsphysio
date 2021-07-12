########################################################
# This is the Dockerfile for a Docker image to extract #
# raw physio data (from a CMRR DICOM file, '.puls' and #
# '.resp' Siemens files, '.acq' file, or eyetracking #
# .edf file) to BIDS physio #
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

# Workaround to get libjpeg8 as Debian buster has deprecated it
RUN apt-get install -y multiarch-support \
    && curl "http://archive.debian.org/debian/pool/main/libj/libjpeg8/libjpeg8_8d-1+deb7u1_amd64.deb" -o "/tmp/libjpeg8_8d-1+deb7u1_amd64.deb" \
    && dpkg -i "/tmp/libjpeg8_8d-1+deb7u1_amd64.deb"

# Install SR Research for Eyelink
# https://www.sr-support.com/forum/downloads/eyelink-display-software/46-eyelink-developers-kit-for-linux-linux-display-software
RUN curl -L "https://download.sr-support.com/SRResearch_key" \
        | apt-key add - \
    && add-apt-repository "deb [arch=amd64] http://download.sr-support.com/software SRResearch main" \
    && apt-get update \
    && apt-get install -y eyelink-edfapi \
    && apt-get clean -y && apt-get autoclean -y && apt-get autoremove -y
# Add the EyeLink headers to the C_INCLUDE_PATH so that Cython finds
# them when building pyedfread:
ENV C_INCLUDE_PATH="/usr/include/EyeLink:$C_INCLUDE_PATH"

# Pip install prefers that you install packages using venv:
RUN pip install --upgrade virtualenv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python3 -m venv $VIRTUAL_ENV \
    && pip install --upgrade pip

# install required python packages for edf2bids:
RUN pip install cython \
        numpy==1.20.3  \
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
    && sed -i "2i# cython: language_level=2" pyedfread/edf_data.pyx \
    && python setup.py install

###


## install required python packages for bidsphysio:
RUN pip install pydicom==1.4.1 \
		etelemetry==0.1.2 \
        bioread>=1.0.4 \
    	pytest \
        bids

### copy module:
ENV INSTALL_FOLDER=/src/bidsphysio
COPY . ${INSTALL_FOLDER}
# Installing in the first place all the subpackages from source ensures that
# they take precedence over versions in PyPI:
RUN pip install ${INSTALL_FOLDER}/bidsphysio.* \
    && pip install ${INSTALL_FOLDER}

ENTRYPOINT ["/bin/bash"]

