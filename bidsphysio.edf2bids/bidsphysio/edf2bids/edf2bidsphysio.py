"""
Purpose
----
Read eye tracker physio data from an EDF file and return a
BIDS physiology recording object and as BIDS events object.
It uses "pyedfread" to read the EDF file
    
Usage
----
edf2physio.py -i <EDF Eyetracker Physio> -b <BIDS file prefix>
    
Authors
----
Chrysa Papadaniil and Pablo Velasco, NYU Center for Brain Imaging
    
Dates
----
2020-09-04

References
----
EDF reader: https://github.com/nwilming/pyedfread
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

import argparse
import json
import os
import sys
import pandas as pd
import numpy as np

from pyedfread import edf
from pyedfread import edfread

from bidsphysio.base.bidsphysio import (PhysioSignal,
                                        PhysioData)
from bidsphysio.events.eventsbase import (EventSignal,
                                        EventData)

def edf2bids( physio_edf ):
    """Reads the EDF file and saves the continuous eye movement data in a PhysioData member
    
    Parameters
    ----------
    physio_edf : str
        Path to the original EDF file
        
    Returns
    -------
    physio : PhysioData
        PhysioData with the contents of the file
    """
    #Read EDF data into three pandas dataframes
    samples, events, messages = edf.pread(physio_edf)
    
    #First we will work on our physio signal
    #Remove rows that only have zero values
    samples=samples.loc[~(samples==0).all(axis=1)]
    
    #Turn time to seconds and adjust time so that it starts at 0
    samples.time = samples.time/1000
    samples.time = samples.time - samples.time[0]
    
    #Calculate sampling frequency and times from samples.time
    sampling_frequency = np.where(samples.time == 1)[0][0]
    if (sampling_frequency % 10 == 1):
        sampling_frequency = sampling_frequency - 1
    sample_times = samples.time.values.tolist()
    
    # Init physiodata object to hold physio signals
    physio = PhysioData()
    
    #Create a list of the columns we want to keep
    samples = samples.rename(columns={'input': 'trigger'})
    column_list = ["time", "gx_left", "gy_left", "gx_right", "gy_right", "pa_left", "pa_right", "hx_left", "hy_left", "hx_right", "hy_right", "buttons", "trigger"]
    
    #Go through the columns and keep the signals we are interested in. Value -32768.0 indicates missing values
    for wc in range(len(column_list)):
        indc = np.where(column_list[wc]==samples.columns)[0]
        physio_label = samples.columns[indc][0]
        s = samples[samples.columns[indc][0]].values.tolist()
        
        if not ((samples[samples.columns[indc][0]]==0.0).all()
                or (samples[samples.columns[indc][0]]==127.0).all()
                or (samples[samples.columns[indc][0]]==-32768.0).all()):
           
            physio.append_signal(
                PhysioSignal(
                    label=physio_label,
                    samples_per_second = int(sampling_frequency),
                    sampling_times = sample_times,
                    signal = s
                )
            )
    
    # Define neuralstarttime and physiostartime as the first trigger time and first sample time, respectively.
    signal_labels = [l.lower() for l in physio.labels()]
    
    if physio.signals[ signal_labels.index('trigger')]:
        physio.digitize_trigger()
        nstarttime = physio.get_trigger_timing()[0]
        pstartime = samples.time[0]
        for p_signal in physio.signals:
            p_signal.neuralstarttime = nstarttime
            p_signal.physiostartime = pstartime
            # we also fill with NaNs the places for which there is missing data:
            p_signal.plug_missing_data()
    else:
        print('No trigger channel was found')

    return physio

def edfevents2bids(physio_edf):
    """Reads the EDF file and saves the events (fixation, saccades, blinks, experiment messages) in a EventData member
        
    Parameters
    ----------
    physio_edf : str
        Path to the original EDF file
        
    Returns
    -------
    event : EventData
        EventData with the contents of the file
    """
    
    # Get all the different trial marker names. The first 11 elements contain some recording information so we drop them
    trial_markers = np.unique(edfread.read_messages(physio_edf)[11:])
    samples, events, messages = edf.pread(physio_edf)
    
    all_messages = pd.DataFrame()

    for tm in trial_markers:
        samples, events, messages = edf.pread(physio_edf, trial_marker = tm)
        all_messages = all_messages.append(messages, ignore_index = True)
    
    #Turn time to seconds and adjust time so that it starts at 0
    events.start = events.start/1000
    events.start = events.start - samples.time[0]/1000
    events.end = events.end/1000
    events.end = events.end - samples.time[0]/1000

    if not all_messages.empty:
        all_messages = all_messages.dropna(subset=['trialid '])

        all_messages.trialid_time = all_messages.trialid_time/1000
        all_messages.trialid_time = all_messages.trialid_time - samples.time[0]/1000
        # change names of messages columns to be consistent with events columns names
        all_messages.columns = ['start' if x=='trialid_time' else 'message' if x=='trialid ' else x for x in all_messages.columns] ##CHECK if space in trialid always there

        # append messages to events and sort by time
        cols = list(set(events.columns) & set(all_messages.columns))
        events = events.append(all_messages[cols], ignore_index=True)
        events = events.sort_values(by=['start'])
        events.type.fillna(events.message, inplace=True) #move messages to type
    
    #Incorporate blinks to events.type
    events.loc[events['blink'] == True, 'type'] = 'blink'

    #duration = end - start
    duration = events["end"] - events["start"]
    events["duration"] = duration
    events = events.rename(columns={'start': 'onset'}) # rename start to onset

    # Init eventdata object to hold physio signals
    event = EventData()

    #Create a list of the columns we want to keep
    event_column_list = ["onset", "duration", "type", "buttons"]

    for ec in range(len(event_column_list)):
        indc_e = np.where(event_column_list[ec]==events.columns)[0]
        event_label = events.columns[indc_e][0]
        es = events[events.columns[indc_e][0]].values.tolist()
    
        if not (events[events.columns[indc_e][0]]==0.0).all():
            if event_label in {'onset', 'duration'}:
                event_units = 'seconds'
                event_type = 'float'
            else:
                event_type = 'str'  #button?
                event_units = ""

            if event_label == 'type':
                event_description = 'Can be saccade, fixation, blink or the name of a sent message'
            else:
                event_description = None
                
            event.append_event(
                EventSignal(
                    label=event_label,
                    units = event_units,
                    description = event_description,
                    event = es,
                    type = event_type
                )
            )

    return event

def main():
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert Eyetracker EDF physiology files to BIDS-compliant physiology recording')
    parser.add_argument('-i', '--infile', required=True, help='SR research eye tracker EDF file')
    parser.add_argument('-b', '--bidsprefix', required=True, help='Prefix of the BIDS file. It should match the _bold.nii.gz')
    args = parser.parse_args()
    
    # make sure input file exists:
    if not os.path.exists(args.infile):
        raise FileNotFoundError( '{i} file not found'.format(i=args.infile))
    
    # make sure output directory exists:
    odir = os.path.dirname(args.bidsprefix)
    if not os.path.exists(odir):
        os.makedirs(odir)
    
    physio_data = edf2bids( args.infile )
    event_data = edfevents2bids ( args.infile )
    if physio_data.labels():
        physio_data.save_to_bids_with_trigger(args.bidsprefix)
    event_data.save_events_to_bids(args.bidsprefix)

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()


