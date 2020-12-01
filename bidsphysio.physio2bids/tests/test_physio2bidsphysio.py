"""   Tests for the module "physio2bidsphysio.py"   """

import sys

import pytest

from bidsphysio.physio2bids import physio2bidsphysio
from bidsphysio.base.bidsphysio import PhysioData
from bidsphysio.acq2bids import acq2bidsphysio as a2bp
from bidsphysio.dcm2bids import dcm2bidsphysio as d2bp
from bidsphysio.pmu2bids import pmu2bidsphysio as p2bp
from .utils import TESTS_DATA_PATH

###   Globals   ###

ACQFILE = 'sample.acq'
DCMFILE = 'samplePhysioCMRR.dcm'
PMUVE11CFILE = 'sample_VE11C.puls'


###   Fixtures   ###

@pytest.fixture
def mock_physio2bidsphysio_calls(monkeypatch):
    """
    Pretend we run acq2bids, dcm2bids and pmu2bids, but do nothing
    This allows us to test physio2bidsphysio.main without actually running
    the conversions
    """

    def mock_acq2bids(*args, **kwargs):
        print('mock_acq2bids called')
        for a in args:
            print(a)
        return PhysioData()

    def mock_dcm2bids(*args, **kwargs):
        print('mock_dcm2bids called')
        for a in args:
            print(a)
        return PhysioData()

    def mock_pmu2bids(*args, **kwargs):
        print('mock_pmu2bids called')
        for a in args:
            print(a)
        return PhysioData()

    monkeypatch.setattr(a2bp, "acq2bids", mock_acq2bids)
    monkeypatch.setattr(d2bp, "dcm2bids", mock_dcm2bids)
    monkeypatch.setattr(p2bp, "pmu2bids", mock_pmu2bids)


###   Tests   ###

def test_main(
        tmpdir,
        monkeypatch,
        mock_physio2bidsphysio_calls,
        capfd
):
    """
    Tests for "main"
    Just check the arguments, etc. We test the call to the differnt XXX2bids functions in a
    separated test module
    """

    bidsPrefix = str(tmpdir / 'mydir' / 'foo')

    # 1) "infile" with wrong extension:
    # Note: we enter "-i" last because we'll be adding a second file in another test below
    infile = str(TESTS_DATA_PATH / 'dcm_cardiac.tsv')
    args = (
        'physio2bidsphysio -b {bp} -i {infile}'.format(
            infile=infile,
            bp=bidsPrefix
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv', args)

    with pytest.raises(Exception) as e_info:
        physio2bidsphysio.main()
    assert str(e_info.value).endswith(' is not a known physio file extension.')

    # 2) "infile" doesn't exist:
    infile = str(tmpdir / 'boo.dcm')
    args[args.index('-i') + 1] = infile  # use the new infile
    monkeypatch.setattr(sys, 'argv', args)

    with pytest.raises(FileNotFoundError) as e_info:
        physio2bidsphysio.main()
    assert str(e_info.value).endswith(' file not found')
    assert str(e_info.value).split(' file not found')[0] == infile

    # 3) test all different known file types:
    for f in [ACQFILE, DCMFILE, PMUVE11CFILE]:
        infile = str(TESTS_DATA_PATH / f)
        args[args.index('-i') + 1] = infile
        monkeypatch.setattr(sys, 'argv', args)
        physio2bidsphysio.main()
        out = capfd.readouterr().out
        printout, inarg, _ = out.split('\n')
        assert 'mock_' in printout and '2bids called' in printout
        assert infile in inarg

    # also, check that the output folder is created:
    assert (tmpdir / 'mydir').exists()

    # 4) "infile" contains more than one file:
    # 4.1) It should fail for '.dcm' files:
    args[args.index('-i') + 1] = str(TESTS_DATA_PATH / DCMFILE)
    args.append(
        str(TESTS_DATA_PATH / DCMFILE)
    )
    # Note: we need to use the same file twice, because the extra file has to exist
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises(Exception) as e_info:
        physio2bidsphysio.main()
    assert 'Only one input file' in str(e_info.value)

    # 4.2) It should work for '.acq' and PMU files:
    for multifile in [
        [str(TESTS_DATA_PATH / ACQFILE), str(TESTS_DATA_PATH / ACQFILE)],
        [str(TESTS_DATA_PATH / PMUVE11CFILE), str(TESTS_DATA_PATH / PMUVE11CFILE)]
    ]:
        args[args.index('-i') + 1:] = multifile
        monkeypatch.setattr(sys, 'argv', args)
        physio2bidsphysio.main()
        out = capfd.readouterr().out
        printout, inarg, _ = out.split('\n')
        assert 'mock_' in printout and '2bids called' in printout
        assert inarg == str(multifile)
