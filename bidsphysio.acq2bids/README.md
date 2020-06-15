# bidsphysio.acq2bids
Base classes for BIDS Physiology

[![Docker image](https://img.shields.io/badge/docker-cbinyu/bidsphysio:latest-brightgreen.svg?logo=docker&style=flat)](https://hub.docker.com/r/cbinyu/bidsphysio/tags/)
[![TravisCI](https://travis-ci.com/cbinyu/bidsphysio.svg?branch=master)](https://travis-ci.com/cbinyu/bidsphysio)
[![CodeCoverage](https://codecov.io/gh/cbinyu/bidsphysio/branch/master/graph/badge.svg)](https://codecov.io/gh/cbinyu/bidsphysio)
[![DOI](https://zenodo.org/badge/239006399.svg)](https://zenodo.org/badge/latestdoi/239006399)

## Usage
```
acq2bidsphysio --infile <physiofiles> --bidsprefix  <Prefix> [--verbose]
```

Example:
```
acq2bidsphysio --infile myPhysio.asq      \
               --bidsprefix BIDSfolder/sub-01/func/sub-01_task-REST_run-1
```

## Arguments
 * `<physiofiles>` space-separated AcqKnowledge files (`<.acq>`) with the physiological
 recordings.
 * `<Prefix>` is the prefix that will be used for the BIDS physiology files.  If all physiological recordings have the same sampling rate and starting time, the script will save the files: `<Prefix>_physio.json` and `<Prefix>_physio.tsv.gz`.  If the physiological signals have different sampling rates and/or starting times, the script will save the files: `<Prefix>_recording-<label>_physio.json` and `<Prefix>_recording-<label>_physio.tsv.gz`, with the corresponding labels (e.g., `cardiac`, `respiratory`, etc.).
 * `--verbose` will print out some warning messages.

Note: If desired, you can use the corresponding `_bold.nii.gz` BIDS file as `--bidsprefix`. The script will strip the `_bold.nii.gz` part from the filename and use what is left as `<Prefix>`. This way, you can assure that the output physiology files match the `_bold.nii.gz` file for which they are intended.

## Installation
You can install the bidsphysio.acq2bids subpackage from PyPI with `pip`:

```
pip install bidsphysio.acq2bids
```

## How to use in your own Python program
After installing the module using `pip` (see [above](#installation "Installation") ), you can use it in your own Python program this way:
```
from bidsphysio.acq2bids import acq2bidsphysio
acq2bidsphysio.acq2bids( [acq_files], prefix )
```


