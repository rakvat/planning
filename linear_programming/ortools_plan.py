from typing import Callable
from ortools.linear_solver import pywraplp

from planning_input import PlanningInput


PRIO_KEY = "prio"


class Planner:
    ENV_ALLOWANCE = 100

    def __init__(self) -> None:
        self.input = PlanningInput()
        self.input.load_data()
        self.solver = pywraplp.Solver(
            "Planning", pywraplp.Solver.GLOP_LINEAR_PROGRAMMING
        )

    def process(self) -> None:
        objectives = [self.set_min_labor_objective, self.set_max_production_objective]

        for objective in objectives:
            self.add_variables()
            self.add_objective(objective)
            self.add_constraints()
            self.solve()
            self.output_solution(debug=True)

    def add_variables(self) -> None:
        self.gross_production_of = {}
        for product_name in self.input.product_names:
            self.gross_production_of[product_name] = self.solver.NumVar(
                0.0, self.solver.infinity(), f"gross_production_of_{product_name}"
            )

        self.net_production_of = {}
        for product_name in self.input.product_names:
            self.net_production_of[product_name] = self.solver.NumVar(
                0.0, self.solver.infinity(), f"net_production_of_{product_name}"
            )

        self.total_labor = self.solver.NumVar(
            0.0, self.solver.infinity(), "Total labor"
        )

        self.total_environmental_credit = self.solver.NumVar(
            0.0, self.solver.infinity(), "Used environmental credit"
        )

    def add_objective(self, build_objective: Callable) -> None:
        print("\n")
        build_objective()

    def set_min_labor_objective(self) -> None:
        print("***** Minimum Labor Objective *****")
        objective = self.solver.Objective()
        for product_name in self.input.product_names:
            if (labor := self.input.product_map[product_name].required_labor) == 0:
                continue
            objective.SetCoefficient(self.gross_production_of[product_name], labor)

        objective.SetMinimization()

    def set_max_production_objective(self) -> None:
        print("***** Maximal Production Objective *****")
        objective = self.solver.Objective()
        for product_name in self.input.product_names:
            product = self.input.product_map[product_name]
            coeff = (product.prio * 0.1) * product.envimpact
            objective.SetCoefficient(self.net_production_of[product_name], coeff)

        objective.SetMaximization()

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
            self.solver.Add(
                self.net_production_of[product_name]
                == self.gross_production_of[product_name] - sum_inputs
            )

        # 1. sum gross production labor == total labor
        sum_labor = sum(
            self.gross_production_of[product_name]
            * self.input.product_map[product_name].required_labor
            for product_name in self.input.product_names
        )
        self.solver.Add(self.total_labor == sum_labor)

        # 3. sum gross production env impact == total envimpact
        sum_envimpact = sum(
            self.gross_production_of[product_name]
            * self.input.product_map[product_name].envimpact
            for product_name in self.input.product_names
        )
        self.solver.Add(self.total_environmental_credit == sum_envimpact)

        # 4. every product reaches it's minimum
        for product_name in self.input.product_names:
            self.solver.Add(
                self.net_production_of[product_name]
                >= self.input.product_map[product_name].minimum,
                f"minimum_{product_name}",
            )

        # 5. gross production stays below env allowance
        self.solver.Add(
            self.total_environmental_credit <= self.ENV_ALLOWANCE,
            "environmental allowance",
        )

    def solve_with(self, build_objective: Callable) -> None:
        print("\n")
        build_objective()
        self.solve()
        self.output_solution(debug=False)

    def solve(self) -> None:
        self.result_status = self.solver.Solve()

    def print_model(self) -> None:
        print("Model")
        print("-----")
        print(self.solver.ExportModelAsLpFormat(obfuscated=False))
        print("-----")

    def output_solution(self, debug: bool) -> None:
        if debug:
            self.print_model()
            print(
                f"Found optimal solution? {self.result_status == pywraplp.Solver.OPTIMAL}"
            )
            print(f"Status: {self.result_status}")
            print("\n")
        print("Suggested Plan")
        print("--------------")
        for product_name in self.input.product_names:
            product = self.input.product_map[product_name]
            print(
                f"{product.name}: {self.gross_production_of[product_name].solution_value():.3f}{product.unit}, "
                f"net output {self.net_production_of[product_name].solution_value():.3f}{product.unit}, "
                f"minimum {product.minimum:.3f}{product.unit}, "
                f"envimpact: {self.gross_production_of[product_name].solution_value() * product.envimpact:.3f}, "
                f"work: {self.gross_production_of[product_name].solution_value() * product.required_labor:.3f}{self.input.labour_resource.unit}, "
            )
        print(
            f"Total labor: {self.total_labor.solution_value():0.3f}{self.input.labour_resource.unit}"
        )
        print(
            f"Used environmental credit: {self.total_environmental_credit.solution_value():0.3f}/{self.ENV_ALLOWANCE:0.3f}"
        )


if __name__ == "__main__":
    Planner().process()
