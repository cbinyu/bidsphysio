"""
This Python module allows you to synchronize a whole session worth
of physiological data to the session images, so the physiological
files will be matched to the corresponding image files and named
accordingly.

The module is file type agnostic, so it can be used for AcqKnowledge
files, Eye-link files (.edf), etc. The module relies on the calling
function extracting the timing of the onsets of the different
scanner runs. The module will then find the best time delay between
the physiological files and the imaging files.

Methods related to saving the physiological files (either as BIDS or
just compressed) are part of this module too, since the call can be
file type independent.

Based on Taylor Salo's conversion.py:
https://github.com/tsalo/phys2bids/blob/eb46a71d7881c4dcd0c5e70469d88cb99bb01f1c/phys2bids/conversion.py
"""
import os
import os.path as op
import tarfile
from tempfile import TemporaryDirectory

from bids import BIDSLayout
import pandas as pd
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt

from bidsphysio.base.bidsphysio import PhysioData


def compress_physio(physio_file, out_prefix, get_physio_acq_time, overwrite):
    """Archives a physiological file into a tarball

    Also it tries to do it reproducibly, so it takes the date for
    the physio_file and targets tarball based on the acquisition time

    Parameters
    ----------
    physio_file : str
      original physiological file
    out_prefix : str
      output path prefix, including the portion of the output file
      name before .*.tgz suffix
    get_physio_acq_time : function
        Function to get the acquisition time of a physiological file
        (e.g., read_file(file).earliest_marker_created_at, from bioread)
    overwrite : bool
      Overwrite existing tarfiles

    Returns
    -------
    filename : str
      Result tarball
    """

    fname, physio_extension = op.splitext(physio_file)
    outtar = out_prefix + physio_extension + '.tgz'

    if op.exists(outtar) and not overwrite:
        print("File {} already exists, will not overwrite".format(outtar))
        return
    # tarfile encodes current time.time inside, making those non-
    # reproducible, so we should use the earliest_marker_created_at
    # of the acq_file

    # return physio file acquisition time as a float (like in
    # the method time.time()):
    acq_time = get_physio_acq_time(physio_file).timestamp()

    def _assign_acq_time(ti):
        # Reset the time of the TarInfo object:
        ti.mtime = acq_time
        return ti

    # poor man mocking since can't rely on having mock
    try:
        import time
        _old_time = time.time
        time.time = lambda: acq_time
        if op.lexists(outtar):
            os.unlink(outtar)
        with tarfile.open(outtar, 'w:gz', dereference=True) as tar:
            tmpdir = TemporaryDirectory()
            outfile = op.join(tmpdir.name, op.basename(physio_file))
            if not op.islink(outfile):
                os.symlink(op.realpath(physio_file), outfile)
            # place into archive stripping any lead directories and
            # adding the one corresponding to prefix
            tar.add(outfile,
                    arcname=op.join(op.basename(out_prefix),
                                    op.basename(outfile)),
                    recursive=False,
                    filter=_assign_acq_time)
    finally:
        time.time = _old_time

    return outtar


