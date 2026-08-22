from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

episodes = api.competition_list_episodes(submission_id=55683892)
print(f"=== Submission 55683892 Match Record ({len(episodes)} games) ===")

wins = 0
losses = 0
ties = 0

our_scores = []
opp_scores = []

for ep in episodes:
    agents = ep.agents if hasattr(ep, 'agents') else ep._agents
    our_ag = [a for a in agents if getattr(a, 'submission_id', getattr(a, '_submission_id', None)) == 55683892 or getattr(a, 'submissionId', getattr(a, '_submission_id', None)) == 55683892][0]
    opp_ag = [a for a in agents if a != our_ag][0]
    
    r_our = getattr(our_ag, 'reward', getattr(our_ag, '_reward', 0))
    r_opp = getattr(opp_ag, 'reward', getattr(opp_ag, '_reward', 0))
    opp_name = getattr(opp_ag, 'team_name', getattr(opp_ag, '_team_name', 'Unknown'))
    
    our_scores.append(r_our)
    opp_scores.append(r_opp)
    
    if r_our > r_opp:
        res = "WIN  ✅"
        wins += 1
    elif r_our < r_opp:
        res = "LOSS ❌"
        losses += 1
    else:
        res = "TIE  ➖"
        ties += 1
        
    ep_id = getattr(ep, 'id', getattr(ep, '_id', 0))
    print(f"Ep {ep_id} | Our: {r_our:7.1f} | Opp: {r_opp:7.1f} ({opp_name[:20]:20s}) | {res}")

print("-" * 65)
print(f"Total: {wins}W - {losses}L - {ties}T (Win Rate: {wins/len(episodes)*100:.1f}%)")
print(f"Our Avg Score: {sum(our_scores)/len(our_scores):.1f} | Opponent Avg: {sum(opp_scores)/len(opp_scores):.1f}")
