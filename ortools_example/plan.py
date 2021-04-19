import os

from typing import Union
from dataclasses import dataclass
import pandas as pd
from ortools.linear_solver import pywraplp


@dataclass
class Resource:
    name: str

@dataclass
class Product:
    name: str
    minimum: float
    envimpact: float
    prio: float
    ingredients: dict[str, "Ingredient"]


@dataclass
class Ingredient:
    resource: Union[Product, Resource]
    amount: float


@dataclass
class Planner:
    INPUT_FOLDER = "."
    LABOR_KEY = "labor"
    ENV_ALLOWANCE = 100

    def process(self) -> None:
        self.load_data()
        self.build_model()
        self.solve()
        self.output_solution()

    def load_data(self) -> None:
        constraints = pd.read_csv(os.path.join(self.INPUT_FOLDER, 'constraints.csv'))
        input_output = pd.read_csv(os.path.join(self.INPUT_FOLDER, 'input_output.csv'))
        self.product_names = input_output.keys()[1:]
        self.resource_map = {}
        for product_name in self.product_names:
            product_constraints = dict(zip(constraints["headings"].values, constraints[product_name]))
            self.resource_map[product_name] = Product(
                name=product_name,
                ingredients={},
                **product_constraints,
            )

        self.resource_map[self.LABOR_KEY] = Resource(name="labor")

        for product_name in self.product_names:
            input_dict = dict(zip(input_output["headings"].values, input_output[product_name]))
            ingredients = {key: Ingredient(resource=self.resource_map[key], amount=value) for key, value in input_dict.items()}
            self.resource_map[product_name].ingredients = ingredients

    def build_model(self) -> None:
        self.solver = pywraplp.Solver('Planning', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)

        # variables
        self.gross_production_of = {}
        for product_name in self.product_names:
            self.gross_production_of[product_name] = self.solver.NumVar(0.0, self.solver.infinity(), f"gross_production_of_{product_name}")

        self.net_production_of = {}
        for product_name in self.product_names:
            self.net_production_of[product_name] = self.solver.NumVar(0.0, self.solver.infinity(), f"net_production_of_{product_name}")
            sum_inputs = sum(self.resource_map[other_product_name].ingredients[product_name].amount for other_product_name in self.product_names)
            self.solver.Add(self.net_production_of[product_name] == self.gross_production_of[product_name] - sum_inputs)

        self.total_labor = self.solver.NumVar(0.0, self.solver.infinity(), "Total labor")
        sum_labor = sum(self.gross_production_of[product_name] * self.resource_map[product_name].ingredients[self.LABOR_KEY].amount for product_name in self.product_names)
        self.solver.Add(self.total_labor == sum_labor)

        self.total_environmental_credit = self.solver.NumVar(0.0, self.solver.infinity(), "Used environmental credit")
        sum_envimpact = sum(self.gross_production_of[product_name] * self.resource_map[product_name].envimpact for product_name in self.product_names)
        self.solver.Add(self.total_environmental_credit == sum_envimpact)

        # constraints
        # 1. every product reaches it's minimum
        for product_name in self.product_names:
            constraint = self.solver.Constraint(self.resource_map[product_name].minimum, self.solver.infinity(), f"minimum_{product_name}")
            constraint.SetCoefficient(self.net_production_of[product_name], 1)

        # 2. gross production stays below env allowance
        env_allowance_constraint = self.solver.Constraint(0, self.ENV_ALLOWANCE, "environmental allowance")
        for product_name in self.product_names:
            if (product:=self.resource_map[product_name]).envimpact == 0:
                continue
            env_allowance_constraint.SetCoefficient(
                self.gross_production_of[product_name],
                float(product.envimpact),
            )

        # objective 1 maximize production
        # TODO

        # objective 2 minimize labor
        objective = self.solver.Objective()
        for product_name in self.product_names:
            if (labor:=self.resource_map[product_name].ingredients[self.LABOR_KEY].amount) == 0:
                continue
            objective.SetCoefficient(self.gross_production_of[product_name], labor)

        objective.SetMinimization()

    def solve(self) -> None:
        self.result_status = self.solver.Solve()
        # TODO solve with 2 variations
        # TODO if minimums can't be met, use priorities

    def print_model(self) -> None:
        print("Model")
        print("-----")
        print(self.solver.ExportModelAsLpFormat(obfuscated = False))
        print("-----")

    def output_solution(self) -> None:
        self.print_model()
        print(f"Found optimal solution? {self.result_status == pywraplp.Solver.OPTIMAL}")
        print("\n-----")
        print("Suggested Plan")
        print("-----")
        for p in self.product_names:
            print(f"{p}: {self.gross_production_of[p].solution_value()} (net output {self.net_production_of[p].solution_value()})")
        print(f"Total labor: {self.total_labor.solution_value()}")
        print(f"Used environmental credit: {self.total_environmental_credit.solution_value()}/{self.ENV_ALLOWANCE}")


if __name__ == '__main__':
    Planner().process()
