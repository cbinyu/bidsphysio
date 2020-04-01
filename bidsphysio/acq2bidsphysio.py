#!/usr/bin/env python3
"""
Purpose
----
Read physio data from an AcqKnowledge file and save as
BIDS physiology recording file
It uses "bioread" to read the AcqKnowledge file

Usage
----
acq2physio.py -i <AcqKnowledge Physio> -b <BIDS file prefix>


Authors
----
Pablo Velasco, NYU Center for Brain Imaging

Dates
----
2020-02-19 PJV Based on bioread (see References)
2020-02-28 PJV It uses the classes defined in bidsphysio

References
----
AcqKnowledge parser: https://github.com/uwmadison-chm/bioread
BIDS specification for physio signal:
https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/06-physiological-and-other-continuous-recordings.html

License
----
MIT License

Copyright (c) 2020      Pablo Velasco

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import sys
import argparse
import numpy as np
import bioread
import json
from bidsphysio.bidsphysio import (physiosignal,
                                   physiodata)


def acq2bids( physio_acq, bids_prefix ):
    # Extract data from AcqKnowledge file:
    physio_data = bioread.read( physio_acq )

    # Init physiodata object to hold physio signals
    physio = physiodata()

    for item in physio_data.channels:
        physio_label = ''
        
        # specify label:
        if 'puls' in item.name.lower():
            physio_label = 'cardiac'

        elif 'resp' in item.name.lower():
            physio_label = 'respiratory'

        elif "trigger" in item.name.lower():
            physio_label = 'trigger'

        else:
            physio_label = item.name

        if physio_label:
            physio.append_signal(
                # Note: Because the channel name is user-defined, the 'TRIGGER' channel might not
                #   correspond to the scanner trigger, but to the stimulus onset, or something
                #   else. So, I'm going to set the BIDS "StartTime" to 0 (by not passing the
                #   physiostarttime and neuralstarttime), and let the user figure out the offset.
                physiosignal(
                    label=physio_label,
                    samples_per_second=item.samples_per_second,
                    sampling_times=item.time_index,
                    signal=item.data,
                    units=item.units
                )
            )

    # remove '_bold.nii(.gz)' or '_physio' if present **at the end of the bids_prefix**
    # (This is a little convoluted, but we make sure we don't delete it if
    #  it happens in the middle of the string)
    for mystr in ['.gz', '.nii', '_bold', '_physio']:
        bids_prefix = bids_prefix[:-len(mystr)] if bids_prefix.endswith(mystr) else bids_prefix
    
    # Save files:
    physio.save_to_bids_with_trigger( bids_prefix )

    return
    


def plug_missing_data(t,s,dt,missing_value=np.nan):
    # Function to plug "missing_value" (NaN, by default) whereever
    #   the signal was not recorded.

    # This finds the first index for which the difference between consecutive
    #   elements is larger than dt (argmax stops at the first "True"; if it
    #   doesn't find any, it returns 0):
    i = np.argmax( np.ediff1d(t) > dt )
    while i != 0:
        # new time array, which adds the missing timepoint:
        t = np.concatenate( (t[:i+1], [t[i]+dt], t[i+1:]) )
        # new signal array, which adds a "missing_value" at the missing timepoint:
        s = np.concatenate( (s[:i+1], [missing_value], s[i+1:]) )
        # check to see if we are done:
        i = np.argmax( np.ediff1d(t) > dt )

    return t,s


def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert AcqKnowledge physiology files to BIDS-compliant physiology recording')
    parser.add_argument('-i', '--infile', required=True, help='AcqKnowledge physio file')
    parser.add_argument('-b', '--bidsprefix', required=True, help='Prefix of the BIDS file. It should match the _bold.nii.gz')
    args = parser.parse_args()

    # make sure input file exists:
    if not os.path.exists(args.infile):
        raise FileNotFoundError( '{i} file not found'.format(i=args.infile))

    # make sure output directory exists:
    odir = os.path.dirname(args.bidsprefix)
    if not os.path.exists(odir):
        os.makedirs(odir)

    acq2bids( args.infile, args.bidsprefix )

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()

