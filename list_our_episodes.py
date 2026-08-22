from kaggle.api.kaggle_api_extended import KaggleApi
import json

api = KaggleApi()
api.authenticate()

# Let's check our recent episodes for submission 55683892, 55683517, 55667580
for sub_id in [55683892, 55682783, 55667580]:
    try:
        episodes = api.competition_list_episodes(submission_id=sub_id)
        print(f"\n--- Submission {sub_id} Episodes (Total: {len(episodes)}) ---")
        for ep in episodes[:8]:
            print(f"  Episode {ep.id} | Date: {ep.date} | Status: {ep.status} | Pass: {getattr(ep, 'pass_reason', '')} | Agents: {getattr(ep, 'agents', '')}")
    except Exception as e:
        print(f"Error on {sub_id}: {e}")

