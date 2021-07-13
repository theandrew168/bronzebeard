from importlib import import_module
from setuptools import setup

with open('README.rst') as f:
    readme = f.read()

setup(
    name='bronzebeard',
    version=import_module('bronzebeard').__version__,
    author='Andrew Dailey',
    author_email='andrew@shallowbrooksoftware.com',
    description='Minimal ecosystem for bare-metal RISC-V development',
    long_description=readme,
    long_description_content_type='text/x-rst',
    url='https://github.com/theandrew168/bronzebeard',
    project_urls={
        'Documentation': 'https://bronzebeard.readthedocs.io',
        'Source Code': 'https://github.com/theandrew168/bronzebeard',
        'Issue Tracker': 'https://github.com/theandrew168/bronzebeard/issues',
    },
    packages=['bronzebeard'],
    include_package_data=True,
    install_requires=[
        'pyserial',
        'pyusb',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Assembly',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development',
        'Topic :: Software Development :: Assemblers',
        'Topic :: Software Development :: Embedded Systems',
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'bronzebeard = bronzebeard.asm:cli_main',
            'bronzebeard-dfu = bronzebeard.dfu:cli_main',
        ],
    },
)
