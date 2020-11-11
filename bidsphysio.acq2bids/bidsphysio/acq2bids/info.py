""" NOTE: When bumping up the version number, double-check if you
need to also bump up the version of the dependencies
"""

__version__ = "1.3.1"
__author__ = "Pablo Velasco"
__author_email__ = "pablo.velasco@nyu.edu"
__url__ = "https://github.com/cbinyu/bidsphysio"
__packagename__ = 'bidsphysio.acq2bids'
__description__ = "AcqKnowledge-to-BIDS Converter"
__license__ = "MIT"
__longdesc__ = """Converts physio data from an AcqKnowledge file to BIDS physiological recording."""

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
    'bidsphysio.base>=1.3.1',
    'bidsphysio.session>=1.1.1',
    'bioread[mat]>=2.0.0',
]

TESTS_REQUIRES = [
    'pytest'
]

EXTRA_REQUIRES = {
    'tests': TESTS_REQUIRES,
}

# Flatten the lists
EXTRA_REQUIRES['all'] = sum(EXTRA_REQUIRES.values(), [])
