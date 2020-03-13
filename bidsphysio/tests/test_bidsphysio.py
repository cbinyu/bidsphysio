import pytest
import numpy as np
from bidsphysio import bidsphysio


@pytest.fixture
def mySignal(
        samples_per_second=5,
        physiostarttime=1000,
        samples_count=100
):
    """    Simulate a physiosignal object    """

    mySignal=bidsphysio.physiosignal(
                 label='simulated',
                 samples_per_second=samples_per_second,
                 physiostarttime=physiostarttime,
                 signal= samples_count * [0]     # fill with zeros
             )

    return mySignal


@pytest.fixture
def trigger_timing(
        physiostarttime=1000,
        scannerdelay=2,
        TR=0.75,
        samples_count=100
):
    """   Simulate trigger timing (times at which the triggers were sent   """
    t_first_trigger = physiostarttime + scannerdelay
    trigger_timing = [t_first_trigger + TR * i for i in range(samples_count)]

    return trigger_timing


def test_calculate_trigger_events(
        mySignal, trigger_timing
):
    """
    Make sure you get as many triggers in the trigger signal
    as elements there are in the trigger timing (between the
    beginning of the recording and the end)
    """

    # calculate trigger events:
    trig_signal = mySignal.calculate_trigger_events( trigger_timing )

    assert isinstance(trig_signal, np.ndarray)

    # calculate how many triggers there are between the first and last sampling_times:
    num_trig_within_physio_samples = np.bitwise_and(
                np.array(trigger_timing) >= mySignal.sampling_times[0],
                np.array(trigger_timing) <= mySignal.sampling_times[-1]
    )
    
    assert ( sum(trig_signal) == sum(num_trig_within_physio_samples) )


def test_matching_trigger_signal(
        mySignal,
        trigger_timing
):
    """
    Test that both physiosignals (the original signal and the derived one with the trigger)
    have the same fields.
    It requires the result of "test_calculate_trigger_events"
    """

    # calculate trigger events:
    trig_signal = mySignal.calculate_trigger_events( trigger_timing )

    trigger_physiosignal = bidsphysio.physiosignal.matching_trigger_signal(mySignal, trig_signal)

    assert isinstance(trigger_physiosignal, bidsphysio.physiosignal)
    assert trigger_physiosignal.label == 'trigger'
    assert trigger_physiosignal.samples_per_second == mySignal.samples_per_second
    assert trigger_physiosignal.physiostarttime == mySignal.physiostarttime
    assert trigger_physiosignal.neuralstarttime == mySignal.neuralstarttime
    assert trigger_physiosignal.sampling_times == mySignal.sampling_times
    assert all(trigger_physiosignal.signal == trig_signal)


@pytest.fixture
def mylabels():
    labels=['signal1', 'signal2', 'signal3']

    return labels

@pytest.fixture
def myphysiodata(
        mylabels
):
    """   Create a "physiodata" object   """

    myphysiodata = bidsphysio.physiodata(
                [ bidsphysio.physiosignal( label = l ) for l in mylabels ]
            )
    return myphysiodata


def test_physiodata_labels(
        mylabels,
        myphysiodata
):
    """
    Test both the physiodata constructor and that
    physiodata.labels() returns the labels of the physiosignals
    """

    assert myphysiodata.labels() == mylabels


def test_append_signal(
        mylabels,
        myphysiodata
):
    """
    Tests that "append_signal" does what it is supposed to do
    """

    myphysiodata.append_signal(
        bidsphysio.physiosignal( label = 'extra_signal' )
    )

    mylabels.append('extra_signal')
    assert myphysiodata.labels() == mylabels
