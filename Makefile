all:

install:
	python3 -m pip install -e .

app:
	streamlit run docs/app.py

test:
	@ cd dev; ./test.sh

