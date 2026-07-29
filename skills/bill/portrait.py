import pandas as pd
from .category import classify_merchant

def build_portrait(df, router=None):
    """
    Builds a behavioral portrait from the transaction DataFrame.
    Extracts night owl habits, top merchants, impulse buying, etc.
    """
    df_expense = df[df['io'] == '支出'].copy()
    if df_expense.empty:
        return {}
        
    portrait = {}
    
    # 1. Night Activity (00:00 - 05:00)
    df_expense.loc[:, 'hour'] = df_expense['time'].dt.hour
    night_trades = df_expense[(df_expense['hour'] >= 0) & (df_expense['hour'] <= 5)]
    
    portrait['night_activity'] = {
        "count": len(night_trades),
        "ratio": round(len(night_trades) / len(df_expense), 2) if len(df_expense) > 0 else 0,
        "is_night_owl": len(night_trades) >= 5, # Threshold for being a night owl
        "sample_merchants": night_trades['counterparty'].value_counts().head(3).index.tolist() if not night_trades.empty else []
    }
    
    # 2. Top Merchants
    top_merchants = df_expense['counterparty'].value_counts().head(5)
    portrait['top_merchants'] = []
    for merchant, count in top_merchants.items():
        # skip empty or known invalid names
        if str(merchant).strip() in ["/", "未知", "美团", "支付宝", "微信支付"]:
            continue
            
        category = classify_merchant(merchant, "", router=router)
        portrait['top_merchants'].append({
            "name": str(merchant),
            "count": int(count),
            "category": category
        })
        
    # 3. Large Expenses (Max 3)
    large_expenses = df_expense.nlargest(3, 'amount')
    portrait['large_expenses'] = []
    for _, row in large_expenses.iterrows():
        portrait['large_expenses'].append({
            "name": str(row['counterparty']) + (" ("+str(row['product'])+")" if row['product'] else ""),
            "amount": float(row['amount']),
            "time": row['time'].strftime('%Y-%m-%d %H:%M')
        })
        
    # 4. Impulse Buying (Rapid successive purchases within 30 mins)
    df_expense = df_expense.sort_values(by='time')
    df_expense['time_diff'] = df_expense['time'].diff().dt.total_seconds() / 60.0
    # Find clusters where time diff is less than 30 minutes, and count > 4
    clusters = (df_expense['time_diff'] > 30).cumsum()
    cluster_counts = df_expense.groupby(clusters).size()
    impulse_clusters = cluster_counts[cluster_counts >= 5]
    
    portrait['impulse_buying'] = {
        "detected": len(impulse_clusters) > 0,
        "episodes": len(impulse_clusters)
    }
    
    # 5. Game / Top-up Expenses
    game_keywords = ["游戏", "充值", "点券", "steam", "腾讯", "网易", "米哈游", "apple", "苹果"]
    df_game = df_expense[df_expense['counterparty'].str.lower().str.contains('|'.join(game_keywords), na=False) | df_expense['product'].str.lower().str.contains('|'.join(game_keywords), na=False)]
    
    if not df_game.empty:
        portrait['game_expenses'] = {
            "total_spent": float(df_game['amount'].sum()),
            "transaction_count": len(df_game),
            "favorite_games": df_game['counterparty'].value_counts().head(2).index.tolist()
        }
    
    return portrait
