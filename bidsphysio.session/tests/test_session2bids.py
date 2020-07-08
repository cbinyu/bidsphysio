'''   Tests for the module "session2bids.py"   '''

from glob import glob
import copy
import gzip
import json
from datetime import datetime
from os.path import join as pjoin
import random
import time

import pandas as pd
import numpy as np
import pytest

from bidsphysio.session import session2bids as s2b
from .utils import TESTS_DATA_PATH, file_md5sum

NOW = datetime.now()
# physio clock is delay w.r.t. the scanner clock:
DELAY = 10 * random.random()
TIME_BETWEEN_RUNS = 100
N_RUNS = 3
# We'll add some jitter in the beginning of the physio recordings:
JITTER_FACTOR = 0.1


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
    """   Create a DataFrame with simulated scan content  """
    return pd.DataFrame(
        {
            'filename': ['scan_{}'.format(i) for i in range(N_RUNS)],
            'onset': [i * TIME_BETWEEN_RUNS for i in range(N_RUNS)],
        }
    )


def test_compress_physio(tmpdir):
    """
    Tests for "compress_physio"
    We want to ensure reproducibility
    """

    physio_file = pjoin(TESTS_DATA_PATH, 'sample.acq')
    out_prefix = str(tmpdir.join("precious"))

    def get_physio_acq_time(file):
        """
        Pretend we run get_physio_acq_time, but just return a fix date
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

    # make sure when run on the same file, we get identical results
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
    # capture output and make sure estimated delay is close to "delay":
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
        # for some reason, to_string adds a space before the string, so split()
        assert scan_fname.split()[0] == 'scan_{}'.format(i)


def test_plot_sync(
        myphysiodf,
        myscandf,
):
    # if physio data has not been synchronized yet, get an error:
    with pytest.raises(RuntimeError) as e_info:
        s2b.plot_sync(myscandf, myphysiodf)
    assert str(e_info.value) == 'The physio data has not been synchronized yet.'

    # add a dummy 'phys_onset' and 'duration' to scan dataframe:
    myscandf['phys_onset'] = [i for i in range(N_RUNS)]
    myscandf['duration'] = myphysiodf['duration'] = [0.9*TIME_BETWEEN_RUNS] * N_RUNS
    myfig, myaxes = s2b.plot_sync(myscandf, myphysiodf)
    assert myfig
    assert len(myaxes) == 2
