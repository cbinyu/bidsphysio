"""
Purpose
----
To handle the conversion of a full session's worth of
Eyelink EDF files into BIDS physiological and event files.

It uses the "conversion.py" module of phys2bids to estimate the
delay between the scanner and physio recording computers and find
which BIDS image corresponds to which EDF recording. Then
it uses `edf2bidsphysio` to save the physiological recording in BIDS
compliant files.

Usage
----
edfsession2bids.py -i <Eyelink EDF Session folder> -b <BIDS folder> -s <Subject ID>

Authors
----
Pablo Velasco and Chrysa Papadaniil, NYU Center for Brain Imaging

Dates
----
2020-07-27 CP First version
"""

import argparse
from glob import glob
import os.path as op
from datetime import datetime

from pyedfread import edfread

from bidsphysio.edf2bids import edf2bidsphysio
from bidsphysio.session import session2bids

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Extract Eyelink EDF physiological files for a full'
                    'session to BIDS-compliant physiology recording'
    )
    parser.add_argument('-i', '--infolder', required=True,
                        help='Folder with Eyelink EDF files for a full '
                             'session.')
    parser.add_argument('-b', '--bidsfolder', required=True,
                        help='BIDS folder where to extract the data')
    parser.add_argument('-s', '--subject', required=True,
                        help='The label of the participant to whom '
                             'the physiological data belong. The '
                             'label corresponds to sub-<participant_label> '
                             'from the BIDS spec (so it does not include '
                             '"sub-").')
    parser.add_argument('-e', '--save_eye_events', default=True,
                        help='Saves eye-motion events (fixations, saccades and blinks) as estimated by Eyelink algorithms')
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

    physio_files = glob(op.join(phys_dir, '*.edf'))

    def _get_physio_acq_time(physio_file):
        buf= edfread.read_preamble(physio_file)
        buff_lines = buf.splitlines()
        buff_parts = buff_lines[0].split()
        time_obj = datetime.strptime(buff_parts[5].decode("utf-8"), '%H:%M:%S')
        return time_obj

    session2bids.convert_edf_session(
        physio_files,
        bids_dir,
        sub=args.subject,
        get_physio_data=edf2bidsphysio.edf2bids,
        get_event_data=edf2bidsphysio.edfevents2bids,
        get_physio_acq_time=_get_physio_acq_time,
        save_eye_events=args.save_eye_events,
        overwrite=args.overwrite,
    )


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
