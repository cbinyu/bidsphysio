'''   Tests for the module "dcm2bidsphysio.py"   '''

import bidsphysio.dcm2bidsphysio as d2bp
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


def test_parse_log():
    '''   Test for parse_log   '''

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

    # generate a binary string, and parse it:
    log_bytes = bytearray()
    log_bytes.extend(simulated_string.encode())
    waveform_name, t, s, dt = d2bp.parse_log(log_bytes)

    assert waveform_name == expected_LogDataType
    assert all(t == expected_times)
    assert all(s == expected_signals)
    assert dt == expected_SampleTime

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

    # generate a binary string, and parse it:
    log_bytes = bytearray()
    log_bytes.extend(simulated_string.encode())
    waveform_name, t, s, dt = d2bp.parse_log(log_bytes)

    assert waveform_name == expected_LogDataType
    assert all(t == expected_times)
    assert all(s == expected_signals)
    assert dt == expected_SampleTime

    # Note: if parse_log tried to incorrectly add the "don't log this: repeated echo"
    #       as time, it would give a "ValueError: invalid literal for int() with base 10"


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
    import gzip

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

    # Check that we have as many signals as expected (2, for this file):
    json_files = sorted(Path(tmpdir / 'mydir').glob('*.json'))
    data_files = sorted(Path(tmpdir / 'mydir').glob('*.tsv*'))
    assert len(json_files)==len(data_files)==2

    for s in ['respiratory','cardiac']:
        expectedFileBaseName = Path(outbids).name + '_recording-' + s + '_physio'
        expectedFileName = tmpdir / 'mydir' / expectedFileBaseName
        assert (expectedFileName + '.json') in json_files
        assert (expectedFileName + '.tsv.gz') in data_files

        # check content of the json file:
        with open(expectedFileName + '.json') as f:
            d = json.load(f)
            assert d['Columns'] == [ s, 'trigger']
            assert d['StartTime'] == -1.632
            if s == 'respiratory':
                assert d['SamplingFrequency'] == 125
            elif s == 'cardiac':
                assert d['SamplingFrequency'] == 500

        # check content of the tsv file:
        with open( TESTS_DATA_PATH / ('dcm_' + s + '.tsv'),'rt' ) as expected, \
            gzip.open(expectedFileName + '.tsv.gz','rt') as f:
                for expected_line, written_line in zip (expected, f):
                    assert expected_line == written_line
