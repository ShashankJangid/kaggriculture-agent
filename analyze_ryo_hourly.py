import json
from collections import defaultdict, Counter

with open('episode-96515070-replay.json', 'r') as f:
    replay = json.load(f)

steps = replay['steps']

# Breakdown of actions by hour across all 30 days for Ryo
hourly_ops = defaultdict(Counter)

for s_idx, step in enumerate(steps):
    obs = step[0]['observation']
    act = step[0].get('action', {})
    hour = obs['hour']
    
    farmer = act.get('farmer', [])
    hands = act.get('hands', [])
    all_acts = [farmer] + hands
    
    for u in all_acts:
        if u:
            op = u[0]
            hourly_ops[hour][op] += 1

print("--- Hourly Action Distribution (Summed across 30 days) ---")
print(f"{'Hour':4s} | {'WATER':6s} | {'HARVEST':7s} | {'FEED':5s} | {'CARE':5s} | {'FERT_COL':8s} | {'FERTILIZE':9s} | {'PLANT':6s} | {'DROP':5s} | {'PICKUP':6s}")
print("-" * 80)
for h in range(24):
    c = hourly_ops[h]
    print(f"Hr {h:2d} | {c['WATER']:6d} | {c['HARVEST']:7d} | {c['FEED']:5d} | {c['CARE']:5d} | {c['COLLECT_FERTILIZER']:8d} | {c['FERTILIZE']:9d} | {c['PLANT']:6d} | {c['DROP']:5d} | {c['PICKUP']:6d}")

