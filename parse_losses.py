import json
with open('/Users/0xshashank/.gemini/antigravity/brain/d41a592d-858f-4888-a87b-e83bcb7e21a5/.system_generated/steps/595/output.txt', 'r') as f:
    data = json.load(f)

for ep in data.get("episodes", []):
    if ep.get("state") != "COMPLETED": continue
    agents = ep.get("agents", [])
    if len(agents) != 2: continue
    
    my_agent = next((a for a in agents if a["submission_id"] == 55668647), None)
    opp_agent = next((a for a in agents if a["submission_id"] != 55668647), None)
    
    if my_agent and opp_agent and my_agent["reward"] < opp_agent["reward"]:
        print(f"LOSS: Us {my_agent['reward']} vs {opp_agent['team_name']} {opp_agent['reward']}")
