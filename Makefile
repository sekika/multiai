all:

install:
	python3 -m pip install .

app:
	streamlit run docs/app.py

test:
	@ cd dev; ./test.sh

