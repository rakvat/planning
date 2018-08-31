"""This creates a 5 year plan for a small example economy
algorithm from https://github.com/wc22m/5yearplan """

from planning import Planning


def main():
    planning = Planning()
    planning.import_example_data()
    planning.setup_solver()
    planning.print_solver()
    planning.solve()
    planning.output_result()
    planning.export_results()

if __name__ == '__main__':
    main()
