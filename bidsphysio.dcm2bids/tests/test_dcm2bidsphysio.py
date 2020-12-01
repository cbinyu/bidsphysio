"""   Tests for the module "dcm2bidsphysio.py"   """

import sys
import re

import pytest

from bidsphysio.dcm2bids import dcm2bidsphysio as d2bp
from bidsphysio.base.bidsphysio import PhysioData
from bidsphysio.base.utils import (check_bidsphysio_outputs,
                                   get_physio_TRs)
from .utils import (TESTS_DATA_PATH,
                    EXPECTED_ACQ_TIME)

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
def mock_dcm2bidsphysio(monkeypatch):
    """
    Pretend we run dcm2bids, but do nothing
    This allows us to test the correct behavior of the runner without
       actually running anything: just the instructions in the runner
       before the call to dcm2bids
    """

    def mock_dcm2bids(*args, **kwargs):
        print('mock_dcm2bids called')
        return PhysioData()

    monkeypatch.setattr(d2bp, "dcm2bids", mock_dcm2bids)


###   Tests   ###

def test_main_args(
        monkeypatch,
        tmpdir,
        mock_dcm2bidsphysio,
        capfd
):
    """
    Tests for "main"
    Just check the arguments, etc. We'll test the call to dcm2bids in a
    separated function
    """
    # 1) "infile" doesn't exist:
    infile = str(tmpdir / 'boo.dcm')
    args = (
        'dcm2bidsphysio -b {bp} -i {infile}'.format(
            infile=infile,
            bp=tmpdir / 'mydir' / 'foo'
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises(FileNotFoundError) as e_info:
        d2bp.main()
    assert str(e_info.value).endswith(' file not found')
    assert str(e_info.value).split(' file not found')[0] == infile

    # 2) "infile" does exist, but output directory doesn't exist:
    #    The output directory should be created and the "dcm2bids" function should be called
    args[args.index('-i') + 1] = str(TESTS_DATA_PATH / 'samplePhysioCMRR.dcm')
    monkeypatch.setattr(sys, 'argv', args)
    d2bp.main()
    assert (tmpdir / 'mydir').exists()
    assert capfd.readouterr().out == 'mock_dcm2bids called\n'

    # 3) "infile" contains more than one file (repeated, in this case):
    args.append(
        str(TESTS_DATA_PATH / 'samplePhysioCMRR.dcm')
    )
    monkeypatch.setattr(sys, 'argv', args)
    # Make sure 'main' runs without errors:
    assert d2bp.main() is None


def test_get_acq_time():
    """   Test for get_acq_time   """
    for f in TESTS_DATA_PATH.glob('*.log'):
        assert d2bp.get_acq_time(f) == EXPECTED_ACQ_TIME


def test_parse_log():
    """   Test for parse_log   """

    expected_uuid = 'uuid'
    expected_ScanDate = 20000101
    expected_ScanTime = 120000
    expected_LogDataType = 'waveform_name'
    expected_SampleTime = 1
    expected_times = [1234, 5678]
    expected_signals = [0.1234, 0.5678]

    common_string = 'UUID = {0}\n'.format(expected_uuid)
    common_string += 'ScanDate = {d}_{t}\n'.format(d=expected_ScanDate, t=expected_ScanTime)
    common_string += 'SampleTime = {0}\n'.format(expected_SampleTime)

    ###   Test PULS or RESP signals   ###
    simulated_string = common_string + 'LogDataType = {0}\n'.format(expected_LogDataType)
    simulated_string += '{t} PULS {s}\n'.format(t=expected_times[0], s=expected_signals[0])
    simulated_string += '{t} RESP {s}\n'.format(t=expected_times[1], s=expected_signals[1])

    # generate a string, line-by-line, and parse it:
    physio_log_lines = simulated_string.splitlines()
    uuid, waveform_name, t, s, dt = d2bp.parse_log(physio_log_lines)

    assert uuid == expected_uuid
    assert waveform_name == expected_LogDataType
    assert all(t == [2.5 * e for e in expected_times])    # the "SampleTime" is in units of 2.5 ms
    assert all(s == expected_signals)
    assert dt == 2.5 * expected_SampleTime   # the "SampleTime" is in units of 2.5 ms

    ###   Test trigger signal   ###
    expected_LogDataType = 'ACQUISITION_INFO'
    expected_times = [123, 456, 789]
    expected_signals = [1, 0, 1]

    simulated_string = common_string + 'LogDataType = {0}\n'.format(expected_LogDataType)
    # format for trigger lines:
    simulated_string += 'VOLUME   SLICE   ACQ_START_TICS  ACQ_FINISH_TICS  ECHO\n'
    simulated_string += '0     0       {t}      foo    0\n'.format(t=expected_times[0])
    # to make sure we don't save this time, for ECHO=1:
    simulated_string += '0     0       {t}      foo    1\n'.format(t="don't_log_this:_repeated_echo")
    # this is another slice, for the same volume:
    simulated_string += '0     1       {t}      foo    0\n'.format(t=expected_times[1])
    # a new volume:
    simulated_string += '1     0       {t}      foo    0\n'.format(t=expected_times[2])

    # generate a string, line-by-line, and parse it:
    physio_log_lines = simulated_string.splitlines()
    uuid, waveform_name, t, s, dt = d2bp.parse_log(physio_log_lines)

    assert waveform_name == expected_LogDataType
    assert all(t == [2.5 * e for e in expected_times])    # the "SampleTime" is in units of 2.5 ms
    assert all(s == expected_signals)
    assert dt == 2.5 * expected_SampleTime   # the "SampleTime" is in units of 2.5 ms

    # Note: if parse_log tried to incorrectly add the "don't log this: repeated echo"
    #       as time, it would give a "ValueError: invalid literal for int() with base 10"


def test_dcm2bids(
        monkeypatch,
        tmpdir,
        capfd
):
    """
    Tests for the call to "dcm2bids"
    We will call it by calling "main" to make sure the output directory
    is created, etc.
    """
    outbids = str(tmpdir / 'dcm' / 'bids')

    # 1) Single DICOM infile:
    print('Testing a single DICOM file...')
    infile = str(TESTS_DATA_PATH / 'samplePhysioCMRR.dcm')
    args = (
        'dcm2bidsphysio -i {infile} -b {bp} -v'.format(
            infile=str(infile),
            bp=outbids
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv', args)

    # call "main" (which will create the output dir and call "dcm2bids"):
    d2bp.main()

    # make sure we are not calling the mock_dcm2bidds, but the real one:
    assert capfd.readouterr().out != 'mock_dcm2bids called\n'

    # Check that we have as many signals as expected (2, for this file):
    check_bidsphysio_outputs(outbids,
                             ['cardiac', 'respiratory', 'external_trigger'],
                             TESTS_DATA_PATH / 'dcm_')

    # 2) Two DICOM infiles: It should give an error:
    print('Testing two DICOM files...')
    infiles = [str(TESTS_DATA_PATH / 'samplePhysioCMRR.dcm'),
               str(TESTS_DATA_PATH / 'samplePhysioCMRR.dcm')]
    args = (
        'dcm2bidsphysio -i {infile} -b {bp} -v'.format(
            infile=" ".join(infiles),
            bp=outbids
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv', args)

    with pytest.raises(RuntimeError) as e_info:
        d2bp.main()
    assert 'dcm2bids can only take one DICOM file' in str(e_info.value)

    # 3) Multiple .log infiles:
    print('Testing multiple ".log" files...')
    infiles = [str(TESTS_DATA_PATH / 'Physio_Info.log'),
               str(TESTS_DATA_PATH / 'Physio_RESP.log'),
               str(TESTS_DATA_PATH / 'Physio_PULS.log')]
    # use a different output dir, to make sure it's empty:
    outbids = str(tmpdir / 'log' / 'bids')
    args = (
        'dcm2bidsphysio -i {infile} -b {bp}'.format(
            infile=" ".join(infiles),
            bp=outbids
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv', args)
    d2bp.main()

    # Check that we have as many signals as expected (2 in this case)
    # (we don't check the content of the .tsv file):
    check_bidsphysio_outputs(outbids,
                             ['cardiac', 'respiratory'],
                             None)


def test_timing(
        monkeypatch,
        tmpdir,
        capfd
):
    """
    This test checks that the timing is OK.
    It will read the physio signals from a DICOM file and save them as BIDS.
    Then, from the trigger signal in the physio bids files, we'll estimate
    the TR, and compare it with the actual TR.
    """
    outbids = str(tmpdir / 'mydir' / 'bids')

    infile = str(TESTS_DATA_PATH / 'samplePhysioCMRR.dcm')
    args = (
        'dcm2bidsphysio -i {infile} -b {bp} -v'.format(
            infile=str(infile),
            bp=outbids
        )
    ).split(' ')
    monkeypatch.setattr(sys, 'argv', args)

    # call "main" (which will create the output dir and call "dcm2bids"):
    d2bp.main()

    # now, read the TR from the Siemens private header in the physio DICOM file:
    d = d2bp.pydicom.dcmread(infile, stop_before_pixels=True)
    header = d.get((0x0029, 0x1120)).value.decode(encoding='ISO-8859-1')
    # TR in the private header is in micro-seconds
    expected_TR = int(re.findall(r'alTR\[0\]\s+=\s+(\d+)', header)[0])/1000000

    TRs = get_physio_TRs(outbids)
    assert TRs == [expected_TR]*len(TRs)
