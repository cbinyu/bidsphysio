"""   Tests for the module "bidsphysio.py"   """

import copy
from glob import glob
import gzip
import json
import random
from os import remove
from os.path import join as pjoin

import numpy as np
import pytest

from bidsphysio.base.bidsphysio import (PhysioSignal,
                                        PhysioData)

###  Globals   ###

PHYSIO_SAMPLES_PER_SECOND = random.randint(10, 100)
PHYSIO_START_TIME = random.uniform(10, 111)  # (in sec) with respect to some reference clock
PHYSIO_DURATION = random.uniform(15, 25)
PHYSIO_SAMPLES_COUNT = round(PHYSIO_SAMPLES_PER_SECOND * PHYSIO_DURATION)
LABELS = ['signal1', 'signal2', 'signal3']
TRIGGER_SAMPLES_PER_SECOND = random.randint(15, 25)
# (in sec) beginning of the trigger recording (same ref clock):
TRIGGER_START_TIME = random.uniform(0, PHYSIO_START_TIME)
SCANNER_DELAY = random.uniform(1, 3)  # From the beginning of the physio recording to the first volume
SCANNER_TR = random.uniform(0.5, 2)  # (in sec)


###   TESTS FOR CLASS "PhysioSignal"   ###

@pytest.fixture
def mySignal(scope="module"):
    """    Simulate a PhysioSignal object    """

    mySignal = PhysioSignal(
        label='simulated',
        samples_per_second=PHYSIO_SAMPLES_PER_SECOND,
        physiostarttime=PHYSIO_START_TIME,
        neuralstarttime=PHYSIO_START_TIME + SCANNER_DELAY,
        signal=PHYSIO_SAMPLES_COUNT * [0]  # fill with zeros
    )

    return mySignal


@pytest.fixture
def trigger_timing(scope="module"):
    """
    Simulate trigger timing (times at which the triggers were sent)
    With respect to the reference clock
    """

    t_first_trigger = PHYSIO_START_TIME + SCANNER_DELAY  # w.r.t. reference clock
    scanner_duration_seconds = PHYSIO_DURATION - SCANNER_DELAY
    number_of_scanner_triggers = int(scanner_duration_seconds / SCANNER_TR)
    # (note: both scanner_duration_seconds and TR can be floats, so "//" is not enough)

    trigger_timing = [t_first_trigger + SCANNER_TR * i for i in range(number_of_scanner_triggers)]

    return trigger_timing


def test_calculate_timing(
        mySignal
):
    """
    Test for calculate_timing
    It checks that it gives an error when it is supposed to, and it returns the
    correct timing when the neccessary parameters are present
    """

    # 1) Try with a PhysioSignal without sampling rate:
    with pytest.raises(Exception) as e_info:
        PhysioSignal(
            label='simulated',
            physiostarttime=PHYSIO_START_TIME
        ).calculate_timing()

    # 2) With a correct signal:
    mySignal.calculate_timing()
    assert len(mySignal.sampling_times) == PHYSIO_SAMPLES_COUNT
    assert mySignal.sampling_times[0] == mySignal.physiostarttime
    np.testing.assert_allclose(np.ediff1d(mySignal.sampling_times), 1 / mySignal.samples_per_second, 1e-10)


def test_calculate_trigger_events(
        capfd,
        mySignal,
        trigger_timing
):
    """
    Make sure you get as many triggers in the trigger signal
    as elements there are in the trigger timing (between the
    beginning of the recording and the end)
    """

    # 1) If you try to calculate it for a signal for which we cannot calculate
    #    the timing, it should print an error and return None:
    assert PhysioSignal(
        label='simulated',
        physiostarttime=PHYSIO_START_TIME
    ).calculate_trigger_events(trigger_timing) is None
    assert capfd.readouterr().out == "Unable to calculate the recording timing\n"

    # 2) Run it successfully:
    # calculate trigger events:
    trig_signal = mySignal.calculate_trigger_events(trigger_timing)

    assert isinstance(trig_signal, np.ndarray)

    # calculate how many triggers there are between the first and last sampling_times:
    num_trig_within_physio_samples = np.bitwise_and(
        np.array(trigger_timing) >= mySignal.sampling_times[0],
        np.array(trigger_timing) <= mySignal.sampling_times[-1]
    )

    assert (sum(trig_signal) == sum(num_trig_within_physio_samples))


