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
import os

import bioread

from bidsphysio.base.bidsphysio import (PhysioSignal,
                                        PhysioData)


def acq2bids(physio_acq_files, trigger_label='trigger'):
    """Reads the physiological data from a series of AcqKnowledge
    files and stores it in a PhysioData member

    Parameters
    ----------
    physio_acq_files : list of str
        List of paths of the original physio files
    trigger_label : str
        Label of the channel that carries the scanner trigger.
        Just one word from the channel name is enough

    Returns
    -------
    physio : PhysioData
        PhysioData with the contents of the file
    """
    # In case we are handled just a single file, make it a one-element list:
    if isinstance(physio_acq_files, str):
        physio_acq_files = [physio_acq_files]

    # Init PhysioData object to hold physio signals:
    physio = PhysioData()

    # Read the files from the list, extract the relevant information and
    #   add a new PhysioSignal to the list:
    trigger_channel = ''
    for physio_acq in physio_acq_files:
        # Extract data from AcqKnowledge file:
        physio_data = bioread.read( physio_acq )
        # Get the time the file was created:
        physiostarttime = physio_data.earliest_marker_created_at

        for item in physio_data.channels:
            physio_label = ''

            # specify label:
            if 'puls' in item.name.lower():
                physio_label = 'cardiac'

            elif 'resp' in item.name.lower():
                physio_label = 'respiratory'

            elif trigger_label.lower() in item.name.lower():
                physio_label = 'trigger'
                trigger_channel = item.name

            else:
                physio_label = item.name

            if physio_label:
                physio.append_signal(
                    PhysioSignal(
                        label=physio_label,
                        samples_per_second=item.samples_per_second,
                        sampling_times=item.time_index,
                        physiostarttime=physiostarttime.timestamp(),
                        signal=item.data,
                        units=item.units
                    )
                )

    # Get the "neuralstarttime" for the PhysioSignals by finding the first trigger.
    # We do this after we have read all signals to make sure we have read the trigger
    # (if present in the file. If not present, use the physiostart time. This is the
    # same as assuming the physiological recording started at the same time as the
    # neural recording.)
    # This assumes that the channel named "trigger" indeed contains the scanner trigger
    # and not something else (e.g., stimulus trigger). So we print a warning.
    neuralstarttime = ''
    if trigger_channel:
        print('Warning: Assuming "{}" channel corresponds to the scanner trigger'.format(trigger_channel))
        # The sampling_times are w.r.t. the start of the recording, so we need
        # to also add the 'physiostarttime' (time when file was created):
        neuralstarttime = physio.get_scanner_onset() + physiostarttime.timestamp()
    for p_signal in physio.signals:
        p_signal.neuralstarttime = neuralstarttime or p_signal.physiostarttime
        # we also fill with NaNs the places for which there is missing data:
        p_signal.plug_missing_data()

    return physio


def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert AcqKnowledge physiology files to BIDS-compliant physiology recording')
    parser.add_argument('-i', '--infiles', nargs='+', required=True, help='AcqKnowledge physio file(s) (space separated)')
    parser.add_argument('-b', '--bidsprefix', required=True, help='Prefix of the BIDS file. It should match the _bold.nii.gz')
    parser.add_argument('-t', '--triggerlabel', required=False, help='Label of the trigger channel in the physio file(s). Just one word from the channel name is enough.', default='trigger')
    args = parser.parse_args()

    # make sure input files exist:
    for infile in args.infiles:
        if not os.path.exists(infile):
            raise FileNotFoundError( '{i} file not found'.format(i=infile))

    # make sure output directory exists:
    odir = os.path.dirname(args.bidsprefix)
    if not os.path.exists(odir):
        os.makedirs(odir)

    physio_data = acq2bids(args.infiles, args.triggerlabel)
    if physio_data.labels():
        physio_data.save_to_bids_with_trigger(args.bidsprefix)


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()

