import pandas as pd

def analyze_relationships(df):
    """
    Finds interesting relationship dynamics like "Money Loops" (fighting over the bill).
    """
    # Look for "转账", "收款", "红包"
    transfer_keywords = ["转账", "收款", "红包"]
    df_transfers = df[df['type'].str.contains('|'.join(transfer_keywords), na=False) | df['product'].str.contains('|'.join(transfer_keywords), na=False)].copy()
    
    if df_transfers.empty:
        return {"money_loops": []}
        
    loops = []
    
    # Sort by time
    df_transfers = df_transfers.sort_values(by='time')
    
    # Group by counterparty
    grouped = df_transfers.groupby('counterparty')
    
    for person, group in grouped:
        if person in ["/", "无", "未知", ""]:
            continue
            
        # Look for a pattern of sending and receiving similar amounts closely in time
        # Or just high frequency back-and-forth
        incomes = group[group['io'] == '收入']
        expenses = group[group['io'] == '支出']
        
        if len(incomes) > 0 and len(expenses) > 0:
            # They have both sent and received
            total_in = incomes['amount'].sum()
            total_out = expenses['amount'].sum()
            
            # If the amounts are very similar (net balance is close to 0) or frequency is high
            if abs(total_in - total_out) < (max(total_in, total_out) * 0.3) or (len(incomes) + len(expenses)) >= 4:
                loops.append({
                    "friend_name": str(person),
                    "interaction_count": len(group),
                    "total_money_exchanged": float(total_in + total_out),
                    "pattern": "你们之间经常互相转账，是不是经常在一起抢着买单或者 AA 呀？资金一直在你们两人之间玩传送门！"
                })
                
    # Sort by interaction count
    loops = sorted(loops, key=lambda x: x['interaction_count'], reverse=True)[:3]
    
    return {
        "money_loops": loops
    }
