#!/bin/sh
set -e
git clone https://github.com/nwilming/pyedfread.git
cd pyedfread && sed -i -e "s/cython: profile=True/cython: profile=True, language_level=2/" pyedfread/edfread.pyx && python setup.py install
