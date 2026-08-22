import json

with open('episode-96515070-replay.json', 'r') as f:
    replay = json.load(f)

steps = replay['steps']

print("=== Ryo Day 1 Actions (Hours 0 - 10) ===")
for h in range(11):
    step = steps[24 + h]
    obs0 = step[0]['observation']
    act0 = step[0].get('action', {})
    
    mkt = act0.get('market', [])
    farmer = act0.get('farmer', [])
    hands = act0.get('hands', [])
    
    invs = obs0.get('private', {}).get('inventories', [])
    shed = obs0.get('private', {}).get('shed', {})
    
    print(f"Hour {h:2d} | Mkt: {mkt}")
    print(f"        Farmer: {farmer} | Hands ({len(hands)}): {hands}")
    print(f"        Shed: {shed} | Invs: {invs[:4]}")

