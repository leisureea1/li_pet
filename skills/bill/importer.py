import pandas as pd
import os

def load_bill(file_path):
    """
    Loads a WeChat or Alipay bill (CSV or Excel) and normalizes the columns.
    Returns a standardized DataFrame.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path, encoding='utf-8')
    except Exception as e:
        try:
            # Fallback for some Chinese CSV encodings
            df = pd.read_csv(file_path, encoding='gbk')
        except:
            return None
            
    # Find the header row (sometimes bills have metadata at the top)
    header_idx = 0
    
    # Check if the very first row (the column headers of our dummy df) is actually the real header
    header_str = str(df.columns.tolist()).lower()
    if '金额' in header_str and ('交易对方' in header_str or '交易时间' in header_str or '付款时间' in header_str):
        header_idx = 0
    else:
        for i, row in df.iterrows():
            row_str = str(row.values).lower()
            if '金额' in row_str and ('交易对方' in row_str or '交易时间' in row_str or '付款时间' in row_str):
                header_idx = i + 1
                break
            
    # Re-read with correct header
    if ext in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path, header=header_idx)
    else:
        try:
            df = pd.read_csv(file_path, encoding='utf-8', header=header_idx)
        except:
            df = pd.read_csv(file_path, encoding='gbk', header=header_idx)
            
    # Clean up columns
    df.columns = [str(c).strip().replace('\n', '').replace('\r', '').replace('\ufeff', '') for c in df.columns]
    
    # Standardized columns mapping
    mapping = {
        '交易时间': 'time',
        '付款时间': 'time',
        '交易类型': 'type',
        '交易对方': 'counterparty',
        '商品': 'product',
        '商品名称': 'product',
        '收/支': 'io',
        '收/付款': 'io',
        '收/付': 'io',
        '金额(元)': 'amount',
        '金额': 'amount',
        '当前状态': 'status',
        '交易状态': 'status',
        '备注': 'remarks'
    }
    
    # Rename columns that exist
    rename_dict = {}
    for col in df.columns:
        for k, v in mapping.items():
            if k == col or k in col:
                rename_dict[col] = v
                break
                
    df.rename(columns=rename_dict, inplace=True)
    
    # Ensure required columns exist
    required = ['time', 'counterparty', 'io', 'amount']
    for req in required:
        if req not in df.columns:
            return None # Missing crucial data
            
    # Clean data
    df['amount'] = pd.to_numeric(df['amount'].astype(str).str.replace('¥', '').str.replace(',', '').str.strip(), errors='coerce')
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df['io'] = df['io'].astype(str).str.strip()
    
    if 'product' not in df.columns:
        df['product'] = ""
    if 'type' not in df.columns:
        df['type'] = ""
        
    df['counterparty'] = df['counterparty'].astype(str).str.strip()
    df['product'] = df['product'].astype(str).str.strip()
    
    # Filter valid rows
    df = df.dropna(subset=['time', 'amount'])
    
    return df
