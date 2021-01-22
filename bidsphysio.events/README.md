# bidsevents.base
Base classes for BIDS Events

[![Docker image](https://img.shields.io/badge/docker-cbinyu/bidsphysio:latest-brightgreen.svg?logo=docker&style=flat)](https://hub.docker.com/r/cbinyu/bidsphysio/tags/)
[![TravisCI](https://travis-ci.com/cbinyu/bidsphysio.svg?branch=master)](https://travis-ci.com/cbinyu/bidsphysio)
[![CodeCoverage](https://codecov.io/gh/cbinyu/bidsphysio/branch/master/graph/badge.svg)](https://codecov.io/gh/cbinyu/bidsphysio)
[![DOI](https://zenodo.org/badge/239006399.svg)](https://zenodo.org/badge/latestdoi/239006399)

## Installation
You can install the base class from PyPI with `pip`:

```
pip install bidsevents.base
```

Alternatively, you can download the package and install the sub-package with `pip`:
```
mkdir /tmp/bidsphysio && \
    curl -sSL https://github.com/cbinyu/bidsphysio/archive/master.tar.gz \
        | tar -vxz -C /tmp/bidsphysio --strip-components=1 && \
    cd /tmp/bidsphysio/bidsevents.base/ && \
    pip install . && \
    cd / && \
    rm -rf /tmp/bidsphysio
```

## How to use in your own Python program
After installing the module using `pip` (see [above](#installation "Installation") ), you can use it in your own Python program this way:
```
from bidsphysio.base.bidsevents import (EventSignal,
                                        EventData)

mySignal = EventSignal()
...
```
