#!/usr/bin/env python
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See dcm2bidsphysio.py file for the copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os.path as op

from setuptools import setup, find_packages


def main():

    thispath = op.dirname(__file__)
    ldict = locals()

    # Get version and release info, which is all stored in info.py
    info_file = op.join(thispath, 'bidsphysio', 'events', 'info.py')
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
        python_requires=ldict['PYTHON_REQUIRES'],
        install_requires=ldict['REQUIRES'],
        extras_require=ldict['EXTRA_REQUIRES'],
    )


if __name__ == '__main__':
    main()
