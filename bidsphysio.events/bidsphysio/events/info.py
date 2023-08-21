__version__ ="21.06.24"
__author__ = "Chrysa Papadaniil, Pablo Velasco"
__author_email__ = "chrysa@nyu.edu"
__url__ = "https://github.com/cbinyu/bidsphysio"
__packagename__ = 'bidsphysio.events'
__description__ = "BIDS Events classes"
__license__ = "MIT"
__longdesc__ = """Base classes to handle BIDS event data."""

CLASSIFIERS = [
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',

    'Topic :: Scientific/Engineering'
]

PYTHON_REQUIRES = ">=3.6"

REQUIRES = [
    'numpy >= 1.20.1',
    'pandas>=1.1.0',
]

TESTS_REQUIRES = [
    'pytest'
]

EXTRA_REQUIRES = {
    'tests': TESTS_REQUIRES,
}

# Flatten the lists
EXTRA_REQUIRES['all'] = sum(EXTRA_REQUIRES.values(), [])
