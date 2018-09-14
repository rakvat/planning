from collections import defaultdict
import pandas as pd
import numpy as np
import math
import sys
import pdb

class Planning:
    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir

    def import_data(self):
        self.flows = pd.read_csv(f"{self.input_dir}/flows.csv")
        rows = list(self.flows['headings'])
        self.products = list(self.flows)[1:]
        self.flows = np.array(self.flows)[:,1:].astype(float)
        self.num_products = len(self.products)
        self.row_map = {name: index for index, name in enumerate(rows)}
        self.targets = pd.read_csv(f"{self.input_dir}/targets.csv")
        self.years = self.targets.shape[0]
        # strip year and labor column
        self.product_targets = np.array(self.targets)[:,1:(self.num_products + 1)].astype(float)

    def harmonize(self):
        # random initial production weights
        self.production_weights = 100 * np.random.rand(5, self.num_products)
        self.calc_outputs()
        self.calc_harmony()
        self.calc_labor()
        self.calc_target_fulfillment()

    def export_results(self):
        df = pd.DataFrame(self.target_fulfillment_in_year)
        df.to_csv(f"{self.output_dir}/target_fulfillment_in_year.csv")
        df = pd.DataFrame(self.labor_in_year)
        df.to_csv(f"{self.output_dir}/labor_in_year.csv")
        df = pd.DataFrame(self.final_consumption_of, columns=self.products)
        df.to_csv(f"{self.output_dir}/final_consumption_of.csv", columns=self.products)
        df = pd.DataFrame(self.labor_for, columns=self.products)
        df.to_csv(f"{self.output_dir}/labor_for.csv", columns=self.products)
        df = pd.DataFrame(self.productive_consumption_of, columns=self.products)
        df.to_csv(f"{self.output_dir}/productive_consumption_of.csv", columns=self.products)
        df = pd.DataFrame(self.output_of, columns=self.products)
        df.to_csv(f"{self.output_dir}/output_of.csv", columns=self.products)

    def harmony(self, target, netouput):
        scale = (netouput - target) / target
        return scale - 0.5 * pow(scale, 2) if scale < 0 else math.log(scale+1)

    def derivative_harmony(self, target, netoutput):
        epsilon = 0.000001
        base = self.harmony(target, netoutput)
        base_plus_epsilon = self.harmony(target, epsilon + netoutput)
        return (base_plus_epsilon - base) / epsilon

    def calc_outputs(self):
        self.output_of = np.multiply(self.production_weights, self.__output_row())
        # A shape year/products
        # B shape products/products
        # Aik*Bjk->ij
        self.productive_consumption_of = np.einsum(
                'ik,jk->ij', self.production_weights, self.__product_flow_matrix())
        # self.productive_consumption_of = np.random.rand(5, self.num_products)
        self.final_consumption_of = self.output_of - self.productive_consumption_of

    def calc_harmony(self):
        return 1

    def calc_target_fulfillment(self):
        self.target_fulfillment_of = np.divide(
                self.final_consumption_of,
                self.product_targets,
                out = np.ones_like(self.final_consumption_of),
                where = self.product_targets != 0
        )
        self.target_fulfillment_in_year = np.sum(self.target_fulfillment_of, axis = 1)

    def calc_labor(self):
        self.labor_for = np.multiply(self.production_weights, self.__labor_row())
        self.labor_in_year = np.sum(self.labor_for, axis = 1)

    def __target(self, key, year):
        return float(self.targets[key][year])

    def __io(self, input_product, output_product):
        return self.flows[output_product][self.row_map[input_product]]

    def __output_row(self):
        return self.flows[-1]

    def __labor_row(self):
        return self.flows[-2]

    def __product_flow_matrix(self):
        return self.flows[:-2,:]
