run:
	python planning/plan.py

run_uk:
	python planning/plan.py uk_data out/uk_data

run_harmonizer:
	python planning_alg3/plan.py test_data out/harmonizer

run_harmonizer_uk:
	python planning_alg3/plan.py uk_data out/uk_data

test:
	python -m unittest tests/*.py

cov:
	py.test --cov=planning tests/

lint:
	pylint planning/*.py
