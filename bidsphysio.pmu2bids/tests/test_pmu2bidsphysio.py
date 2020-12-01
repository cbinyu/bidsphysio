"""   Tests for the module "pmu2bidsphysio.py"   """

import gzip
import json
from pathlib import Path
import sys

import pytest

from bidsphysio.pmu2bids import pmu2bidsphysio as p2bp
from bidsphysio.base.bidsphysio import PhysioData
from bidsphysio.base.utils import check_bidsphysio_outputs
from .utils import TESTS_DATA_PATH

'''
TO-DO:

- Set the expected signals (and maybe file contents) from the
  tests data in a separate file , with the data, which the test
  functions will read. That way, if we change the tests datasets,
  we will change the expected values right there, rather than
  changing the tests in this file
'''

###   Globals   ###

MSG = 'Test: %r'
PMUVE11CFILE = 'sample_VE11C.puls'
PMUVB15AFILE = 'sample_VB15A.resp'
PMUVBXFILE = 'sample_VBX.puls'
EXPSTR = 'expected'
GOTSTR = 'foo'

# These are specific to the PMUVE11CFILE
STARTMDHTIME = 39008572
STOPMDHTIME = 39017760


###   Fixtures   ###

@pytest.fixture
def myErrmsg(scope="module"):
    """   myErrmsg   """
    return p2bp.errmsg(MSG, PMUVE11CFILE, EXPSTR, GOTSTR)


@pytest.fixture
def mock_pmu2bidsphysio(monkeypatch):
    """
    Pretend we run pmu2bids, but do nothing
    This allows us to test the correct behavior of the runner without
       actually running anything: just the instructions in the runner
       before the call to pmu2bids
    """

    def mock_pmu2bids(*args, **kwargs):
        print('mock_pmu2bids called')
        return PhysioData()

    monkeypatch.setattr(p2bp, "pmu2bids", mock_pmu2bids)


@pytest.fixture
def mock_readXXXXpmu_caller(monkeypatch):
    """
    Pretend we run readVE11Cpmu, readVB15Apmu or readVBXpmu, but do nothing
    """

    def mock_readXXXXpmu(*args, **kwargs):
        return

    monkeypatch.setattr(p2bp, 'readVE11Cpmu', mock_readXXXXpmu)
    monkeypatch.setattr(p2bp, 'readVB15Apmu', mock_readXXXXpmu)
    monkeypatch.setattr(p2bp, 'readVBXpmu', mock_readXXXXpmu)


###   Tests   ###

def test_errmsg():
    """
    Test that the message is what you expect, given the input args
    """

    expectedMsg1 = "Test: '" + PMUVE11CFILE + "'"
    expectedMsg2 = expectedMsg1 + ": Expected: '" + EXPSTR + "'; got: '" + GOTSTR + "'"
    assert p2bp.errmsg(MSG, PMUVE11CFILE) == expectedMsg1
    assert p2bp.errmsg(MSG, PMUVE11CFILE, EXPSTR, GOTSTR) == expectedMsg2
    # NOTE: don't assert p2bp.errmsg(...) == myErrmsg, because here we're testing
    #       the output message formatting.


def test_PMUFormatError_class(myErrmsg):
    """
    Test that when we create a new object of the class PMUFormatError, it
    gets initialized properly
    """
    myError = p2bp.PMUFormatError(MSG, PMUVE11CFILE, EXPSTR, GOTSTR)
    assert isinstance(myError, p2bp.PMUFormatError)
    with pytest.raises(p2bp.PMUFormatError) as err_info:
        raise myError
    assert str(err_info.value) == myErrmsg


def test_parserawPMUsignal(capfd):
    """
    Tests for parserawPMUsignal
    """

    # 1) simulated raw signal without a '5003' value to indicate the end of the recording:
    raw_signal = ['', '1733', '1725', '1725', '1721', '1721', '1718']
    psignal = p2bp.parserawPMUsignal(raw_signal)
    assert capfd.readouterr().out.startswith('Warning: End of physio recording not found')
    assert float('NaN') not in psignal
    # make sure it returns all the values, except for the first empty one:
    assert psignal == [int(i) for i in raw_signal[1:]]

    # 2) simulated raw signal with '5003' and with '5000' and '6000', to indicate "trigger on" and "trigger off":
    raw_signal = ['1733', '5000', '1725', '6000', '1721', '5003', '1718']
    psignal = p2bp.parserawPMUsignal(raw_signal)
    assert 5000 not in psignal
    assert 6000 not in psignal
    assert psignal == pytest.approx([1733, float('NaN'), 1725, float('NaN'), 1721], nan_ok=True)


