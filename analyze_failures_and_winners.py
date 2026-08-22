import json
from collections import defaultdict, Counter

def analyze_ep(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    
    steps = data['steps']
    num_steps = len(steps)
    
    # Identify which index is which player
    p0_name = steps[0][0]['observation'].get('players', ['P0', 'P1'])[0]
    
    # Let's print day-by-day stats for both players
    print(f"\n{'='*70}\nAnalyzing {filename} ({num_steps} steps)\n{'='*70}")
    
    for day in range(30):
        # Step at start of day (hour 0)
        s_idx = day * 24
        if s_idx >= num_steps:
            break
        
        obs0 = steps[s_idx][0]['observation']
        farms = obs0['farms']
        
        farm0 = farms[0]
        farm1 = farms[1]
        
        m0 = farm0.get('money', 0)
        m1 = farm1.get('money', 0)
        
        q0 = len(farm0.get('unlocked_quadrants', []))
        q1 = len(farm1.get('unlocked_quadrants', []))
        
        h0 = len(farm0.get('hands', []))
        h1 = len(farm1.get('hands', []))
        
        # Count tiles for player 0
        p0_crops = Counter()
        p0_weeds = 0
        for row in farm0['tiles']:
            for t in row:
                if isinstance(t, dict):
                    if t.get('kind') == 'PLANT':
                        p0_crops[t.get('crop')] += 1
                    elif t.get('kind') == 'WEED':
                        p0_weeds += 1
                    elif t.get('kind') == 'PASTURE':
                        p0_crops['PASTURE_' + str(t.get('animal'))] += 1
                        
        # Count tiles for player 1
        p1_crops = Counter()
        p1_weeds = 0
        for row in farm1['tiles']:
            for t in row:
                if isinstance(t, dict):
                    if t.get('kind') == 'PLANT':
                        p1_crops[t.get('crop')] += 1
                    elif t.get('kind') == 'WEED':
                        p1_weeds += 1
                    elif t.get('kind') == 'PASTURE':
                        p1_crops['PASTURE_' + str(t.get('animal'))] += 1

        if day in [0, 1, 3, 5, 8, 11, 14, 17, 20, 24, 28, 29]:
            print(f"Day {day:2d} | P0 (${m0:7.0f}, Q{q0}, H{h0:2d}) Crops: {dict(p0_crops)} | Weeds: {p0_weeds}")
            print(f"       | P1 (${m1:7.0f}, Q{q1}, H{h1:2d}) Crops: {dict(p1_crops)} | Weeds: {p1_weeds}")

analyze_ep("episode-96555745-replay.json") # Malak Reda 77k
analyze_ep("episode-96562623-replay.json") # Our low score 6k
