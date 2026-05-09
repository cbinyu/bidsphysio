# bidsphysio.dcm2bids
Converts physio data saved in a DICOM file to BIDS physiological recording.
Two flavors of physio DICOM are supported:

  * **CMRR Multi-Band sequence (Siemens VE11C).** The classic format: a raw
    binary blob at private tag `(7FE1,1010)` containing one 1024-byte header
    per waveform followed by ASCII log lines.
  * **Siemens XA-line PhysioLogging (XA30 / XA60).** A gzip-compressed XML
    document at the same `(7FE1,1010)` tag, written by the Siemens
    PhysioLogging feature on `syngo MR XA*` scanners. See the Siemens
    [PhysioLogging application tip](https://www.magnetomworld.siemens-healthineers.com/clinical-corner/application-tips/physiologging)
    for background on enabling and using this feature on the scanner.

Format detection is automatic — the parser sniffs the gzip magic bytes
(`1F 8B`) on the payload and dispatches to the appropriate reader, so the
same `dcm2bidsphysio` command handles both.

[![Docker image](https://img.shields.io/badge/docker-cbinyu/bidsphysio:latest-brightgreen.svg?logo=docker&style=flat)](https://hub.docker.com/r/cbinyu/bidsphysio/tags/)
[![TravisCI](https://travis-ci.com/cbinyu/bidsphysio.svg?branch=master)](https://travis-ci.com/cbinyu/bidsphysio)
[![CodeCoverage](https://codecov.io/gh/cbinyu/bidsphysio/branch/master/graph/badge.svg)](https://codecov.io/gh/cbinyu/bidsphysio)
[![DOI](https://zenodo.org/badge/239006399.svg)](https://zenodo.org/badge/latestdoi/239006399)

## Usage
```
dcm2bidsphysio --infile <DCMfile> --bidsprefix <Prefix> [--verbose]
```

Example:
```
dcm2bidsphysio --infile myPhysio.dcm      \
               --bidsprefix BIDSfolder/sub-01/func/sub-01_task-REST_run-1
```

## Arguments
 * `<DCMfile>` Physio DICOM file (`<.dcm>`) with the physiological
 recordings — either a CMRR VE11C blob or a Siemens XA PhysioLogging
 (XA30/XA60) gzip-XML payload.
 * `<Prefix>` is the prefix that will be used for the BIDS physiology files.  If all physiological recordings have the same sampling rate and starting time, the script will save the files: `<Prefix>_physio.json` and `<Prefix>_physio.tsv.gz`.  If the physiological signals have different sampling rates and/or starting times, the script will save the files: `<Prefix>_recording-<label>_physio.json` and `<Prefix>_recording-<label>_physio.tsv.gz`, with the corresponding labels (e.g., `cardiac`, `respiratory`, etc.).
 * `--verbose` will print out some warning messages.

Note: If desired, you can use the corresponding `_bold.nii.gz` BIDS file as `--bidsprefix`. The script will strip the `_bold.nii.gz` part from the filename and use what is left as `<Prefix>`. This way, you can assure that the output physiology files match the `_bold.nii.gz` file for which they are intended.

## XA-line PhysioLogging notes

Both VE11C and XA payloads time-stamp samples and scan events in MDH tics
(2.5 ms each, on the Siemens Measurement Data Header clock). The fields
`LogStartMDHTime` and `LogStopMDHTime` (VE11C) — and the `TIME_TICS`
attributes on `<PMU>` elements (XA) — indicate the start and stop times of
the recording of each physiological signal, which are *not* synced to the
MRI acquisition (it is manual) but use the same clock (MDH).

Practical consequence for XA recordings: the operator typically starts
PMU logging from the console a few seconds before the scan, so the
`StartTime` field in the resulting `_physio.json` sidecar will usually be
**negative** (samples before the first scan trigger). This is correct per
the BIDS specification — `StartTime` is defined relative to the first
scan trigger, not the absolute clock — and downstream tools that respect
that convention will align the recording correctly.

Per-volume scan triggers are derived from the
`<Volume ACQUISITION_TIME_TICS>` entries in the XA XML
(scan-locked), in preference to `<PhysioTrigger>` entries (which are
PMU-detected events with a device-dependent `SIGNAL` bitmask). Each
`<Volume>` entry marks the instant the scanner began that volume, so
each `1` in the BIDS trigger column should be read as "scanner volume
started here", not "TR has elapsed" — spacing can be non-uniform for
SBRef / pre-scan / variable-TR runs.

If the XA payload's per-stream sample rate inferred from `span/(N-1)`
disagrees with the modal inter-sample tic gap (typically because one or
more samples were dropped during recording), `dcm2bidsphysio` prints a
`WARNING:` line to stdout naming the affected stream. The conversion
still completes; the message is advisory so you can decide whether the
resulting timing is acceptable downstream.

## Installation
You can install the bidsphysio.dcm2bids subpackage from PyPI with `pip`:

```
pip install bidsphysio.dcm2bids
```

Alternatively, you can download the package and install the sub-package with `pip`:
```
mkdir /tmp/bidsphysio && \
    curl -sSL https://github.com/cbinyu/bidsphysio/archive/master.tar.gz \
        | tar -vxz -C /tmp/bidsphysio --strip-components=1 && \
    cd /tmp/bidsphysio/bidsphysio.dcm2bids/ && \
    pip install . && \
    cd / && \
    rm -rf /tmp/bidsphysio
```

## How to use in your own Python program
After installing the module using `pip` (see [above](#installation "Installation") ), you can use it in your own Python program this way:
```
from bidsphysio.dcm2bids import dcm2bidsphysio
dcm2bidsphysio.dcm2bids( dmc_file, prefix )
```
