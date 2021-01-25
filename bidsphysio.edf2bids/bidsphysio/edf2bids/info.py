""" NOTE: When bumping up the version number, double-check if you
need to also bump up the version of the dependencies
"""

__version__ = "21.1.25"
__author__ = "Chrysa Papadaniil"
__author_email__ = "chrysa@nyu.edu"
__url__ = "https://github.com/cbinyu/bidsphysio"
__packagename__ = 'bidsphysio.edf2bids'
__description__ = "EDF-to-BIDS Converter"
__license__ = "MIT"
__longdesc__ = """Converts EDF eye-tracker data (from a SR Research Eyelink system) to BIDS eye-tracker physiological recording and events."""

CLASSIFIERS = [
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Topic :: Scientific/Engineering'
]

PYTHON_REQUIRES = ">=3.6"

REQUIRES = [
    'bidsphysio.base>=21.1.25',
    'bidsphysio.session>=21.1.25',
    'bidsphysio.events>=21.1.25',
    'h5py>=2.9.0',
    'Cython>=0.29.13',
    'pandas>=1.1.0',
    'numpy>= 1.17.1'
]

TESTS_REQUIRES = [
    'pytest'
]

EXTRA_REQUIRES = {
    'tests': TESTS_REQUIRES,
}

# Flatten the lists
EXTRA_REQUIRES['all'] = sum(EXTRA_REQUIRES.values(), [])
