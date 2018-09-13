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

    def harmonize(self):
        # fake it till you make it
        self.labor_in_year = {0: 10, 1: 9, 2: 8, 3: 7, 4: 8}
        self.accumulation_of = {
                0: { "coal": 1, "iron" : 1, "corn": 1, "bread": 1},
                1: { "coal": 1, "iron" : 1, "corn": 1, "bread": 1},
                2: { "coal": 1, "iron" : 1, "corn": 1, "bread": 1},
                3: { "coal": 1, "iron" : 1, "corn": 1, "bread": 1},
                4: { "coal": 1, "iron" : 1, "corn": 1, "bread": 1},
        }
        self.labor_for = {
                0: { "coal": 1, "iron" : 1, "corn": 1, "bread": 1},
                1: { "coal": 1, "iron" : 1, "corn": 1, "bread": 1},
                2: { "coal": 1, "iron" : 1, "corn": 1, "bread": 1},
                3: { "coal": 0.1, "iron" : 1, "corn": 1, "bread": 1},
                4: { "coal": 0, "iron" : 1, "corn": 1, "bread": 1},
        }
        self.output_of = {
                0: { "coal": 1.1, "iron" : 0.1, "corn": 1, "bread": 0},
                1: { "coal": 1.1, "iron" : 0.1, "corn": 1, "bread": 0},
                2: { "coal": 1.1, "iron" : 0.1, "corn": 1, "bread": 0},
                3: { "coal": 0.1, "iron" : 0.1, "corn": 1, "bread": 0},
                4: { "coal": 0.1, "iron" : 0.1, "corn": 1, "bread": 0},
        }
        self.productive_consumption_of = {
                0: { "coal": 0.1, "iron" : 0.1, "corn": 1, "bread": 0},
                1: { "coal": 0.1, "iron" : 0.1, "corn": 1, "bread": 0},
                2: { "coal": 0.1, "iron" : 0.1, "corn": 1, "bread": 0},
                3: { "coal": 0.1, "iron" : 0.1, "corn": 1, "bread": 0},
                4: { "coal": 0.1, "iron" : 0.1, "corn": 1, "bread": 0},
        }
        self.final_consumption_of = {
                0: { "coal": 1, "iron" : 0.1, "corn": 0, "bread": 1},
                1: { "coal": 0.5, "iron" : 0.1, "corn": 0, "bread": 1},
                2: { "coal": 0.25, "iron" : 0.1, "corn": 0, "bread": 1},
                3: { "coal": 0.1, "iron" : 0.1, "corn": 0, "bread": 1},
                4: { "coal": 0, "iron" : 0.1, "corn": 0, "bread": 1},
        }

        self.target_fulfillment_in_year = { 0: 1, 1: 1, 2: 1, 3: 1, 4: 1 }

    def export_results(self):
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


    def __target(self, key, year):
        return float(self.targets[key][year])

    def __io(self, input_product, output_product):
        return self.flows[output_product][self.row_map[input_product]]

    def __capital_stock(self, input_product, output_product):
        return self.cap[output_product][self.row_map[input_product]]

    def __depreciation_rates(self, input_product, output_product):
        return self.dep[output_product][self.row_map[input_product]]
