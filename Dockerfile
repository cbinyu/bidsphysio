###########################################################
# This is the Dockerfile for an app to extract raw physio #
# data (from a CMRR DICOM file, '.puls' and '.resp'       #
# Siemens files or '.acq' file) to BIDS physio            #
###########################################################

ARG DEBIAN_VERSION=buster
ARG BASE_PYTHON_VERSION=3.8
# (don't use simply PYTHON_VERSION because it's an env variable)

# Use an official Python runtime as a parent image
FROM python:${BASE_PYTHON_VERSION}-slim-${DEBIAN_VERSION}

## install required python packages:
#  Not sure why, but I have to install bioread in
#  a separated pip install command.
RUN pip install pydicom==1.4.1 \
		numpy==1.18.1  \
		etelemetry==0.1.2 && \
    pip install	bioread>=1.0.4


### copy module:
COPY [".", "/tmp/bidsphysio"]
RUN \
    cd /tmp/bidsphysio && \
    pip install . && \
    cd / && \
    rm -rf /tmp/bidsphysio

ENTRYPOINT ["/usr/local/bin/dcm2bidsphysio"]


