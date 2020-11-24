"""   Tests for the module "session2bids.py"

Because the functionality of extracting BIDS info from a session and
getting physio data from a file, etc. is not the scope of the
module, I'm mocking a lot of the functions and I just test the code
specific to the module

Also, this way allows us to run the tests without a dataset.
"""

from datetime import datetime, timedelta
from os.path import join as pjoin
import random
import time

from bids import BIDSLayout
import pandas as pd
import nibabel as nib
import numpy as np
import pytest

from bidsphysio.session import session2bids as s2b
from .utils import TESTS_DATA_PATH, file_md5sum

NOW = datetime.now()
# physio clock delay w.r.t. the scanner clock:
DELAY = random.uniform(0, 10)
TIME_BETWEEN_RUNS = random.uniform(95, 105)
N_RUNS = random.randint(3, 5)
# We'll add some jitter to the beginning of the physio recordings:
JITTER_FACTOR = random.uniform(0.01, 0.1)
TR = random.uniform(0.5, 3)
N_VOLS = random.randint(1, 100)
SECS_IN_DAY = 24 * 60 * 60


class MockBidsFile(object):
    """ Class that mocks a BIDSFile, so we can mock the methods
    without the need to include a full dataset in the tests.
    """
    def __init__(self, path=''):
        self.path = path

    @staticmethod
    def get_metadata():
        """ Returns a dictionary with the needed keys
        """
        return {
            'RepetitionTime': TR,
            'AcquisitionTime': str(timedelta(seconds=random.random() * SECS_IN_DAY))
        }


def mock_layout_init(*args, **kwargs):
    """ Mocks the __init__ method of BIDSLayout
    This way we don't run the verifications normally run at init
    """
    pass


def mock_layout_get(*args, **kwargs):
    """ Mocks the BIDSLayout.get method to get the files
    It returns a list of MockBidsFiles
    """
    # We add one extra file ("N_RUNS + 1") so that we can have a BIDS
    # file that doesn't exist in the "scan_df" dataframe and test a
    # special case in "determine_scan_durations"
    return [MockBidsFile(path='scan_{}'.format(i)) for i in range(N_RUNS + 1)]


def mock_nibabel_load(*args, **kwargs):
    """ Mock the method nibabel.load so that it returns a np.array
    of shape [1, 1, 1, N_VOLS]:
    """
    return np.array([0]*N_VOLS).reshape([1, 1, 1, N_VOLS])


class MockPhysioData(object):
    """ Class that mocks a PhysioData class, so we can mock the class
    methods without the need to include a full dataset in the tests.
    """
    def __init__(self, path=''):
        self.path = path
        self.scanner_onset = JITTER_FACTOR * random.random()
        self.signals = []

    def get_scanner_onset(self):
        return self.scanner_onset

    @staticmethod
    def save_to_bids_with_trigger(path):
        pass

@pytest.fixture
def my_mocks(monkeypatch):
    """ Applies the monkeypatches for BIDSLayout.__init__ and .get,
    as well as for nibabel.load
    """
    monkeypatch.setattr(BIDSLayout, "__init__", mock_layout_init)
    monkeypatch.setattr(BIDSLayout, "get", mock_layout_get)
    monkeypatch.setattr(nib, "load", mock_nibabel_load)


@pytest.fixture
def myphysiodf(scope="module"):
    """   Create a DataFrame with simulated physio content.
    The order of the runs in the dataframe is randomized.
    """
    physio_df = pd.DataFrame(
        {
            'filename': ['foo_{}'.format(i) for i in range(N_RUNS)],
            'onset': [
                i * TIME_BETWEEN_RUNS
                + DELAY
                + JITTER_FACTOR * random.random()
                for i in range(N_RUNS)
            ],
        }
    )
    # randomize order of the dataframe:
    physio_df = physio_df.sample(frac=1).reset_index(drop=True)
    return physio_df


@pytest.fixture
def myscandf(scope="module"):
    """   Create a DataFrame with simulated scan content
    """
    return pd.DataFrame(
        {
            'filename': ['scan_{}'.format(i) for i in range(N_RUNS)],
            'onset': [i * TIME_BETWEEN_RUNS for i in range(N_RUNS)],
        }
    )


