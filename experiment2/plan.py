from ortools.linear_solver import pywraplp
from collections import defaultdict
import pandas as pd

flows = pd.read_csv('flows.csv')
products = list(flows)[1:]
rows = list(flows['headings'])
row_map = { name: index for index, name in enumerate(rows)}

targets = pd.read_csv('targets.csv')
years = targets.shape[0]

cap = pd.read_csv('capital_stock.csv')
dep = pd.read_csv('depreciation_rates.csv')



def target(key, year):
    return targets[key][year]

def io(input_product, output_product):
    return flows[output_product][row_map[input_product]]

def capital_stock(input_product, output_product):
    return cap[output_product][row_map[input_product]]

def depreciation_rates(input_product, output_product):
    return dep[output_product][row_map[input_product]]


# algorithm from https://github.com/wc22m/5yearplan
def main():
    solver = pywraplp.Solver('Planning', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)

    # variables
    accumulation_for_of = defaultdict(lambda: defaultdict(dict))
    accumulation_of = defaultdict(lambda: defaultdict(dict))
    capital_stock_for_of = defaultdict(lambda: defaultdict(dict))
    depreciation_in_production_of = defaultdict(lambda: defaultdict(dict))
    final_consumption_of = defaultdict(lambda: defaultdict(dict))
    flow_for_of = defaultdict(lambda: defaultdict(dict))
    labor_in_year = defaultdict(lambda: defaultdict(dict))
    labor_for = defaultdict(lambda: defaultdict(dict))
    output_of = defaultdict(lambda: defaultdict(dict))
    productive_consumption_of = defaultdict(lambda: defaultdict(dict))
    target_fulfillment_in_year = defaultdict(lambda: defaultdict(dict))

    for y in range(years):
        target_fulfillment_in_year[y] = solver.NumVar(0.0, solver.infinity(),
                f"target_fulfillment_in_year_{y}")
        labor_in_year[y] = solver.NumVar(0.0, solver.infinity(),
                f"labor_in_year_{y}")

        for p in products:
            accumulation_of[y][p] = solver.NumVar(0.0, solver.infinity(),
                    f"accumulation_of_{p}_year_{y}")
            final_consumption_of[y][p] = solver.NumVar(0.0, solver.infinity(),
                    f"final_consumption_of_{p}_year_{y}")
            labor_for[y][p] = solver.NumVar(0.0, solver.infinity(),
                    f"labor_for_{p}_year_{y}")
            output_of[y][p] = solver.NumVar(0.0, solver.infinity(),
                    f"output_of_{p}_year_{y}")
            productive_consumption_of[y][p] = solver.NumVar(0.0, solver.infinity(),
                    f"productive_comsumption_of_{p}_year_{y}")

            for q in products:
                accumulation_for_of[y][p][q] = solver.NumVar(0.0, solver.infinity(),
                        f"accumulation_for_{p}_of_{q}_year_{y}")
                capital_stock_for_of[y][p][q] = solver.NumVar(0.0, solver.infinity(),
                        f"capital_stock_for_{p}_of_{q}_year_{y}")
                depreciation_in_production_of[y][p][q] = solver.NumVar(0.0, solver.infinity(),
                        f"depreciation_in_{p}_production_of_{q}_year_{y}")
                flow_for_of[y][p][q] = solver.NumVar(0.0, solver.infinity(),
                        f"flow_for_{p}_of_{q}_year_{y}")

                # constraints
    for y in range(years):
        # 1. targets given by leontief demand for year
        for p in products:
            if target(p, y) > 0:
                leontief_constraint = solver.Constraint(0, solver.infinity(), 'leontief')
                leontief_constraint.SetCoefficient(final_consumption_of[y][p], 1/target(p, y))
                leontief_constraint.SetCoefficient(target_fulfillment_in_year[y], -1)
        # 2. labor total
        labor_total_constraint = solver.Constraint(0, solver.infinity(), 'labor_total')
        labor_total_constraint.SetCoefficient(labor_in_year[y], 1)
        for p in products:
            labor_total_constraint.SetCoefficient(labor_for[y][p], -1)
        # 3. labor supply
        labor_supply_contraint = solver.Constraint(-solver.infinity(), target('labor', y), 'labor_supply')
        labor_supply_contraint.SetCoefficient(labor_in_year[y], 1)

        for p in products:
            # 4. labor constraint
            if (io('output', p) != 0):
                labor_constraint = solver.Constraint(0, solver.infinity(), 'labor')
                labor_constraint.SetCoefficient(output_of[y][p], -1)
                labor_constraint.SetCoefficient(labor_for[y][p], io('output', p)/io('labor', p))
            # 5. accumulation total
            accumulation_total_constraint = solver.Constraint(0, solver.infinity(), 'accumulation_total')
            accumulation_total_constraint.SetCoefficient(accumulation_of[y][p], 1)
            for q in products:
                accumulation_total_constraint.SetCoefficient(accumulation_for_of[y][q][p], -1)
            # 6. productive consumption
            productive_consumption_constraint = solver.Constraint(0, solver.infinity(), 'productive_consumption')
            productive_consumption_constraint.SetCoefficient(productive_consumption_of[y][p], 1)
            for q in products:
                productive_consumption_constraint.SetCoefficient(flow_for_of[y][q][p], -1)
            # 7. consumption
            consumption_constraint = solver.Constraint(0, solver.infinity(), 'consumption')
            consumption_constraint.SetCoefficient(output_of[y][p], 1)
            consumption_constraint.SetCoefficient(accumulation_of[y][p], -1)
            consumption_constraint.SetCoefficient(final_consumption_of[y][p], -1)
            consumption_constraint.SetCoefficient(productive_consumption_of[y][p], -1)

            for q in products:
                # 8. output equation
                if (capital_stock(q, p) != 0):
                    output_constraint = solver.Constraint(0, solver.infinity(), 'output')
                    output_constraint.SetCoefficient(capital_stock_for_of[y][p][q], io('output', p)/capital_stock(q, p))
                    output_constraint.SetCoefficient(output_of[y][p], -1)
                # 9. flow constraint
                if (io(q, p) != 0):
                    flow_constraint = solver.Constraint(0, solver.infinity(), 'flow')
                    flow_constraint.SetCoefficient(flow_for_of[y][p][q], io('output', p)/io(q, p))
                    flow_constraint.SetCoefficient(output_of[y][p], -1)
                # 10. depreciation
                depreciation_constraint = solver.Constraint(0, 0, 'depreciation')
                depreciation_constraint.SetCoefficient(depreciation_in_production_of[y][p][q], 1)
                depreciation_constraint.SetCoefficient(capital_stock_for_of[y][p][q], -depreciation_rates(q, p))
                if (y > 0):
                    # 11. accumulation constraint
                    accumulation_constraint = solver.Constraint(0, solver.infinity(), 'accumulation')
                    accumulation_constraint.SetCoefficient(capital_stock_for_of[y-1][p][q], 1)
                    accumulation_constraint.SetCoefficient(accumulation_for_of[y-1][p][q], 1)
                    accumulation_constraint.SetCoefficient(depreciation_in_production_of[y-1][p][q], -1)
                    accumulation_constraint.SetCoefficient(capital_stock_for_of[y][p][q], -1)
            else:
                # 12. initial capital stocks
                inital_capital_stock_constraint = solver.Constraint(-solver.infinity(),
                        float(capital_stock(q, p)), 'initial_capital_stocks')
                inital_capital_stock_constraint.SetCoefficient(capital_stock_for_of[y][p][q], 1)


    # objective
    objective = solver.Objective()
    for y in range(years):
        objective.SetCoefficient(target_fulfillment_in_year[y], 1)
    objective.SetMaximization()

    print(solver.ExportModelAsLpFormat(obfuscated = False))
    print(f"number of variables: {solver.NumVariables()}")
    print(f"number of constraints: {solver.NumConstraints()}")

    # solve
    result_status = solver.Solve()

    # output results
    print(f"Found optimal solution? {result_status == pywraplp.Solver.OPTIMAL}")
    print('\nSolution:')

    if (result_status == pywraplp.Solver.OPTIMAL):
        target_fulfillment_in_year = { y: v.solution_value() for y, v in target_fulfillment_in_year.items() }
        labor_in_year = { y: v.solution_value() for y, v in labor_in_year.items() }
        for y in range(years):
            print(f"target_fulfillment_in_year_{y}: {target_fulfillment_in_year[y]}")
            print(f"labor_in_year_{y}: {labor_in_year[y]}")

            accumulation_of[y] = { p: v.solution_value() for p, v in accumulation_of[y].items() }
            final_consumption_of[y] = { p: v.solution_value() for p, v in final_consumption_of[y].items() }
            labor_for[y] = { p: v.solution_value() for p, v in labor_for[y].items() }
            output_of[y] = { p: v.solution_value() for p, v in output_of[y].items() }
            productive_consumption_of[y] = { p: v.solution_value() for p, v in productive_consumption_of[y].items() }

            for p in products:
                print(f"accumulation_of_{p}_year_{y}: {accumulation_of[y][p]}")
                print(f"final_consumption_of_{p}_year_{y}: {final_consumption_of[y][p]}")
                print(f"labor_for_{p}_year_{y}: {labor_for[y][p]}")
                print(f"output_of_{p}_year_{y}: {output_of[y][p]}")
                print(f"productive_comsumption_of_{p}_year_{y}: {productive_consumption_of[y][p]}")

                accumulation_for_of[y][p] = { q: v.solution_value() for q, v in accumulation_for_of[y][p].items() }
                capital_stock_for_of[y][p] = { q: v.solution_value() for q, v in capital_stock_for_of[y][p].items() }
                depreciation_in_production_of[y][p] = { q: v.solution_value() for q, v
                        in depreciation_in_production_of[y][p].items() }
                flow_for_of[y][p] = { q: v.solution_value() for q, v in flow_for_of[y][p].items() }

                for q in products:
                    print(f"accumulation_for_{p}_of_{q}_year_{y}: {accumulation_for_of[y][p][q]}")
                    print(f"capital_stock_for_{p}_of_{q}_year_{y}: {capital_stock_for_of[y][p][q]}")
                    print(f"depreciation_in_{p}_production_of_{q}_year_{y}: {depreciation_in_production_of[y][p][q]}")
                    print(f"flow_for_{q}_of_{q}_year_{y}: {flow_for_of[y][p][q]}")

    # export
    df = pd.DataFrame.from_dict(target_fulfillment_in_year, orient='index')
    df.to_csv('out/target_fulfillment_in_year.csv')

    df = pd.DataFrame.from_dict(labor_in_year, orient='index')
    df.to_csv('out/labor_in_year.csv')

    df = pd.DataFrame.from_dict(accumulation_of, orient='index')
    df.to_csv('out/accumulation_of.csv', columns=products)
    df = pd.DataFrame.from_dict(final_consumption_of, orient='index')
    df.to_csv('out/final_consumption_of.csv', columns=products)
    df = pd.DataFrame.from_dict(labor_for, orient='index')
    df.to_csv('out/labor_for.csv', columns=products)
    df = pd.DataFrame.from_dict(productive_consumption_of, orient='index')
    df.to_csv('out/productive_consumption_of.csv', columns=products)
    df = pd.DataFrame.from_dict(output_of, orient='index')
    df.to_csv('out/output_of.csv', columns=products)


if __name__ == '__main__':
    main()
