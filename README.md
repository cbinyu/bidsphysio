# bidsphysio
Converts physio data (CMRR, AcqKnowledge, Siemens PMU) to BIDS physiological recording

[![Docker image](https://img.shields.io/badge/docker-cbinyu/bidsphysio:latest-brightgreen.svg?logo=docker&style=flat)](https://hub.docker.com/r/cbinyu/bidsphysio/tags/)
[![TravisCI](https://travis-ci.com/cbinyu/bidsphysio.svg?branch=master)](https://travis-ci.com/cbinyu/bidsphysio)
[![CodeCoverage](https://codecov.io/gh/cbinyu/bidsphysio/branch/master/graph/badge.svg)](https://codecov.io/gh/cbinyu/bidsphysio)
[![DOI](https://zenodo.org/badge/239006399.svg)](https://zenodo.org/badge/latestdoi/239006399)

## Usage
```
physio2bidsphysio --infile <physiofiles> --bidsprefix  <Prefix> [--verbose]
```

Example:
```
physio2bidsphysio --infile 07+epi_MB4_2mm_Physio+00001.dcm      \
                  --bidsprefix BIDSfolder/sub-01/func/sub-01_task-REST_run-1
```

## Arguments
 * `<physiofiles>` space-separated files with the physiological recordings.
 
    Supported file types:
	 * `<.dcm>`: DICOM file with physiological recording from a CMRR
     Multi-Band sequence (only a single file for this file type).
	 * `<.acq>`: AcqKnowledge file (BioPac).
	 * `<.puls>` or `<.resp>`: Siemens PMU file (VB15A, VBX, VE11C).
	 * (`<.edf>` (SR-Research) support coming soon...)
 * `<Prefix>` is the prefix that will be used for the BIDS physiology files.  If all physiological recordings have the same sampling rate and starting time, the script will save the files: `<Prefix>_physio.json` and `<Prefix>_physio.tsv.gz`.  If the physiological signals have different sampling rates and/or starting times, the script will save the files: `<Prefix>_recording-<label>_physio.json` and `<Prefix>_recording-<label>_physio.tsv.gz`, with the corresponding labels (e.g., `cardiac`, `respiratory`, etc.).
 * `--verbose` will print out some warning messages.



Note: If desired, you can use the corresponding `_bold.nii.gz` BIDS file as `--bidsprefix`. The script will strip the `_bold.nii.gz` part from the filename and use what is left as `<Prefix>`. This way, you can assure that the output physiology files match the `_bold.nii.gz` file for which they are intended.

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
`dcm2bids` (for `.dcm` CMRR physiology files)
 and `pmu2bids` (for Siemens PMU files). 
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
```
docker run [docker options] cbinyu/bidsphysio \
    --infile <physiofiles>      \
    --bidsprefix <Prefix>
```
Note that the `<physiofiles>` and the `<Prefix>` should use the corresponding paths inside the Docker container.

Example:
```
docker run --rm \
    --user $(id -u):$(id -g) \
    --name test_bidsphysio \
    --volume /tmp:/tmp \
    cbinyu/bidsphysio \
        --infile /tmp/07+epi_MB4_2mm_Physio+00001.dcm \
        --bidsprefix /tmp/test
```

## Alternative use:

The package will also install the binaries: `dcm2bidsphysio`, `acq2bidsphysio`
and `pmu2bidsphysio`, to extract a specific file type:

```
dcm2bidsphysio --infile <DCMfile> --bidsprefix <Prefix>
acq2bidsphysio --infile <acqfiles> --bidsprefix <Prefix>
pmu2bidsphysio --infile <pmufiles> --bidsprefix <Prefix>
```

## How to use in your own Python program
After installing the module using `pip` (see [above](https://github.com/cbinyu/bidsphysio#installation "Installation") ), you can use it in your own Python program this way:
```
from bidsphysio.dcm2bids import dcm2bidsphysio
dcm2bidsphysio.dcm2bids( dicom_file, prefix )
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

