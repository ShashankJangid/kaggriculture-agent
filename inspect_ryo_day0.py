import json

with open('episode-96515070-replay.json', 'r') as f:
    replay = json.load(f)

steps = replay['steps']

print("=== Ryo Day 0 Actions (Hours 0 - 23) ===")
for h in range(24):
    step = steps[h]
    obs0 = step[0]['observation']
    act0 = step[0].get('action', {})
    
    mkt = act0.get('market', [])
    farmer = act0.get('farmer', [])
    hands = act0.get('hands', [])
    
    invs = obs0.get('private', {}).get('inventories', [])
    shed = obs0.get('private', {}).get('shed', {})
    
    print(f"Hour {h:2d} | Mkt: {mkt}")
    print(f"        Farmer: {farmer} | Hands ({len(hands)}): {hands}")
    if h in [0, 1, 2, 3, 4, 5, 10, 20]:
        print(f"        Shed: {shed} | Invs: {invs[:4]}")

