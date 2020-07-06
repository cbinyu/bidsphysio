#!/usr/bin/env python
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See ../LICENSE file for the copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os.path as op

from setuptools import setup, find_packages


def main():

    thispath = op.dirname(__file__)
    ldict = locals()

    # Get version and release info, which is all stored in info.py
    info_file = op.join(thispath, 'bidsphysio', 'acq2bids', 'info.py')
    with open(info_file) as infofile:
        exec(infofile.read(), globals(), ldict)


    setup(
        name=ldict['__packagename__'],
        author=ldict['__author__'],
        author_email=ldict['__author_email__'],
        version=ldict['__version__'],
        description=ldict['__description__'],
        long_description=ldict['__longdesc__'],
        license=ldict['__license__'],
        classifiers=ldict['CLASSIFIERS'],
        packages=find_packages(),
        namespace_packages=['bidsphysio'],
        entry_points={'console_scripts': [
            'acq2bidsphysio=bidsphysio.acq2bids.acq2bidsphysio:main',
            'acqsession2bids=bidsphysio.acq2bids.acqsession2bids:main',
        ]},
        python_requires=ldict['PYTHON_REQUIRES'],
        install_requires=ldict['REQUIRES'],
        extras_require=ldict['EXTRA_REQUIRES'],
        package_data={
            'bidsphysio.acq2bids.tests': [
                        op.join('data', '*.acq'),
                        op.join('data', '*.tsv')
            ],
        }
    )


if __name__ == '__main__':
    main()
