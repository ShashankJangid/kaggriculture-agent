import json
with open('/Users/0xshashank/.gemini/antigravity/brain/d41a592d-858f-4888-a87b-e83bcb7e21a5/.system_generated/steps/595/output.txt', 'r') as f:
    data = json.load(f)

wins = 0
losses = 0
ties = 0
my_rewards = []
opp_rewards = []

for ep in data.get("episodes", []):
    if ep.get("state") != "COMPLETED": continue
    agents = ep.get("agents", [])
    if len(agents) != 2: continue
    
    my_agent = next((a for a in agents if a["submission_id"] == 55668647), None)
    opp_agent = next((a for a in agents if a["submission_id"] != 55668647), None)
    
    if my_agent and opp_agent:
        my_rewards.append(my_agent["reward"])
        opp_rewards.append(opp_agent["reward"])
        if my_agent["reward"] > opp_agent["reward"]:
            wins += 1
        elif my_agent["reward"] < opp_agent["reward"]:
            losses += 1
        else:
            ties += 1

print(f"Wins: {wins}, Losses: {losses}, Ties: {ties}")
print(f"My Avg Reward: {sum(my_rewards)/len(my_rewards) if my_rewards else 0:.1f}")
print(f"Opp Avg Reward: {sum(opp_rewards)/len(opp_rewards) if opp_rewards else 0:.1f}")
