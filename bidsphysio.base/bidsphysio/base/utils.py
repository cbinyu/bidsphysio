import gzip
import json
from pathlib import Path

import numpy as np


def check_bidsphysio_outputs(outPrefix,
                             expectedPhysioLabels,
                             expectedDataFilePrefix,
                             ):
    """
    Auxiliary function to check the output of running dcm2bids

    Parameters
    ----------
    outPrefix : Path or str
        Prefix of the path of the output of dcm2bids (the bidsprefix arg).
        E.g.: '/tmp/mydir/sub-01_task-rest'
    expectedPhysioLabels : list
        List with the expected physio labels
    expectedDataFilePrefix : Path or str or None
        Prefix of the path to the file with the expected data
        (If we don't need to check the results, set to None)
        If there is only one expectedPhysioLabel, the expectedDataFilePrefix
        must be the whols file path (including extension)

    Returns
    -------

    """
    outPrefix = Path(outPrefix)
    if not isinstance(expectedPhysioLabels, list):
        expectedPhysioLabels = [expectedPhysioLabels]

    json_files = sorted(outPrefix.parent.glob('*.json'))
    data_files = sorted(outPrefix.parent.glob('*.tsv*'))
    assert len(json_files) == len(data_files) == len(expectedPhysioLabels)

    for label in expectedPhysioLabels:
        if len(expectedPhysioLabels) == 1:
            expectedFileBaseName = Path(outPrefix).name + '_physio'
        else:
            expectedFileBaseName = Path(str(outPrefix) + '_recording-' + ''.join(label) + '_physio').name
        expectedFileName = outPrefix.parent / expectedFileBaseName
        assert expectedFileName.with_suffix('.json') in json_files
        assert expectedFileName.with_suffix('.tsv.gz') in data_files

        # check content of the json file:
        with open(expectedFileName.with_suffix('.json')) as f:
            d = json.load(f)
            if isinstance(label, list):
                for c in d['Columns']:
                    assert c in label or c == 'trigger'
            else:
                assert d['Columns'] == [label, 'trigger']

        # check content of the tsv file:
        if expectedDataFilePrefix:
            expectedDataFilePrefix = Path(expectedDataFilePrefix)
            if len(expectedPhysioLabels) == 1:
                expectedDataFile = expectedDataFilePrefix.with_suffix('.tsv')
                expectedJsonFile = expectedDataFilePrefix.with_suffix('.json')
            else:
                expectedDataFile = str(expectedDataFilePrefix) + ''.join(label) + '.tsv'
                expectedJsonFile = str(expectedDataFilePrefix) + ''.join(label) + '.json'
            with open(expectedJsonFile) as f:
                expected_d = json.load(f)
            assert d['SamplingFrequency'] == expected_d['SamplingFrequency']
            if 'StartTime' in d:
                assert d['StartTime'] == expected_d['StartTime']

            with open(expectedDataFile, 'rt') as expected, \
                    gzip.open(expectedFileName.with_suffix('.tsv.gz'), 'rt') as f:
                for expected_line, written_line in zip(expected, f):
                    assert expected_line == written_line


def get_physio_TRs(bids_prefix):
    """
    Get the TRs from the triggers of BIDS physiology files

    Parameters
    ----------
    bids_prefix : Path or str
        Prefix of the path of the BIDS physio files.
        E.g.: '/tmp/mydir/sub-01_task-rest'

    Returns
    -------
    TRs : list
        List with the TRs of the files found

    """
    bids_prefix = Path(bids_prefix)

    json_files = sorted(bids_prefix.parent.glob('*.json'))
    data_files = sorted(bids_prefix.parent.glob('*.tsv*'))

    TRs = []
    for j_file, d_file in zip(json_files, data_files):
        # check that we have a trigger column:
        with open(j_file) as f:
            d = json.load(f)
        if 'trigger' not in d['Columns']:
            pass

        # we have a trigger column:
        # get the triggers from the data itself:
        trig_column = d['Columns'].index('trigger')
        freq = d['SamplingFrequency']
        trigger = np.genfromtxt(fname=d_file, delimiter="\t")[:, trig_column]
        trigger_indices = np.nonzero(trigger)
        if not trigger_indices:
            tr = float('NaN')
        else:
            tr = np.mean(np.diff(trigger_indices) / freq)
        TRs.append(tr)

    return TRs
