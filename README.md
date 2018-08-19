# Planning Experiments

These are experiments with planning an economy by setting targets based on needs, collecting input data and generating optimal production suggestions.

## Requirements

You need to install python3, [OR-tools](https://developers.google.com/optimization/install/python/linux) and the listed [requirements](requirements.txt).

`pip install git+https://github.com/anazalea/pySankey.git` is required for some visualizations.

## How To Run

In each experiment folder there is a python script that can be run with

```bash
python3 plan.py

```

Some experiments also have jupyter notebooks with visualizations.


## The Experiments

### Experiment 1

uses linear programming with targets, input output flows, and additional constraints but does not reach an optimal solution.

### Experiment 2

uses the algorithm (linear programming) from https://github.com/wc22m/5yearplan. This repository also has additional explanations about the input data.
