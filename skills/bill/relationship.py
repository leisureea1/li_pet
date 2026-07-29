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
            
        group = group.sort_values(by='time')
        
        # 1. Detect "Money Loops" (Pushing money back and forth)
        # Condition: Same amount transferred back and forth within 24 hours
        loops_found = 0
        loop_amount = 0
        
        # We can just iterate through adjacent transactions with this person
        for i in range(len(group) - 1):
            row1 = group.iloc[i]
            row2 = group.iloc[i+1]
            
            time_diff = (row2['time'] - row1['time']).total_seconds() / 3600.0 # in hours
            if time_diff <= 2.0 and row1['io'] != row2['io'] and abs(row1['amount'] - row2['amount']) < 0.01:
                loops_found += 1
                loop_amount = row1['amount']
                
        if loops_found > 0:
            loops.append({
                "person": str(person),
                "type": "推诿/抢买单",
                "loop_count": loops_found,
                "amount": float(loop_amount),
                "pattern": f"你们在短时间内为 {loop_amount} 块钱互相转过来转过去，是不是抢着买单呀？",
                "specific_example": f"比如在 {group.iloc[0]['time'].strftime('%m月%d日 %H:%M')} 左右"
            })
            
        # 2. Detect "Intimate Relationship" (Extremely high frequency transfers)
        if len(group) >= 10:
            total_money = group['amount'].sum()
            loops.append({
                "person": str(person),
                "type": "亲密关系",
                "interaction_count": len(group),
                "total_money_exchanged": float(total_money),
                "pattern": "你们之间转账极其频繁（高达十几次），这绝对不是普通朋友！是女朋友还是家人呀？"
            })
                
    # Sort by priority
    loops = sorted(loops, key=lambda x: x.get('interaction_count', x.get('loop_count', 0)), reverse=True)[:4]
    
    return {
        "money_loops": loops
    }
