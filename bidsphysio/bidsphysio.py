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
    """

    def __init__(
            self,
            label=None,
            units="V",
            samples_per_second=None,
            sampling_times=None,
            t_start=None,
            signal=None
            ):
        self.label = label
        self.units = units
        self.samples_per_second = samples_per_second
        self.sampling_times = sampling_times
        # t_start is the time (in seconds) of the first sample with respect to
        #   the first neural sample (MR image, EEG recording, etc.).
        #   A negative number means the physio signal started recording before
        #   the first neural sample.
        self.t_start = t_start
        self.signal = signal
        self.samples_count = len( signal ) if signal is not None else None


    def calculate_trigger_events(self, t_trig):
        """
        Function to calculate the trigger events for a given physiosignal, given
        the timing of the scanner triggers (t_trig)
        """

        trig_signal = np.full( np.shape(self.signal), False )
        for t in t_trig:
            trig_signal[ np.argmax( self.sampling_times >= t ) ] = True
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
                   t_start=mysignal.t_start
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
            len( np.unique([item.t_start            for item in self.signals]) ) == 1
        ),"The different signals have different sampling rates. You can't save them in a single file!"

        # make sure the file name ends with "_physio.json":
        for myStr in ['.json','_physio']:
            json_fName = json_fName[:-len(myStr)] if json_fName.endswith( myStr ) else json_fName
        
        json_fName = json_fName + '_physio.json'

        with open( json_fName, 'w') as f:
            json.dump({
                "SamplingFrequency": self.signals[0].samples_per_second,
                "StartTime": self.signals[0].t_start,
                "Columns": [item.label for item in self.signals],
                **{            # this syntax allows us to add the elements of this dictionary to the one we are creating
                    item.label: {
                        "Units": item.units
                    }
                    for item in self.signals
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
                                   [ [item.samples_per_second,item.t_start] for item in self.signals ],
                                   axis=0,
                                   return_index=True
                               )

        if len(unique_sr_ts) == 1:
            # All the physio signals have the same sampling rate and t_start, so
            #   there will be just one _physio file and we don't need to add "_recording-"
            
            print('')
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
                                                              item.t_start == ts ]
                       )

                print('')
                print('Saving {0} waveform'.format(rec_label))

                hola.save_bids_json(rec_fName)
                hola.save_bids_data(rec_fName)


    def get_trigger_timing(self):
        """
        Returns the timing of the received triggers.
        It finds the first physiosignal labeled 'trigger' in the object and returns
        the times for which the trigger signal is 1
        """

        # list all the signal labels:
        signal_labels = self.labels()

        # physiosignal object corresponding to the trigger:
        trig_physiosignal = self.signals[ signal_labels.index('trigger') ]

        # return timing of the triggers:
        return trig_physiosignal.sampling_times[np.where(trig_physiosignal.signal>0)]


    def save_to_bids_with_trigger(self, bids_fName):
        """
        Rather than saving the triggers as a separate physiological signal, save a column with
        triggers for each list of signals sharing the same timing:
        """

        t_trig = self.get_trigger_timing()

        # find the unique pairs of sampling rate and t_start (and indices):
        unique_sr_ts, idx_un = np.unique(
                                   [ [item.samples_per_second,item.t_start] for item in self.signals ],
                                   axis=0,
                                   return_index=True
                               )

        if len(unique_sr_ts) == 1:
            # All the physio signals have the same sampling rate and t_start, so
            #   there will be just one _physio file and we don't need to add "_recording-"
            
            print('')
            print('Saving physio data')
            self.save_bids_json(bids_fName)
            self.save_bids_data(bids_fName)

        else:

            for idx, [sr,ts] in enumerate( unique_sr_ts ):
                rec_label = self.signals[idx_un[idx]].label

                rec_fName = '{0}_recording-{1}_physio'.format(bids_fName, rec_label)
                # create a new physiodata object with just the signals with matching sampling rate and t_start
                #   (but not if the signal is trigger: we'll add it later).
                hola = physiodata(
                           [ item for item in self.signals if item.samples_per_second == sr and
                                                              item.t_start == ts ]
                       )

                if not 'trigger' in hola.labels():
                    # Find the trigger events for any of them (the timing for all of them is the same)
                    #   and create a new signal with that timing.
                    trigger_signal = physiosignal.matching_trigger_signal(
                                         hola.signals[0],
                                         hola.signals[0].calculate_trigger_events(t_trig)
                                     )
                    # Append this new signal to "hola":
                    hola.append_signal( trigger_signal )

                # At this point, we have at least one signal: 'trigger'. If we only have that one, don't
                #   save it (it will be attached to signals with other sampling rates and t_start). So,
                #   only save "hola" if it has more than one signal:
                if len(hola.labels()) > 1:

                    print('')
                    print('Saving {0} waveform'.format(rec_label))

                    hola.save_bids_json(rec_fName)
                    hola.save_bids_data(rec_fName)

