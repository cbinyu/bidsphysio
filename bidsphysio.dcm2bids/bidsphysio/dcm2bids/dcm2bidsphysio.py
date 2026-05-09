#!/usr/bin/env python3
"""
Purpose
----
Read physio data from a CMRR Multiband generated DICOM file and save as
BIDS physiology recording file
Current CMRR MB sequence version : VE11C R016a
Also supports Siemens XA-line scanners (XA30/XA60), where the same DICOM tag
(7FE1,1010) holds a gzip-compressed XML payload (PhysioLogging feature).

Usage
----
dcm2bidsphysio -i <CMRR DICOM Physio> -b <BIDS file prefix>


Timing notes (Siemens MDH clock)
----
For both VE11C and XA payloads, every timestamp is expressed in MDH tics
(2.5 ms each) on the same scanner clock. In the legacy VE11C format these
appear as the LogStartMDHTime / LogStopMDHTime fields; in XA they appear
as TIME_TICS attributes on <PMU>, <Volume>, and <PhysioTrigger> elements.

LogStartMDHTime and LogStopMDHTime indicate the start and stop times of
the recording of each physiological signal, which are NOT synced to the
MRI acquisition (it is manual) but use the same clock (MDH). The XA TIME_TICS
on <PMU> samples behave identically: the operator starts/stops PMU
recording from the console, so the first PMU tic typically precedes the
first acquired volume by a manual head-start of seconds. Alignment of
physio to scan must therefore use the offset between the PMU stream and
the scan-locked <Volume ACQUISITION_TIME_TICS> entries (or the legacy
ACQUISITION_INFO trigger lines), not the absolute MDH value.


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
2026-05-09 CR  Add Siemens XA (gzip-XML PhysioLogging) parser branch

References
----
Matlab parser: https://github.com/CMRR-C2P/MB/blob/master/extractCMRRPhysio.m
Siemens XA PhysioExtractor demo (Magnetom World, 2024-10-04)
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
import re
import sys
import xml.etree.ElementTree as ET
import zlib

import numpy as np
import pydicom

from bidsphysio.base.bidsphysio import (PhysioSignal,
                                        PhysioData)


def dcm2bids(physio_dcm, verbose=False):
    """Reads the physiological data from either a CMRR DICOM file or
    from a series of CMRR .log files and stores it in a PhysioData
    member.

    Parameters
    ----------
    physio_dcm : list of str
        List of paths of the original physio files (or single path)
    verbose : bool
        Verbose output flag.

    Returns
    -------
    physio : PhysioData
        PhysioData with the contents of the file
    """

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

        # Detect Siemens XA-line PhysioLogging payload: a gzip stream begins
        # with magic bytes 0x1f 0x8b. XA wraps the same DICOM tag around an
        # XML document (PhysioLogging feature) instead of the legacy VE11C
        # binary blob.
        if len(physio_data) >= 2 and physio_data[:2] == b'\x1f\x8b':
            if verbose:
                print('Detected Siemens XA gzip-compressed XML PhysioLogging payload')
            # zlib with wbits = 16+MAX_WBITS decodes a single gzip member and
            # stops cleanly at the end of the stream; this matches the approach
            # used by the Siemens PhysioExtractor reference scripts and avoids
            # gzip.decompress() complaining about non-member trailing bytes.
            # The XA payload commonly has a trailing NUL after </PhysioData>;
            # strip it so the XML parser doesn't reject the document.
            xml_text = zlib.decompress(
                physio_data, 16 + zlib.MAX_WBITS
            ).decode('utf-8', 'ignore').rstrip('\x00').rstrip()
            uuid = getattr(d, 'SOPInstanceUID', 'UNKNOWN')
            for waveform_name, t, s, dt in parse_xa_xml(xml_text, verbose=verbose):
                physio_label, physio_signal, first_trigger_this_waveform = to_physiosignal(uuid, waveform_name, t, s, dt)
                t_first_trigger = t_first_trigger or first_trigger_this_waveform
                if physio_label:
                    physio.append_signal(physio_signal)
        else:
            # Legacy CMRR VE11C path: raw binary blob with one 1024-byte header
            # per waveform followed by ASCII log lines.
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
                uuid, waveform_name, t, s, dt = parse_log(physio_log_lines, verbose=verbose)
                physio_label, physio_signal, first_trigger_this_waveform = to_physiosignal(uuid, waveform_name, t, s, dt)
                t_first_trigger = t_first_trigger or first_trigger_this_waveform
                if physio_label:
                    physio.append_signal(physio_signal)

    elif dcm_or_logs == 'LOGS':

        # read the log files:
        for f in physio_dcm:
            physio_log_lines = [line.rstrip() for line in open(f)]

            # Parse physio_log_lines
            uuid, waveform_name, t, s, dt = parse_log(physio_log_lines, verbose=verbose)
            physio_label, physio_signal, first_trigger_this_waveform = to_physiosignal(uuid, waveform_name, t, s, dt)
            t_first_trigger = t_first_trigger or first_trigger_this_waveform
            if physio_label:
                physio.append_signal(physio_signal)

    # We do this after we have read all signals to make sure we have read the trigger
    #   (if present in the file)
    for p_signal in physio.signals :
        p_signal.neuralstarttime = t_first_trigger or p_signal.physiostarttime
        # we also fill with NaNs the places for which there is missing data:
        p_signal.plug_missing_data()

    return physio


# MDH tic length, in milliseconds. The Siemens MDH (Measurement Data Header)
# clock advances in 2.5 ms tics. All XA TIME_TICS values, as well as the
# legacy VE11C LogStartMDHTime / LogStopMDHTime fields, are quoted in this unit.
MDH_TIC_MS = 2.5


def _avg_dt(t):
    """Average inter-sample interval of a 1-D timestamp array, in the same
    units as t. With N samples spanning (t[-1] - t[0]) there are N-1
    intervals, so the as-acquired average is span / (N-1) (minding the
    fencepost). This matches what you'd compute from explicit start/end
    timestamps and is robust to one-off jitter in any single diff. For
    N < 2 there is no interval to measure, so we fall back to MDH_TIC_MS
    (the underlying clock resolution) as a non-zero sentinel.
    """
    if len(t) >= 2:
        return float((t[-1] - t[0]) / (len(t) - 1))
    return MDH_TIC_MS


def parse_xa_xml(xml_text, verbose=False):
    """Parse a Siemens XA-line PhysioLogging XML payload.

    The XA payload is a single <PhysioData> XML document containing:
      * <VolumeAcquisitionDescription> with one <Volume ACQUISITION_TIME_TICS=...>
        per acquired volume. These are scan-locked: each entry marks the
        instant the scanner began that volume. Spacing reflects the actual
        acquisition pattern within the PMU recording window, which is
        not necessarily uniform — for example, an SBRef DICOM contains
        the calibration / dummy / reference volumes that fall inside its
        recording window, with non-TR-spaced timestamps. Downstream code
        consuming the BIDS trigger column should treat each `1` as
        "scanner volume started here", not as "TR has elapsed".
      * Zero or more <PhysioStream TYPE="PULS|RESP|ECG|EXT|...">, each
        carrying <PMU TIME_TICS="..." DATA="..."/> samples. These tics are
        on the same MDH clock as the Volume entries, BUT the PMU recording
        is started and stopped manually by the operator from the console,
        so the first PMU tic is not aligned to scan start. Alignment must
        use the offset between the streams, not the absolute MDH value.
        (This matches the legacy VE11C semantics of LogStartMDHTime /
        LogStopMDHTime: same clock, manual start.)
      * Optional <PhysioTrigger ACQUISITION_TIME_TICS="..." SIGNAL="..."/>
        entries for PMU-detected events. These are NOT used here as scan
        triggers because their SIGNAL bitmask is device-dependent; we use
        <Volume> entries instead.

    Yields tuples (waveform_name, t_ms, s, dt_ms) compatible with
    to_physiosignal(). For triggers the waveform_name is "ACQUISITION_INFO"
    (matching the VE11C convention) so that to_physiosignal() routes it to
    the trigger branch.
    """
    # Strip every inline DOCTYPE before parsing. The XA payload declares a
    # DTD with element rules but no entities; stdlib ElementTree blocks
    # external entities since Python 3.7 but still expands internal ones,
    # so a maliciously crafted DICOM could embed billion-laughs entities in
    # the DTD. Removing the DOCTYPE eliminates that surface without adding
    # a defusedxml dependency. The element structure is inferred from the
    # body, so the DTD is not needed for parsing.
    # Both the internal-subset form (<!DOCTYPE name [...]>) and the bare /
    # external-DTD form (<!DOCTYPE name>, <!DOCTYPE name SYSTEM "...">) are
    # stripped. Removing all matches (no count cap) closes a bypass where a
    # benign first DOCTYPE shields a malicious second one from a single-shot
    # strip.
    xml_text = re.sub(
        r'<!DOCTYPE[^[>]*(?:\[.*?\])?\s*>\s*',
        '', xml_text, flags=re.DOTALL,
    )
    root = ET.fromstring(xml_text)

    # Scan triggers: one per <Volume>. Use ACQUISITION_TIME_TICS, which is
    # the scan-locked timestamp for the first slice of each volume.
    volume_tics = []
    for vol in root.iter('Volume'):
        tics = vol.get('ACQUISITION_TIME_TICS')
        if tics is not None:
            volume_tics.append(int(tics))
    volume_tics.sort()
    if volume_tics:
        t_trig = np.array(volume_tics, dtype=float) * MDH_TIC_MS
        # to_physiosignal() filters on s == 1 in the ACQUISITION_INFO branch;
        # all entries here are real volume triggers, so emit ones.
        s_trig = np.ones(len(t_trig))
        # dt for the trigger "waveform" is informational. With N volumes
        # spanning (last - first) ms there are N-1 intervals, so the
        # average TR is span / (N-1) (fencepost). Falls back to MDH_TIC_MS
        # for a single-volume run, which is a sentinel value rather than
        # a meaningful TR (single shot has no inter-volume interval).
        dt_trig = _avg_dt(t_trig)
        if verbose:
            print('XA: %d volume triggers, avg TR %.1f ms' % (len(t_trig), dt_trig))
        yield 'ACQUISITION_INFO', t_trig, s_trig, dt_trig

    # Physiology streams. Each <PhysioStream TYPE="PULS"> etc. carries
    # <PMU> samples. Yield one waveform per stream.
    for stream in root.iter('PhysioStream'):
        stream_type = stream.get('TYPE') or 'UNKNOWN'
        t_list, s_list = [], []
        for pmu in stream.findall('PMU'):
            tics = pmu.get('TIME_TICS')
            data = pmu.get('DATA')
            if tics is None or data is None:
                continue
            # Validate both fields BEFORE appending so that t_list and s_list
            # stay length-matched even when one PMU element has a malformed
            # value (e.g. non-numeric DATA). Negative TIME_TICS values are
            # rejected: the MDH clock is monotonic and unsigned, and a
            # negative value would propagate as a negative timestamp into
            # samples_per_second.
            try:
                t_val = int(tics)
                s_val = float(data)
            except ValueError:
                continue
            if t_val < 0:
                continue
            t_list.append(t_val)
            s_list.append(s_val)
        if not t_list:
            if verbose:
                print('XA: stream %s has no TIME_TICS samples; skipping' % stream_type)
            continue
        # Sort samples by tic. Document order matches scanner emission order
        # in practice, but a stream with reordered <PMU> entries would yield
        # negative diffs, breaking _avg_dt and the modal-tic warning.
        order = np.argsort(t_list, kind='stable')
        t_tics = np.asarray(t_list, dtype=int)[order]
        s = np.asarray(s_list, dtype=float)[order]
        t = t_tics.astype(float) * MDH_TIC_MS
        # As-acquired sample interval: total span / (N-1) intervals,
        # equivalent to deriving the rate from explicit log start / stop
        # timestamps. PULS is nominally 5 ms (200 Hz); RESP 20 ms (50 Hz);
        # ECG 2.5 ms (400 Hz). For modern Siemens hardware the inferred
        # value matches the nominal exactly; a deviation indicates either
        # a dropped sample or a non-standard recording rate.
        dt = _avg_dt(t)
        # Sanity check: compare the span-based dt to the modal inter-sample
        # tic gap. For clean data these agree to within rounding. A
        # significant disagreement implies dropped or duplicated samples,
        # in which case dt (and the resulting samples_per_second) is
        # biased and downstream NaN-filling against it will be misaligned.
        # Surface this as a warning rather than silently correcting, so
        # the user can decide how to handle the recording.
        # `np.unique` is used instead of `np.bincount` because bincount
        # allocates O(max(diff)) memory and a single very-large gap (or a
        # malicious payload) would balloon it to gigabytes.
        if len(t_tics) >= 2:
            diffs = np.diff(t_tics)
            positive_diffs = diffs[diffs > 0]
            if positive_diffs.size:
                values, counts = np.unique(positive_diffs, return_counts=True)
                modal_tic = int(values[counts.argmax()])
                modal_dt = modal_tic * MDH_TIC_MS
                if modal_dt > 0 and abs(dt - modal_dt) / modal_dt > 0.01:
                    print('WARNING: XA stream %s sample rate inferred from '
                          'span/(N-1) is %.4f ms, but modal inter-sample gap '
                          'is %.4f ms. This usually means one or more samples '
                          'were dropped; downstream timing may be off.'
                          % (stream_type, dt, modal_dt))
        if verbose:
            fs = 1000.0 / dt if dt > 0 else float('nan')
            print('XA: stream %s, %d samples, dt %.4f ms (%.3f Hz)'
                  % (stream_type, len(t), dt, fs))
        yield stream_type, t, s, dt


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

        # Data lines have the form "<tag> = <value>" or "<time> <name/channel> <value>"
        # Data lines with trigger have a forth column with "PULS_TRIGGER", which we can ignore
        if len(parts) >= 3:

            p1, p2, p3 = parts[:3]

            if any([s in p2 for s in ('PULS', 'RESP', 'EXT', 'ECG')]):
                # The times are in multiples of 2.5 ms
                t_list.append(2.5 * int(p1))
                # in principle, these will also be int, but let's make them
                #  float to support more general signals:
                s_list.append(float(p3))

            elif 'UUID' in p1:
                uuid = p3

            elif 'ScanDate' in p1:
                scan_date = p3

            elif 'LogDataType' in p1:
                waveform_name = p3

            elif 'SampleTime' in p1:
                # 'SampleTime' is in units of 2.5 ms
                # 'dt' is in ms:
                dt = 2.5 * float(p3)

        # Detect the scanner trigger by going through the ACQUISITION_INFO
        # and detecting when a new volume has been started:
        if waveform_name == 'ACQUISITION_INFO':
            if len(parts) == 5:
                if not header_read:
                    # The first line with 5 elements contains the header for the columns of data
                    header_read = True
                elif parts[4] == '0':
                    # (we only save trigger data for the first echo: the other echoes are the same)
                    # The times are in multiples of 2.5 ms
                    t_list.append(2.5 * int(parts[2]))
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
    return uuid, waveform_name, np.array(t_list), np.array(s_list), dt


def get_acq_time(physio_file):
    """
    Function to get the acquisition time of a '.log' file
    Inputs:
    ------
    physio_file : str or Path
        Name of the physio file

    Returns:
    -------
    acq_time : float or None
        Time of the beginning of the physiological acquisition
    """
    with open(physio_file,'r') as f:
        for line in f:
            if line.startswith('ScanDate'):
                acq_date_time = line.rsplit()[-1]
                break
    if acq_date_time:
        acq_time = float(acq_date_time.split('_')[-1])
    else:
        acq_time = None
    return acq_time


def to_physiosignal(uuid, waveform_name, t, s, dt):

    physio_label = ''
    t_first_trigger = None

    # specify suffix:
    if 'PULS' in waveform_name:
        physio_label = 'cardiac'

    elif 'RESP' in waveform_name:
        physio_label = 'respiratory'

    elif 'EXT' in waveform_name:
        physio_label = 'external_trigger'

    elif 'ECG' in waveform_name:
        physio_label = 'ecg'

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
                uuid=uuid,
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
            raise FileNotFoundError('{i} file not found'.format(i=infile))

    # make sure output directory exists:
    odir = os.path.dirname(args.bidsprefix)
    if odir:
        if not os.path.exists(odir):
            os.makedirs(odir)

    physio_data = dcm2bids(args.infiles, verbose=args.verbose)
    if physio_data.labels():
        physio_data.save_to_bids_with_trigger(args.bidsprefix)


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()

