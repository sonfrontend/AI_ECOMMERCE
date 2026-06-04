import pandas as pd
df = pd.read_excel('Transactions.xlsx', nrows=5)
print(df.columns.tolist())
