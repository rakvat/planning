import pulp as pl

from typing import Callable

from planning_input import PlanningInput


PRIO_KEY = "prio"


class Planner:
    ENV_ALLOWANCE = 100

    def __init__(self) -> None:
        self.input = PlanningInput()
        self.input.load_data()

    def process(self) -> None:
        objectives = [self.set_min_labor_objective, self.set_max_production_objective]

        for objective in objectives:
            self.add_variables()
            self.add_objective(objective)
            self.add_constraints()

    def add_variables(self):
        self.gross_production_of = {}
        for product_name in self.input.product_names:
            self.gross_production_of[product_name] = pl.LpVariable(
                f"gross_production_of_{product_name}", lowBound=0
            )

        self.net_production_of = {}
        for product_name in self.input.product_names:
            self.net_production_of[product_name] = pl.LpVariable(
                f"net_production_of_{product_name}", lowBound=0
            )

        self.total_labor = pl.LpVariable("Total labor", lowBound=0)

        self.total_environmental_credit = pl.LpVariable(
            "Used environmental credit", lowBound=0
        )

    def add_constraints(self) -> None:
        # 0. inputs + net production == gross production
        for product_name in self.input.product_names:
            sum_inputs = sum(
                self.gross_production_of[other_product_name]
                * self.input.product_map[other_product_name]
                .ingredients[product_name]
                .amount
                for other_product_name in self.input.product_names
            )
            self.model += self.net_production_of[product_name] == self.gross_production_of[product_name] - sum_inputs

        # 1. sum gross production labor == total labor
        sum_labor = sum(
            self.gross_production_of[product_name]
            * self.input.product_map[product_name].required_labor
            for product_name in self.input.product_names
        )
        self.model += self.total_labor == sum_labor

        # 3. sum gross production env impact == total envimpact
        sum_envimpact = sum(
            self.gross_production_of[product_name]
            * self.input.product_map[product_name].envimpact
            for product_name in self.input.product_names
        )
        self.model += self.total_environmental_credit == sum_envimpact

        # 4. every product reaches it's minimum
        for product_name in self.input.product_names:
            self.model += self.net_production_of[product_name] >= self.input.product_map[product_name].minimum, f"minimum_{product_name}"

        # 5. gross production stays below env allowance
        self.model += self.total_environmental_credit <= self.ENV_ALLOWANCE, "environmental allowance"

    def add_objective(self, build_objective: Callable) -> None:
        print("\n")
        self.solver = pl.getSolver('PULP_CBC_CMD')
        build_objective()
        self.solve()
        self.output_solution(debug=True)

    def set_min_labor_objective(self) -> None:
        self.model = pl.LpProblem("Planning", pl.LpMinimize)

        print("***** Minimum Labor Objective *****")
        objective = 0
        for product_name in self.input.product_names:
            if (labor := self.input.product_map[product_name].required_labor) == 0:
                continue
            objective += self.gross_production_of[product_name] * labor
        self.model += objective, "minimize labor"

    def set_max_production_objective(self) -> None:
        print("***** Maximal Production Objective *****")
        self.model = pl.LpProblem("Planning", pl.LpMaximize)
        objective = 0
        for product_name in self.input.product_names:
            product = self.input.product_map[product_name]
            coeff = (product.prio * 0.1) * product.envimpact
            objective += self.net_production_of[product_name] * coeff
        self.model += objective, "maximize productivity"

    def solve(self) -> None:
        self.result = self.model.solve(self.solver)

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


if __name__ == "__main__":
    Planner().process()