def synchronize_onsets(phys_df, scan_df):
    """Find matching scans and physio trigger periods from separate DataFrames,
    using time differences within each DataFrame.

    There can be fewer physios than scans (task failed to trigger physio)
    or fewer scans than physios (aborted scans are not retained in BIDS dataset).

    Onsets are in seconds. The baseline (i.e., absolute timing) doesn't matter.
    Relative timing is all that matters.

    Parameters
    ----------
    phys_df : pandas.DataFrame
        DataFrame with onsets of physio trigger periods, in seconds. The
        baseline does not matter, so it is reasonable for the onsets to start
        with zero. The following columns are required: 'onset', 'index'.
    scan_df : pandas.DataFrame
        DataFrame with onsets and names of functional scans from BIDS dataset,
        in seconds. The baseline does not matter, so it is reasonable for the
        onsets to start with zero. The following columns are required: 'onset',
        'duration'.

    Returns
    -------
    phys_df : pandas.DataFrame
        Updated scan DataFrame, now with columns for predicted physio onsets in
        seconds and in indices of the physio trigger channel, as well as scan
        duration in units of the physio trigger channel.
    """
    phys_df = phys_df.sort_values(by=['onset'])
    scan_df = scan_df.sort_values(by=['onset'])
    scan_df.index = range(scan_df.shape[0])   # overwrite the run number

    # Get difference between each physio trigger onset and each scan onset
    onset_diffs = np.zeros((scan_df.shape[0], phys_df.shape[0]))
    for i, i_scan in scan_df.iterrows():
        for j, j_phys in phys_df.iterrows():
            onset_diff = j_phys['onset'] - i_scan['onset']
            onset_diffs[i, j] = onset_diff

    # Find the delay that gives the smallest difference between scan onsets
    # and physio onsets
    selected = (None, None)
    thresh = 1000
    for i_scan in range(onset_diffs.shape[0]):
        for j_phys in range(onset_diffs.shape[1]):
            test_offset = onset_diffs[i_scan, j_phys]
            diffs_from_phys_onset = onset_diffs - test_offset
            diffs_from_abs = np.abs(diffs_from_phys_onset)
            min_diff_row_idx = np.argmin(diffs_from_abs, axis=0)
            min_diff_col_idx = np.arange(len(min_diff_row_idx))
            min_diffs = diffs_from_abs[min_diff_row_idx, min_diff_col_idx]
            min_diff_sum = np.sum(min_diffs)
            if min_diff_sum < thresh:
                selected = (i_scan, j_phys)
                thresh = min_diff_sum

    offset = onset_diffs[selected[0], selected[1]]

    # Isolate close, but negative relative onsets, to ensure scan onsets are
    # always before or at physio triggers.
    close_thresh = 2  # threshold for "close" onsets, in seconds
    diffs_from_phys_onset = onset_diffs - offset
    min_diff_row_idx = np.argmin(np.abs(diffs_from_phys_onset), axis=0)
    min_diff_col_idx = np.arange(len(min_diff_row_idx))
    min_diffs = diffs_from_phys_onset[min_diff_row_idx, min_diff_col_idx]
    min_diffs_tmp = min_diffs[abs(min_diffs) <= close_thresh]
    min_val = min(min_diffs_tmp)
    min_diffs += min_val
    offset += min_val
    print('Scan DF should be adjusted forward by {} seconds'.format(offset))

    # Find the filename of the scan the 'onset' of which is close to
    # the 'physio_onset' (if none is close enough, enter None):
    scan_df['phys_onset'] = scan_df['onset'] + offset
    scan_fnames = []
    for p_on in phys_df['onset']:
        corresponding_scan = scan_df.loc[
            abs(scan_df['phys_onset'] - p_on) < close_thresh,
            'filename'
        ]
        if len(corresponding_scan) == 0:
            scan_fnames.append(None)
        else:
            # append the scan filename
            scan_fnames.append(corresponding_scan.iloc[0])

    # Add the scan filenames to the phys_df:
    phys_df['scan_fname'] = [sf for sf in scan_fnames]
    return phys_df


