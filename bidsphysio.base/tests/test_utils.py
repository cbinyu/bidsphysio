"""   Tests for the module "utils.py"   """

from shutil import (copyfile,
                    copyfileobj)
import gzip

import pytest

from bidsphysio.base.utils import (check_bidsphysio_outputs,
                                   get_physio_TRs)
from .utils import (TESTS_DATA_PATH,
                    EXPECTED_TR)

###  Globals   ###
CHECK_OUTPUTS_FILE_PREFIX = 'test_nan_TR'

def test_check_bidsphysio_outputs(tmpdir):
    """
    Tests for check_bidsphysio_outputs
    """
    json_files = list(TESTS_DATA_PATH.glob(CHECK_OUTPUTS_FILE_PREFIX + '*.json'))
    data_files = list(TESTS_DATA_PATH.glob(CHECK_OUTPUTS_FILE_PREFIX + '*.tsv.gz'))
    # we only expect one file for each
    assert len(json_files) == len(data_files) == 1

    # take first match and remove '_physio' from end:
    j_file = json_files[0].stem.split('_physio')[-2]
    true_bids_prefix = TESTS_DATA_PATH / j_file

    # 1) Check that when files don't match, the function fails
    # (The function has its own "assert" lines)
    with pytest.raises(AssertionError) as e_info:
        check_bidsphysio_outputs(true_bids_prefix,
                                 ['cardiac'],
                                 TESTS_DATA_PATH / 'foo')

    # Check that when we compare some files against themselves, it passes.
    # The expectedDataFiles (from the third argument) are supposed to be
    # unzipped, so make a copy to a temp folder and unzip:
    f = json_files[0]
    copyfile(f, tmpdir / f.name)
    f = data_files[0]
    with gzip.open(f, 'r') as f_in, \
            open(tmpdir / f.name.split('.gz')[0], 'wb') as f_out:
        copyfileobj(f_in, f_out)

    check_bidsphysio_outputs(true_bids_prefix,
                             ['external_trigger'],
                             tmpdir / f.name.split('.tsv.gz')[0])


def test_get_physio_TRs():
    """
    Check that we get the expected result.
    We'll use a file that has NaN's, and it still should work
    """
    TRs = get_physio_TRs(TESTS_DATA_PATH / 'test_nan_TR')
    assert isinstance(TRs, list)
    assert TRs == [EXPECTED_TR]

