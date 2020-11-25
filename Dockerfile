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

## install required python packages:
RUN pip install pydicom==1.4.1 \
		numpy==1.18.1  \
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

