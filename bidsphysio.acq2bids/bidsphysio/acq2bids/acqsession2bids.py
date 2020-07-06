"""
Purpose
----
To handle the conversion of a full session's worth of
AcqKnowledge files into BIDS physiological files.

It uses the "session2bids.py" module of bidsphysio.session to
estimate the delay between the scanner and physio recording
computers and find which BIDS image corresponds to which
physiological recording. Then it uses `acq2bidsphysio` to save the
physiological recording in BIDS compliant files

Usage
----
acqsession2bids.py -i <AcqKnowledge Session folder> -b <BIDS folder> -s <Subject ID>

Authors
----
Pablo Velasco, NYU Center for Brain Imaging

Dates
----
2020-06-05 PV First version
2020-06-22 PV RF to use bidsphysio.session sub-package
"""

import argparse
from glob import glob
import os.path as op

import bioread

from . import acq2bidsphysio
from bidsphysio.session import session2bids


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Extract AcqKnowledge physiological files for a full'
                    'session to BIDS-compliant physiology recording'
    )
    parser.add_argument('-i', '--infolder', required=True,
                        help='Folder with AcqKnowledge files for a full '
                             'session.')
    parser.add_argument('-b', '--bidsfolder', required=True,
                        help='BIDS folder where to extract the data')
    parser.add_argument('-s', '--subject', required=True,
                        help='The label of the participant to whom '
                             'the physiological data belong. The '
                             'label corresponds to sub-<participant_label> '
                             'from the BIDS spec (so it does not include '
                             '"sub-").')
    parser.add_argument('--overwrite', action='store_true', default=False,
                        help='flag to allow overwriting existing converted '
                             'files')
    args = parser.parse_args()

    # make sure input files exist:
    phys_dir = args.infolder
    if not op.exists(phys_dir):
        raise NotADirectoryError('{} folder not found'.format(phys_dir))

    # make sure BIDS folder exists:
    bids_dir = args.bidsfolder
    if not op.exists(bids_dir):
        raise NotADirectoryError('{} folder not found'.format(bids_dir))

    physio_files = glob(op.join(phys_dir, '*.acq'))

    def _get_physio_acq_time(physio_file):
        # Return the method to get the acq_time for a .acq file:
        return bioread.read_file(physio_file).earliest_marker_created_at

    session2bids.convert_session(
        physio_files,
        bids_dir,
        sub=args.subject,
        get_physio_data=acq2bidsphysio.acq2bids,
        get_physio_acq_time=_get_physio_acq_time,
        overwrite=args.overwrite,
    )


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
