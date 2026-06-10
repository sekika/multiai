#!/bin/sh
# Change to this directory
cd `echo $0 | sed -e 's/[^/]*$//'`
cp ../src/multiai/data/system.ini ../docs/_includes/system.ini
cd ..
pytest
cd dev
echo '=== test'
ai -o hi
ai -a 土壌について
# ai -g hi
# ai -p hi
# ai -i hi
ai -d hi
ai -x hi
# ai -l hi

echo '=== autopep8'
autopep8 -i --aggressive ../src/multiai/*.py

echo '=== mypy'
mypy ../src/multiai/*.py

echo '=== flake8'
flake8 --ignore=E501,F401 ../src/multiai/*.py
