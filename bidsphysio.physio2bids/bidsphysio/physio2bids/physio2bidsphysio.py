#!/usr/bin/env python3
"""
Purpose
----
Read physio data and save as BIDS physiology recording file.
Currently supported:
- CMRR Multiband generated DICOM file
- Acqknowledge file (BioPac)
- Siemens PMU file (VB15A, VBX, VE11C)

Usage
----
physio2bidsphysio -i <physio file> -b <BIDS file prefix>


Author
----
Pablo Velasco, NYU Center for Brain Imaging

Dates
----
2020-04-08 PJV First version

References
----
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
import os
import sys

from bidsphysio.acq2bids import acq2bidsphysio as a2bp
from bidsphysio.dcm2bids import dcm2bidsphysio as d2bp
from bidsphysio.pmu2bids import pmu2bidsphysio as p2bp


def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert physiology files to BIDS-compliant physiology recording')
    parser.add_argument('-i', '--infiles', nargs='+', required=True, help='physio file(s)')
    parser.add_argument('-b', '--bidsprefix', required=True, help='Prefix of the BIDS file. It should match the _bold.nii.gz')
    parser.add_argument('-v', '--verbose', action="store_true", default=False, help='verbose screen output')
    args = parser.parse_args()

    # make sure input files exist:
    for infile in args.infiles:
        if not os.path.exists(infile):
            raise FileNotFoundError( '{i} file not found'.format(i=infile))

    # check that the input file is recognized (check extension):
    knownExtensions = ['dcm', 'puls', 'resp', 'acq', 'log']
    allowedExtensions = knownExtensions
    for infile in args.infiles:
        fileExtension = infile.split('.')[-1]
        if not fileExtension in allowedExtensions:
            raise Exception("{fe} is not a known physio file extension.".format(fe=fileExtension))
        else:
            # For now, all files need to be of the same type. To do that,
            #   at this point we limit the list of allowedExtensions:
            if fileExtension in ['puls','resp']:
                allowedExtensions = ['puls','resp']
            else:
                allowedExtensions = fileExtension

    # make sure output directory exists:
    odir = os.path.dirname(args.bidsprefix)
    if not os.path.exists(odir):
        os.makedirs(odir)

    # depending on the allowedExtension, call the XXX2bids method of corresponding module:
    if allowedExtensions == 'dcm':
        if len(args.infiles) > 1:
            raise Exception('Only one input file is allowed for DICOM physio files')
        d2bp.dcm2bids( args.infiles[0], args.bidsprefix, verbose=args.verbose )
    elif allowedExtensions == 'acq':
        a2bp.acq2bids( args.infiles, args.bidsprefix )
    elif allowedExtensions == ['puls','resp']:
        p2bp.pmu2bids( args.infiles, args.bidsprefix, verbose=args.verbose )



# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
