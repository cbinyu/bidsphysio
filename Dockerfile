#######################################################
# This is the Dockerfile for an app to extract physio #
# data from a CMRR DICOM file to BIDS physio          #
#######################################################

ARG DEBIAN_VERSION=buster
ARG BASE_PYTHON_VERSION=3.8
# (don't use simply PYTHON_VERSION because it's an env variable)

# Use an official Python runtime as a parent image
FROM python:${BASE_PYTHON_VERSION}-slim-${DEBIAN_VERSION}

## install required python packages:
RUN pip install pydicom==1.4.1 \
		numpy==1.18.1  \
		etelemetry==0.1.2 && \
    pip install	bioread>=1.0.4


### copy module:
COPY [".", "/tmp/dcm2bidsphysio"]
RUN \
    cd /tmp/dcm2bidsphysio && \
    pip install . && \
    cd / && \
    rm -rf /tmp/dcm2bidsphysio

ENTRYPOINT ["/usr/local/bin/dcm2bidsphysio"]


