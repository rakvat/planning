# -*- coding: utf-8 -*-
#
import unittest
import pandas as pd
from planning import Planning
import pdb

class TestPlanningAlg1(unittest.TestCase):

    def test_import_example_data(self):
        planning = Planning()
        planning.import_example_data()
        self.assertEqual(planning.flows.shape, (6,5))

    def test_plan_result(self):
        planning = Planning()
        planning.import_example_data()
        planning.setup_solver()
        planning.solve()
        planning.export_results()
        target_fulfillment = pd.read_csv('out/target_fulfillment_in_year.csv')
        output = pd.read_csv('out/output_of.csv')
        self.assertTrue(0.15922 < target_fulfillment.iloc[0][1] < 0.15923)
        self.assertTrue(9.02671 < output.iloc[0]['iron'] < 9.02672)
        self.assertTrue(0.19788 < output.iloc[4]['iron'] < 0.19789)
