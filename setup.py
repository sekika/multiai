# -*- coding: utf-8 -*-

from setuptools import setup
from codecs import open
from os import path
import configparser

# Read system information from multiai/data/system.ini
inifile = configparser.ConfigParser()
here = path.abspath(path.dirname(__file__))
inifile.read(path.join(here, 'multiai/data/system.ini'))
version = inifile.get('system', 'version')
description = inifile.get('system', 'description')
url = inifile.get('system', 'url')
# Read long description from Readme.md
with open(path.join(here, 'Readme.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='multiai',
    version=version,
    description=description,
    long_description=long_description,
    long_description_content_type='text/markdown',
    url=url,
    author='Katsutoshi Seki',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        "Intended Audience :: Science/Research",
        'Environment :: Console',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Operating System :: Microsoft :: Windows :: Windows 11',
        'Operating System :: POSIX',
        'Operating System :: POSIX :: BSD',
        'Operating System :: POSIX :: Linux',
        'Topic :: Software Development :: Libraries :: Python Modules',
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        'Natural Language :: English',
    ],
    keywords='AI',
    packages=['multiai'],
    package_data={'multiai': ['data/*']},
    install_requires=[
        'openai',
        'anthropic',
        'google-generativeai',
        'requests',
        'mistralai',
        'pypager',
        'pyperclip',
        'PyPDF2',
        'trafilatura'],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "ai = multiai.entry:entry",
        ]
    },
)
