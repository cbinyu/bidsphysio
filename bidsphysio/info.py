__version__ = "4.0.rc0"
__author__ = "Pablo Velasco"
__author_email__ = "pablo.velasco@nyu.edu"
__url__ = "https://github.com/cbinyu/bidsphysio"
__packagename__ = 'bidsphysio'
__description__ = "Physio-to-BIDS Converter"
__license__ = "MIT"
__longdesc__ = """Converts physio data from either CMRR DICOM, Siemens PMU or AcqKnowledge file to BIDS physiological recording."""

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
]

TESTS_REQUIRES = [
    'pytest'
]

EXTRA_REQUIRES = {
    'tests': TESTS_REQUIRES,
}

# Flatten the lists
EXTRA_REQUIRES['all'] = sum(EXTRA_REQUIRES.values(), [])
