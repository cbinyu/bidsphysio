"""   Tests for the module "eventsbase.py"   """

import copy
from glob import glob
import gzip
import json
import random
import string
from os.path import join as pjoin

import numpy as np
import pytest

from bidsphysio.events.eventsbase import (EventSignal,
                                          EventData)

###  Globals   ###
EVENT_SAMPLES_COUNT = 1000
LABELS = ['signal1', 'signal2'] # signal1 contains numbers, signal2 contains strings
LENGTH = 8

def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

###   TESTS FOR CLASS "EventSignal"   ###

@pytest.fixture
def myEvent(scope="module"):
    """    Simulate an EventSignal object    """
    
    myEvent = EventSignal(
        label='simulated',
        event=EVENT_SAMPLES_COUNT * [0],
        type=None
    )
                            
    return myEvent


###   TESTS FOR CLASS "EventData"   ###

@pytest.fixture
def myeventdata(scope="module"):
    """   Create a "EventData" object with barebones content  """
    
    myeventdata = EventData(
        [EventSignal(
            label=l,
            event=np.random.uniform(size=(EVENT_SAMPLES_COUNT,)),
            type='float'
        ) for l in LABELS]
    )
    
    myeventdata.events[1].type = 'str'
    myeventdata.events[1].event = [get_random_string(LENGTH) for i in range(EVENT_SAMPLES_COUNT)]
    
    return myeventdata

def test_eventdata_labels(
        myeventdata
):
    """
    Test both the EventData constructor and that
    EventData.labels() returns the labels of the EventSignals
    """
    
    assert myeventdata.labels() == LABELS

def test_append_event(
        myeventdata
):
    """
    Tests that "append_event" does what it is supposed to do
    """
    
    # Make a copy of myeventdata to make sure we don't modify it,
    #  so that it is later available unmodified to other tests:
    evdata = copy.deepcopy(myeventdata)
    evdata.append_event(
        EventSignal(label='extra_event')
    )
        
    mylabels = LABELS.copy()
    mylabels.append('extra_event')
    assert evdata.labels() == mylabels

def test_save_events_bids_json(
        tmpdir,
        myeventdata
):
    """
    Tests  "save_events_bids_json"
    """
    
    json_file_name = pjoin(tmpdir.strpath, 'foo.json')
    
    # make sure the filename ends with "_events.json"
    myeventdata.save_events_bids_json(json_file_name)
    json_files = glob(pjoin(tmpdir, '*.json'))
    assert len(json_files) == 1
    json_file = json_files[0]
    assert json_file.endswith('_events.json')
    
    # read the json file and check the content vs. the EventData:
    with open(json_file) as f:
        d = json.load(f)
    assert d['Columns'] == LABELS
    # ADD MORE CHECKS IF I ADD MORE ATTRIBUTES TO EVENTSIGNAL

def test_save_events_bids_data(
        tmpdir,
        myeventdata
):
    """
    Tests  "save_events_bids_data"
    """
    data_file_name = pjoin(tmpdir.strpath, 'foo.tsv')
    
    # make sure the filename ends with "_events.tsv.gz"
    myeventdata.save_events_bids_data(data_file_name)
    data_files = glob(pjoin(tmpdir, '*.tsv*'))
    assert len(data_files) == 1
    data_file = data_files[0]
    assert data_file.endswith('_events.tsv.gz')
    
    # read the data file and check the content vs. the EventData:
    with gzip.open(data_file, 'rt') as f:
        for idx, line in enumerate(f):
            assert [float(s) for s in line.split('\t')] == [s.signal[idx] for s in myeventdata.events]

def test_save_events_to_bids(
        tmpdir,
        myeventdata
):
    """
    Test "save_events_to_bids"
    """
    output_file_name = pjoin(tmpdir.strpath, 'foo')
    
    # when all sample rates and t_starts are the same, there should be only one
    #   (.sjon/.tsv.gz) pair:
    myeventdata.save_events_to_bids(output_file_name)
    json_files = glob(pjoin(tmpdir, '*.json'))
    assert len(json_files) == 1
    json_file = json_files[0]
    assert json_file.endswith('_events.json')
    data_files = glob(pjoin(tmpdir, '*.tsv*'))
    assert len(data_files) == 1
    data_file = data_files[0]
    assert data_file.endswith('_events.tsv.gz')
