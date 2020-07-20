# bidsphysio.acq2bids
Converts AcqKnowledge physio data (from a BioPac system) to BIDS physiological recording

[![Docker image](https://img.shields.io/badge/docker-cbinyu/bidsphysio:latest-brightgreen.svg?logo=docker&style=flat)](https://hub.docker.com/r/cbinyu/bidsphysio/tags/)
[![TravisCI](https://travis-ci.com/cbinyu/bidsphysio.svg?branch=master)](https://travis-ci.com/cbinyu/bidsphysio)
[![CodeCoverage](https://codecov.io/gh/cbinyu/bidsphysio/branch/master/graph/badge.svg)](https://codecov.io/gh/cbinyu/bidsphysio)
[![DOI](https://zenodo.org/badge/239006399.svg)](https://zenodo.org/badge/latestdoi/239006399)

## Usage - Single file
```
acq2bidsphysio --infile <physiofiles> --bidsprefix  <Prefix> [--verbose]
```

Example:
```
acq2bidsphysio --infile myPhysio.asq      \
               --bidsprefix BIDSfolder/sub-01/func/sub-01_task-REST_run-1
```

### Arguments
 * `<physiofiles>` space-separated AcqKnowledge files (`<.acq>`) with the physiological
 recordings.
 * `<Prefix>` is the prefix that will be used for the BIDS physiology files.  If all physiological recordings have the same sampling rate and starting time, the script will save the files: `<Prefix>_physio.json` and `<Prefix>_physio.tsv.gz`.  If the physiological signals have different sampling rates and/or starting times, the script will save the files: `<Prefix>_recording-<label>_physio.json` and `<Prefix>_recording-<label>_physio.tsv.gz`, with the corresponding labels (e.g., `cardiac`, `respiratory`, etc.).
 * `--verbose` will print out some warning messages.

Note: If desired, you can use the corresponding `_bold.nii.gz` BIDS file as `--bidsprefix`. The script will strip the `_bold.nii.gz` part from the filename and use what is left as `<Prefix>`. This way, you can assure that the output physiology files match the `_bold.nii.gz` file for which they are intended.

## Usage - Full session

Alternatively, you can convert a whole session worth of `.acq` physiology files automatically naming them:
```
acqsession2bids --infolder <infolder> --bidsfolder <bidsfolder> --subject <subID>
```

The tool will find which physiological file corresponds to which functional image file and will name it accordingly.


### Arguments

 * `<infolder>`: Path to a folder containing all the `.acq` files for a full session.
 * `<bidsfolder>`: Path to the top level BIDS folder where you want to extract the physiological data.
 The functional images corresponding to this session need to have been extracted.
 * `<subID>`: label of the participant to whom the physiological data belong. The label corresponds to `sub-<participant_label>` from the BIDS spec (so it does not include "sub-").  

## Installation
You can install the bidsphysio.acq2bids subpackage from PyPI with `pip`:

```
pip install bidsphysio.acq2bids
```

Alternatively, you can download the package and install the sub-package with `pip`:
```
mkdir /tmp/bidsphysio && \
    curl -sSL https://github.com/cbinyu/bidsphysio/archive/master.tar.gz \
        | tar -vxz -C /tmp/bidsphysio --strip-components=1 && \
    cd /tmp/bidsphysio/bidsphysio.acq2bids/ && \
    pip install . && \
    cd / && \
    rm -rf /tmp/bidsphysio
```

## How to use in your own Python program
After installing the module using `pip` (see [above](#installation "Installation") ), you can use it in your own Python program this way:
```
from bidsphysio.acq2bids import acq2bidsphysio
acq2bidsphysio.acq2bids( [acq_files], prefix )
```


