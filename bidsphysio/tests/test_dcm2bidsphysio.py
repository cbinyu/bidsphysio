#from bidsphysio.dcm2bidsphysio import (main as runner,
#                                       plug_missing_data)
import bidsphysio.dcm2bidsphysio as d2bp
from bidsphysio.bidsphysio import (physiosignal,
                                   physiodata)
from .utils import TESTS_DATA_PATH

import pytest
import sys
from pathlib import Path

'''
TO-DO:

- Set the expected signals (and maybe file contents) from the
  tests data in a separate file , with the data, which the test
  functions will read. That way, if we change the tests datasets,
  we will change the expected values right there, rather than
  changing the tests in this file

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
        print('mock_dcm2bids called')
        return

    monkeypatch.setattr(d2bp, "dcm2bids", mock_dcm2bids)



###   Tests   ###

def test_main_args(
        monkeypatch,
        tmpdir,
        mock_dcm2bidsphysio,
        capfd
):
    '''
    Tests for "main"
    Just check the arguments, etc. We'll test the call to dcm2bids in a
    separated function
    '''
    # 1) "infile" doesn't exist:
    infile = str(tmpdir / 'boo.dcm')
    args = (
        'dcm2bidsphysio -i {infile} -b {bp}'.format(
            infile=infile,
            bp=tmpdir / 'mydir' / 'foo'
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv',args)
    with pytest.raises(FileNotFoundError) as e_info:
        d2bp.main()
        assert str(e_info.value).endswith(' file not found')
        assert str(e_info.value).split(' file not found')[0] == infile

    # 2) "infile" does exist, but output directory doesn't exist:
    #    The output directory should be created and the "dcm2bids" function should be called
    args[ args.index('-i')+1 ] = str(TESTS_DATA_PATH / 'samplePhysio+02+physio_test+00001.dcm')
    monkeypatch.setattr(sys, 'argv',args)
    d2bp.main()
    assert (tmpdir / 'mydir').exists()
    assert capfd.readouterr().out == 'mock_dcm2bids called\n'

def test_dcm2bids(
        monkeypatch,
        tmpdir,
        capfd
):
    '''
    Tests for the call to "dcm2bids"
    We will call it by calling "main" to make sure the output directory
    is created, etc.
    '''
    import json

    infile = str(TESTS_DATA_PATH / 'samplePhysio+02+physio_test+00001.dcm')
    outbids = str(tmpdir / 'mydir' / 'bids')

    args = (
        'dcm2bidsphysio -i {infile} -b {bp}'.format(
            infile=str(infile),
            bp=outbids
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv',args)

    # call "main" (which will create the output dir and call "dcm2bids"):
    d2bp.main()

    # make sure we are not calling the mock_dcm2bidds, but the real one:
    assert capfd.readouterr().out != 'mock_dcm2bids called\n'

    # Check that we have as many signals as expected
    json_files = sorted(Path(tmpdir / 'mydir').glob('*.json'))
    assert len(json_files)==2
    for s in ['respiratory', 'cardiac']:
        expectedFileName = Path(outbids).name + '_recording-' + s + '_physio.json'
        jsonFile = tmpdir / 'mydir' / expectedFileName
        assert jsonFile in json_files

        # check content of the json file:
        with open(jsonFile) as f:
            d = json.load(f)
            assert d['Columns'] == [ s, 'trigger']
            assert d['StartTime'] == -1.632
            if s == 'respiratory':
                assert d['SamplingFrequency'] == 125
            elif s == 'cardiac':
                assert d['SamplingFrequency'] == 500
