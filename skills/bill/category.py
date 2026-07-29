import os
import sys

# Fast local keyword dictionary
CATEGORY_KEYWORDS = {
    "便利店/超市": ["711", "全家", "美宜佳", "罗森", "红旗", "便利蜂", "超市", "多点", "沃尔玛", "盒马", "大润发", "永辉", "吉美佳"],
    "奶茶/咖啡": ["蜜雪", "喜茶", "奈雪", "瑞幸", "星巴克", "茶百道", "霸王茶姬", "库迪", "一点点", "蜜恋"],
    "交通出行": ["滴滴", "高德", "地铁", "公交", "铁路", "12306", "哈啰", "青桔", "美团单车", "曹操出行", "T3"],
    "餐饮美食": ["外卖", "美团", "饿了么", "餐厅", "饭店", "小吃", "面馆", "烤肉", "火锅", "烧烤", "麦当劳", "肯德基", "必胜客", "米线", "肉夹馍", "烤面筋", "拉条子", "精酿"],
    "生活缴费": ["话费", "电费", "水费", "燃气", "物业", "宽带", "充值", "联通", "移动", "电信", "智能充电"],
    "学习/办公": ["学费", "书店", "考试", "培训", "文具", "知网", "打印"],
    "娱乐游戏": ["Steam", "腾讯游戏", "网易游戏", "米哈游", "电影", "KTV", "酒吧", "视频", "爱奇艺", "B站", "网易云", "音乐"],
    "医疗健康": ["医院", "药房", "药店", "挂号", "体检", "大药房", "诊所"],
    "网购/快递": ["淘宝", "京东", "拼多多", "快递", "顺丰", "菜鸟", "中通", "圆通", "申通", "Apple"]
}

def classify_merchant(merchant_name, product_name, router=None):
    """
    Classifies a transaction based on the merchant name and product name.
    Layer 1: Keyword matching (fast).
    Layer 2: Semantic matching (fallback).
    """
    text = str(merchant_name) + " " + str(product_name)
    
    # Layer 1: Keyword matching
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(k in text for k in keywords):
            return cat
            
    # Layer 2: Semantic Router (if available)
    if router:
        # We can use the SemanticRouter to classify unknown merchants
        # However, it might be slow for hundreds of items. We only do it if necessary.
        intent = router.get_intent(text, threshold=0.6)
        if intent and intent in CATEGORY_KEYWORDS.keys():
            return intent
            
    return "其他消费"
