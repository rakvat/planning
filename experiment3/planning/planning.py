from collections import defaultdict
import pandas as pd
from ortools.linear_solver import pywraplp

class Planning:
    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir

    def import_example_data(self):
        self.flows = pd.read_csv(f"{self.input_dir}/flows.csv")
        self.products = list(self.flows)[1:]
        rows = list(self.flows['headings'])
        self.row_map = {name: index for index, name in enumerate(rows)}

        self.targets = pd.read_csv(f"{self.input_dir}/targets.csv")
        self.years = self.targets.shape[0]

        self.cap = pd.read_csv(f"{self.input_dir}/capital_stock.csv")
        self.dep = pd.read_csv(f"{self.input_dir}/depreciation_rates.csv")

    def setup_variables(self):
        self.accumulation_for_of = defaultdict(lambda: defaultdict(dict))
        self.accumulation_of = defaultdict(lambda: defaultdict(dict))
        self.capital_stock_for_of = defaultdict(lambda: defaultdict(dict))
        self.depreciation_in_production_of = defaultdict(lambda: defaultdict(dict))
        self.final_consumption_of = defaultdict(lambda: defaultdict(dict))
        self.flow_for_of = defaultdict(lambda: defaultdict(dict))
        self.labor_in_year = defaultdict(lambda: defaultdict(dict))
        self.labor_for = defaultdict(lambda: defaultdict(dict))
        self.output_of = defaultdict(lambda: defaultdict(dict))
        self.productive_consumption_of = defaultdict(lambda: defaultdict(dict))
        self.target_fulfillment_in_year = defaultdict(lambda: defaultdict(dict))

        for y in range(self.years):
            self.target_fulfillment_in_year[y] = self.solver.NumVar(
                0.0, self.solver.infinity(), f"target_fulfillment_in_year_{y}")
            self.labor_in_year[y] = self.solver.NumVar(0.0, self.solver.infinity(), f"labor_in_year_{y}")

            for p in self.products:
                self.accumulation_of[y][p] = self.solver.NumVar(
                    0.0, self.solver.infinity(), f"accumulation_of_{p}_year_{y}")
                self.final_consumption_of[y][p] = self.solver.NumVar(
                    0.0, self.solver.infinity(), f"final_consumption_of_{p}_year_{y}")
                self.labor_for[y][p] = self.solver.NumVar(
                    0.0, self.solver.infinity(), f"labor_for_{p}_year_{y}")
                self.output_of[y][p] = self.solver.NumVar(
                    0.0, self.solver.infinity(), f"output_of_{p}_year_{y}")
                self.productive_consumption_of[y][p] = self.solver.NumVar(
                    0.0, self.solver.infinity(), f"productive_comsumption_of_{p}_year_{y}")

                for q in self.products:
                    self.accumulation_for_of[y][p][q] = self.solver.NumVar(
                        0.0, self.solver.infinity(), f"accumulation_for_{p}_of_{q}_year_{y}")
                    self.capital_stock_for_of[y][p][q] = self.solver.NumVar(
                        0.0, self.solver.infinity(), f"capital_stock_for_{p}_of_{q}_year_{y}")
                    self.depreciation_in_production_of[y][p][q] = self.solver.NumVar(
                        0.0, self.solver.infinity(), f"depreciation_in_{p}_production_of_{q}_year_{y}")
                    self.flow_for_of[y][p][q] = self.solver.NumVar(
                        0.0, self.solver.infinity(), f"flow_for_{p}_of_{q}_year_{y}")

    def __setup_year_based_constraints(self, y):
        # 1. targets given by leontief demand for year
        for p in self.products:
            if self.__target(p, y) > 0:
                leontief_constraint = self.solver.Constraint(0, self.solver.infinity(), 'leontief')
                leontief_constraint.SetCoefficient(self.final_consumption_of[y][p], 1/self.__target(p, y))
                leontief_constraint.SetCoefficient(self.target_fulfillment_in_year[y], -1)
        # 2. labor total
        labor_total_constraint = self.solver.Constraint(0, self.solver.infinity(), 'labor_total')
        labor_total_constraint.SetCoefficient(self.labor_in_year[y], 1)
        for p in self.products:
            labor_total_constraint.SetCoefficient(self.labor_for[y][p], -1)
        # 3. labor supply
        labor_supply_contraint = self.solver.Constraint(
            -self.solver.infinity(), self.__target('labor', y), 'labor_supply')
        labor_supply_contraint.SetCoefficient(self.labor_in_year[y], 1)

        for p in self.products:
            self.__setup_year_p_based_constraints(y, p)

    def __setup_year_p_based_constraints(self, y, p):
        # 4. labor constraint
        if self.__io('labor', p) != 0:
            labor_constraint = self.solver.Constraint(0, self.solver.infinity(), 'labor')
            labor_constraint.SetCoefficient(self.output_of[y][p], -1)
            labor_constraint.SetCoefficient(self.labor_for[y][p], self.__io('output', p)/self.__io('labor', p))
        # 5. accumulation total
        accumulation_total_constraint = self.solver.Constraint(
            0, self.solver.infinity(), 'accumulation_total')
        accumulation_total_constraint.SetCoefficient(self.accumulation_of[y][p], 1)
        for q in self.products:
            accumulation_total_constraint.SetCoefficient(self.accumulation_for_of[y][q][p], -1)
        # 6. productive consumption
        productive_consumption_constraint = self.solver.Constraint(
            0, self.solver.infinity(), 'productive_consumption')
        productive_consumption_constraint.SetCoefficient(self.productive_consumption_of[y][p], 1)
        for q in self.products:
            productive_consumption_constraint.SetCoefficient(self.flow_for_of[y][q][p], -1)
        # 7. consumption
        consumption_constraint = self.solver.Constraint(0, self.solver.infinity(), 'consumption')
        consumption_constraint.SetCoefficient(self.output_of[y][p], 1)
        consumption_constraint.SetCoefficient(self.accumulation_of[y][p], -1)
        consumption_constraint.SetCoefficient(self.final_consumption_of[y][p], -1)
        consumption_constraint.SetCoefficient(self.productive_consumption_of[y][p], -1)

        for q in self.products:
            self.__setup_year_p_q_based_constraints(y, p, q)

    def __setup_year_p_q_based_constraints(self, y, p, q):
        # 8. output equation
        if self.__capital_stock(q, p) != 0:
            output_constraint = self.solver.Constraint(0, self.solver.infinity(), 'output')
            output_constraint.SetCoefficient(
                self.capital_stock_for_of[y][p][q], self.__io('output', p)/self.__capital_stock(q, p))
            output_constraint.SetCoefficient(self.output_of[y][p], -1)
        # 9. flow constraint
        if self.__io(q, p) != 0:
            flow_constraint = self.solver.Constraint(0, self.solver.infinity(), 'flow')
            flow_constraint.SetCoefficient(self.flow_for_of[y][p][q], self.__io('output', p)/self.__io(q, p))
            flow_constraint.SetCoefficient(self.output_of[y][p], -1)
        # 10. depreciation
        depreciation_constraint = self.solver.Constraint(0, 0, 'depreciation')
        depreciation_constraint.SetCoefficient(self.depreciation_in_production_of[y][p][q], 1)
        depreciation_constraint.SetCoefficient(
            self.capital_stock_for_of[y][p][q], -self.__depreciation_rates(q, p))
        if y > 0:
            # 11. accumulation constraint
            accumulation_constraint = self.solver.Constraint(
                0, self.solver.infinity(), 'accumulation')
            accumulation_constraint.SetCoefficient(
                self.capital_stock_for_of[y-1][p][q], 1)
            accumulation_constraint.SetCoefficient(
                self.accumulation_for_of[y-1][p][q], 1)
            accumulation_constraint.SetCoefficient(
                self.depreciation_in_production_of[y-1][p][q], -1)
            accumulation_constraint.SetCoefficient(
                self.capital_stock_for_of[y][p][q], -1)
        else:
            # 12. initial capital stocks
            inital_capital_stock_constraint = self.solver.Constraint(
                -self.solver.infinity(), float(self.__capital_stock(q, p)), 'initial_capital_stocks')
            inital_capital_stock_constraint.SetCoefficient(self.capital_stock_for_of[y][p][q], 1)

    def setup_constraints(self):
        for y in range(self.years):
            self.__setup_year_based_constraints(y)

    def setup_objective(self):
        objective = self.solver.Objective()
        for y in range(self.years):
            objective.SetCoefficient(self.target_fulfillment_in_year[y], 1)
        objective.SetMaximization()

    def setup_solver(self):
        self.solver = pywraplp.Solver('Planning', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)

        self.setup_variables()
        self.setup_constraints()
        self.setup_objective()

    def print_solver(self):
        print(self.solver.ExportModelAsLpFormat(obfuscated=False))
        print(f"number of variables: {self.solver.NumVariables()}")
        print(f"number of constraints: {self.solver.NumConstraints()}")

    def solve(self):
        self.result_status = self.solver.Solve()

    def format_results(self):
        self.target_fulfillment_in_year = {
            y: v.solution_value() for y, v in self.target_fulfillment_in_year.items()}
        self.labor_in_year = {y: v.solution_value() for y, v in self.labor_in_year.items()}
        for y in range(self.years):
            self.accumulation_of[y] = {p: v.solution_value() for p, v in self.accumulation_of[y].items()}
            self.final_consumption_of[y] = {
                p: v.solution_value() for p, v in self.final_consumption_of[y].items()}
            self.labor_for[y] = {p: v.solution_value() for p, v in self.labor_for[y].items()}
            self.output_of[y] = {p: v.solution_value() for p, v in self.output_of[y].items()}
            self.productive_consumption_of[y] = {
                p: v.solution_value() for p, v in self.productive_consumption_of[y].items()}

            for p in self.products:
                self.accumulation_for_of[y][p] = {
                    q: v.solution_value() for q, v in self.accumulation_for_of[y][p].items()}
                self.capital_stock_for_of[y][p] = {
                    q: v.solution_value() for q, v in self.capital_stock_for_of[y][p].items()}
                self.depreciation_in_production_of[y][p] = {
                    q: v.solution_value() for q, v in self.depreciation_in_production_of[y][p].items()}
                self.flow_for_of[y][p] = {
                    q: v.solution_value() for q, v in self.flow_for_of[y][p].items()}

    def export_results(self):
        if self.result_status != pywraplp.Solver.OPTIMAL:
            print("no optimal solution")
            return

        self.format_results()
        df = pd.DataFrame.from_dict(self.target_fulfillment_in_year, orient='index')
        df.to_csv(f"{self.output_dir}/target_fulfillment_in_year.csv")

        df = pd.DataFrame.from_dict(self.labor_in_year, orient='index')
        df.to_csv(f"{self.output_dir}/labor_in_year.csv")

        df = pd.DataFrame.from_dict(self.accumulation_of, orient='index')
        df.to_csv(f"{self.output_dir}/accumulation_of.csv", columns=self.products)
        df = pd.DataFrame.from_dict(self.final_consumption_of, orient='index')
        df.to_csv(f"{self.output_dir}/final_consumption_of.csv", columns=self.products)
        df = pd.DataFrame.from_dict(self.labor_for, orient='index')
        df.to_csv(f"{self.output_dir}/labor_for.csv", columns=self.products)
        df = pd.DataFrame.from_dict(self.productive_consumption_of, orient='index')
        df.to_csv(f"{self.output_dir}/productive_consumption_of.csv", columns=self.products)
        df = pd.DataFrame.from_dict(self.output_of, orient='index')
        df.to_csv(f"{self.output_dir}/output_of.csv", columns=self.products)

    def output_result(self):
        print(f"Found optimal solution? {self.result_status == pywraplp.Solver.OPTIMAL}")
        print('\nSolution:')

        if self.result_status == pywraplp.Solver.OPTIMAL:
            for y in range(self.years):
                print(f"target_fulfillment_in_year_{y}: {self.target_fulfillment_in_year[y]}")
                print(f"labor_in_year_{y}: {self.labor_in_year[y]}")

                for p in self.products:
                    print(f"accumulation_of_{p}_year_{y}: {self.accumulation_of[y][p]}")
                    print(f"final_consumption_of_{p}_year_{y}: {self.final_consumption_of[y][p]}")
                    print(f"labor_for_{p}_year_{y}: {self.labor_for[y][p]}")
                    print(f"output_of_{p}_year_{y}: {self.output_of[y][p]}")
                    print(f"productive_comsumption_of_{p}_year_{y}: {self.productive_consumption_of[y][p]}")

                    for q in self.products:
                        print(f"accumulation_for_{p}_of_{q}_year_{y}: {self.accumulation_for_of[y][p][q]}")
                        print(f"capital_stock_for_{p}_of_{q}_year_{y}: {self.capital_stock_for_of[y][p][q]}")
                        print(f"depreciation_in_{p}_production_of_{q}_year_{y}: "
                              "{self.depreciation_in_production_of[y][p][q]}")
                        print(f"flow_for_{q}_of_{q}_year_{y}: {self.flow_for_of[y][p][q]}")

    def __target(self, key, year):
        return float(self.targets[key][year])

    def __io(self, input_product, output_product):
        return self.flows[output_product][self.row_map[input_product]]

    def __capital_stock(self, input_product, output_product):
        return self.cap[output_product][self.row_map[input_product]]

    def __depreciation_rates(self, input_product, output_product):
        return self.dep[output_product][self.row_map[input_product]]
