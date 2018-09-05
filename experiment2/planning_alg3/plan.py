"""This creates a 5 year plan for a small example economy
algorithm from https://github.com/wc22m/5yearplan """

import sys
import more_itertools as mit
from planning import Planning


def main():
    input_dir = mit.nth(sys.argv, 1, 'test_data')
    output_dir = mit.nth(sys.argv, 2, 'out/test_data')
    planning = Planning(input_dir, output_dir)
    planning.import_data()
    planning.setup_solver()
    planning.print_solver()
    planning.solve()
    planning.output_result()
    planning.export_results()

if __name__ == '__main__':
    main()
