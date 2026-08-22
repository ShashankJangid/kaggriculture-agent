import kaggle_environments
from agent_v130_dedicated_sectors import agent

env = kaggle_environments.make('kaggriculture', configuration={'boardSize': 10})
env.reset()

for day in range(30):
    for h in range(24):
        if env.done:
            break
        state = env.state[0]
        obs = state.observation
        act0 = agent(obs)
        act1 = {'farmer': ['PASS'], 'hands': [], 'market': []}
        env.step([act0, act1])
        
    farm0 = env.state[0].observation['farms'][0]
    money = farm0['money']
    quads = len(farm0['unlocked_quadrants'])
    pastures = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('kind') == 'PASTURE')
    cows = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('kind') == 'PASTURE' and t.get('animal') == 'COW')
    sheep = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('kind') == 'PASTURE' and t.get('animal') == 'SHEEP')
    straw = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('crop') == 'STRAWBERRY')
    wheat = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('crop') == 'WHEAT')
    melon = sum(1 for row in farm0['tiles'] for t in row if isinstance(t, dict) and t.get('crop') == 'MELON')
    
    print(f"Day {day:2d} | Money: ${money:8.0f} | Quads: {quads} | Pastures: {pastures:2d} (Cows: {cows:2d}, Sheep: {sheep:2d}) | Straw: {straw:2d} | Wheat: {wheat:2d} | Melon: {melon:2d}")

reward = env.steps[-1][0]["reward"]
print(f"\nFinal Score: ${reward:,.2f}")