def test_plug_missing_data():
    """   Test for plug_missing_data   """

    # generate a PhysioSignal with a temporal series and corresponding fake signal with
    #   missing timepoints:
    st = [i / 1 for i in range(35) if i % 10]
    spamSignal = PhysioSignal(
        label='simulated',
        samples_per_second=1,
        sampling_times=st,
        signal=[i for i in range(len(st))]
    )

    spamSignal.plug_missing_data()
    assert all(np.ediff1d(spamSignal.sampling_times)) == 1
    assert all(np.isnan(spamSignal.signal[[i for i in range(len(spamSignal.signal)) if not (i + 1) % 10]]))
    assert len(spamSignal.signal) == spamSignal.samples_count


def test_matching_trigger_signal(
        mySignal,
        trigger_timing
):
    """
    Test that both PhysioSignals (the original signal and the derived one with the trigger)
    have the same fields.
    It requires the result of "test_calculate_trigger_events"
    """

    # calculate trigger events:
    trig_signal = mySignal.calculate_trigger_events(trigger_timing)

    trigger_physiosignal = PhysioSignal.matching_trigger_signal(mySignal, trig_signal)

    assert isinstance(trigger_physiosignal, PhysioSignal)
    assert trigger_physiosignal.label == 'trigger'
    assert trigger_physiosignal.samples_per_second == mySignal.samples_per_second
    assert trigger_physiosignal.physiostarttime == mySignal.physiostarttime
    assert trigger_physiosignal.neuralstarttime == mySignal.neuralstarttime
    assert trigger_physiosignal.sampling_times == mySignal.sampling_times
    assert all(trigger_physiosignal.signal == trig_signal)


###   TESTS FOR CLASS "PhysioData"   ###

@pytest.fixture
def myphysiodata(scope="module"):
    """   Create a "PhysioData" object with barebones content  """

    myphysiodata = PhysioData(
        [PhysioSignal(
            label=l,
            samples_per_second=PHYSIO_SAMPLES_PER_SECOND,
            physiostarttime=PHYSIO_START_TIME,
            neuralstarttime=PHYSIO_START_TIME + SCANNER_DELAY,
            signal=[i for i in range(PHYSIO_SAMPLES_COUNT)]
        ) for l in LABELS]
    )
    return myphysiodata


@pytest.fixture
def simulated_trigger_signal(scope="module"):
    """
    Simulates some recordings for the scanner trigger
    """

    trigger_samples_per_tr = TRIGGER_SAMPLES_PER_SECOND * SCANNER_TR
    physio_recoding_delay = PHYSIO_START_TIME - TRIGGER_START_TIME
    first_trigger_delay = physio_recoding_delay + SCANNER_DELAY  # w.r.t. beginning of trigger recording
    first_trigger_delay_in_samples = first_trigger_delay * TRIGGER_SAMPLES_PER_SECOND
    # supposing the trigger recording ends at the same time as the physio recording:
    trigger_recording_duration = physio_recoding_delay + PHYSIO_DURATION
    trigger_samples_count = round(trigger_recording_duration * TRIGGER_SAMPLES_PER_SECOND)

    trigger_signal = trigger_samples_count * [0]  # initialize to zeros
    for i in range(trigger_samples_count):
        sample_offset = i - first_trigger_delay_in_samples
        if (sample_offset >= 0) and (sample_offset % trigger_samples_per_tr < 1):
            trigger_signal[i] = 1

    return trigger_signal

