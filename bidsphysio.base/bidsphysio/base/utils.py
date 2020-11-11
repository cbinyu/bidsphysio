import gzip
import json
from pathlib import Path


def check_bidsphysio_outputs(outPrefix,
                             expectedPhysioLabels,
                             expectedFrequencies,
                             expectedDelay,
                             expectedFilePrefix,
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
    expectedDelay : float
        Expected delay for the physio signals (in sec.)
    expectedCardiacFreq : float
        Expected frequency of the cardiac recording (in Hz.)
    expectedRespFreq : float
        Expected frequency of the respiratory recording (in Hz.)
    expectedFilePrefix : Path or str or None
        Prefix of the path to the file with the expected results
        (If we don't need to check the results, set to None)

    Returns
    -------

    """
    outPrefix = Path(outPrefix)
    if not isinstance(expectedPhysioLabels, list):
        expectedPhysioLabels = [expectedPhysioLabels]
    if not isinstance(expectedFrequencies, list):
        expectedFrequencies = [expectedFrequencies]

    json_files = sorted(outPrefix.parent.glob('*.json'))
    data_files = sorted(outPrefix.parent.glob('*.tsv*'))
    assert len(json_files) == len(data_files) == len(expectedPhysioLabels)

    for label, expFreq in zip(expectedPhysioLabels, expectedFrequencies):
        expectedFileBaseName = Path(str(outPrefix) + '_recording-' + label + '_physio')
        expectedFileName = outPrefix.parent / expectedFileBaseName
        assert expectedFileName.with_suffix('.json') in json_files
        assert expectedFileName.with_suffix('.tsv.gz') in data_files

        # check content of the json file:
        with open(expectedFileName.with_suffix('.json')) as f:
            d = json.load(f)
            assert d['Columns'] == [label, 'trigger']
            assert d['StartTime'] == expectedDelay
            assert d['SamplingFrequency'] == expFreq

        # check content of the tsv file:
        if expectedFilePrefix:
            with open(str(expectedFilePrefix) + label + '.tsv', 'rt') as expected, \
                    gzip.open(expectedFileName.with_suffix('.tsv.gz'), 'rt') as f:
                for expected_line, written_line in zip(expected, f):
                    assert expected_line == written_line
