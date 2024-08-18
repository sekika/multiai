#!/bin/sh
# Change to this directory
cd `echo $0 | sed -e 's/[^/]*$//'`
echo '=== test'
ai -o hi
ai -a 土壌について
ai -g 土壌について
ai -p hi
ai -i hi

echo '=== autopep8'
autopep8 -i --aggressive ../src/multiai/*.py

echo '=== mypy'
mypy ../src/multiai/*.py

echo '=== flake8'
flake8 --ignore=E501,F401 ../src/multiai/*.py
