"""
packaging setup for adl2pydm
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_namespace_packages
from os import path
import sys
import versioneer

here = path.abspath(path.dirname(__file__))
sys.path.insert(0, path.join('src',))
import adl2pydm as package


__entry_points__  = {
    'console_scripts': [
        'adl2pydm = adl2pydm.cli:main',
        ],
    #'gui_scripts': [],
}


setup(
    author           = package.__author__,
    author_email     = package.__author_email__,
    classifiers      = package.__classifiers__,
    description      = package.__description__,
    license          = package.__license__,
    long_description = package.__long_description__,
    install_requires = package.__install_requires__,
    name             = package.__project__,
    #platforms        = package.__platforms__,
    package_dir      = {'': 'src'},
    packages         = find_namespace_packages(
                        "src",
                        exclude=package.__exclude_project_dirs__),
    url              = package.__url__,
    python_requires  = package.__python_version_required__,
    zip_safe         = package.__zip_safe__,

    entry_points     = __entry_points__,

    version          = versioneer.get_version(),
    cmdclass         = versioneer.get_cmdclass(),
 )
