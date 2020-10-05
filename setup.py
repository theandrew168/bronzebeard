from setuptools import setup

with open('README.md') as f:
    readme = f.read()

setup(
    name='bronzebeard',
    version='0.0.1',
    author='Andrew Dailey',
    description='Bare-metal RISC-V development with Python and Forth',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/theandrew168/bronzebeard',
    packages=['bronzebeard'],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.0',
)
