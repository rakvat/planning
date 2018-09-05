import pandas as pd
import pdb

flows = pd.read_csv('flows.csv')
depreciation_rates = flows.copy()
depreciation_rates.loc[:,1:] = 0.1
depreciation_rates.to_csv('depreciation_rates.csv', index = False)
capital_stock = flows.copy()
capital_stock.loc[:,1:] = 1
capital_stock.to_csv('capital_stock.csv', index = False)
