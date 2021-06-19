from importlib import import_module
from setuptools import setup

with open('README.md') as f:
    readme = f.read()

setup(
    name='bronzebeard',
    version=import_module('bronzebeard').__version__,
    author='Andrew Dailey',
    description='Minimal ecosystem for bare-metal RISC-V development',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/theandrew168/bronzebeard',
    packages=['bronzebeard'],
    install_requires=[
        'pyserial',
        'pyusb',
    ],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'bronzebeard = bronzebeard.asm:cli_main',
        ],
    },
)
