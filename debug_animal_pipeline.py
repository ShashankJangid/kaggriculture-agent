import kaggle_environments
import json
from collections import defaultdict, Counter

# Let's inspect Ryo's exact animal purchase and placement actions from episode-96515070-replay.json
with open('episode-96515070-replay.json', 'r') as f:
    replay = json.load(f)

steps = replay['steps']

print("--- Day-by-Day Ryo Animal & Pasture Timeline ---")
for day in range(30):
    s_idx = day * 24
    obs0 = steps[s_idx][0]['observation']
    farms = obs0['farms']
    farm0 = farms[0] # Ryo
    
    pastures = 0
    cows = 0
    sheep = 0
    empty_p = 0
    strawberries = 0
    wheat = 0
    melons = 0
    
    for row in farm0['tiles']:
        for t in row:
            if isinstance(t, dict):
                k = t.get('kind')
                if k == 'PASTURE':
                    pastures += 1
                    anim = t.get('animal')
                    if anim == 'COW': cows += 1
                    elif anim == 'SHEEP': sheep += 1
                    elif anim is None: empty_p += 1
                elif k == 'PLANT':
                    c = t.get('crop')
                    if c == 'STRAWBERRY': strawberries += 1
                    elif c == 'WHEAT': wheat += 1
                    elif c == 'MELON': melons += 1
                    
    money = farm0.get('money', 0)
    quads = len(farm0.get('unlocked_quadrants', []))
    hands = len(farm0.get('hands', []))
    
    print(f"Day {day:2d} | Money: ${money:8.0f} | Quads: {quads} | Pastures: {pastures:2d} (Cows: {cows:2d}, Sheep: {sheep:2d}, Empty: {empty_p}) | Straw: {strawberries:2d} | Wheat: {wheat:2d} | Melons: {melons:2d}")