def test_getPMUtiming():
    """
    Tests for getPMUtiming
    We only care about the lines that contain te MPCUTime and MDHTime
    """

    # 1) If the keywords are missing, the outputs should be 0
    assert p2bp.getPMUtiming([]) == ([0, 0], [0, 0])

    # 1) If the keywords are present, we should get them back (as int)
    LogStartMPCUTime = 39009937
    LogStopMPCUTime = 39019125

    lines = [
        'LogStartMDHTime:  {0}'.format(STARTMDHTIME),
        'LogStopMDHTime:   {0}'.format(STOPMDHTIME),
        'LogStartMPCUTime: {0}'.format(LogStartMPCUTime),
        'LogStopMPCUTime:  {0}'.format(LogStopMPCUTime),
        '6003'
    ]

    assert p2bp.getPMUtiming(lines) == (
        [LogStartMPCUTime, LogStopMPCUTime],
        [STARTMDHTIME, STOPMDHTIME]
    )


def test_readVE11Cpmu():
    """
    Tests for readVE11Cpmu
    """

    # 1) If you test with a file with the wrong format, you should get a PMUFormatError
    with pytest.raises(p2bp.PMUFormatError) as err_info:
        physio_file = str(TESTS_DATA_PATH / PMUVBXFILE)
        p2bp.readVE11Cpmu(physio_file)
    assert str(err_info.value).startswith(
        p2bp.errmsg(
            'File %r does not seem to be a valid {sv} PMU file'.format(sv='VE11C'),
            physio_file
        )
    )

    # 2) With the correct file format, you get the expected results:
    physio_file = str(TESTS_DATA_PATH / PMUVE11CFILE)

    physio_type, MDHTime, sampling_rate, physio_signal = p2bp.readVE11Cpmu(physio_file)
    assert physio_type == 'PULS'
    assert MDHTime == [STARTMDHTIME, STOPMDHTIME]
    assert sampling_rate == 400
    with open(TESTS_DATA_PATH / ('pmu_VE11C_cardiac.tsv'), 'rt') as expected:
        for expected_line, returned_signal in zip(expected, physio_signal):
            assert float(expected_line) == returned_signal


def test_readVB15Apmu():
    """
    Tests for readVB15Apmu
    """

    # 1) If you test with a file with the wrong format, you should get a PMUFormatError
    with pytest.raises(p2bp.PMUFormatError) as err_info:
        physio_file = str(TESTS_DATA_PATH / PMUVBXFILE)
        p2bp.readVB15Apmu(physio_file)
    assert str(err_info.value).startswith(
        p2bp.errmsg(
            'File %r does not seem to be a valid {sv} PMU file'.format(sv='VB15A'),
            physio_file
        )
    )

    # 2) With the correct file format, you get the expected results:
    physio_file = str(TESTS_DATA_PATH / PMUVB15AFILE)

    physio_type, MDHTime, sampling_rate, physio_signal = p2bp.readVB15Apmu(physio_file)
    assert physio_type == 'RESP'
    assert MDHTime == [57335095, 60647840]
    assert sampling_rate == 50
    with open(TESTS_DATA_PATH / ('pmu_VB15A_respiratory.tsv'), 'rt') as expected:
        for expected_line, returned_signal in zip(expected, physio_signal):
            assert float(expected_line) == returned_signal


def test_readVBXpmu():
    """
    Tests for readVBXpmu
    """

    # 1) If you test with a file with the wrong format, you should get a PMUFormatError
    with pytest.raises(p2bp.PMUFormatError) as err_info:
        physio_file = str(TESTS_DATA_PATH / PMUVE11CFILE)
        p2bp.readVBXpmu(physio_file)
    assert str(err_info.value).startswith(
        p2bp.errmsg(
            'File %r does not seem to be a valid {sv} PMU file'.format(sv='VBX'),
            physio_file
        )
    )

    # 2) With the correct file format, you get the expected results:
    physio_file = str(TESTS_DATA_PATH / PMUVBXFILE)

    physio_type, MDHTime, sampling_rate, physio_signal = p2bp.readVBXpmu(physio_file)
    assert physio_type == 'PULSE'
    assert MDHTime == [47029710, 47654452]
    assert sampling_rate == 50
    with open(TESTS_DATA_PATH / ('pmu_VBX_cardiac.tsv'), 'rt') as expected:
        for expected_line, returned_signal in zip(expected, physio_signal):
            assert float(expected_line) == returned_signal


