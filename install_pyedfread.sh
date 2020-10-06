#!/bin/sh
set -ex
wget https://github.com/nwilming/pyedfread/archive/master.tar.gz
tar -xzvf pyedfread-master.tar.gz
cd pyedfread-master && sed -i -e "s/cython: profile=True/cython: profile=True, language_level=2/" pyedfread/edfread.pyx && python setup.py install