@pytest.fixture
def simulated_edf_trigger_signal(scope="module"):
    """
    Simulates some recordings for the scanner trigger, as parsed by pyedfread
    """
    #TODO: Simulate an analog signal
    
    trigger_samples_per_tr = TRIGGER_SAMPLES_PER_SECOND * SCANNER_TR
    physio_recoding_delay = PHYSIO_START_TIME - TRIGGER_START_TIME
    first_trigger_delay = physio_recoding_delay + SCANNER_DELAY  # w.r.t. beginning of trigger recording
    first_trigger_delay_in_samples = first_trigger_delay * TRIGGER_SAMPLES_PER_SECOND
    # supposing the trigger recording ends at the same time as the physio recording:
    trigger_recording_duration = physio_recoding_delay + PHYSIO_DURATION
    trigger_samples_count = round(trigger_recording_duration * TRIGGER_SAMPLES_PER_SECOND)
    
    trigger_signal = trigger_samples_count * [4]  # initialize to fours
    for i in range(trigger_samples_count):
        sample_offset = i - first_trigger_delay_in_samples
        if (sample_offset >= 0) and (sample_offset % trigger_samples_per_tr < 1):
            trigger_signal[i] = 127

    # Adding some noise (even though edf-recorded scanner triggers don't have it)
    y = trigger_signal + np.random.random(trigger_samples_count) * 0.2

    return trigger_signal

@pytest.fixture
def myphysiodata_with_trigger(
        myphysiodata,
        simulated_trigger_signal,
        scope="module"
):
    myphysiodata_with_trigger = copy.deepcopy(myphysiodata)

    # add a trigger signal to the physiodata_with_trigger:
    myphysiodata_with_trigger.append_signal(
        PhysioSignal(
            label='trigger',
            samples_per_second=TRIGGER_SAMPLES_PER_SECOND,
            physiostarttime=TRIGGER_START_TIME,
            neuralstarttime=TRIGGER_START_TIME,
            signal=simulated_trigger_signal
        )
    )
    return myphysiodata_with_trigger

@pytest.fixture
def myphysiodata_with_edf_trigger(
        myphysiodata,
        simulated_edf_trigger_signal,
        scope="module"
):
    myphysiodata_with_edf_trigger = copy.deepcopy(myphysiodata)
    
    # add a trigger signal to the physiodata_with_trigger:
    myphysiodata_with_edf_trigger.append_signal(
        PhysioSignal(
            label='trigger',
            samples_per_second=TRIGGER_SAMPLES_PER_SECOND,
            physiostarttime=TRIGGER_START_TIME,
            neuralstarttime=TRIGGER_START_TIME,
            signal=simulated_edf_trigger_signal
        )
    )
    return myphysiodata_with_edf_trigger

def test_physiodata_labels(
        myphysiodata
):
    """
    Test both the PhysioData constructor and that
    PhysioData.labels() returns the labels of the PhysioSignals
    """

    assert myphysiodata.labels() == LABELS


def test_append_signal(
        myphysiodata
):
    """
    Tests that "append_signal" does what it is supposed to do
    """

    # Make a copy of myphysiodata to make sure we don't modify it,
    #  so that it is later available unmodified to other tests:
    physdata = copy.deepcopy(myphysiodata)
    physdata.append_signal(
        PhysioSignal(label='extra_signal')
    )

    mylabels = LABELS.copy()
    mylabels.append('extra_signal')
    assert physdata.labels() == mylabels


def test_save_bids_json(
        tmpdir,
        myphysiodata
):
    """
    Tests  "save_bids_json"
    """

    json_file_name = pjoin(tmpdir.strpath, 'foo.json')

    # make sure it gives an error if sampling or t_start are not the same for all PhysioSignals
    # samples_per_second:
    myphysiodata.signals[0].samples_per_second *= 2
    with pytest.raises(Exception) as e_info:
        myphysiodata.save_bids_json(json_file_name)

    # now, set the sampling rate back like the rest and test the t_start:
    myphysiodata.signals[0].samples_per_second = myphysiodata.signals[1].samples_per_second
    myphysiodata.signals[0].physiostarttime += 1
    with pytest.raises(Exception) as e_info:
        myphysiodata.save_bids_json(json_file_name)

    # set all t_start to the same (by fixing the physiostarttime:
    myphysiodata.signals[0].physiostarttime = myphysiodata.signals[1].physiostarttime

    # make sure the filename ends with "_physio.json"
    myphysiodata.save_bids_json(json_file_name)
    json_files = glob(pjoin(tmpdir, '*.json'))
    assert len(json_files) == 1
    json_file = json_files[0]
    assert json_file.endswith('_physio.json')

    # read the json file and check the content vs. the PhysioData:
    with open(json_file) as f:
        d = json.load(f)
    assert d['Columns'] == LABELS
    assert d['SamplingFrequency'] == myphysiodata.signals[0].samples_per_second
    assert d['StartTime'] == myphysiodata.signals[0].t_start()


