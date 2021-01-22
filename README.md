# bidsphysio
Converts physio data (CMRR, AcqKnowledge, Siemens PMU) to BIDS physiological recording

[![Docker image](https://img.shields.io/badge/docker-cbinyu/bidsphysio:latest-brightgreen.svg?logo=docker&style=flat)](https://hub.docker.com/r/cbinyu/bidsphysio/tags/)
[![TravisCI](https://travis-ci.com/cbinyu/bidsphysio.svg?branch=master)](https://travis-ci.com/cbinyu/bidsphysio)
[![CodeCoverage](https://codecov.io/gh/cbinyu/bidsphysio/branch/master/graph/badge.svg)](https://codecov.io/gh/cbinyu/bidsphysio)
[![DOI](https://zenodo.org/badge/239006399.svg)](https://zenodo.org/badge/latestdoi/239006399)

## Usage - Single File

You can use `physio2bidsphysio` to convert a single file:
```
physio2bidsphysio --infile <physiofiles> --bidsprefix  <Prefix> [--verbose]
```

Example:
```
physio2bidsphysio --infile 07+epi_MB4_2mm_Physio+00001.dcm      \
                  --bidsprefix BIDSfolder/sub-01/func/sub-01_task-REST_run-1
```

### Arguments
 * `<physiofiles>` space-separated files with the physiological recordings.
 
    Supported file types:
	 * `<.dcm>` or `<.log>`: DICOM or log file with physiological recording from a CMRR
     Multi-Band sequence (only a single file for `<.dcm>`).
	 * `<.acq>`: AcqKnowledge file (BioPac).
	 * `<.puls>` or `<.resp>`: Siemens PMU file (VB15A, VBX, VE11C).
	 * `<.edf>` SR Research .edf file
 * `<Prefix>` is the prefix that will be used for the BIDS physiology files.  If all physiological recordings have the same sampling rate and starting time, the script will save the files: `<Prefix>_physio.json` and `<Prefix>_physio.tsv.gz`.  If the physiological signals have different sampling rates and/or starting times, the script will save the files: `<Prefix>_recording-<label>_physio.json` and `<Prefix>_recording-<label>_physio.tsv.gz`, with the corresponding labels (e.g., `cardiac`, `respiratory`, etc.).
 * `--verbose` will print out some warning messages.



Note: If desired, you can use the corresponding `_bold.nii.gz` BIDS file as `--bidsprefix`. The script will strip the `_bold.nii.gz` part from the filename and use what is left as `<Prefix>`. This way, you can assure that the output physiology files match the `_bold.nii.gz` file for which they are intended.

## Usage - Full session

Alternatively, you can convert a whole session worth of physiology files automatically naming them. Currently,  AcqKnowledge and eyetracking .edf files are supported:

```
acqsession2bids --infolder <physiofolder> --bidsfolder <bidsfolder> --subject <subID>

edfsession2bids --infolder <physiofolder> --bidsfolder <bidsfolder> --subject <subID>
```
The tool will find which physiological file corresponds to which functional image file and will name it accordingly.


### Arguments

 * `<physiofolder>`: Path to a folder containing all the `.acq` files for a full session.
 * `<bidsfolder>`: Path to the top level BIDS folder where you want to extract the physiological data.
 The functional images corresponding to this session need to have been extracted.
 * `<subID>`: label of the participant to whom the physiological data belong. The label corresponds to `sub-<participant_label>` from the BIDS spec (so it does not include "sub-").  


## Installation
You can install the tool directly from PyPI:
```
pip install bidsphysio
```

If you don't want to install the whole package, you can install individual subpackages:
```
pip install bidsphysio.<sub-package>
```
Available sub-packages are `acq2bids` (for `.acq` files),
`dcm2bids` (for `.dcm` and `.log` CMRR physiology files)
, `pmu2bids` (for Siemens PMU files) and `edf2bids` (for SR Research eyetracking .edf files). 
You can also install the base classes with the `bidsphysio.base` sub-package.

Alternatively, you can download the package and install it with `pip`:
```
mkdir /tmp/bidsphysio && \
    curl -sSL https://github.com/cbinyu/bidsphysio/archive/master.tar.gz \
        | tar -vxz -C /tmp/bidsphysio --strip-components=1 && \
    cd /tmp/bidsphysio && \
    pip install . && \
    cd / && \
    rm -rf /tmp/bidsphysio
```

## Docker usage
After pulling the latest version (`docker pull cbinyu/bidsphysio`), start a Docker container with:
```
docker run [docker options] cbinyu/bidsphysio
```
Then, you can run any `bidsphysio` command (see `Usage` above)


## Alternative use:

Installing `bidsphysio` will also install the binaries: `dcm2bidsphysio`, `acq2bidsphysio`
and `pmu2bidsphysio`, to extract a specific file type:

```
dcm2bidsphysio --infile <DCMfile> --bidsprefix <Prefix>
acq2bidsphysio --infile <acqfiles> --bidsprefix <Prefix>
pmu2bidsphysio --infile <pmufiles> --bidsprefix <Prefix>
edf2bidsphysio --infile <edffile> --bidsprefix <Prefix> 
```

## How to use in your own Python program
After installing the module using `pip` (see [above](https://github.com/cbinyu/bidsphysio#installation "Installation") ), you can use it in your own Python program this way:
```
from bidsphysio.dcm2bids import dcm2bidsphysio
dcm2bidsphysio.dcm2bids( dicom_file, prefix )
# or:
dcm2bidsphysio.dcm2bids( [log_files], prefix )
```
or:
```
from bidsphysio.acq2bids import acq2bidsphysio
acq2bidsphysio.acq2bids( [acq_files], prefix )
```
or:
```
from bidsphysio.pmu2bids import pmu2bidsphysio
pmu2bidsphysio.pmu2bids( [pmu_files], prefix )
```
or:
```
from bidsphysio.edf2bids import edf2bidsphysio
edf2bidsphysio.edf2bids( edf_file, prefix )
edf2bidsphysio.edfevents2bids( edf_file, prefix )
```
