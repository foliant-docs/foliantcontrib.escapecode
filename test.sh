#!/bin/bash

# before testing make sure that you have installed the fresh version of preprocessor:
 pip3 install .
# also make sure that fresh version of test framework is installed:
 pip3 install --upgrade foliantcontrib.test_framework
python3 -m unittest discover