def test_save_bids_data(
        tmpdir,
        myphysiodata
):
    """
    Tests  "save_bids_data"
    """
    data_file_name = pjoin(tmpdir.strpath, 'foo.tsv')

    # make sure the filename ends with "_physio.tsv.gz"
    myphysiodata.save_bids_data(data_file_name)
    data_files = glob(pjoin(tmpdir, '*.tsv*'))
    assert len(data_files) == 1
    data_file = data_files[0]
    assert data_file.endswith('_physio.tsv.gz')

    # read the data file and check the content vs. the PhysioData:
    with gzip.open(data_file, 'rt') as f:
        for idx, line in enumerate(f):
            assert [float(s) for s in line.split('\t')] == [s.signal[idx] for s in myphysiodata.signals]


def test_save_to_bids(
        tmpdir,
        myphysiodata
):
    """
    Test "save_to_bids"
    """
    output_file_name = pjoin(tmpdir.strpath, 'foo')

    # when all sample rates and t_starts are the same, there should be only one
    #   (.sjon/.tsv.gz) pair:
    myphysiodata.save_to_bids(output_file_name)
    json_files = glob(pjoin(tmpdir, '*.json'))
    assert len(json_files) == 1
    json_file = json_files[0]
    assert json_file.endswith('_physio.json')
    data_files = glob(pjoin(tmpdir, '*.tsv*'))
    assert len(data_files) == 1
    data_file = data_files[0]
    assert data_file.endswith('_physio.tsv.gz')
    remove(json_file)
    remove(data_file)

    # make the last signal different from the rest, so that it is saved
    #   in a separate file:
    myphysiodata.signals[-1].samples_per_second *= 2
    myphysiodata.save_to_bids(output_file_name)
    json_files = glob(pjoin(tmpdir, '*.json'))
    assert len(json_files) == 2
    # make sure one of them ends with "_recording-" plus the label of the last signal, etc:
    assert [jf for jf in json_files if jf.endswith('_recording-{s3}_physio.json'.format(s3=LABELS[-1]))]
    data_files = glob(pjoin(tmpdir, '*.tsv*'))
    assert len(data_files) == 2
    # make sure one of them ends with "_recording-" plus the label of the last signal, etc:
    assert [df for df in data_files if df.endswith('_recording-{s3}_physio.tsv.gz'.format(s3=LABELS[-1]))]


def test_get_trigger_timing(
        myphysiodata,
        simulated_trigger_signal,
        myphysiodata_with_trigger
):
    """   Tests for 'get_trigger_timing'   """

    # try it on a PhysioData without trigger signal:
    with pytest.raises(ValueError) as e_info:
        myphysiodata.get_trigger_timing()
    assert str(e_info.value) == "'trigger' is not in list"

    # try with physiodata_with_trigger
    assert myphysiodata_with_trigger.get_trigger_timing() == [
        TRIGGER_START_TIME + idx / TRIGGER_SAMPLES_PER_SECOND
        for idx, trig in enumerate(simulated_trigger_signal) if trig == 1
    ]


def test_digitize_trigger(
        myphysiodata,
        myphysiodata_with_trigger,
        myphysiodata_with_edf_trigger
):
    """   Tests for 'digitize_trigger'   """

    # try it on a PhysioData without trigger signal:
    with pytest.raises(ValueError) as e_info:
        myphysiodata.get_trigger_timing()
    assert str(e_info.value) == "'trigger' is not in list"

    # try with physiodata_with_trigger:
    myphysiodata_with_edf_trigger.digitize_trigger()
    assert myphysiodata_with_edf_trigger.get_trigger_physiosignal().signal == \
           myphysiodata_with_trigger.get_trigger_physiosignal().signal


