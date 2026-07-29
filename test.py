with open('支付宝交易明细(20260430-20260730).csv', 'rb') as f:
    lines = f.readlines()
for i in range(20, 26):
    try:
        print(f'Line {i}: {lines[i].decode("gbk").strip()}')
    except Exception as e:
        print(f'Line {i}: DECODE ERROR {e}')
