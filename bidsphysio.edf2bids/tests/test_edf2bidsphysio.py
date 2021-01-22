'''   Tests for the module "edf2bidsphysio.py"   '''

import json
import gzip
from pathlib import Path
import sys

import pytest

from _pytest.monkeypatch import MonkeyPatch
monkeypatch = MonkeyPatch()

from bidsphysio.edf2bids import edf2bidsphysio as e2bp
from .utils import TESTS_DATA_PATH

'''
TO-DO:

'''

###   Fixtures   ###

@pytest.fixture
def mock_edf2bidsphysio(monkeypatch):
    """
    Pretend we run edf2bids, but do nothing
    This allows us to test the correct behavior of the runner without
       actually running anything: just the instructions in the runner
       before the call to edf2bids
    """
    def mock_edf2bids(*args, **kwargs):
        print('mock_edf2bids called')
        return

    monkeypatch.setattr(e2bp, "edf2bids", mock_edf2bids)



###   Tests   ###

def test_main_args(
        monkeypatch,
        tmpdir,
        mock_edf2bidsphysio,
        capfd
):
    '''
    Tests for "main"
    Just check the arguments, etc. We'll test the call to edf2bids in a
    separated function
    '''
    # 1) "infile" doesn't exist:
    infile = str(tmpdir / 'boo.edf')
    args = (
        'edf2bidsphysio -i {infile} -b {bp}'.format(
            infile=infile,
            bp=tmpdir / 'mydir' / 'foo'
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv',args)
    with pytest.raises(FileNotFoundError) as e_info:
        e2bp.main()
    assert str(e_info.value).endswith(' file not found')
    assert str(e_info.value).split(' file not found')[0] == infile

    # 2) "infile" does exist, but output directory doesn't exist:
    #    The output directory should be created and the "edf2bids" function should be called
    args[ args.index('-i')+1 ] = str(TESTS_DATA_PATH / 'sample.edf')
    monkeypatch.setattr(sys, 'argv',args)
    e2bp.main()
    assert (tmpdir / 'mydir').exists()
    assert capfd.readouterr().out == 'mock_edf2bids called\n'


def test_edf2bids(
        monkeypatch,
        tmpdir,
        capfd
):
    '''
    Tests for the call to "edf2bids"
    We will call it by calling "main" to make sure the output directory
    is created, etc.
    '''
    infile = str(TESTS_DATA_PATH / 'sample.edf')
    outbids = str(tmpdir / 'mydir' / 'bids')

    args = (
        'edf2bidsphysio -i {infile} -b {bp}'.format(
            infile=str(infile),
            bp=outbids
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv',args)

    # call "main" (which will create the output dir and call "edf2bids"):
    e2bp.main()

    # make sure we are not calling the mock_edf2bidds, but the real one:
    assert capfd.readouterr().out != 'mock_edf2bids called\n'

    # Check that we have as many signals as expected (2, for this file):
    json_files = sorted(Path(tmpdir / 'mydir').glob('*.json'))
    data_files = sorted(Path(tmpdir / 'mydir').glob('*.tsv*'))
    assert len(json_files)==len(data_files)==2

    expectedFileBaseName = Path(outbids).name + '_physio'
    expectedFileName = tmpdir / 'mydir' / expectedFileBaseName
    assert (expectedFileName + '.json') in json_files
    assert (expectedFileName + '.tsv.gz') in data_files

    # check content of the json file:
    expectedSignals = ['samples', 'gx_left', 'gy_left', 'pa_left', 'trigger', 'fixation', 'saccade', 'blink']
    with open(expectedFileName + '.json') as f:
        d = json.load(f)
        assert d['Columns'] == expectedSignals
        assert d['RecordedEye'] == 'Left'
        assert d['SamplingFrequency'] == 500
        assert d['StartTime'] == -21.256
    
    # check content of the tsv file:
    with open( TESTS_DATA_PATH / ('testeye_physio.tsv'),'rt' ) as expected, \
        gzip.open(expectedFileName + '.tsv.gz','rt') as f:
            for expected_line, written_line in zip (expected, f):
                assert expected_line == written_line

def test_edfevents2bids(
        monkeypatch,
        tmpdir,
        capfd
):
    '''
    Tests for the call to "edfevents2bids"
    We will call it by calling "main" to make sure the output directory
    is created, etc.
    '''
    infile = str(TESTS_DATA_PATH / 'sample.edf')
    outbids = str(tmpdir / 'mydir' / 'bids')
    
    args = (
        'edf2bidsphysio -i {infile} -b {bp}'.format(
            infile=str(infile),
            bp=outbids
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv',args)
            
    # call "main" (which will create the output dir and call "edf2bids"):
    e2bp.main()
            
    # make sure we are not calling the mock_edf2bidds, but the real one:
    assert capfd.readouterr().out != 'mock_edf2bids called\n'
            
    # Check that we have as many signals as expected (1, for this file):
    data_files = sorted(Path(tmpdir / 'mydir').glob('*.tsv*'))
    assert len(json_files)==len(data_files)==1
            
    expectedFileBaseName = Path(outbids).name + '_events'
    expectedFileName = tmpdir / 'mydir' / expectedFileBaseName
    assert (expectedFileName + '.tsv') in data_files
    
    # check content of the tsv file:
    with open( TESTS_DATA_PATH / ('testeye_events.tsv'),'rt' ) as expected, \
        gzip.open(expectedFileName + '.tsv.gz','rt') as f:
            for expected_line, written_line in zip (expected, f):
                assert expected_line == written_line