def test_main_args(
        monkeypatch,
        tmpdir,
        mock_pmu2bidsphysio,
        capfd
):
    """
    Tests for "main"
    Just check the arguments, etc. We'll test the call to pmu2bids in a
    separated function
    """
    # 1) "infile" doesn't exist:
    # Note: we enter "-i" last because in 3), we'll be adding a second file
    infile = str(tmpdir / 'boo.dcm')
    args = (
        'pmu2bidsphysio -b {bp} -i {infile}'.format(
            infile=infile,
            bp=tmpdir / 'mydir' / 'foo'
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises(FileNotFoundError) as e_info:
        p2bp.main()
    assert str(e_info.value).endswith(' file not found')
    assert str(e_info.value).split(' file not found')[0] == infile

    # 2) "infile" does exist, but output directory doesn't exist:
    #    The output directory should be created and the "pmu2bids" function should be called
    args[args.index('-i') + 1] = str(TESTS_DATA_PATH / PMUVE11CFILE)
    monkeypatch.setattr(sys, 'argv', args)
    p2bp.main()
    assert (tmpdir / 'mydir').exists()
    assert capfd.readouterr().out == 'mock_pmu2bids called\n'

    # 3) "infile" contains more than one file:
    args.append(
        str(TESTS_DATA_PATH / PMUVBXFILE)
    )
    monkeypatch.setattr(sys, 'argv', args)
    # Make sure 'main' runs without errors:
    assert p2bp.main() is None


def test_testSamplingRate():
    """   Tests for testSamplingRate   """

    # 1) If the tolerance is wrong, we should get an error
    for t in [-0.5, 5]:
        with pytest.raises(ValueError) as err_info:
            p2bp.testSamplingRate(tolerance=t)
        assert str(err_info.value) == 'tolerance has to be between 0 and 1. Got ' + str(t)

    # 2) If the sampling rate is incorrect (allowing for default tolerance),
    #    we should also get an error:
    #    Note that the logTimes are in ms, and the sampling rate in samples per sec
    with pytest.raises(ValueError) as err_info:
        p2bp.testSamplingRate(
            sampling_rate=1,
            Nsamples=100,
            logTimes=[0, 10000]
        )
    assert 'sampling rate' in str(err_info.value)

    # 3) If the sampling rate is correct (within the default tolerance),
    #    we should NOT get an error:
    assert p2bp.testSamplingRate(
        sampling_rate=10,
        Nsamples=99,
        logTimes=[0, 10000]
    ) is None


def test_readpmu_with_incorrect_file():
    """
    Tests for readpmu when called with an incorrect file
    Given an input file from any PMU software version, check that it is saved to bids
    """

    physio_file = str(TESTS_DATA_PATH / PMUVBXFILE)

    # 1) If you call it with an unknown PMU software version, raise an error:
    with pytest.raises(Exception) as err_info:
        p2bp.readpmu(physio_file, 'Vfoo')
    assert str(err_info.value) == "Vfoo is not a known software version."

    # 2) If you test with a file with the wrong format, you should get a PMUFormatError
    softwareVersionToRead = 'VE11C'
    with pytest.raises(p2bp.PMUFormatError) as err_info:
        p2bp.readpmu(physio_file, softwareVersion=softwareVersionToRead)
    assert str(err_info.value) == p2bp.errmsg(
        'File %r does not seem to be a valid Siemens {sv} PMU file'.format(sv=softwareVersionToRead),
        physio_file
    )

    # 3) If you test with an ASCII file that is not a PMU file at all, or
    #    with a binaryfile, you should get a PMUFormatError
    ascii_file = str(TESTS_DATA_PATH / 'pmu_VBX_cardiac.tsv')
    binary_file = str(TESTS_DATA_PATH / 'sample.acq')
    for f in [ascii_file, binary_file]:
        with pytest.raises(p2bp.PMUFormatError) as err_info:
            p2bp.readpmu(f)
        assert str(err_info.value) == p2bp.errmsg(
            'File %r does not seem to be a valid Siemens PMU file',
            f
        )


def test_readpmu(
        monkeypatch,
        mock_readXXXXpmu_caller
):
    """
    Tests for readpmu with the right file
    Given an input file from any PMU software version, check that it does not give an error
    We don't need to check the results because those are checked
    in the corresponding test_readXXXXpmu tests above.
    """

    # Specifying the (correct) version:
    assert p2bp.readpmu(
        str(TESTS_DATA_PATH / PMUVBXFILE),
        softwareVersion='VBX'
    ) is None
    assert p2bp.readpmu(
        str(TESTS_DATA_PATH / PMUVE11CFILE),
        softwareVersion='VE11C'
    ) is None

    # Default mode: try all known versions:
    for f in [
        str(TESTS_DATA_PATH / PMUVBXFILE),
        str(TESTS_DATA_PATH / PMUVE11CFILE)
    ]:
        assert p2bp.readpmu(f) is None


def test_pmu2bids(
        monkeypatch,
        tmpdir,
        capfd
):
    """
    Tests for the call to "pmu2bids"
    We will call it by calling "main" to make sure the output directory
    is created, etc.
    """
    infile1 = str(TESTS_DATA_PATH / PMUVE11CFILE)
    infile2 = infile1[:-5] + '.resp'
    outbids = str(tmpdir / 'mydir' / 'bids')

    args = (
        'pmu2bidsphysio -i {infiles} -b {bp}'.format(
            infiles=infile1 + ' ' + infile2,
            bp=outbids
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv', args)

    # call "main" (which will create the output dir and call "pmu2bids"):
    p2bp.main()

    # make sure we are not calling the mock_dcm2bidds, but the real one:
    assert capfd.readouterr().out != 'mock_pmu2bids called\n'

    # Check that we have as many signals as expected (2 in this case):
    check_bidsphysio_outputs(outbids,
                             [['cardiac'], ['respiratory']],
                             TESTS_DATA_PATH / 'pmu_VE11C_')
