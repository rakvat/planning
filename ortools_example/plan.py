import os

from typing import Union, Callable
from dataclasses import dataclass
import pandas as pd
from ortools.linear_solver import pywraplp


LABOR_KEY = "labor"
PRIO_KEY = "prio"


@dataclass
class Resource:
    name: str
    unit: str

@dataclass
class Product(Resource):
    minimum: float
    envimpact: float
    prio: float  # should be between 10 (highest) and 0 (lowest)
    ingredients: dict[str, "Ingredient"]

    @property
    def required_labor(self) -> float:
        return self.ingredients[LABOR_KEY].amount


@dataclass
class Ingredient:
    resource: Resource
    amount: float


@dataclass
class Planner:
    INPUT_FOLDER = "."
    ENV_ALLOWANCE = 100

    def process(self) -> None:
        objectives = [self.set_min_labor_objective, self.set_max_production_objective]
        self.load_data()

        for objective in objectives:
            self.build_model()
            self.solve_with(objective)

    def get_resource(self, key: str) -> Resource:
        return self.labour_resource if key == LABOR_KEY else self.product_map[key]

    def load_data(self) -> None:
        units = pd.read_csv(os.path.join(self.INPUT_FOLDER, 'units.csv'))
        constraints = pd.read_csv(os.path.join(self.INPUT_FOLDER, 'constraints.csv'))
        input_output = pd.read_csv(os.path.join(self.INPUT_FOLDER, 'input_output.csv'))
        self.product_names = input_output.keys()[1:]
        self.product_map:dict[str, Product] = {}
        for product_name in self.product_names:
            product_constraints = dict(zip(constraints["headings"].values, constraints[product_name]))
            unit = units[product_name][0]
            self.product_map[product_name] = Product(
                name=product_name,
                ingredients={},
                unit=unit,
                **product_constraints,
            )

        self.labour_resource = Resource(name="labor", unit="kh")

        for product_name in self.product_names:
            input_dict = dict(zip(input_output["headings"].values, input_output[product_name]))
            ingredients = {key: Ingredient(resource=self.get_resource(key), amount=value) for key, value in input_dict.items()}
            self.product_map[product_name].ingredients = ingredients

    def build_model(self) -> None:
        self.solver = pywraplp.Solver('Planning', pywraplp.Solver.GLOP_LINEAR_PROGRAMMING)

        # variables
        self.gross_production_of = {}
        for product_name in self.product_names:
            self.gross_production_of[product_name] = self.solver.NumVar(0.0, self.solver.infinity(), f"gross_production_of_{product_name}")

        self.net_production_of = {}
        for product_name in self.product_names:
            self.net_production_of[product_name] = self.solver.NumVar(0.0, self.solver.infinity(), f"net_production_of_{product_name}")
            sum_inputs = sum(
                self.gross_production_of[other_product_name] * self.product_map[other_product_name].ingredients[product_name].amount
                for other_product_name in self.product_names
            )
            self.solver.Add(self.net_production_of[product_name] == self.gross_production_of[product_name] - sum_inputs)

        self.total_labor = self.solver.NumVar(0.0, self.solver.infinity(), "Total labor")
        sum_labor = sum(
            self.gross_production_of[product_name] * self.product_map[product_name].required_labor
            for product_name in self.product_names
        )
        self.solver.Add(self.total_labor == sum_labor)

        self.total_environmental_credit = self.solver.NumVar(0.0, self.solver.infinity(), "Used environmental credit")
        sum_envimpact = sum(
            self.gross_production_of[product_name] * self.product_map[product_name].envimpact
            for product_name in self.product_names
        )
        self.solver.Add(self.total_environmental_credit == sum_envimpact)

        # constraints
        # 1. every product reaches it's minimum
        for product_name in self.product_names:
            self.solver.Add(self.net_production_of[product_name] >= self.product_map[product_name].minimum, f"minimum_{product_name}")

        # 2. gross production stays below env allowance
        self.solver.Add(self.total_environmental_credit <= self.ENV_ALLOWANCE, "environmental allowance")

    def solve_with(self, build_objective: Callable) -> None:
        print("\n")
        build_objective()
        self.solve()
        self.output_solution(debug=False)

    def set_min_labor_objective(self) -> None:
        print("***** Minimum Labor Objective *****")
        objective = self.solver.Objective()
        for product_name in self.product_names:
            if (labor:=self.product_map[product_name].required_labor) == 0:
                continue
            objective.SetCoefficient(self.gross_production_of[product_name], labor)

        objective.SetMinimization()

    def set_max_production_objective(self) -> None:
        print("***** Maximal Production Objective *****")
        objective = self.solver.Objective()
        for product_name in self.product_names:
            product = self.product_map[product_name]
            coeff = (product.prio * 0.1) * product.envimpact
            objective.SetCoefficient(self.net_production_of[product_name], coeff)

        objective.SetMaximization()

    def solve(self) -> None:
        self.result_status = self.solver.Solve()

    def print_model(self) -> None:
        print("Model")
        print("-----")
        print(self.solver.ExportModelAsLpFormat(obfuscated = False))
        print("-----")

    def output_solution(self, debug:bool) -> None:
        if debug:
            self.print_model()
            print(f"Found optimal solution? {self.result_status == pywraplp.Solver.OPTIMAL}")
            print(f"Status: {self.result_status}")
            print("\n")
        print("Suggested Plan")
        print("--------------")
        for product_name in self.product_names:
            product = self.product_map[product_name]
            print(
                f"{product.name}: {self.gross_production_of[product_name].solution_value():.3f}{product.unit}, "
                f"net output {self.net_production_of[product_name].solution_value():.3f}{product.unit}, "
                f"minimum {product.minimum:.3f}{product.unit}, "
                f"envimpact: {self.gross_production_of[product_name].solution_value() * product.envimpact:.3f}, "
                f"work: {self.gross_production_of[product_name].solution_value() * product.required_labor:.3f}{self.labour_resource.unit}, "
            )
        print(f"Total labor: {self.total_labor.solution_value():0.3f}{self.labour_resource.unit}")
        print(f"Used environmental credit: {self.total_environmental_credit.solution_value():0.3f}/{self.ENV_ALLOWANCE:0.3f}")


if __name__ == '__main__':
    Planner().process()
