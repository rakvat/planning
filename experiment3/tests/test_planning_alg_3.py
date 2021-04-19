# -*- coding: utf-8 -*-
#
import unittest
import pandas as pd
from planning_alg3.planning import Planning
import pdb

class TestPlanningAlg3(unittest.TestCase):

    def test_import_example_data(self):
        planning = Planning('test_data', 'out/test_run')
        planning.import_data()
        self.assertEqual(planning.flows.shape, (6, 4))

    def test_harmony(self):
        planning = Planning('test_data', 'out/test_run')
        self.assertEqual(planning.harmony(5, 5), 0)
        self.assertEqual(planning.harmony(1, 1), 0)
        self.assertGreater(planning.harmony(1, 2), 0) # target overfulfillment
        self.assertLess(planning.harmony(2, 1), 0) # target underfulfillment
        self.assertLess(planning.harmony(10, 11), abs(planning.harmony(10, 9)))
        self.assertGreater(planning.harmony(10, 20), abs(planning.harmony(10, 9))) # huge overfulfillments win over smaller underfulfillments
        self.assertLess(planning.harmony(1, 1.1), abs(planning.harmony(1, 0.9)))
        self.assertLess(planning.harmony(0.1, 0.11), abs(planning.harmony(0.1, 0.09)))

    def test_derivative_harmony(self):
        planning = Planning('test_data', 'out/test_run')
        self.assertGreater(planning.derivative_harmony(5, 5), 0)
        self.assertLess(planning.derivative_harmony(5, 5), planning.derivative_harmony(1, 1)) # why?
        self.assertGreater(planning.derivative_harmony(1, 5), 0)
        self.assertLess(planning.derivative_harmony(1, 5), planning.derivative_harmony(5, 1))
