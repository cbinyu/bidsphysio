# bidsphysio.edf2bids
Converts eyetracking data from a SR Research Eyelink system (.edf file) to BIDS eye-tracker physiological recording and task events files.

[![Docker image](https://img.shields.io/badge/docker-cbinyu/bidsphysio:latest-brightgreen.svg?logo=docker&style=flat)](https://hub.docker.com/r/cbinyu/bidsphysio/tags/)
[![TravisCI](https://travis-ci.com/cbinyu/bidsphysio.svg?branch=master)](https://travis-ci.com/cbinyu/bidsphysio)
[![CodeCoverage](https://codecov.io/gh/cbinyu/bidsphysio/branch/master/graph/badge.svg)](https://codecov.io/gh/cbinyu/bidsphysio)
[![DOI](https://zenodo.org/badge/239006399.svg)](https://zenodo.org/badge/latestdoi/239006399)

## Usage - Single file
```
edf2bidsphysio --infile <physiofile> --bidsprefix  <Prefix> [--verbose]
```

Example:
```
edf2bidsphysio --infile myEDFFile.edf      \
                --bidsprefix BIDSfolder/sub-01/func/sub-01_task-rest_acq-normal_run-01
```

### Arguments
 * `<physiofile> EDF file (<.edf>) with the eye-tracker recordings.
 * `<Prefix>` is the prefix that will be used for the BIDS physiology files. The script will save the files: <Prefix>-eyetracker_physio.json, <Prefix>-eyetracker_physio.tsv.gz, <Prefix>-eyetracker_events.json and <Prefix>-eyetracker_events.tsv.gz
 * `--verbose` will print out some warning messages.

Note: If desired, you can use the corresponding `_bold.nii.gz` BIDS file as `--bidsprefix`. The script will strip the `_bold.nii.gz` part from the filename and use what is left as `<Prefix>`. This way, you can assure that the output physiology files match the `_bold.nii.gz` file for which they are intended.

## Usage - Full session

Alternatively, you can convert a whole session worth of `.edf` eyetracker files automatically naming them:
```
edfsession2bids --infolder <infolder> --bidsfolder <bidsfolder> --subject <subID>
```

The tool will find which physiological file corresponds to which functional image file and will name it accordingly.


### Arguments

 * `<infolder>`: Path to a folder containing all the `.edf` files for a full session.
 * `<bidsfolder>`: Path to the top level BIDS folder where you want to extract the physiological data.
 The functional images corresponding to this session need to have been extracted.
 * `<subID>`: label of the participant to whom the physiological data belong. The label corresponds to `sub-<participant_label>` from the BIDS spec (so it does not include "sub-").  

## Installation
You can install the bidsphysio.edf2bids subpackage from PyPI with `pip`:

```
pip install bidsphysio.edf2bids
```

Alternatively, you can download the package and install the sub-package with `pip`:
```
mkdir /tmp/bidsphysio && \
    curl -sSL https://github.com/cbinyu/bidsphysio/archive/master.tar.gz \
        | tar -vxz -C /tmp/bidsphysio --strip-components=1 && \
    cd /tmp/bidsphysio/bidsphysio.edf2bids/ && \
    pip install . && \
    cd / && \
    rm -rf /tmp/bidsphysio
```

## How to use in your own Python program
After installing the module using `pip` (see [above](#installation "Installation") ), you can use it in your own Python program this way:
```
from bidsphysio.edf2bids import edf2bidsphysio
edf2bidsphysio.edf2bids( edf_file, prefix )
edf2bidsphysio.edfevents2bids( edf_file, prefix )
```


