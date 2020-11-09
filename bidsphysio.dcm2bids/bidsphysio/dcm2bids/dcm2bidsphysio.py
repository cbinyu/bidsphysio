#!/usr/bin/env python3
"""
Purpose
----
Read physio data from a CMRR Multiband generated DICOM file and save as
BIDS physiology recording file
Current CMRR MB sequence version : VE11C R016a

Usage
----
dcm2bidsphysio -i <CMRR DICOM Physio> -b <BIDS file prefix>


Authors
----
Pablo Velasco, NYU Center for Brain Imaging
based on the work of:
Mike Tyszka, Caltech Brain Imaging Center

Dates
----
2018-03-29 JMT From scratch
2018-11-19 JMT Adapt parsing logic from extractCMRRPhysio.m (Ed Auerbach)
2020-02-07 PJV Save PULSE and RESPIRATION to separated files
2020-02-13 PJV Save just the signal and the corresponding scanner triggers in the .tsv.gz file
               Save the timing info in the .json sidecar
2020-02-28 PJV It uses the classes defined in bidsphysio

References
----
Matlab parser: https://github.com/CMRR-C2P/MB/blob/master/extractCMRRPhysio.m
BIDS specification for physio signal:
https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/06-physiological-and-other-continuous-recordings.html

License
----
MIT License

Copyright (c) 2020      Pablo Velasco
Copyright (c) 2017-2018 Mike Tyszka

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

import numpy as np
import pydicom

from bidsphysio.base.bidsphysio import (PhysioSignal,
                                        PhysioData)


def dcm2bids( physio_dcm, bids_prefix, verbose=False ):

    # Because a physio DICOM file contains all of the physio channels, we can
    # only handle a single DICOM file per bids_prefix. So check that we have
    # either just a single DICOM file or one or more .log files:
    if isinstance(physio_dcm, list):
        if len(physio_dcm) > 1:
            if len([f for f in physio_dcm if str(f).endswith('.dcm')]) > 0:
                raise RuntimeError('dcm2bids can only take one DICOM file, since it contains all the physiology')
            dcm_or_logs = 'LOGS'    # at this point, we know we have ".log" files.
        elif len(physio_dcm) == 1:
            physio_dcm = physio_dcm[0]
            dcm_or_logs = 'DCM'
    else:
        # we don't have a list. Check if we have a single DICOM, or a single ".log" file.
        if str(physio_dcm).endswith('.dcm'):
            dcm_or_logs = 'DCM'
        else:
            dcm_or_logs = 'LOGS'
            # make it a single-element list:
            physio_dcm = [physio_dcm]

    # Init PhysioData object to hold physio signals and time of first trigger:
    physio = PhysioData()
    t_first_trigger = None

    if dcm_or_logs == 'DCM':
        # Create DICOM object
        d = pydicom.dcmread(physio_dcm, stop_before_pixels=True)

        # Extract data from Siemens spectroscopy tag (0x7fe1, 0x1010)
        # Yields one long byte array
        if [0x7fe1, 0x1010] in d:
           physio_data = d[0x7fe1, 0x1010].value
        else:
            raise RuntimeError('Physiological data are not available or cannot be accessed from current input data: Element tag [0x7fe1, 0x1010] is missing.')

        # Extract relevant info from header
        n_points = len(physio_data)
        n_rows = d.AcquisitionNumber

        if (n_points % n_rows):
            print('* Points (%d) is not an integer multiple of rows (%d) - exiting' % (n_points, n_rows))
            sys.exit(-1)

        n_cols = int(n_points / n_rows)

        if (n_points % 1024):
            print('* Columns (%d) is not an integer multiple of 1024 (%d) - exiting' % (n_cols, 1024))
            sys.exit(-1)

        n_waves = int(n_cols / 1024)
        wave_len = int(n_points / n_waves)

        for wc in range(n_waves):
            physio_label = ''
        
            if verbose:
                print('')
                print('Parsing waveform %d' % wc)

            offset = wc * wave_len

            wave_data = physio_data[slice(offset, offset+wave_len)]

            data_len = int.from_bytes(wave_data[0:4], byteorder=sys.byteorder)
            fname_len = int.from_bytes(wave_data[4:8], byteorder=sys.byteorder)
            fname = wave_data[slice(8, 8+fname_len)]

            if verbose:
                print('Data length     : %d' % data_len)
                print('Filename length : %d' % fname_len)
                print('Filename        : %s' % fname)

            # Extract waveform log byte data
            log_bytes = wave_data[slice(1024, 1024+data_len)]
            # Convert from a bytes literal to a UTF-8 encoded string, ignoring errors; split lines:
            physio_log_lines = log_bytes.decode('utf-8', 'ignore').splitlines()

            # Parse physio_log_lines
            waveform_name, t, s, dt = parse_log(physio_log_lines, verbose=verbose)
            physio_label, physio_signal, t_first_trigger = to_physiosignal(waveform_name, t, s, dt)
            if physio_label:
                physio.append_signal(physio_signal)

    elif dcm_or_logs == 'LOGS':

        # read the log files:
        for f in physio_dcm:
            physio_log_lines = [line.rstrip() for line in open(f)]

            # Parse physio_log_lines
            waveform_name, t, s, dt = parse_log(physio_log_lines, verbose=verbose)
            physio_label, physio_signal, t_first_trigger = to_physiosignal(waveform_name, t, s, dt)
            if physio_label:
                physio.append_signal(physio_signal)

    # We do this after we have read all signals to make sure we have read the trigger
    #   (if present in the file)
    for p_signal in physio.signals :
        p_signal.neuralstarttime = t_first_trigger or p_signal.physiostarttime
        # we also fill with NaNs the places for which there is missing data:
        p_signal.plug_missing_data()

    # Save files:
    physio.save_to_bids_with_trigger( bids_prefix )

    return


def parse_log(physio_log, verbose=False):

    # Init parameters and lists
    uuid = "UNKNOWN"
    waveform_name = "UNKNOWN"
    scan_date = "UNKNOWN"
    dt = 1.0
    t_list, s_list = [], []
    header_read = False
    vol = ''

    for line in physio_log:

        # Divide the line at whitespace
        parts = line.split()

        # Data lines have the form "<tag> = <value>" or "<time> <name> <signal>"
        if len(parts) == 3:

            p1, p2, p3 = parts

            if 'UUID' in p1:
                uuid = p3

            if 'ScanDate' in p1:
                scan_date = p3

            if 'LogDataType' in p1:
                waveform_name = p3

            if 'SampleTime' in p1:
                dt = float(p3)

            if 'PULS' in p2 or 'RESP' in p2:
                t_list.append(int(p1))
                # in principle, these will also be int, but let's make them
                #  float to support more general signals:
                s_list.append(float(p3))

        # Detect the scanner trigger by going through the ACQUISITION_INFO
        # and detecting when a new volume has been started:
        if waveform_name == 'ACQUISITION_INFO':
            if len(parts) == 5:
                if not header_read:
                    # The first line with 5 elements contains the header for the columns of data
                    header_read = True
                elif parts[4] == '0':
                    # (we only save trigger data for the first echo: the other echoes are the same)
                    t_list.append(int(parts[2]))
                    if parts[0] == vol:
                        # same volume as before:
                        s_list.append(0)
                    else:
                        # we have a new volume - record a scanner trigger:
                        vol = parts[0]
                        s_list.append(1)

    if verbose:
        print('UUID            : %s' % uuid)
        print('Scan date       : %s' % scan_date)
        print('Waveform type   : %s' % waveform_name)

    # Return numpy arrays
    return waveform_name, np.array(t_list), np.array(s_list), dt


def to_physiosignal(waveform_name, t, s, dt):

    t_first_trigger = None

    # specify suffix:
    if 'PULS' in waveform_name:
        physio_label = 'cardiac'

    elif 'RESP' in waveform_name:
        physio_label = 'respiratory'

    elif "ACQUISITION_INFO" in waveform_name:
        physio_label = 'trigger'
        # We only care about the trigger for each volume, so keep only
        #   the timepoints for which the trigger signal is 1:
        t = t[np.where(s == 1)]
        s = np.full(len(t), True)
        # time for the first trigger:
        t_first_trigger = t[0] / 1000

    physio_signal = PhysioSignal(
                label=physio_label,
                samples_per_second=1000 / dt,  # dt is in ms.
                sampling_times=t / 1000,
                physiostarttime=t[0] / 1000,
                signal=s
            )
    return physio_label, physio_signal, t_first_trigger


def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert DICOM physiology files to BIDS-compliant physiology recording')
    parser.add_argument('-i', '--infiles', nargs='+', required=True, help='CMRR physio DICOM file or log files')
    parser.add_argument('-b', '--bidsprefix', required=True,
                        help='Prefix of the BIDS file. It should match the _bold.nii.gz')
    parser.add_argument('-v', '--verbose', action="store_true", default=False, help='verbose screen output')
    args = parser.parse_args()

    # make sure input files exist:
    for infile in args.infiles:
        if not os.path.exists(infile):
            raise FileNotFoundError( '{i} file not found'.format(i=infile))

    # make sure output directory exists:
    odir = os.path.dirname(args.bidsprefix)
    if odir:
        if not os.path.exists(odir):
            os.makedirs(odir)

    dcm2bids( args.infiles, args.bidsprefix, verbose=args.verbose )


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()

