"""
Purpose
----
To handle the conversion of a full session's worth of
AcqKnowledge files into BIDS physiological files.

It uses the "conversion.py" module of phys2bids to estimate the
delay between the scanner and physio recording computers and find
which BIDS image corresponds to which physiological recording. Then
it uses `acq2bidsphysio` to save the physiological recording in BIDS
compliant files

Usage
----
acqSession2bids.py -i <AcqKnowledge Session folder> -b <BIDS folder> -s <Subject ID>

Authors
----
Pablo Velasco, NYU Center for Brain Imaging

Dates
----
2020-06-05 PJV First version
"""

import argparse
from glob import glob
import os
import os.path as op
import tarfile
from tempfile import TemporaryDirectory

from bids import BIDSLayout
from bidsphysio import acq2bidsphysio, conversion
import bioread
import pandas as pd


def compress_acq(acq_file, out_prefix, overwrite):
    """Archives an AcqKnowledge file into a tarball

    Also it tries to do it reproducibly, so it takes the date for
    the acq_file and targets tarball based on the acquisition time

    Parameters
    ----------
    acq_file : str
      AcqKnowledge file
    out_prefix : str
      output path prefix, including the portion of the output file
      name before .acq.tgz suffix
    overwrite : bool
      Overwrite existing tarfiles

    Returns
    -------
    filename : str
      Result tarball
    """

    outtar = out_prefix + '.acq.tgz'

    if op.exists(outtar) and not overwrite:
        print("File {} already exists, will not overwrite".format(outtar))
        return
    # tarfile encodes current time.time inside, making those non-
    # reproducible, so we should use the earliest_marker_created_at
    # of the acq_file

    # return time the first marker in acq_file was created as a
    # float (like in time.time()):
    acq_time = bioread.read_file(acq_file).earliest_marker_created_at.timestamp()

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
            outfile = op.join(tmpdir.name, op.basename(acq_file))
            if not op.islink(outfile):
                os.symlink(op.realpath(acq_file), outfile)
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


def convert_physio(phys_dir, bids_dir, sub, ses=None, outdir=None, overwrite=False):
    """Function to save the physiology data in a given folder as BIDS,
    matching the filenames from the study imaging files

    Parameters
    ----------
    phys_dir: str
        Path to the folder with the raw AcqKnowledge files
    bids_dir : str
        Path to BIDS dataset
    sub : str
        Subject ID. Used to search the BIDS dataset for relevant scans.
    ses : str or None, optional
        Session ID. Used to search the BIDS dataset for relevant scans in
        longitudinal studies. Default is None.
    outdir: str
        Path to a BIDS folder where we want to store the physio data.
        Default: bids_dir
    """

    # Default out_dir is bids_dir:
    outdir = outdir or bids_dir

    physio_files = glob(op.join(phys_dir, '*.acq'))
    file_times = [bioread.read_file(f).earliest_marker_created_at for f in physio_files]
    # relative to the first one:
    rel_file_times = [f - min(file_times) for f in file_times]

    physio_df = []
    for idx, f in enumerate(physio_files):
        p_df = conversion.extract_physio_onsets(f)
        # adjust for relative file time:
        p_df['onset'] = [o + rel_file_times[idx].total_seconds() for o in p_df['onset']]
        p_df['filename'] = f
        physio_df.append(p_df)

    # Concatenate all dataframes, adding the filename as key:
    physio_df = pd.concat(physio_df, keys=range(len(physio_df)))
    physio_df.index.names = [None, 'trig_number']

    # Now, for the scanner timing:
    layout = BIDSLayout(bids_dir)
    df = conversion.load_scan_data(layout, sub=sub, ses=ses)

    out_df = conversion.synchronize_onsets(physio_df, df)

    sourcedir = op.join(outdir, 'sourcedata')
    if not op.isdir(sourcedir):
        os.makedirs(sourcedir)
    sub_ses_dir = op.join('sub-' + sub, ('ses-' + str(ses)) if ses else '')

    for (phys_file, scan_file) in zip(out_df['filename'], out_df['scan_fname']):
        if scan_file:
            prefix = op.join(sub_ses_dir, scan_file.split('.nii')[0])
            outdir_ = op.join(outdir, op.dirname(prefix))
            if not op.isdir(outdir_):
                os.makedirs(outdir_)
            acq2bidsphysio.acq2bids(phys_file, op.join(outdir, prefix))
            sourcedir_ = op.join(sourcedir, op.dirname(prefix))
            if not op.isdir(sourcedir_):
                os.makedirs(sourcedir_)
            compress_acq(phys_file,
                         op.join(sourcedir_, op.basename(prefix)),
                         overwrite=overwrite)


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

    convert_physio(
        phys_dir,
        bids_dir,
        sub=args.subject,
        overwrite=args.overwrite,
    )


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
