SHELL := /bin/bash
CONDA_ENV := py38_trulens
CONDA := source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate $(CONDA_ENV)

slackbot:
	$(CONDA); (PYTHONPATH=. python -u trulens_eval/slackbot.py)

# 1>&2 > slackbot.log)

test:
	$(CONDA); python -m pytest -s test_tru_chain.py

format:
	$(CONDA); bash format.sh

lab:
	$(CONDA); jupyter lab --ip=0.0.0.0 --no-browser --ServerApp.token=deadbeef

example_app:
	$(CONDA); PYTHONPATH=. streamlit run trulens_eval/Example_Application.py

example_trubot:
	$(CONDA); PYTHONPATH=. streamlit run trulens_eval/Example_TruBot.py

leaderboard:
	$(CONDA); PYTHONPATH=. streamlit run trulens_eval/Leaderboard.py
