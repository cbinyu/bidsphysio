import numpy as np
from bidsphysio import bidsphysio


def simulate_signal_and_trigger(
        samples_per_second=1,
        physiostarttime=0,
        samples_count=1
        ):
    """
    Simulate a physiosignal object and the timing for the scanner triggers.
    It's used by some of the tests below.
    """

    # simulate signal:
    mySignal=bidsphysio.physiosignal(
                 label='simulated',
                 samples_per_second=samples_per_second,
                 physiostarttime=physiostarttime,
                 signal= samples_count * [0]     # fill with zeros
             )

    # simulate scanner trigger (times at which the triggers were sent, according
    #   to the reference clock).
    # Let's assume the first sample is collected 2 sec after physio recording started:
    t_first_trigger = physiostarttime + 2
    TR = 0.75   # in s
    trigger_timing = [t_first_trigger + TR * i for i in range(samples_count)]

    return mySignal, trigger_timing


def test_calculate_trigger_events():
    """
    Make sure you get as many triggers in the trigger signal
    as elements there are in the trigger timing (between the
    beginning of the recording and the end)
    """

    # simulate signal at 5 Hz, starting at time 1000 sec (according to some
    #   clock)
    mysignal, trigger_timing =simulate_signal_and_trigger(
                 samples_per_second=5,
                 physiostarttime=1000,
                 samples_count=100
             )

    # calculate trigger events:
    trig_signal = mysignal.calculate_trigger_events( trigger_timing )

    assert isinstance(trig_signal, np.ndarray)

    # calculate how many triggers there are between the first and last sampling_times:
    num_trig_within_physio_samples = np.bitwise_and(
                np.array(trigger_timing) >= mysignal.sampling_times[0],
                np.array(trigger_timing) <= mysignal.sampling_times[-1]
    )
    
    assert ( sum(trig_signal) == sum(num_trig_within_physio_samples) )


def test_matching_trigger_signal():
    """
    Test that both physiosignals (the original signal and the derived one with the trigger)
    have the same fields.
    """

    # simulate signal at 5 Hz, starting at time 1000 sec (according to some
    #   clock)
    mysignal, trigger_timing =simulate_signal_and_trigger(
                 samples_per_second=5,
                 physiostarttime=1000,
                 samples_count=10
             )

    # calculate trigger events:
    trig_signal = mysignal.calculate_trigger_events( trigger_timing )

    trigger_physiosignal = bidsphysio.physiosignal.matching_trigger_signal(mysignal, trig_signal)

    assert isinstance(trigger_physiosignal, bidsphysio.physiosignal)
    assert trigger_physiosignal.label == 'trigger'
    assert trigger_physiosignal.samples_per_second == mysignal.samples_per_second
    assert trigger_physiosignal.physiostarttime == mysignal.physiostarttime
    assert trigger_physiosignal.neuralstarttime == mysignal.neuralstarttime
    assert trigger_physiosignal.sampling_times == mysignal.sampling_times
    assert all(trigger_physiosignal.signal == trig_signal)


def test_physiodata_labels():
    """
    Test that physiodata.labels() returns the labels of the physiosignals
    """

    myphysiodata = bidsphysio.physiodata(
        [
            bidsphysio.physiosignal( label = 'signal1' ),
            bidsphysio.physiosignal( label = 'signal2' ),
            bidsphysio.physiosignal( label = 'signal3' )
        ]
    )

    assert myphysiodata.labels() == ['signal1','signal2','signal3']


