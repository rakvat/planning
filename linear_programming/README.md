# Experiment with linear programming tools

## ortools

```bash
python ortools_plan.py

```

## pulp

```bash
python pulp_plan.py

```

## Expected results

Both tools should result in the same suggested plans.

## Observations

Optimizing by maximal productivity does not make any sense.
It will just create huge amounts of some product, that no one will use.
So it's a waste of resources.