def plot_sync(scan_df, physio_df):
    """
    Plot unsynchronized and synchonized scan and physio onsets and durations.
    """

    # You need a scan_df already synchronized (so it has the 'phys_onset':
    if 'phys_onset' not in scan_df.columns:
        raise RuntimeError('The physio data has not been synchronized yet.')

    fig, axes = plt.subplots(nrows=2, figsize=(20, 6), sharex=True)

    # get max value rounded to nearest 1000
    max_ = int(1000 * np.ceil(max((
        physio_df['onset'].max(),
        scan_df['onset'].max(),
        scan_df['phys_onset'].max())) / 1000))
    scalar = 10
    x = np.linspace(0, max_, (max_*scalar)+1)

    # first the raw version
    physio_timeseries = np.zeros(x.shape)
    func_timeseries = np.zeros(x.shape)
    for i, row in scan_df.iterrows():
        func_timeseries[
            int(row['onset'] * scalar):int((row['onset'] + row['duration']) * scalar)
        ] = 1

    for i, row in physio_df.iterrows():
        physio_timeseries[
            int(row['onset'] * scalar):int((row['onset'] + row['duration']) * scalar)
        ] = 0.5

    axes[0].fill_between(x, func_timeseries, where=func_timeseries >= 0,
                         interpolate=True, color='red', alpha=0.3,
                         label='Functional scans')
    axes[0].fill_between(x, physio_timeseries, where=physio_timeseries >= 0,
                         interpolate=True, color='blue', alpha=0.3,
                         label='Physio triggers')

    # now the adjusted version
    physio_timeseries = np.zeros(x.shape)
    func_timeseries = np.zeros(x.shape)
    for i, row in scan_df.iterrows():
        func_timeseries[
            int(row['phys_onset'] * scalar):int((row['phys_onset'] + row['duration']) * scalar)
        ] = 1

    for i, row in physio_df.iterrows():
        physio_timeseries[
            int(row['onset'] * scalar):int((row['onset'] + row['duration']) * scalar)
        ] = 0.5

    axes[1].fill_between(x, func_timeseries, where=func_timeseries >= 0,
                         interpolate=True, color='red', alpha=0.3,
                         label='Functional scans')
    axes[1].fill_between(x, physio_timeseries, where=physio_timeseries >= 0,
                         interpolate=True, color='blue', alpha=0.3,
                         label='Physio triggers')

    axes[0].set_xlim((min(x), max(x)))
    axes[0].set_ylim((0, None))
    axes[1].set_xlabel('Time (s)')
    axes[0].legend()
    return fig, axes


def determine_scan_durations(layout, scan_df, sub, ses):
    """Extract scan durations by loading fMRI files/metadata and
    multiplying TR by number of volumes. This can be used to determine the
    endpoints for the physio files.

    Parameters
    ----------
    layout : bids.layout.BIDSLayout
        Dataset layout. Used to identify functional scans and load them to
        determine scan durations.
    scan_df : pandas.DataFrame
        Scans DataFrame containing functional scan filenames and onset times.
    sub : str
        Subject ID
    ses : str or None, optional
        Session ID. If None, then no session.

    Returns
    -------
    scan_df : pandas.DataFrame
        Updated DataFrame with new "duration" column. Calculated durations are
        in seconds.
    """
    # TODO: parse entities in func files for searches instead of larger search.
    func_files = layout.get(datatype='func', suffix='bold',
                            extension=['nii.gz', 'nii'],
                            subject=sub, session=ses)
    scan_df['duration'] = None
    for func_file in func_files:
        filename = func_file.path
        if filename in scan_df['filename'].values:
            n_vols = nib.load(func_file.path).shape[3]
            tr = func_file.get_metadata()['RepetitionTime']
            duration = n_vols * tr
            scan_df.loc[scan_df['filename'] == filename, 'duration'] = duration
        else:
            print('Skipping {}'.format(filename))
    return scan_df


