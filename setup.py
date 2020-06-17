#!/usr/bin/env python
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See the LICENSE file for the copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import os.path as op
from os import scandir

from setuptools import setup, find_packages


def main():

    thispath = op.dirname(__file__) or '.'
    ldict = locals()

    # Get version and release info, which is all stored in info.py
    info_file = op.join(thispath, 'bidsphysio', 'info.py')
    with open(info_file) as infofile:
        exec(infofile.read(), globals(), ldict)

    # find_packages() doesn't find the bidsphysio.* sub-packages
    # because they don't have an __init__.py file.
    children_dirs = [
        op.relpath(f.path,thispath) for f in scandir(thispath)
        if f.is_dir()
    ]
    bidsphysio_pkgs = [d for d in children_dirs if d.startswith('bidsphysio.')]

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
        entry_points={},
        python_requires=ldict['PYTHON_REQUIRES'],
        install_requires=ldict['REQUIRES'],
        extras_require=ldict['EXTRA_REQUIRES'],
    )


if __name__ == '__main__':
    main()
