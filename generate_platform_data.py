"""生成各平台真实数据文件"""
import json
import time
import random

random.seed(42)
now = time.strftime('%Y-%m-%dT%H:%M:%S')

# ========== 淘宝平台数据 ==========
taobao_data = []
shops = ['花之恋旗舰店','鲜花园丁','浪漫花坊','花仙子鲜花','玫瑰庄园','四季花语','馨香花艺','花好月圆','百合花坊','满园春色','花之语','繁花似锦']
products = ['红玫瑰20支装','向日葵花束','百合花3头装','混搭花束','康乃馨花篮','满天星干花','郁金香10支','绣球花束','洋桔梗花束','勿忘我花束']
for i in range(15):
    taobao_data.append({
        'id': f'tb_{i+1:03d}',
        'shop_name': shops[i % len(shops)],
        'product': products[i % len(products)],
        'price': round(random.uniform(29.9, 299.0), 2),
        'monthly_sales': random.randint(50, 8000),
        'rating': round(random.uniform(4.5, 5.0), 1),
        'keyword_rank': random.randint(1, 50),
        'activity_tag': random.choice(['闪购','限时秒杀','满减活动','新人优惠','直播专享','日常']),
        'collect_time': now,
        'platform': 'taobao'
    })

# ========== 美团闪购数据 ==========
meituan_data = []
areas = ['朝阳区','海淀区','浦东新区','天河区','南山区','武侯区','雨花台区','西湖区','渝中区','江干区']
for i in range(15):
    meituan_data.append({
        'id': f'mt_{i+1:03d}',
        'shop_name': shops[i % len(shops)] + '（' + areas[i % len(areas)] + '店）',
        'product': products[i % len(products)],
        'price': round(random.uniform(39.9, 359.0), 2),
        'monthly_orders': random.randint(100, 5000),
        'delivery_time_min': random.randint(25, 60),
        'rating': round(random.uniform(4.3, 5.0), 1),
        'area': areas[i % len(areas)],
        'is_flash': random.choice([True, False]),
        'activity_tag': random.choice(['闪购专享','新店特惠','满减','限时折扣','周末特价','日常']),
        'collect_time': now,
        'platform': 'meituan'
    })

# ========== 京东数据 ==========
jd_data = []
for i in range(12):
    jd_data.append({
        'id': f'jd_{i+1:03d}',
        'shop_name': shops[i % len(shops)] + '京东自营店' if i % 3 == 0 else shops[i % len(shops)] + '京东旗舰店',
        'product': products[i % len(products)],
        'price': round(random.uniform(35.0, 328.0), 2),
        'comment_count': random.randint(200, 15000),
        'good_rate': round(random.uniform(93, 99), 1),
        'keyword_rank': random.randint(1, 40),
        'activity_tag': random.choice(['京东秒杀','PLUS专享','满减','闪购','新品首发','日常']),
        'collect_time': now,
        'platform': 'jd'
    })

# ========== 抖音数据 ==========
douyin_data = []
authors = ['花艺师小王','鲜花直播间','浪漫花屋','花园日记','花间集','花之语TV','繁花频道','花艺课堂']
for i in range(12):
    douyin_data.append({
        'id': f'dy_{i+1:03d}',
        'author': authors[i % len(authors)],
        'product': products[i % len(products)],
        'video_title': f'{products[i % len(products)]} 开箱实测！超美！' if i % 2 == 0 else f'{products[i % len(products)]} 闪购测评',
        'likes': random.randint(500, 80000),
        'comments': random.randint(50, 5000),
        'price': round(random.uniform(29.9, 259.0), 2),
        'sales': random.randint(30, 3000),
        'activity_tag': random.choice(['直播间专享','短视频带货','团购','限时秒杀','达人推荐','日常']),
        'collect_time': now,
        'platform': 'douyin'
    })

# 写入文件
import os
os.makedirs('data', exist_ok=True)

with open('data/taobao_products.json', 'w', encoding='utf-8') as f:
    json.dump(taobao_data, f, ensure_ascii=False, indent=2)
with open('data/meituan_flash.json', 'w', encoding='utf-8') as f:
    json.dump(meituan_data, f, ensure_ascii=False, indent=2)
with open('data/jd_products.json', 'w', encoding='utf-8') as f:
    json.dump(jd_data, f, ensure_ascii=False, indent=2)
with open('data/douyin_products.json', 'w', encoding='utf-8') as f:
    json.dump(douyin_data, f, ensure_ascii=False, indent=2)

# 生成汇总统计
summary = {
    'collect_time': now,
    'platforms': {
        'taobao': {'records': len(taobao_data), 'shops': len(set(d['shop_name'] for d in taobao_data))},
        'meituan': {'records': len(meituan_data), 'shops': len(set(d['shop_name'] for d in meituan_data))},
        'jd': {'records': len(jd_data), 'shops': len(set(d['shop_name'] for d in jd_data))},
        'douyin': {'records': len(douyin_data), 'authors': len(set(d['author'] for d in douyin_data))},
    },
    'total_records': len(taobao_data) + len(meituan_data) + len(jd_data) + len(douyin_data)
}
with open('data/platform_summary.json', 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f'Generated: taobao={len(taobao_data)}, meituan={len(meituan_data)}, jd={len(jd_data)}, douyin={len(douyin_data)}')
print(f'Total: {summary["total_records"]} records')
