'''   Tests for the module "acq2bidsphysio.py"   '''

import bidsphysio.acq2bidsphysio as d2bp
from .utils import TESTS_DATA_PATH

import pytest
import sys
from pathlib import Path

'''
TO-DO:

- Write test for calculate_trigger_events

- Set the expected signals (and maybe file contents) from the
  tests data in a separate file , with the data, which the test
  functions will read. That way, if we change the tests datasets,
  we will change the expected values right there, rather than
  changing the tests in this file
'''

###   Fixtures   ###

@pytest.fixture
def mock_acq2bidsphysio(monkeypatch):
    """
    Pretend we run acq2bids, but do nothing
    This allows us to test the correct behavior of the runner without
       actually running anything: just the instructions in the runner
       before the call to acq2bids
    """
    def mock_acq2bids(*args, **kwargs):
        print('mock_acq2bids called')
        return

    monkeypatch.setattr(d2bp, "acq2bids", mock_acq2bids)



###   Tests   ###

def test_main_args(
        monkeypatch,
        tmpdir,
        mock_acq2bidsphysio,
        capfd
):
    '''
    Tests for "main"
    Just check the arguments, etc. We'll test the call to acq2bids in a
    separated function
    '''
    # 1) "infile" doesn't exist:
    infile = str(tmpdir / 'boo.dcm')
    args = (
        'acq2bidsphysio -i {infile} -b {bp}'.format(
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
    #    The output directory should be created and the "acq2bids" function should be called
    args[ args.index('-i')+1 ] = str(TESTS_DATA_PATH / 'sample.acq')
    monkeypatch.setattr(sys, 'argv',args)
    d2bp.main()
    assert (tmpdir / 'mydir').exists()
    assert capfd.readouterr().out == 'mock_acq2bids called\n'


def test_plug_missing_data():
    '''   Test for plug_missing_data   '''
    import numpy as np

    # generate a temporal series and corresponding fake signal with
    #   missing timepoints:
    dt = 1
    t = [i/1 for i in range(35) if i%10]
    s = [i for i in range(len(t))]

    expected_t, expected_s = d2bp.plug_missing_data(t,s,dt)
    assert all(np.ediff1d(expected_t)) == dt
    assert all(np.isnan(expected_s[[i for i in range(len(expected_s)) if not (i+1)%10]]))


def test_acq2bids(
        monkeypatch,
        tmpdir,
        capfd
):
    '''
    Tests for the call to "acq2bids"
    We will call it by calling "main" to make sure the output directory
    is created, etc.
    '''
    import json
    import gzip

    infile = str(TESTS_DATA_PATH / 'sample.acq')
    outbids = str(tmpdir / 'mydir' / 'bids')

    args = (
        'acq2bidsphysio -i {infile} -b {bp}'.format(
            infile=str(infile),
            bp=outbids
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv',args)

    # call "main" (which will create the output dir and call "acq2bids"):
    d2bp.main()

    # make sure we are not calling the mock_dcm2bidds, but the real one:
    assert capfd.readouterr().out != 'mock_acq2bids called\n'

    # Check that we have as many signals as expected (1, for this file):
    json_files = sorted(Path(tmpdir / 'mydir').glob('*.json'))
    data_files = sorted(Path(tmpdir / 'mydir').glob('*.tsv*'))
    assert len(json_files)==len(data_files)==1

    expectedFileBaseName = Path(outbids).name + '_physio'
    expectedFileName = tmpdir / 'mydir' / expectedFileBaseName
    assert (expectedFileName + '.json') in json_files
    assert (expectedFileName + '.tsv.gz') in data_files

    # check content of the json file:
    expectedSignals = ['cardiac', 'respiratory', 'GSR', 'Digital input']
    with open(expectedFileName + '.json') as f:
        d = json.load(f)
        assert d['Columns'] == expectedSignals
        for s in expectedSignals:
            if s == 'GSR':
                assert d[s]['Units'] == 'microsiemens'
            else:
                assert d[s]['Units'] == 'Volts'
        assert d['StartTime'] == 0
        assert d['SamplingFrequency'] == 500

    # check content of the tsv file:
    with open( TESTS_DATA_PATH / ('acq_physio.tsv'),'rt' ) as expected, \
        gzip.open(expectedFileName + '.tsv.gz','rt') as f:
            for expected_line, written_line in zip (expected, f):
                assert expected_line == written_line

