import pandas as pd

def analyze_basic_stats(df):
    """
    Computes basic statistics: total income, total expense.
    Filters out neutral transactions like "充值/提现" or transfers to self.
    """
    # Filter out neutral trades
    df_valid = df[~df['io'].isin(['/', '中性交易', ''])]
    
    # Total expenses (where io == '支出')
    expenses = df_valid[df_valid['io'] == '支出']['amount'].sum()
    
    # Total income (where io == '收入')
    incomes = df_valid[df_valid['io'] == '收入']['amount'].sum()
    
    # Count valid transactions
    count = len(df_valid)
    
    return {
        "total_expense": float(expenses),
        "total_income": float(incomes),
        "transaction_count": count
    }
