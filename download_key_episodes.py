from kaggle.api.kaggle_api_extended import KaggleApi
import json

api = KaggleApi()
api.authenticate()

episodes_to_fetch = [96555745, 96558023, 96562623]

for ep_id in episodes_to_fetch:
    print(f"Fetching episode {ep_id}...")
    try:
        replay = api.competition_episode_replay(episode_id=ep_id)
        with open(f"episode-{ep_id}-replay.json", "w") as f:
            json.dump(replay, f)
        print(f"Saved episode-{ep_id}-replay.json")
    except Exception as e:
        print(f"Failed to fetch {ep_id}: {e}")

