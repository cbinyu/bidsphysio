"""   Tests for the module "acq2bidsphysio.py"   """

import json
import gzip
from pathlib import Path
import sys

import pytest

from bidsphysio.acq2bids import acq2bidsphysio as a2bp
from bidsphysio.base.bidsphysio import PhysioData
from .utils import TESTS_DATA_PATH

'''
TO-DO:

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
        return PhysioData()

    monkeypatch.setattr(a2bp, "acq2bids", mock_acq2bids)



###   Tests   ###

def test_main_args(
        monkeypatch,
        tmpdir,
        mock_acq2bidsphysio,
        capfd
):
    """
    Tests for "main"
    Just check the arguments, etc. We'll test the call to acq2bids in a
    separated function
    """
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
        a2bp.main()
    assert str(e_info.value).endswith(' file not found')
    assert str(e_info.value).split(' file not found')[0] == infile

    # 2) "infile" does exist, but output directory doesn't exist:
    #    The output directory should be created and the "acq2bids" function should be called
    args[ args.index('-i')+1 ] = str(TESTS_DATA_PATH / 'sample.acq')
    monkeypatch.setattr(sys, 'argv',args)
    a2bp.main()
    assert (tmpdir / 'mydir').exists()
    assert capfd.readouterr().out.startswith('mock_acq2bids called\n')


def test_acq2bids(
        monkeypatch,
        tmpdir,
        capfd
):
    """
    Tests for the call to "acq2bids"
    We will call it by calling "main" to make sure the output directory
    is created, etc.
    """
    infile = str(TESTS_DATA_PATH / 'sample.acq')
    outbids = str(tmpdir / 'mydir' / 'bids')

    args = (
        'acq2bidsphysio -i {infile} -b {bp} -t {tl}'.format(
            infile=str(infile),
            bp=outbids,
            tl='digital',
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv',args)

    # call "main" (which will create the output dir and call "acq2bids"):
    a2bp.main()

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
    expectedSignals = ['cardiac', 'respiratory', 'GSR', 'trigger']
    with open(expectedFileName + '.json') as f:
        d = json.load(f)
        assert d['Columns'] == expectedSignals
        for s in expectedSignals:
            if s == 'GSR':
                assert d[s]['Units'] == 'microsiemens'
            else:
                assert d[s]['Units'] == 'Volts'
        assert d['StartTime'] == 1583762929.924
        assert d['SamplingFrequency'] == 500

    # check content of the tsv file:
    with open( TESTS_DATA_PATH / ('acq_physio.tsv'),'rt' ) as expected, \
        gzip.open(expectedFileName + '.tsv.gz','rt') as f:
            for expected_line, written_line in zip (expected, f):
                assert expected_line == written_line

