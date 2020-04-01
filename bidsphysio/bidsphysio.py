#!/usr/bin/env python3
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

import numpy as np
import json

class physiosignal(object):
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
        Start time in seconds of the corresponding recording
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
        Function to calculate the trigger events for a given physiosignal, given
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


    @classmethod
    def matching_trigger_signal(cls, mysignal, trigger_s):
        """
        Given a physiosignal object (mysignal), return another one with the same timing but
        with 'signal' the trigger_s
        """

        assert (
            isinstance(mysignal, cls)
        ),"You can only add physiosignals to physiodata"

        return cls(
                   label='trigger',
                   signal=trigger_s,
                   samples_per_second=mysignal.samples_per_second,
                   sampling_times=mysignal.sampling_times,
                   physiostarttime=mysignal.physiostarttime,
                   neuralstarttime=mysignal.neuralstarttime
               )


        
####################

class physiodata(object):
    """
    List of physiological signals. It has its own methods to write to file
    """

    def __init__(
            self,
            signals = None
            ):
        self.signals = signals if signals is not None else []


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
            isinstance(signal, physiosignal)
        ),"You can only add physiosignals to physiodata"

        if hasattr(self,'signals'):
            self.signals.append( signal )
        else:
            self.signals = [signal]
        

    def save_bids_json(self, json_fName):
        """
        Saves the physiodata header information to the BIDS json file.
        It's the responsibility of the calling function to make sure they can all be
        saved in the same fileNone: if all the signals don't have the same sampling rate
        and t_start, it will give an error.
        """

        assert (
            len( np.unique([item.samples_per_second for item in self.signals]) ) == 1 and
            len( np.unique([item.t_start()          for item in self.signals]) ) == 1
        ),"The different signals have different sampling rates. You can't save them in a single file!"

        # make sure the file name ends with "_physio.json":
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
        Saves the physiodata signal to the BIDS .tsv.gz file.
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


    def save_to_bids(self, bids_fName):
        """
        Saves the physiodata sidecar '.json' file(s) and signal(s).
        It saves all signals with the same sampling rate and t_start in a single
        .json/.tsv.gz pair.
        """

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
            self.save_bids_json(bids_fName)
            self.save_bids_data(bids_fName)

        else:

            for idx, [sr,ts] in enumerate( unique_sr_ts ):
                rec_label = self.signals[idx_un[idx]].label

                rec_fName = '{0}_recording-{1}_physio'.format(bids_fName, rec_label)
                # create a new physiodata object with just the signals with matching sampling rate and t_start:
                hola = physiodata(
                           [ item for item in self.signals if item.samples_per_second == sr and
                                                              item.t_start() == ts ]
                       )

                print('Saving {0} waveform'.format(rec_label))
                hola.save_bids_json(rec_fName)
                hola.save_bids_data(rec_fName)

        print('')


    def get_trigger_timing(self):
        """
        Returns the timing of the received triggers.
        It finds the first physiosignal labeled 'trigger' in the object and returns
        the times for which the trigger signal is 1
        """

        # list all the signal labels:
        signal_labels = [l.lower() for l in self.labels()]

        # physiosignal object corresponding to the trigger:
        trig_physiosignal = self.signals[ signal_labels.index('trigger') ]

        # make sure we have the timing of the trigger samples; otherwise, calculate:
        if trig_physiosignal.sampling_times is not []:
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


    def save_to_bids_with_trigger(self, bids_fName):
        """
        Rather than saving the triggers as a separate physiological signal, save a column with
        triggers for each list of signals sharing the same timing:
        """

        # list all the signal labels:
        signal_labels = [l.lower() for l in self.labels()]

        # Sanity check: make sure we have a "trigger" signal
        if 'trigger' not in self.labels():
            print("We cannot save with trigger because we found no trigger.")
            self.save_to_bids(bids_fName)
            return

        # From now on, we do have a trigger
        # physiosignal object corresponding to the trigger:
        trig_physiosignal = self.signals[ signal_labels.index('trigger') ]
        t_trig = self.get_trigger_timing()

        # find the unique pairs of sampling rate and t_start (and indices),
        #   excluding the "trigger" signal (since we'll be interpolating the
        #   trigger to the other signals, if it has different sampling):
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
                rec_fName = bids_fName
                print('Saving physio data')

            else:
                rec_label = self.signals[idx_un[idx]].label
                rec_fName = '{0}_recording-{1}_physio'.format(bids_fName, rec_label)
                print('Saving {0} waveform'.format(rec_label))

            ###   Create group of signals to save   ###

            # Now, create a new physiodata object with the signals for this sampling
            #   rate and t_start as the rest of the signals:
            physiodata_group = physiodata(
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

                trigger_for_this_group = physiosignal.matching_trigger_signal(
                    physiodata_group.signals[0],
                    physiodata_group.signals[0].calculate_trigger_events(t_trig)
                )

                # Append this new signal to "hola":
                physiodata_group.append_signal( trigger_for_this_group )

            ###   Save the data   ###

            physiodata_group.save_bids_json(rec_fName)
            physiodata_group.save_bids_data(rec_fName)

        print('')