def test_get_scanner_onset(
        myphysiodata,
        myphysiodata_with_trigger
):
    """   Tests for 'get_scanner_onset'   """

    # try it on a PhysioData without trigger signal:
    with pytest.raises(ValueError) as e_info:
        myphysiodata.get_scanner_onset()
    assert str(e_info.value) == "'trigger' is not in list"

    # try with physiodata_with_trigger.
    # Make sure the scanner onset happens when expected (within
    # sampling resolution):
    assert myphysiodata_with_trigger.get_scanner_onset() == \
           pytest.approx(PHYSIO_START_TIME + SCANNER_DELAY, 1 / PHYSIO_SAMPLES_PER_SECOND)


def test_save_to_bids_with_trigger(
        tmpdir,
        capfd,
        myphysiodata,
        myphysiodata_with_trigger
):
    """   Tests for 'save_to_bids_with_trigger'   """

    output_file_name = pjoin(tmpdir.strpath, 'foo')

    ###   A) test on a PhysioData without trigger signal   ###
    myphysiodata.save_to_bids_with_trigger(output_file_name)
    # we should get a warning, and then a print out indicating save_to_bids was called:
    out = capfd.readouterr().out
    assert 'We cannot save with trigger because we found no trigger.' in out
    assert 'Saving physio data' in out

    ###   B)test the case of all signals (except the trigger) have the same     ###
    ###     sampling rate and t_start. We expect one "_physio" json/tsv pair:   ###
    myphysiodata_with_trigger.save_to_bids_with_trigger(output_file_name)

    json_files = glob(pjoin(tmpdir, '*.json'))
    assert len(json_files) == 1
    json_file = json_files[0]
    assert '_recording-' not in json_file

    # read the json file and check the content vs. the physiodata_with_trigger:
    with open(json_file) as f:
        d = json.load(f)
    expected_labels = list(LABELS)
    expected_labels.append('trigger')
    assert d['Columns'] == expected_labels
    assert d['SamplingFrequency'] == myphysiodata_with_trigger.signals[0].samples_per_second
    assert d['StartTime'] == myphysiodata_with_trigger.signals[0].t_start()

    # make sure the filename ends with "_physio.tsv.gz"
    data_files = glob(pjoin(tmpdir, '*.tsv*'))
    assert len(data_files) == 1
    data_file = data_files[0]
    assert '_recording-' not in data_file

    # read the data file and check the content vs. the PhysioData:
    with gzip.open(data_file, 'rt') as f:
        for idx, line in enumerate(f):
            s = [float(s) for s in line.split('\t')]
            # check that the signals (except for the last, that has the tirgger)
            #   are what we expect:
            assert s[:-1] == [s.signal[idx] for s in myphysiodata_with_trigger.signals[:-1]]
    remove(json_file)
    remove(data_file)

    ###   C) test the case of two different types of sampling rates   ###

    # make the first signal twice as fast:
    myphysiodata_with_trigger.signals[0].samples_per_second *= 2
    myphysiodata_with_trigger.save_to_bids_with_trigger(output_file_name)

    # Check that there are two sets of files, one corresponding to signal[0] and
    #   the other to signal[1]:
    json_files = glob(pjoin(tmpdir, '*.json'))
    assert len(json_files) == 2
    for idx, s in enumerate(myphysiodata_with_trigger.labels()[0:1]):
        json_file = json_files[
            json_files.index(
                '{0}_recording-{1}_physio.json'.format(output_file_name, s)
            )
        ]
        assert json_file in json_files

        # read the json file and check the content vs. the physiodata_with_trigger:
        with open(json_file) as f:
            d = json.load(f)
        assert d['Columns'][0] == s
        assert d['SamplingFrequency'] == myphysiodata_with_trigger.signals[idx].samples_per_second
        assert d['StartTime'] == myphysiodata_with_trigger.signals[idx].t_start()

    # For the data itself, because case B) worked, and the json files contained the
    #   right info, we just make sure that there are two of them:
    data_files = glob(pjoin(tmpdir, '*.tsv*'))
    assert len(data_files) == 2

    # reset the sampling rate for the first signal, in case we need to use
    #   the variable again:
    myphysiodata_with_trigger.signals[0].samples_per_second /= 2