def load_scan_data(layout, sub, ses):
    """Extract subject- and session-specific scan onsets and durations from
    BIDSLayout.
    Start times are relative to the start of the first run.
    Times are in seconds.

    Parameters
    ----------
    layout : BIDSLayout
        Dataset layout. Used to identify functional scans and load them to
        determine scan durations.
    sub : str
        Subject ID
    ses : str
        Session ID

    Returns
    -------
    df : pandas.DataFrame
        DataFrame with the following columns: 'filename', 'acq_time',
        'duration', 'onset'.
    """
    # This is the strategy we'll use in the future. Commented out for now.
    # scans_file = layout.get(extension='tsv', suffix='scans', subject=sub, session=ses)
    # df = pd.read_table(scans_file)

    # Collect acquisition times:
    # NOTE: Will be replaced with scans file if heudiconv makes the change
    img_files = layout.get(datatype='func', suffix='bold',
                           extension=['nii.gz', 'nii'],
                           subject=sub, session=ses)
    df = pd.DataFrame(
        {
            'filename': [f.path for f in img_files],
            'acq_time': [f.get_metadata()['AcquisitionTime'] for f in img_files],
        }
    )

    # Get "first" scan from multi-file acquisitions
    df['acq_time'] = pd.to_datetime(df['acq_time'])
    df = df.sort_values(by='acq_time')
    df = df.drop_duplicates(subset='filename', keep='first', ignore_index=True)

    # Now back to general-purpose code
    df = determine_scan_durations(layout, df, sub=sub, ses=ses)
    df = df.dropna(subset=['duration'])  # limit to relevant scans

    # Convert scan times to relative onsets (first scan is at 0 seconds)
    df['acq_time'] = pd.to_datetime(df['acq_time'])
    df = df.sort_values(by='acq_time')
    df['onset'] = (df['acq_time'] - df['acq_time'].min())
    df['onset'] = df['onset'].dt.total_seconds()
    return df


def convert_session(physio_files, bids_dir, sub, ses=None,
                    get_physio_data=None,
                    get_physio_acq_time=None,
                    outdir=None, overwrite=False):
    """Function to save the physiology data in a given folder as BIDS,
    matching the filenames from the study imaging files

    Parameters
    ----------
    physio_files : list of str
        List of paths of the original physio files
    bids_dir : str
        Path to BIDS dataset
    sub : str
        Subject ID. Used to search the BIDS dataset for relevant scans.
    ses : str or None, optional
        Session ID. Used to search the BIDS dataset for relevant scans in
        longitudinal studies. Default is None.
    get_physio_data : function
        Function to get physio data from a file to "PhysioData" class
        (e.g., acq2bids)
    get_physio_acq_time : function
        Function to get the acquisition time of a physiological file
        (e.g., read_file(file).earliest_marker_created_at, from bioread)
    outdir : str
        Path to a BIDS folder where we want to store the physio data.
        Default: bids_dir
    overwrite : bool
      Overwrite existing tarfiles
    """

    # Default out_dir is bids_dir:
    outdir = outdir or bids_dir

    file_times = [get_physio_acq_time(f) for f in physio_files]
    # relative to the first one:
    rel_file_times = [(f - min(file_times)).total_seconds() for f in file_times]

    physio_data = [get_physio_data(f) for f in physio_files]

    # It might happen that different log files correspond to the same run. To
    # group all the PhysioData corresponding to the same run into a single
    # one, we check the UUID.
    # Note: use set comprehension to keep just unique elements. Then, make
    # it a list to be able to use the "index" method.
    uuids = list({s.uuid for d in physio_data for s in d.signals if s.uuid})
    if len(uuids):
        # if there are no s.uuid (they are all None), uuids will be an empty
        # list, and we don't need to run the following
        grouped_physio_data = [PhysioData()] * len(uuids)
        for d in physio_data:
            for s in d.signals:
                idx = uuids.index(s.uuid)
                grouped_physio_data[idx].append_signal(s)
        physio_data = grouped_physio_data

    onsets_in_sec = [
        p.get_scanner_onset() + rt for p, rt in zip(physio_data, rel_file_times)
    ]
    physio_df = pd.DataFrame(
        {
            'onset': onsets_in_sec,
            'data': physio_data,
            'filename': physio_files
        }
    )

    # Now, for the scanner timing:
    layout = BIDSLayout(bids_dir)
    df = load_scan_data(layout, sub=sub, ses=ses)

    out_df = synchronize_onsets(physio_df, df)

    sourcedir = op.join(outdir, 'sourcedata')
    if not op.isdir(sourcedir):
        os.makedirs(sourcedir)
    sub_ses_dir = op.join('sub-' + sub, ('ses-' + str(ses)) if ses else '')

    for (phys_file, phys_data, scan_file) in zip(out_df['filename'], out_df['data'], out_df['scan_fname']):
        if scan_file:
            prefix = op.join(sub_ses_dir, scan_file.split('.nii')[0])
            outdir_ = op.join(outdir, op.dirname(prefix))
            if not op.isdir(outdir_):
                os.makedirs(outdir_)
            phys_data.save_to_bids_with_trigger(op.join(outdir, prefix))
            sourcedir_ = op.join(sourcedir, op.dirname(prefix))
            if not op.isdir(sourcedir_):
                os.makedirs(sourcedir_)
            compress_physio(phys_file,
                            op.join(sourcedir_, op.basename(prefix)),
                            get_physio_acq_time,
                            overwrite=overwrite)


