from collections import defaultdict
import pandas as pd
import math
import sys

class Planning:
    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir

    def harmony(self, target, netouput):
        scale = (netouput - target) / target
        return scale - 0.5 * pow(scale, 2) if scale < 0 else math.log(scale+1)

    def derivative_harmony(self, target, netoutput):
        epsilon = 0.000001
        # sys.float_info.epsilon
        base = self.harmony(target, netoutput)
        base_plus_epsilon = self.harmony(target, epsilon + netoutput)
        return (base_plus_epsilon - base) / epsilon


    def import_data(self):
        self.flows = pd.read_csv(f"{self.input_dir}/flows.csv")
        self.products = list(self.flows)[1:]
        rows = list(self.flows['headings'])
        self.row_map = {name: index for index, name in enumerate(rows)}

        self.targets = pd.read_csv(f"{self.input_dir}/targets.csv")
        self.years = self.targets.shape[0]

        self.cap = pd.read_csv(f"{self.input_dir}/capital_stock.csv")
        self.dep = pd.read_csv(f"{self.input_dir}/depreciation_rates.csv")

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
