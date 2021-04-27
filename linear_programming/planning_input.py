import os

from dataclasses import dataclass
import pandas as pd
import numpy as np


LABOR_KEY = "labor"
OUTPUT_KEY = "output"

INPUT_DICT = dict[str, float]


@dataclass
class Resource:
    name: str
    unit: str


@dataclass
class Product(Resource):
    ingredients: dict[str, "Ingredient"]
    minimum: float
    envimpact: float = 0.00001
    prio: float = 1  # should be between 10 (highest) and 0 (lowest)

    @property
    def required_labor(self) -> float:
        return self.ingredients[LABOR_KEY].amount


@dataclass
class Ingredient:
    resource: Resource
    amount: float


class PlanningInput:
    def __init__(self, input_folder: str) -> None:
        self.input_folder = input_folder

    def get_resource(self, key: str) -> Resource:
        return self.labour_resource if key == LABOR_KEY else self.product_map[key]

    def load_data(self) -> None:
        units = pd.read_csv(os.path.join(self.input_folder, "units.csv")).fillna(value="u")
        constraints = pd.read_csv(os.path.join(self.input_folder, "constraints.csv")).replace({np.nan: None})
        input_output = pd.read_csv(os.path.join(self.input_folder, "input_output.csv"))
        self.product_names = input_output.keys()[1:]
        self.product_map: dict[str, Product] = {}
        for product_name in self.product_names:
            product_constraints = dict(
                zip(constraints["headings"].values, constraints[product_name])
            )
            product_constraints = {k:v for k,v in product_constraints.items() if v is not None}

            unit = units[product_name][0]
            self.product_map[product_name] = Product(
                name=product_name,
                ingredients={},
                unit=unit,
                **product_constraints,
            )

        self.labour_resource = Resource(name="labor", unit="kh")

        for product_name in self.product_names:
            input_dict = self._normalize(dict(
                zip(input_output["headings"].values, input_output[product_name])
            ))

            ingredients = {
                key: Ingredient(resource=self.get_resource(key), amount=value)
                for key, value in input_dict.items()
            }
            self.product_map[product_name].ingredients = ingredients

    def _normalize(self, input_dict: INPUT_DICT) -> INPUT_DICT:
        if OUTPUT_KEY in input_dict:
            output = input_dict[OUTPUT_KEY]
            return {key: value / output for key, value in input_dict.items() if key != OUTPUT_KEY}
        else:
            return input_dict

