import pandas as pd

def analyze_basic_stats(df):
    """
    Computes basic statistics: total income, total expense.
    Filters out neutral transactions like "充值/提现" or transfers to self.
    """
    # Filter out neutral trades
    df_valid = df[~df['io'].isin(['/', '中性交易', ''])]
    
    # Total expenses and incomes
    expenses = df_valid[df_valid['io'] == '支出']['amount'].sum()
    incomes = df_valid[df_valid['io'] == '收入']['amount'].sum()
    
    # Monthly breakdown
    df_valid = df_valid.copy()
    df_valid.loc[:, 'month'] = df_valid['time'].dt.strftime('%Y-%m')
    
    monthly_stats = {}
    for month, group in df_valid.groupby('month'):
        m_exp = group[group['io'] == '支出']['amount'].sum()
        m_inc = group[group['io'] == '收入']['amount'].sum()
        monthly_stats[month] = {
            "expense": float(m_exp),
            "income": float(m_inc)
        }
    
    # Count valid transactions
    count = len(df_valid)
    
    return {
        "total_expense": float(expenses),
        "total_income": float(incomes),
        "monthly_breakdown": monthly_stats,
        "transaction_count": count
    }
