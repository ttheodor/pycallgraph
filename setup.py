from setuptools import setup

setup(
    name='pycallgraph',
    version='0.0.1',
    author='Theodoros Theodoridis',
    author_email='theodort@inf.ethz.ch',
    description='An LLVM call graph wrapper',
    url='https://github.com/ttheodor/pycallgraph',
    packages=['pycallgraph'],
    install_requires=['networkx'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)
