import os

from dataclasses import dataclass
import pandas as pd


LABOR_KEY = "labor"


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


class PlanningInput:
    INPUT_FOLDER = "./input"

    def get_resource(self, key: str) -> Resource:
        return self.labour_resource if key == LABOR_KEY else self.product_map[key]

    def load_data(self) -> None:
        units = pd.read_csv(os.path.join(self.INPUT_FOLDER, "units.csv"))
        constraints = pd.read_csv(os.path.join(self.INPUT_FOLDER, "constraints.csv"))
        input_output = pd.read_csv(os.path.join(self.INPUT_FOLDER, "input_output.csv"))
        self.product_names = input_output.keys()[1:]
        self.product_map: dict[str, Product] = {}
        for product_name in self.product_names:
            product_constraints = dict(
                zip(constraints["headings"].values, constraints[product_name])
            )
            unit = units[product_name][0]
            self.product_map[product_name] = Product(
                name=product_name,
                ingredients={},
                unit=unit,
                **product_constraints,
            )

        self.labour_resource = Resource(name="labor", unit="kh")

        for product_name in self.product_names:
            input_dict = dict(
                zip(input_output["headings"].values, input_output[product_name])
            )
            ingredients = {
                key: Ingredient(resource=self.get_resource(key), amount=value)
                for key, value in input_dict.items()
            }
            self.product_map[product_name].ingredients = ingredients
