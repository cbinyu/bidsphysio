"""
Purpose
----
Define a class of physiological data

Author
----
Pablo Velasco, NYU Center for Brain Imaging

Dates
----
2020-02-26 PJV 

References
----
BIDS specification for physio signal:
https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/06-physiological-and-other-continuous-recordings.html

License
----
MIT License

Copyright (c) 2020      Pablo Velasco

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import json

import numpy as np


class PhysioSignal(object):
    """
    Individual physiology signal (e.g., pulse, respiration, etc.)

    Members:
    --------
    label : str
        physiological recording label (e.g., 'cardiac', 'respiratory', 'pulse', etc.)
    units : str
    samples_per_second : number
    sampling_times : list of numbers
        times (in seconds) at which the samples were acquired
    physiostarttime : number
        Start time in seconds of the physiological recording.
        Uses the same clock as 'neuralstarttime'
    neuralstarttime : number
        Start time in seconds of the corresponding neural recording
        (MRI, EEG, etc.)
        Uses the same clock as 'physiostarttime'
    signal : list of numbers
        The physiological signal proper
    t_start : number
        BIDS definition: Start time in seconds in relation to the start
        of acquisition of the first data sample in the corresponding neural
        dataset (negative values are allowed). It is calculated when needed
    """

    def __init__(
            self,
            label=None,
            units="",
            samples_per_second=None,
            sampling_times=[],
            physiostarttime=0,
            neuralstarttime=0,
            signal=[]
            ):
        self.label = label
        self.units = units
        self.samples_per_second = samples_per_second
        self.sampling_times = sampling_times
        self.physiostarttime = physiostarttime
        self.neuralstarttime = neuralstarttime
        self.signal = signal
        self.samples_count = len( signal ) if signal is not [] else None

    def t_start( self ):
        """
        Computes the BIDS t_start (offset between the beginning of the neural signal and the beginning
        of the physiological recording), in seconds
        I round it to the ms
        """
        try:
            t_start_ms = 1000*(self.physiostarttime - self.neuralstarttime)
            # round to the ms:
            return int(t_start_ms) / 1000
        except ValueError:
            pass

    def calculate_timing( self ):
        """
        Calculate the recording timing, based on the physiostarttime
        and the sampling rate
        """
        if self.samples_per_second == None or self.physiostarttime == None:
            raise ValueError('Unable to calculate the recording timing')
        else:
            self.sampling_times = [self.physiostarttime + i/self.samples_per_second for i in range(len(self.signal))]

    def calculate_trigger_events(self, t_trig):
        """
        Function to calculate the trigger events for a given PhysioSignal, given
        the timing of the scanner triggers (t_trig)
        """

        if self.sampling_times is not []:
            try:
                self.calculate_timing()
            except Exception as e:
                print(e)
                return None

        sampling_times = np.array(self.sampling_times)
        trig_signal = np.full( np.shape(self.signal), False )    # initialize to "False"
        for t in t_trig:
            if t >= self.sampling_times[0] and t <= self.sampling_times[-1]:
                trig_signal[np.argmax( sampling_times >= t )] = True
        return trig_signal

    def plug_missing_data(self, missing_value=np.nan):
        """
        Function to plug "missing_value" (NaN, by default) wherever the
        signal was not recorded.
        """

        # The time increment between samples:
        dt = 1/self.samples_per_second

        # The following finds the first index for which the difference between
        #   consecutive elements is larger than dt (plus a small rounding error)
        # (argmax stops at the first "True"; if it doesn't find any, it returns 0):
        i = np.argmax( np.ediff1d(self.sampling_times) > dt*(1.001) )
        while i != 0:
            # new time array, which adds the missing timepoint:
            self.sampling_times = np.concatenate(
                # Note: np.concatenate takes a list as argument, so you need (...)
                (self.sampling_times[:i+1], [self.sampling_times[i]+dt], self.sampling_times[i+1:])
            )
            # new signal array, which adds a "missing_value" at the missing timepoint:
            self.signal = np.concatenate(
                # Note: np.concatenate takes a list as argument, so you need (...)
                (self.signal[:i+1], [missing_value], self.signal[i+1:])
            )
            # check to see if we are done:
            i = np.argmax( np.ediff1d(self.sampling_times) > dt*(1.001) )

        self.samples_count = len( self.signal )

    @classmethod
    def matching_trigger_signal(cls, mysignal, trigger_s):
        """
        Given a PhysioSignal object (mysignal), return another one with the same timing but
        with 'signal' the trigger_s
        """

        assert (
            isinstance(mysignal, cls)
        ), "You can only add PhysioSignals to PhysioData"

        return cls(
                   label='trigger',
                   signal=trigger_s,
                   samples_per_second=mysignal.samples_per_second,
                   sampling_times=mysignal.sampling_times,
                   physiostarttime=mysignal.physiostarttime,
                   neuralstarttime=mysignal.neuralstarttime
               )


####################

class PhysioData(object):
    """
    List of physiological signals. It has its own methods to write to file
    """

    def __init__(
            self,
            signals = None,
            bidsPrefix = None
            ):
        self.signals = signals if signals is not None else []
        self.bidsPrefix = bidsPrefix

    def labels(self):
        """
        Returns a list with the labels of all the object signals
        """
        return [ item.label for item in self.signals ]

    def append_signal(self, signal):
        """
        Appends a new signal to the signals list
        """
        assert (
            isinstance(signal, PhysioSignal)
        ), "You can only add PhysioSignals to PhysioData"

        if hasattr(self,'signals'):
            self.signals.append( signal )
        else:
            self.signals = [signal]

    def set_bidsPrefix(self, bidsPrefix):
        """
        Sets the bidsPrefix attribute for the class
        """

        # remove '_bold.nii(.gz)' or '_physio' if present **at the end of the bidsPrefix**
        # (This is a little convoluted, but we make sure we don't delete it if
        #  it happens in the middle of the string)
        for mystr in ['.gz', '.nii', '_bold', '_physio']:
            bidsPrefix = bidsPrefix[:-len(mystr)] if bidsPrefix.endswith(mystr) else bidsPrefix

        # Whatever is left, we assign to the bidsPrefix class attribute:
        self.bidsPrefix = bidsPrefix

    def save_bids_json(self, json_fName):
        """
        Saves the PhysioData header information to the BIDS json file.
        It's the responsibility of the calling function to make sure they can all be
        saved in the same fileNone: if all the signals don't have the same sampling rate
        and t_start, it will give an error.
        """

        assert (
            len( np.unique([item.samples_per_second for item in self.signals]) ) == 1 and
            len( np.unique([item.t_start()          for item in self.signals]) ) == 1
        ),"The different signals have different sampling rates. You can't save them in a single file!"

        # make sure the file name ends with "_physio.json" by removing it (if present)
        #   and adding it back:
        for myStr in ['.json','_physio']:
            json_fName = json_fName[:-len(myStr)] if json_fName.endswith( myStr ) else json_fName
        json_fName = json_fName + '_physio.json'

        with open( json_fName, 'w') as f:
            json.dump({
                "SamplingFrequency": self.signals[0].samples_per_second,
                "StartTime": self.signals[0].t_start(),
                "Columns": [item.label for item in self.signals],
                **{            # this syntax allows us to add the elements of this dictionary to the one we are creating
                    item.label: {
                        "Units": item.units
                    }
                    for item in self.signals if item.units != ""
                }
            }, f, sort_keys = True, indent = 4, ensure_ascii = False)
            f.write('\n')

    def save_bids_data(self, data_fName):
        """
        Saves the PhysioData signal to the BIDS .tsv.gz file.
        It's the responsibility of the calling function to make sure they can all be
        saved in the same file: if all the signals don't have the same number of points,
        it will give an error.
        """

        assert (
            len( np.unique([item.samples_count for item in self.signals]) ) == 1
        ),"The different signals have different number of samples. You can't save them in a single file!"

        # make sure the file name ends with "_physio.tsv.gz":
        for myStr in ['.gz','.tsv','_physio']:
            if data_fName.endswith( myStr ):
                data_fName = data_fName[:-len(myStr)]
        
        data_fName = data_fName + '_physio.tsv.gz'

        # Save the data:
        # Format: 4 decimals in general, unsigned integer if 'trigger':
        myFmt=['% 1d' if item.label == 'trigger' else '%.4f' for item in self.signals]
        np.savetxt(
            data_fName,
            np.transpose( [item.signal for item in self.signals] ),
            fmt=myFmt,
            delimiter='\t'
        )

    def save_to_bids(self, bids_fName=None):
        """
        Saves the PhysioData sidecar '.json' file(s) and signal(s).
        It saves all signals with the same sampling rate and t_start in a single
        .json/.tsv.gz pair.
        """

        if bids_fName:
            # if bids_fName argument is passed, use it:
            self.set_bidsPrefix(bids_fName)
        else:
            # otherwise, check to see if there is already a 'bidsPrefix'
            # for this instance of the class. If neither of them is
            # present, return an error:
            if not self.bidsPrefix:
                raise Exception('fileName was not a known provided')

        # find the unique pairs of sampling rate and t_start (and indices):
        unique_sr_ts, idx_un = np.unique(
                                   [ [item.samples_per_second,item.t_start()] for item in self.signals ],
                                   axis=0,
                                   return_index=True
                               )

        print('')

        if len(unique_sr_ts) == 1:
            # All the physio signals have the same sampling rate and t_start, so
            #   there will be just one _physio file and we don't need to add "_recording-"

            print('Saving physio data')
            self.save_bids_json(self.bidsPrefix)
            self.save_bids_data(self.bidsPrefix)

        else:

            for idx, [sr,ts] in enumerate( unique_sr_ts ):
                rec_label = self.signals[idx_un[idx]].label

                rec_fName = '{0}_recording-{1}_physio'.format(self.bidsPrefix, rec_label)
                # create a new PhysioData object with just the signals with matching sampling rate and t_start:
                hola = PhysioData(
                           [ item for item in self.signals if item.samples_per_second == sr and
                                                              item.t_start() == ts ]
                       )

                print('Saving {0} waveform'.format(rec_label))
                hola.save_bids_json(rec_fName)
                hola.save_bids_data(rec_fName)

        print('')

    def digitize_trigger(self, ignore_values=None):
        """
        Finds the high and low states of a trigger channel and returns the timing of the received triggers.
        It finds the first physiosignal labeled 'trigger' in the object and returns the times for which the trigger signal is high (a value of 1 means high, a value of 0 means low).
        """
        
        # list all the signal labels:
        signal_labels = [l.lower() for l in self.labels()]
        
        # physiosignal object corresponding to the trigger:
        trig_physiosignal = self.signals[ signal_labels.index('trigger') ]
        
        # make sure we have the timing of the trigger samples; otherwise, calculate:
        if len(trig_physiosignal.sampling_times) == 0:
            try:
                trig_physiosignal.calculate_timing()
            except Exception as e:
                print(e)
                return None
        
        # check if we have any ignore_values, and if we do set them to NaN
        if ignore_values:
            for i in ignore_values:
                trig_physiosignal.signal[trig_physiosignal.signal == i] = np.nan
        
        #make a histogram of trigger values with 10 bins between the min and max values
        tmp = np.array(trig_physiosignal.signal)
        counts, bin_edges = np.histogram(tmp[~np.isnan(tmp)], bins=10, range=[min(trig_physiosignal.signal), max(trig_physiosignal.signal)])
        
        # find the middle values of the two bins with the most counts, we consider these two bins to contain the low a and high trigger values
        first_bin = bin_edges[np.argmax(counts)] + (bin_edges[1]-bin_edges[0])/2
        counts[np.argmax(counts)]=0
        second_bin = bin_edges[np.argmax(counts)] + (bin_edges[1]-bin_edges[0])/2
        
        # define the cuttoff threshold as the mean value between the low and high values (the middle of the corresponding bins), and convert the high states to 1s and the low states to 0s
        threshold=(first_bin + second_bin)/2
        
        #digitize
        tmp_signal = tmp
        tmp_signal[tmp<threshold] = 0
        tmp_signal[tmp>threshold] = 1
        tmp_signal[np.isnan(tmp)] = 0
        
        #assign the digitized trigger signal back to the physiosignal object
        trig_physiosignal.signal = tmp_signal.tolist()
        self.signals[ signal_labels.index('trigger') ] = trig_physiosignal

    def get_trigger_timing(self):
        """
        Returns the timing of the received triggers.
        It finds the first PhysioSignal labeled 'trigger' in the object and returns
        the times for which the trigger signal is 1
        """

        # list all the signal labels:
        signal_labels = [l.lower() for l in self.labels()]

        # PhysioSignal object corresponding to the trigger:
        trig_physiosignal = self.signals[ signal_labels.index('trigger') ]

        # make sure we have the timing of the trigger samples; otherwise, calculate:
        if len(trig_physiosignal.sampling_times) == 0:
            try:
                trig_physiosignal.calculate_timing()
            except Exception as e:
                print(e)
                return None

        # get indices for which the trigger was on (>0):
        trig_indices = np.where(np.array(trig_physiosignal.signal)>0)

        # to extract more than one element from the list of sampling times,
        #   we convert it to a numpy array and pass the trig_indices:
        trigger_timing = np.array(trig_physiosignal.sampling_times)[trig_indices]
        # return timing of the triggers as a list:
        return list(trigger_timing)

    def get_scanner_onset(self):
        """
        Get the time of the first trigger in the PhysioData
        """
        # TODO: maybe there is more than one scanner run in this file.
        #       If that's the case, you can get the onsets, maybe by
        #       checking the mean/mode timing between triggers, and decide
        #       a run is finished when there is a gap of more than 3x
        #       the mean/mode. That way you can get all the onsets
        return self.get_trigger_timing()[0]

    def save_to_bids_with_trigger(self, bids_fName=None):
        """
        Rather than saving the triggers as a separate physiological signal, save a column with
        triggers for each list of signals sharing the same timing:
        """

        if bids_fName:
            # if bids_fName argument is passed, use it:
            self.set_bidsPrefix(bids_fName)
        else:
            # otherwise, check to see if there is already a 'bidsPrefix'
            # for this instance of the class. If neither of them is
            # present, return an error:
            if not self.bidsPrefix:
                raise Exception('fileName was not a known provided')

        # list all the signal labels:
        signal_labels = [l.lower() for l in self.labels()]

        # Sanity check: make sure we have a "trigger" signal
        if 'trigger' not in self.labels():
            print("We cannot save with trigger because we found no trigger.")
            self.save_to_bids()
            return

        # From now on, we do have a trigger
        # PhysioSignal object corresponding to the trigger:
        trig_physiosignal = self.signals[ signal_labels.index('trigger') ]
        t_trig = self.get_trigger_timing()

        # find the unique pairs of sampling rate and t_start (and indices),
        #   excluding the "trigger" signal (since we'll be interpolating the
        #   trigger to the other signals, if it has different sampling):
        labels_no_trigger = [l for l in self.labels() if not l.lower() == 'trigger']
        unique_sr_ts, idx_un = np.unique(
            [[s.samples_per_second,s.t_start()] for s in self.signals if not s.label.lower() == 'trigger'],
            axis=0,
            return_index=True
        )
        print('')

        for idx, [sr,ts] in enumerate( unique_sr_ts ):

            ###   Get filename   ###

            if len(unique_sr_ts) == 1:
                # All the physio signals (except, potentially, the "trigger") have the
                #   same sampling rate and t_start, there will be just one _physio file
                #   and we don't need to add "_recording-":
                rec_fName = self.bidsPrefix
                print('Saving physio data')

            else:
                rec_label = labels_no_trigger[idx_un[idx]]
                rec_fName = '{0}_recording-{1}_physio'.format(self.bidsPrefix, rec_label)
                print('Saving {0} waveform'.format(rec_label))

            ###   Create group of signals to save   ###

            # Now, create a new PhysioData object with the signals for this sampling
            #   rate and t_start as the rest of the signals:
            physiodata_group = PhysioData(
                [ s for s in self.signals if (
                    s.samples_per_second == sr and
                    s.t_start() == ts
                  )
                ]
            )

            # Now, because we excluded the "trigger" from the unique_sr_ts calculation,
            #   we need to check whether it has the same sampling rate and t_start or not.
            #   If it does, the "trigger" signal has been already included in physiodata_group.
            #   If not, we need to create a new trigger signal interpolated to the sampling
            #   rate and t_start of this group:
            if not (trig_physiosignal.samples_per_second == sr and
                    trig_physiosignal.t_start()          == ts):

                trigger_for_this_group = PhysioSignal.matching_trigger_signal(
                    physiodata_group.signals[0],
                    physiodata_group.signals[0].calculate_trigger_events(t_trig)
                )

                # Append this new signal to "physiodata_group":
                physiodata_group.append_signal( trigger_for_this_group )

            ###   Save the data   ###

            physiodata_group.save_bids_json(rec_fName)
            physiodata_group.save_bids_data(rec_fName)

        print('')
