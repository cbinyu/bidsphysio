#!/usr/bin/env python3
"""
Purpose
----
Read physio data from saved from a Siemens scanner using the PMU system and
save it as BIDS physiology recording file
Tested on a Prisma scanner running VE11C 

Usage
----
pmu2bidsphysio -i <Siemens PMU Physio file(s)> -b <BIDS file prefix>


Author
----
Pablo Velasco, NYU Center for Brain Imaging

Dates
----
2020-03-02 PJV

References
----
BIDS specification for physio signal:
https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/06-physiological-and-other-continuous-recordings.html
Notes on the HPC physio timing (you should use MDHTime, not MPCUTime):
https://wiki.humanconnectome.org/display/PublicData/Understanding+Timing+Information+in+HCP+Physiological+Monitoring+Files

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
import math
import os
import re
import sys

from bidsphysio.base.bidsphysio import (PhysioSignal,
                                        PhysioData)


def errmsg(msg, pmuFile, expStr=None, gotStr=None):
    msg = msg.replace('%r', repr(pmuFile))
    if expStr and gotStr:
        formattedMsg = '{msg}: Expected: {expStr}; got: {gotStr}'
        return formattedMsg.format(msg=msg, expStr=repr(expStr), gotStr=repr(gotStr))
    else:
        return msg


class PMUFormatError(ValueError):
    """
    Subclass of ValueError with the following additional properties:
    msg    : The unformatted error message
    pmuFile: The PMU file being parsed
    expStr : The string we expected
    gotStr : The string that didn't match what we expected
    """
    def __init__(self, msg, pmuFile, expStr=None, gotStr=None):
        ValueError.__init__(self, errmsg(msg, pmuFile, expStr, gotStr))
        self.msg = msg
        self.pmuFile = pmuFile
        self.mystr = expStr
        self.gotStr = gotStr

    def __reduce__(self):
        return self.__class__, (self.msg, self.pmuFile, self.expStr, self.gotStr)



def pmu2bids( physio_files, bids_prefix, verbose=False ):
    """
    Function to read a list of Siemens PMU physio files and
    save them as a BIDS physiological recording.

    Parameters
    ----------
    physio_files : list of str
        list of paths to files with a Siemens PMU recording
    bids_prefix : str
        string with the BIDS filename to save the physio signal (full path)

    Returns
    -------

    """

    # In case we are handled just a single file, make it a one-element list:
    if isinstance(physio_files, str):
        physio_files = [physio_files]
    
    # Init PhysioData object to hold physio signals:
    physio = PhysioData()

    # Read the files from the list, extract the relevant information and
    #   add a new PhysioSignal to the list:
    for f in physio_files:
        physio_type, MDHTime, sampling_rate, physio_signal = readpmu( f, verbose=verbose )

        testSamplingRate(
                            sampling_rate = sampling_rate,
                            Nsamples = len(physio_signal),
                            logTimes=MDHTime
        )

        # specify label:
        if 'PULS' in physio_type:
            physio_label = 'cardiac'

        elif 'RESP' in physio_type:
            physio_label = 'respiratory'

        elif "TRIGGER" in physio_type:
            physio_label = 'trigger'

        else:
            physio_label = physio_type

        physio.append_signal(
            PhysioSignal(
                label=physio_label,
                units='',
                samples_per_second=sampling_rate,
                physiostarttime=MDHTime[0],
                signal=physio_signal
            )
        )

    # Save files:
    physio.save_to_bids_with_trigger( bids_prefix )

    return


def readpmu( physio_file, softwareVersion=None, verbose=False ):
    """
    Function to read the physiological signal from a Siemens PMU physio file
    It would try to open the knew formats (currently, VB15A, VE11C)

    Parameters
    ----------
    physio_file : str
        path to a file with a Siemens PMU recording
    softwareVersion : str or None (default)
        Siemens scanner software version
        If None (default behavior), it will try all known versions

    Returns
    -------
    physio_type : str
        type of physiological recording
    MDHTime : list
        list of two integers indicating the time in ms since last midnight.
        MDHTime[0] gives the start of the recording
        MDHTime[1] gives the end   of the recording
    sampling_rate : int
        number of samples per second
    physio_signal : list of int
        signal proper. NaN indicate points for which there was no recording
        (the scanner found a trigger in the signal)
    """

    # Check for known software versions:
    knownVersions = [ 'VB15A', 'VE11C', 'VBX' ]

    if not (
            softwareVersion in knownVersions or
            # (if None, we'll try all knownVersions)
            softwareVersion == None
           ):
        raise Exception("{sv} is not a known software version.".format(sv=softwareVersion))

    # Define what versions we need to test:
    versionsToTest = [softwareVersion] if softwareVersion else knownVersions

    # Try to read as each of the versions to test, until we find one:
    for sv in versionsToTest:
        # try to read all new versions, if successful, return the results.
        # If unsuccessful, it will print a warning and try the next versionToTest
        try:
            if sv == 'VE11C':
                return readVE11Cpmu( physio_file )
            elif sv == 'VB15A':
                return readVB15Apmu( physio_file )
            elif sv == 'VBX':
                return readVBXpmu( physio_file )
        except UnicodeDecodeError as e:
            # not an ascii file, so it's not a valid PMU file:
            raise PMUFormatError(
                'File %r does not seem to be a valid Siemens PMU file',
                physio_file
            )
        except PMUFormatError as e:
            if verbose:
                print( 'Warning: ' + str(e))
            continue

    # if we made it this far, there was a problem:
    if softwareVersion is None:
        # because we have tested all known version:
        raise PMUFormatError(
            'File %r does not seem to be a valid Siemens PMU file',
            physio_file
        )
    else:
        raise PMUFormatError(
            'File %r does not seem to be a valid Siemens {sv} PMU file'.format(sv=softwareVersion),
            physio_file
        )


def readVE11Cpmu( physio_file, forceRead=False ):
    """
    Function to read the physiological signal from a VE11C Siemens PMU physio file

    Parameters
    ----------
    physio_file : str
        path to a file with a Siemens PMU recording
    forceRead : bool
        flag indicating to read the file whether the format seems correct or not

    Returns
    -------
    physio_type : str
        type of physiological recording
    MDHTime : list
        list of two integers indicating the time in ms since last midnight.
        MDHTime[0] gives the start of the recording
        MDHTime[1] gives the end   of the recording
    sampling_rate : int
        number of samples per second
    physio_signal : list of int
        signal proper. NaN indicate points for which there was no recording
        (the scanner found a trigger in the signal)
    """

    # Read the file, splitting by lines and removing the "newline" (and any blank space)
    #   at the end of the line:
    lines = [line.rstrip() for line in open( physio_file )]

    # According to Siemens (IDEA documentation), the sampling rate is 2.5ms for all signals:
    sampling_rate = int(400)    # 1000/2.5

    # For that first line, different information regions are bound by "5002 and "6002".
    #   Find them:
    s = re.split('5002(.*?)6002', lines[0])
    if len(s) == 1:
        # we failed to find even one "5002 ... 6002" group.
        raise PMUFormatError(
                  'File %r does not seem to be a valid VE11C PMU file',
                  physio_file,
                  '5002(.*?)6002',
                  s[0]
              )

    # The first group contains the triggering method, gate open and close times, etc for
    #   compatibility with previous versions. Ignore it.
    # The second group tells us the type of signal ('RESP', 'PULS', etc.)
    try:
        physio_type = re.search('LOGVERSION_([A-Z]*)', s[1]).group(1)
    except AttributeError:
        print( 'Could not find type of recording for ' + physio_file )
        if not forceRead:
            raise PMUFormatError(
                      'File %r does not seem to be a valid VE11C PMU file',
                      physio_file,
                      'LOGVERSION_([A-Z]*)',
                      s[1]
                  )
        else:
            print( 'Setting recording type to "Unknown"' )
            physio_type = "Unknown"
            # (continue reading the file)


    # The third and fouth groups we ignore, and the fifth gives us the physio signal itself.
    raw_signal = s[4].split(' ')
    
    physio_signal = parserawPMUsignal(raw_signal)

    # The rest of the lines have statistics about the signals, plus start and finish times.
    # Get timing:
    MPCUTime, MDHTime = getPMUtiming( lines[1:] )

    return physio_type, MDHTime, sampling_rate, physio_signal


def readVB15Apmu( physio_file, forceRead=False ):
    """
    Function to read the physiological signal from a VB15A Siemens PMU physio file
    (e.g.: https://github.com/gitpan/App-AFNI-SiemensPhysio/blob/master/data/wpc4951_10824_20111108_110811.puls)
    (The DICOMs that go with this file are in the "MR" folder, and the header specifies the software version:
     "N4_VB15A_LATEST_20070519")

    Parameters
    ----------
    physio_file : str
        path to a file with a Siemens PMU recording
    forceRead : bool
        flag indicating to read the file whether the format seems correct or not

    Returns
    -------
    physio_type : str
        type of physiological recording
    MDHTime : list
        list of two integers indicating the time in ms since last midnight.
        MDHTime[0] gives the start of the recording
        MDHTime[1] gives the end   of the recording
    sampling_rate : int
        number of samples per second
    physio_signal : list of int
        signal proper. NaN indicate points for which there was no recording
        (the scanner found a trigger in the signal)
    """

    # Read the file, splitting by lines and removing the "newline" (and any blank space)
    #   at the end of the line:
    lines = [line.rstrip() for line in open( physio_file )]

    # The first line starts with four integers with info about the recording, followed
    #   by the data. So split by spaces:
    line0 = lines[0].split(' ')
    try:
        recInfo = [ int(v) for v in line0[:4] ]
    except:
        raise PMUFormatError(
                  'File %r does not seem to be a valid VB15A PMU file',
                  physio_file,
                  '"1 2 40 280" or "1 2 20 2"',
                  str(line0[:4])
              )

    raw_signal = line0[4:]     # we'll transform the signal to int later

    # According to Siemens (IDEA documentation), the sampling rate is 50 samples/s for all signals:
    sampling_rate = int(50)

    # Check the recording. These are fixed:
    if recInfo == [1, 2, 40, 280]:
        physio_type = 'PULS'
    elif recInfo == [1, 2, 20, 2]:
        physio_type = 'RESP'
    else:
        print( 'Unknown type of recording for ' + physio_file )
        if not forceRead:
            raise PMUFormatError(
                      'File %r does not seem to be a valid VB15A PMU file',
                      physio_file,
                      '"1 2 40 280" or "1 2 20 2"',
                      str(recInfo)
                  )

    # VB files continue with physio data right away. VE files continue with some more
    #   information, starting with the code "5002":
    if raw_signal[0] == '5002':
        raise PMUFormatError(
                  'File %r does not seem to be a valid VB15A PMU file',
                  physio_file,
                  'not 5002',
                  '5002 [...]'
              )

    physio_signal = parserawPMUsignal(raw_signal)

    # The rest of the lines have statistics about the signals, plus start and finish times.
    # Get timing:
    MPCUTime, MDHTime = getPMUtiming( lines[1:] )

    return physio_type, MDHTime, sampling_rate, physio_signal


def readVBXpmu( physio_file, forceRead=False ):
    """
    Function to read the physiological signal from some VB Siemens PMU physio file
    (Possibly VB17? or VB19?)
    See:
    https://gitlab.ethz.ch/physio/physio-doc/-/wikis/MANUAL_PART_READIN#siemens

    Parameters
    ----------
    physio_file : str
        path to a file with a Siemens PMU recording
    forceRead : bool
        flag indicating to read the file whether the format seems correct or not

    Returns
    -------
    physio_type : str
        type of physiological recording
    MDHTime : list
        list of two integers indicating the time in ms since last midnight.
        MDHTime[0] gives the start of the recording
        MDHTime[1] gives the end   of the recording
    sampling_rate : int
        number of samples per second
    physio_signal : list of int
        signal proper. NaN indicate points for which there was no recording
        (the scanner found a trigger in the signal)
    """

    # Read the file, splitting by lines and removing the "newline" (and any blank space)
    #   at the end of the line:
    lines = [line.rstrip() for line in open( physio_file )]

    # For that first line, different information regions are bound by "5002 and "6002".
    #   Find them:
    s = re.split('5002(.*?)6002', lines[0])
    if len(s) == 1:
        # we failed to find even one "5002 ... 6002" group.
        raise PMUFormatError(
                  'File %r does not seem to be a valid VBX PMU file',
                  physio_file,
                  '5002(.*?)6002',
                  s[0]
              )

    # The first group contains the triggering method, gate open and close times, etc for
    #   compatibility with previous versions. Ignore it.
    # The second group tells us the type of signal ('RESP', 'PULS', etc.)
    try:
        physio_type = re.search('Logging ([A-Z]*) signal', s[1]).group(1)
    except AttributeError:
        print( 'Could not find type of recording for ' + physio_file )
        if not forceRead:
            raise PMUFormatError(
                      'File %r does not seem to be a valid VBX PMU file',
                      physio_file,
                      'Logging ([A-Z]*) signal',
                      s[1]
                  )
        else:
            print( 'Setting recording type to "Unknown"' )
            physio_type = "Unknown"
            # (continue reading the file)

    # Also, the sampling rate:
    try:
        sampling_rate = int(re.search('_SAMPLES_PER_SECOND = ([0-9]*)', s[1]).group(1))
    except AttributeError:
        print( 'Could not find the sampling rate for ' + physio_file )
        raise PMUFormatError(
                  'File %r does not seem to be a valid VBX PMU file',
                  physio_file,
                  '_SAMPLES_PER_SECOND = ([0-9]*)',
                  s[1]
              )

    # The third group gives us the physio signal itself.
    raw_signal = s[2].split(' ')

    physio_signal = parserawPMUsignal(raw_signal)

    # The rest of the lines have statistics about the signals, plus start and finish times.
    # Get timing:
    MPCUTime, MDHTime = getPMUtiming( lines[1:] )

    return physio_type, MDHTime, sampling_rate, physio_signal


def getPMUtiming( lines ):
    """
    Function to get the timing for the PMU recording.

    Parameters
    ----------
    lines : list of str
        list with PMU file lines
        To improve speed, don't pass the first line, which contains the raw data.

    Returns
    -------
    MPCUTime : list of two int
        MARS timestamp (in ms, since the previous midnight) for the start and finish
        of the signal logging, respectively
    MDHTime : list of two int
        Mdh timestamp (in ms, since the previous midnight) for the start and finish
        of the signal logging, respectively

    """

    MPCUTime = [0,0]
    MDHTime = [0,0]
    for l in lines:
        if 'MPCUTime' in l:
            ls = l.split()
            if 'LogStart' in l:
                MPCUTime[0]= int(ls[1])
            elif 'LogStop' in l:
                MPCUTime[1]= int(ls[1])
        if 'MDHTime' in l:
            ls = l.split()
            if 'LogStart' in l:
                MDHTime[0]= int(ls[1])
            elif 'LogStop' in l:
                MDHTime[1]= int(ls[1])

    return MPCUTime, MDHTime


def parserawPMUsignal( raw_signal ):
    """
    Function to parse raw physio signal.

    Parameters
    ----------
    raw_signal : list of str
        list with raw PMU signal

    Returns
    -------
    physio_signal : list of int
        signal proper. NaN indicate points for which there was no recording
        (the scanner found a trigger in the signal)
    """

    # Sometimes, there is an empty string ('') at the beginning of the string. Remove it:
    if raw_signal[0] == '':
        raw_signal = raw_signal[1:]

    # Convert to integers:
    raw_signal = [ int(v) for v in raw_signal ]

    # only keep up to "5003" (indicates end of signal recording):
    try:
        raw_signal = raw_signal[:raw_signal.index(5003)]
    except ValueError:
        print( "Warning: End of physio recording not found. Keeping whole data" )

    # Values "5000" and "6000" indicate "trigger on" and "trigger off", respectively, so they
    #   are not a real physio_signal value. So replace them with NaN:
    physio_signal = raw_signal
    for idx,v in enumerate(raw_signal):
        if v == 5000 or v == 6000:
            physio_signal[idx] = float('NaN')

    return physio_signal


def testSamplingRate(
        sampling_rate=0,
        Nsamples=0,
        logTimes=[0,0],
        tolerance=0.1
        ):
    """
    Function to test if the sampling rate is correct.
    If it is incorrect, it will raise a ValueError

    Parameters
    ----------
    sampling_rate : int
        Sampling rate (samples per second) we want to test
    Nsamples : int
        Number of samples in the data
    logTimes : list of two int
        Start and Stop logging times (in ms)
    tolerance : float (> 0 and < 1)
        relative tolerance in the error

    Returns
    -------
    """

    if not (tolerance < 1 and tolerance > 0):
        raise ValueError('tolerance has to be between 0 and 1. Got ' + str(tolerance))

    loggingTime_sec = (logTimes[1] - logTimes[0])/1000
    expected_samples = int(loggingTime_sec * sampling_rate)
    if not math.isclose( Nsamples, expected_samples, rel_tol=tolerance):
        raise ValueError(
            'Expected sampling rate: {expected}. Got: {got}'.format(
                expected=int(Nsamples/loggingTime_sec),
                got=sampling_rate
            )
        )


def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert Siemens physiology files to BIDS-compliant physiology recording')
    parser.add_argument('-i', '--infiles', nargs='+', required=True, help='.puls or .resp physio file(s)')
    parser.add_argument('-b', '--bidsprefix', required=True, help='Prefix of the BIDS file. It should match the _bold.nii.gz')
    parser.add_argument('-v', '--verbose', action="store_true", default=False, help='verbose screen output')
    args = parser.parse_args()

    # make sure input files exist:
    for infile in args.infiles:
        if not os.path.exists(infile):
            raise FileNotFoundError( '{i} file not found'.format(i=infile))

    # make sure output directory exists:
    odir = os.path.dirname(args.bidsprefix)
    if not os.path.exists(odir):
        os.makedirs(odir)

    pmu2bids( args.infiles, args.bidsprefix, verbose=args.verbose )

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()