def convert_edf_session(physio_files, bids_dir, sub, ses=None,
                        get_physio_data=None,
                        get_event_data=None,
                        get_physio_acq_time=None,
                        outdir=None, save_eye_events=True, overwrite=False):
    """Function to save the EDF data in a given folder as BIDS physiology and events files, matching the filenames from the study imaging files
        
    Parameters
    ----------
    physio_files : list of str
        List of paths of the original physio files
    bids_dir : str
        Path to BIDS dataset
    sub : str
        Subject ID. Used to search the BIDS dataset for relevant scans.
    ses : str or None, optional
        Session ID. Used to search the BIDS dataset for relevant scans in
        longitudinal studies. Default is None.
    get_physio_data : function
        Function to get physio data from a file to "PhysioData" class
        (e.g., edf2bids)
    get_event_data : function
        Function to get event data from a file to "eventdata" class
        (e.g., edfevents2bids)
    get_physio_acq_time : function
        Function to get the acquisition time of a physiological file
        (e.g., read_file(file).earliest_marker_created_at, from bioread)
    outdir : str
        Path to a BIDS folder where we want to store the physio data.
        Default: bids_dir
    save_eye_events : bool
        Save eye motion events (fixations, saccades and blinks) as estimated by Eyelink algorithms
    overwrite : bool
        Overwrite existing tarfiles
    """
    
    # Default out_dir is bids_dir:
    outdir = outdir or bids_dir
    
    file_times = [get_physio_acq_time(f) for f in physio_files]
    # relative to the first one:
    rel_file_times = [(f - min(file_times)).total_seconds() for f in file_times]
    
    physio_data = [get_physio_data(f, saveevents) for f in physio_files]
    event_data = [get_event_data(f) for f in physio_files]
    
    onsets_in_sec = [
                     p.get_scanner_onset() + rt for p, rt in zip(physio_data, rel_file_times)
    ]
        
    physio_df = pd.DataFrame(
        {
            'onset': onsets_in_sec,
            'data': physio_data,
            'event_data' : event_data,
            'filename': physio_files
        }
    )
                     
    # Now, for the scanner timing:
    layout = BIDSLayout(bids_dir)
    df = load_scan_data(layout, sub=sub, ses=ses)
                     
    out_df = synchronize_onsets(physio_df, df)
                     
    sourcedir = op.join(outdir, 'sourcedata')
    if not op.isdir(sourcedir):
        os.makedirs(sourcedir)
    sub_ses_dir = op.join('sub-' + sub, ('ses-' + str(ses)) if ses else '')

    for (phys_file, phys_data, ev_data, scan_file) in zip(out_df['filename'], out_df['data'], out_df['event_data'], out_df['scan_fname']):
        if scan_file:
            prefix = op.join(sub_ses_dir, scan_file.split('.nii')[0])
            outdir_ = op.join(outdir, op.dirname(prefix))
            if not op.isdir(outdir_):
                os.makedirs(outdir_)
            phys_data.save_to_bids_with_trigger(eye_prefix)
            ev_data.save_events_bids_data(eye_prefix)
