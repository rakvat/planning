import click
import pulp as pl
from typing import Callable

from planning_input import PlanningInput


PRIO_KEY = "prio"


class Planner:
    ENV_ALLOWANCE = 100

    def __init__(self, input_folder: str, debug: bool) -> None:
        self.debug = debug
        self.input = PlanningInput(input_folder)
        self.input.load_data()

    def process(self) -> None:
        objectives = [self.set_min_labor_objective, self.set_max_production_objective]

        for objective in objectives:
            self.add_variables()
            self.add_objective(objective)
            self.add_constraints()
            self.solve()
            self.output_solution(debug=self.debug)

    def add_variables(self):
        self.gross_production_of = pl.LpVariable.dicts(
            "gross production of",
            (product_name for product_name in self.input.product_names),
            lowBound=0,
            cat="Continuous",
        )

        self.net_production_of = pl.LpVariable.dicts(
            "net production of",
            (product_name for product_name in self.input.product_names),
            lowBound=0,
            cat="Continuous",
        )

        self.total_labor = pl.LpVariable("total labor", lowBound=0, cat="Continuous")

        self.total_environmental_credit = pl.LpVariable(
            "used environmental credit", lowBound=0, cat="Continuous"
        )

    def add_objective(self, build_objective: Callable) -> None:
        print("\n")
        build_objective()

    def set_min_labor_objective(self) -> None:
        print("***** Minimum Labor Objective *****")
        self.model = pl.LpProblem("Planning", pl.LpMinimize)

        self.model += (
            pl.lpSum(
                [
                    labor * self.gross_production_of[product_name]
                    for product_name in self.input.product_names
                    if (labor := self.input.product_map[product_name].required_labor)
                    > 0
                ]
            ),
            "minimize labor",
        )

    def set_max_production_objective(self) -> None:
        print("***** Maximal Production Objective *****")
        self.model = pl.LpProblem("Planning", pl.LpMaximize)

        self.model += (
            pl.lpSum(
                [
                    ((product := self.input.product_map[product_name]).prio * 0.1)
                    * product.envimpact
                    * self.net_production_of[product_name]
                    for product_name in self.input.product_names
                ]
            ),
            "maximize productivity",
        )

    def add_constraints(self) -> None:
        # 0. inputs + net production == gross production
        for product_name in self.input.product_names:
            sum_inputs = pl.lpSum(
                self.gross_production_of[other_product_name]
                * self.input.product_map[other_product_name]
                .ingredients[product_name]
                .amount
                for other_product_name in self.input.product_names
            )
            self.model += (
                self.net_production_of[product_name]
                == self.gross_production_of[product_name] - sum_inputs,
                f"net production {product_name}",
            )

        # 1. sum gross production labor == total labor
        sum_labor = pl.lpSum(
            self.gross_production_of[product_name]
            * self.input.product_map[product_name].required_labor
            for product_name in self.input.product_names
        )
        self.model += self.total_labor == sum_labor, "sum labor"

        # 3. sum gross production env impact == total envimpact
        sum_envimpact = sum(
            self.gross_production_of[product_name]
            * self.input.product_map[product_name].envimpact
            for product_name in self.input.product_names
        )
        self.model += (
            self.total_environmental_credit == sum_envimpact,
            "sum enviromental impact",
        )

        # 4. every product reaches it's minimum
        for product_name in self.input.product_names:
            self.model += (
                self.net_production_of[product_name]
                >= self.input.product_map[product_name].minimum,
                f"minimum {product_name}",
            )

        # 5. gross production stays below env allowance
        self.model += (
            self.total_environmental_credit <= self.ENV_ALLOWANCE,
            "environmental allowance",
        )

    def solve(self) -> None:
        self.model.solve()

    def print_model(self) -> None:
        print("Model")
        print("-----")
        print(self.model)
        print("-----")

    def output_solution(self, debug: bool) -> None:
        if debug:
            self.print_model()
            print(f"Status: {pl.LpStatus[self.model.status]}")
            print("\n")
        print("Suggested Plan")
        print("--------------")
        for product_name in self.input.product_names:
            product = self.input.product_map[product_name]
            print(
                f"{product.name}: {self.gross_production_of[product_name].varValue:.3f}{product.unit}, "
                f"net output {self.net_production_of[product_name].varValue:.3f}{product.unit}, "
                f"minimum {product.minimum:.3f}{product.unit}, "
                f"envimpact: {self.gross_production_of[product_name].varValue * product.envimpact:.3f}, "
                f"work: {self.gross_production_of[product_name].varValue * product.required_labor:.3f}{self.input.labour_resource.unit}, "
            )
        print(
            f"Total labor: {self.total_labor.varValue:0.3f}{self.input.labour_resource.unit}"
        )
        print(
            f"Used environmental credit: {self.total_environmental_credit.varValue:0.3f}/{self.ENV_ALLOWANCE:0.3f}"
        )

@click.command()
@click.argument('input_folder', default='./input_simple')
@click.option('--debug/--nodebug', default=False, show_default=True, type=bool)
def plan(input_folder: str, debug: bool):
    planner = Planner(input_folder, debug)
    planner.process()

if __name__ == '__main__':
    plan()