def test_compress_physio(tmpdir):
    """ Tests for "compress_physio"
    We want to ensure reproducibility
    """

    physio_file = pjoin(TESTS_DATA_PATH, 'sample.acq')
    out_prefix = str(tmpdir.join("precious"))

    def get_physio_acq_time(file):
        """ Pretend we run get_physio_acq_time, but just return a
        fix date.
        This allows us to run the test without the bioread dependency
        """
        return NOW

    args = [
        physio_file,
        out_prefix,
        get_physio_acq_time,
        True
    ]
    tarball = s2b.compress_physio(*args)
    md5 = file_md5sum(tarball)
    assert tarball

    # When overwrite is set to False, make sure it doesn't overwrite
    args[-1] = False
    assert s2b.compress_physio(*args) is None

    # reset overwrite
    args[-1] = True

    # make sure when run on the same file at a later time, we get
    # identical results
    time.sleep(1.1)  # need to guarantee change of time
    tarball_ = s2b.compress_physio(*args)
    md5_ = file_md5sum(tarball_)
    assert tarball == tarball_
    assert md5 == md5_


def test_synchronize_onsets(
        myphysiodf,
        myscandf,
        capfd
):
    """    Tests for the call to "synchronize_onsets"
    """
    out_df = s2b.synchronize_onsets(myphysiodf, myscandf)
    # capture the output and make sure estimated delay is close to
    # "DELAY":
    for t in capfd.readouterr().out.split():
        try:
            estimated_delay = float(t)
        except ValueError:
            pass
    assert estimated_delay == pytest.approx(DELAY, abs=JITTER_FACTOR)

    # make sure out_df has a "scan_filename" with the name of the
    # scan filenames:
    for i in range(N_RUNS):
        physio_name = 'foo_{}'.format(i)
        scan_fname = out_df.scan_fname[out_df.filename == physio_name].to_string(index=False)
        # for some reason, ".to_string" adds a space before the
        # string, so split() to remove it
        assert scan_fname.split()[0] == 'scan_{}'.format(i)


def test_plot_sync(
        myphysiodf,
        myscandf,
):
    """   Tests for "plot_sync"
    """
    # if physio data has not been synchronized yet, get an error:
    with pytest.raises(RuntimeError) as e_info:
        s2b.plot_sync(myscandf, myphysiodf)
    assert str(e_info.value) == 'The physio data has not been synchronized yet.'

    # add a dummy 'phys_onset' to scan dataframe, and 'duration' to
    # both, so it looks like we did run "synchronize_onsets":
    myscandf['phys_onset'] = [i for i in range(N_RUNS)]
    myscandf['duration'] = myphysiodf['duration'] = [0.9*TIME_BETWEEN_RUNS] * N_RUNS
    myfig, myaxes = s2b.plot_sync(myscandf, myphysiodf)
    assert myfig
    assert len(myaxes) == 2


def test_determine_scan_durations(
        myscandf,
        my_mocks,
        capfd
):
    """   Tests for "determine_scan_durations"
    """

    layout = BIDSLayout()
    subject = '01'
    session = None

    mynewscandf = s2b.determine_scan_durations(layout, myscandf, subject, session)

    # make sure we skip files that are in the 'layout' but not in
    # 'myscandf' (that will be the file 'scan_X', with X=N_RUNS):
    out = capfd.readouterr().out
    assert ('Skipping' in out and str(N_RUNS) in out)

    # make sure mynewfscandf has a "duration" column with the
    # correct duration:
    for dur in mynewscandf['duration']:
        assert dur == pytest.approx(TR*N_VOLS)


def test_load_scan_data(
        my_mocks,
):
    """ Tests for "load_scan_data"
    """

    layout = BIDSLayout()
    subject = '01'
    session = None

    scandf = s2b.load_scan_data(layout, subject, session)

    # make sure scandf has the columns: "acq_time", "duration" and
    # "onset":
    for col_name in ['acq_time', 'duration', 'onset']:
        assert col_name in scandf.columns


def test_convert_session(
        monkeypatch,
        my_mocks,
):
    """ Tests for "load_scan_data"
    """

    def mock_compress_physio(*args, **kwargs):
        pass

    # apply the monkeypatch for "compress_physio":
    monkeypatch.setattr(s2b, "compress_physio", mock_compress_physio)

    def _get_physio_data(fname):
        """ Function to return a MockPhysioData object
        """
        return MockPhysioData(path=fname)

    def _get_physio_acq_time(fname):
        """ Mock a function to retrieve the physio acquisition time:
        given the file name, it will be run number x TIME_BETWEEN_RUNS
        """
        try:
            run_no = int(fname.split('_')[-1])
        except ValueError:
            raise FileNotFoundError('This is not a valid filename')
        return timedelta(seconds=run_no * TIME_BETWEEN_RUNS)

    # run convert_session:
    phys_files = ['phys_{}'.format(i) for i in range(N_RUNS)]
    bids_dir = 'foo'
    sub = '01'
    s2b.convert_session(phys_files, bids_dir, sub,
                        get_physio_data=_get_physio_data,
                        get_physio_acq_time=_get_physio_acq_time,
                        outdir='bar', overwrite=True)
