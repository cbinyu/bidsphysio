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

import argparse
import json
import os
import sys

import bioread

from bidsphysio.bidsphysio import (physiosignal,
                                   physiodata)


def acq2bids( physio_acq_files, bids_prefix ):
    # In case we are handled just a single file, make it a one-element list:
    if isinstance(physio_acq_files, str):
        physio_acq_files = [physio_acq_files]

    # Init physiodata object to hold physio signals:
    physio = physiodata()

    # Read the files from the list, extract the relevant information and
    #   add a new physiosignal to the list:
    for physio_acq in physio_acq_files:
        # Extract data from AcqKnowledge file:
        physio_data = bioread.read( physio_acq )

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

    # Save files:
    physio.save_to_bids_with_trigger( bids_prefix )

    return


def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert AcqKnowledge physiology files to BIDS-compliant physiology recording')
    parser.add_argument('-i', '--infiles', nargs='+', required=True, help='AcqKnowledge physio file(s) (space separated)')
    parser.add_argument('-b', '--bidsprefix', required=True, help='Prefix of the BIDS file. It should match the _bold.nii.gz')
    args = parser.parse_args()

    # make sure input files exist:
    for infile in args.infiles:
        if not os.path.exists(infile):
            raise FileNotFoundError( '{i} file not found'.format(i=infile))

    # make sure output directory exists:
    odir = os.path.dirname(args.bidsprefix)
    if not os.path.exists(odir):
        os.makedirs(odir)

    acq2bids( args.infiles, args.bidsprefix )

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()

