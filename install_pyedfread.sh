#!/bin/sh
set -e
git clone https://github.com/nwilming/pyedfread.git
cd pyedfread && python setup.py install
