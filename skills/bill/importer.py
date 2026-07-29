import pandas as pd
import os

def load_bill(file_path):
    """
    Loads a WeChat or Alipay bill (CSV or Excel) and normalizes the columns.
    Returns a standardized DataFrame.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    load_method = None
    header_idx = 0
    
    if ext in ['.xlsx', '.xls']:
        try:
            df_temp = pd.read_excel(file_path)
            load_method = "excel"
            
            # Find header
            header_str = str(df_temp.columns.tolist()).lower()
            if '金额' in header_str and ('交易对方' in header_str or '交易时间' in header_str or '付款时间' in header_str):
                header_idx = 0
            else:
                for i, row in df_temp.iterrows():
                    row_str = str(row.values).lower()
                    if '金额' in row_str and ('交易对方' in row_str or '交易时间' in row_str or '付款时间' in row_str):
                        header_idx = i + 1
                        break
        except Exception as e:
            # Might be a fake xls (actually a CSV)
            pass
            
    if load_method != "excel":
        # It's a CSV or a fake xls. Read text line by line to find header and encoding
        found_header = False
        
        # Try UTF-8
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    line_lower = line.lower()
                    if '金额' in line_lower and ('交易对方' in line_lower or '交易时间' in line_lower or '付款时间' in line_lower):
                        header_idx = i
                        load_method = "csv_utf8"
                        found_header = True
                        break
        except Exception:
            pass
            
        if not found_header:
            # Try GBK
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    for i, line in enumerate(f):
                        line_lower = line.lower()
                        if '金额' in line_lower and ('交易对方' in line_lower or '交易时间' in line_lower or '付款时间' in line_lower):
                            header_idx = i
                            load_method = "csv_gbk"
                            found_header = True
                            break
            except Exception as e:
                print(f"[Bill Importer Debug] Text parsing failed: {e}")
                return None
                
        if not found_header:
            print("[Bill Importer Debug] Could not find header row containing '金额' and '交易对方'.")
            return None

    print(f"[Bill Importer Debug] load_method={load_method}, header_idx={header_idx}")
            
    # Re-read with correct header
    try:
        if load_method == "excel":
            df = pd.read_excel(file_path, header=header_idx)
        elif load_method == "csv_utf8":
            df = pd.read_csv(file_path, encoding='utf-8', header=header_idx)
        else:
            df = pd.read_csv(file_path, encoding='gbk', header=header_idx)
    except Exception as e:
        print(f"[Bill Importer Debug] Final pandas load failed: {e}")
        return None
            
    # Clean up columns
    df.columns = [str(c).strip().replace('\n', '').replace('\r', '').replace('\ufeff', '') for c in df.columns]
    
    # Standardized columns mapping
    mapping = {
        '交易时间': 'time',
        '付款时间': 'time',
        '交易类型': 'type',
        '交易分类': 'type',
        '交易对方': 'counterparty',
        '商品': 'product',
        '商品名称': 'product',
        '商品说明': 'product',
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
            print(f"[Bill Importer Debug] Missing required column: {req}. Current columns: {df.columns.tolist()}")
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
