#from bidsphysio.dcm2bidsphysio import (main as runner,
#                                       plug_missing_data)
import bidsphysio.dcm2bidsphysio as d2bp
from bidsphysio.bidsphysio import (physiosignal,
                                   physiodata)
from .utils import TESTS_DATA_PATH

import pytest
import sys


'''
TO-DO:

- Tests for "main":
    * test arguments
    * test mkdir

- Tests "dcm2bids":
  Using the real file, check the output matches what we expect:
    * check that the file names are what we expect
    * check the content of the files

- Tests for "plug_missing_data"
  Create my own t, s, etc.
    * check the output

- Test "parse_log":
   * we need to get the input somehow
   * check the returns of the function
   * Maybe check the errors?
   * 
'''

###   Fixtures   ###

@pytest.fixture
def mock_dcm2bidsphysio(monkeypatch):
    """
    Pretend we run dcm2bids, but do nothing
    This allows us to test the correct behavior of the runner without
       actually running anything: just the instructions in the runner
       before the call to dcm2bids
    """
    def mock_dcm2bids(*args, **kwargs):
        return

    monkeypatch.setattr(d2bp, "dcm2bids", mock_dcm2bids)



###   Tests   ###

def test_main_args(
        monkeypatch,
        tmpdir,
        mock_dcm2bidsphysio
):
    '''
    Tests for "main"
    Just check the arguments, etc. We'll test the call to dcm2bids in a
    separated function
    '''
    # 1) "infile" doesn't exist:
    infile = tmpdir / 'boo.dcm'
    args = (
        'dcm2bidsphysio -i {infile} -b {bp}'.format(
            infile=str(infile),
            bp=tmpdir / 'mydir' / 'foo'
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv',args)
    with pytest.raises(FileNotFoundError) as e_info:
        d2bp.main()
        assert str(e_info.value).endswith(' file not found')
        assert str(e_info.value).split(' file not found')[0] == str(infile)

    # 2) "infile" does exist, but output directory doesn't exist:
    #    The output directory should be created and the "dcm2bids" function should be called
    args[ args.index('-i')+1 ] = str(TESTS_DATA_PATH / 'samplePhysio+02+physio_test+00001.dcm')
    monkeypatch.setattr(sys, 'argv',args)
    d2bp.main()

    assert (tmpdir / 'mydir').exists()
    #assert False
    
