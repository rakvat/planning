from __future__ import print_function
from ortools.linear_solver import pywraplp
import pandas as pd
import pdb

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
  accumulation_for_of = {}
  accumulation_of = {}
  capital_stock_for_of = {}
  depreciation_in_production_of = {}
  final_consumption_of = {}
  flow_for_of = {}
  labor_in_year = {}
  labor_for = {}
  output_of = {}
  productive_consumption_of = {}
  target_fullfillment_in_year = {} #x

  for y in range(years):
    accumulation_for_of[y] = {}
    accumulation_of[y] = {}
    capital_stock_for_of[y] = {}
    depreciation_in_production_of[y] = {}
    final_consumption_of[y] = {}
    flow_for_of[y] = {}
    labor_for[y] = {}
    output_of[y] = {}
    productive_consumption_of[y] = {}

    target_fullfillment_in_year[y] = solver.NumVar(0.0, solver.infinity(),
            f"target_fullfillment_in_year_{y}")
    labor_in_year[y] = solver.NumVar(0.0, solver.infinity(),
            f"labor_in_year_{y}")

    for p in products:
      accumulation_for_of[y][p] = {}
      capital_stock_for_of[y][p] = {}
      depreciation_in_production_of[y][p] = {}
      flow_for_of[y][p] = {}

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
        leontief_constraint.SetCoefficient(target_fullfillment_in_year[y], -1)
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
      objective.SetCoefficient(target_fullfillment_in_year[y], 1)
  objective.SetMaximization()

  print(solver.ExportModelAsLpFormat(obfuscated = False))
  print(f"number of variables: {solver.NumVariables()}")
  print(f"number of constraints: {solver.NumConstraints()}")

  # solve
  result_status = solver.Solve()

  # output results
  print(result_status == pywraplp.Solver.OPTIMAL)

  if (result_status == pywraplp.Solver.OPTIMAL):
    for y in range(years):
      print(f"target_fullfillment_in_year_{y}: {target_fullfillment_in_year[y].solution_value()}")
      print(f"labor_in_year_{y}: {labor_in_year[y].solution_value()}")

      for p in products:
        print(f"accumulation_of_{p}_year_{y}: {accumulation_of[y][p].solution_value()}")
        print(f"final_consumption_of_{p}_year_{y}: {final_consumption_of[y][p].solution_value()}")
        print(f"labor_for_{p}_year_{y}: {labor_for[y][p].solution_value()}")
        print(f"output_of_{p}_year_{y}: {output_of[y][p].solution_value()}")
        print(f"productive_comsumption_of_{p}_year_{y}: {productive_consumption_of[y][p].solution_value()}")

        for q in products:
          print(f"accumulation_for_{p}_of_{q}_year_{y}: {accumulation_for_of[y][p][q].solution_value()}")
          print(f"capital_stock_for_{p}_of_{q}_year_{y}: {capital_stock_for_of[y][p][q].solution_value()}")
          print(f"depreciation_in_{p}_production_of_{q}_year_{y}: {depreciation_in_production_of[y][p][q].solution_value()}")
          print(f"flow_for_{q}_of_{q}_year_{y}: {flow_for_of[y][p][q].solution_value()}")

if __name__ == '__main__':
  main()
