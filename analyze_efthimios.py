import json

with open('/Users/0xshashank/Downloads/97516207-0.json', 'r') as f:
    data = json.load(f)

steps = data if isinstance(data, list) else data.get('steps', [])
print(f"Total steps in match 97516207: {len(steps)}")

print("\n" + "=" * 105)
print("🌾 EFTHIMIOS (94,974 Coins Winner) vs OUR AGENT (18,868 Coins) — COMPLETE MATCH BREAKDOWN")
print("=" * 105)

for day in range(30):
    step_idx = day * 24 + 1
    if step_idx >= len(steps):
        break
    s = steps[step_idx]
    obs = s[0].get('observation', {})
    farms = obs.get('farms', [])
    if len(farms) < 2:
        continue
    farm0 = farms[0] # Our Agent
    farm1 = farms[1] # Efthimios
    
    # Efthimios
    p1_money = farm1.get('money', 0)
    p1_quads = len(farm1.get('unlocked_quadrants', []))
    p1_pastures = sum(1 for row in farm1['tiles'] for t in row if isinstance(t, dict) and t.get('kind') == 'PASTURE')
    p1_cows = sum(1 for row in farm1['tiles'] for t in row if isinstance(t, dict) and t.get('kind') == 'PASTURE' and t.get('animal') == 'COW')
    p1_sheep = sum(1 for row in farm1['tiles'] for t in row if isinstance(t, dict) and t.get('kind') == 'PASTURE' and t.get('animal') == 'SHEEP')
    p1_straw = sum(1 for row in farm1['tiles'] for t in row if isinstance(t, dict) and t.get('crop') == 'STRAWBERRY')
    p1_wheat = sum(1 for row in farm1['tiles'] for t in row if isinstance(t, dict) and t.get('crop') == 'WHEAT')
    p1_melon = sum(1 for row in farm1['tiles'] for t in row if isinstance(t, dict) and t.get('crop') == 'MELON')
    p1_carrot = sum(1 for row in farm1['tiles'] for t in row if isinstance(t, dict) and t.get('crop') == 'CARROT')
    p1_hands = len(farm1.get('hands', []))

    # Our Agent
    p0_money = farm0.get('money', 0)
    p0_quads = len(farm0.get('unlocked_quadrants', []))
    p0_pastures = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('kind') == 'PASTURE')
    p0_cows = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('kind') == 'PASTURE' and t.get('animal') == 'COW')
    p0_straw = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('crop') == 'STRAWBERRY')
    p0_wheat = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('crop') == 'WHEAT')
    p0_melon = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('crop') == 'MELON')
    p0_carrot = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('crop') == 'CARROT')
    p0_hands = len(farm0.get('hands', []))

    print(f"Day {day:2d} | Efthimios: ${p1_money:6.0f} (H:{p1_hands} Q:{p1_quads} P:{p1_pastures} C:{p1_cows} S:{p1_sheep} W:{p1_wheat:2d} St:{p1_straw:2d} M:{p1_melon:2d} Ca:{p1_carrot:2d}) || Ours: ${p0_money:6.0f} (H:{p0_hands} Q:{p0_quads} M:{p0_melon:2d} Ca:{p0_carrot:2d})")

