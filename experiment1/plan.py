import pandas as pd
from ortools.linear_solver import pywraplp

MAX_COAL_PRODUCTION = 50
MAX_SEED_USAGE = 100
GOAL_CONST = 100
LABOR_CONST = 1

FLOWS = pd.read_csv('flows.csv')
PRODUCTS = list(FLOWS)[1:]
ROWS = list(FLOWS['headings'])
ROW_MAP = {name: index for index, name in enumerate(ROWS)}
GOALS = pd.read_csv('goals.csv')

def goal(key):
    return GOALS[key][0]

def io(input_product, output_product):
    return FLOWS[output_product][ROW_MAP[input_product]]


def main():
    solver = pywraplp.Solver('Planning', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)

    # variables
    production_of = {}
    for p in PRODUCTS:
        production_of[p] = solver.NumVar(0.0, solver.infinity(), f"production_of_{p}")

    # constraints
    # 1. restrict coal prodution for environmental reasons
    coal_constraint = solver.Constraint(0, MAX_COAL_PRODUCTION)
    coal_constraint.SetCoefficient(production_of['coal'], 1)
    # only for testing (it seems like we are getting "no solution errors" if
    # there is no constraint for iron
    iron_constraint = solver.Constraint(0, MAX_COAL_PRODUCTION)
    iron_constraint.SetCoefficient(production_of['iron'], 1)
    # 2. the amout of corn seeds is limited
    corn_constraint = solver.Constraint(0, MAX_SEED_USAGE)
    for p in PRODUCTS:
        corn_constraint.SetCoefficient(production_of[p], io('corn', p))
    # 3. total outputs of production have to be positive
    total_output_constraint = {}
    for p in PRODUCTS:
        total_output_constraint[p] = solver.Constraint(0, solver.infinity())
        for q in PRODUCTS:
            total_output_constraint[p].SetCoefficient(
                production_of[q], (1 if p == q else 0) - io(p, q))

    # objective
    objective = solver.Objective()
    for p in PRODUCTS:
        # view total output relative to goal
        coef = GOAL_CONST * (1/goal(p) if goal(p) > 0 else 0)
        for q in PRODUCTS:
            coef -= GOAL_CONST * (io(p, q)/goal(q) if goal(q) > 0 else 0)
        # labor should be minimized
        coef -= LABOR_CONST * io('labor', p)
        objective.SetCoefficient(production_of[p], coef)

    objective.SetMaximization()

    result_status = solver.Solve()

    print(solver.ExportModelAsLpFormat(obfuscated = False))
    print(solver.NumVariables())
    print(solver.NumConstraints())
    print(result_status == pywraplp.Solver.OPTIMAL)
    for p in PRODUCTS:
        print(f"produce {production_of[p].solution_value()} of {p}")

if __name__ == '__main__':
    main()
