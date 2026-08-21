import argparse
import kaggle_environments
from main import agent

def evaluate(agent_fn, opponent="starter", episodes=5, seeds=None):
    if seeds is None:
        seeds = [42, 100, 2026, 777, 1234][:episodes]
    
    rewards_p0 = []
    rewards_p1 = []
    wins = 0

    print(f"============================================================")
    print(f" Running Evaluation: Our Agent vs '{opponent}' ({len(seeds)} episodes)")
    print(f"============================================================")

    for i, s in enumerate(seeds):
        env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": s}, debug=False)
        env.run([agent_fn, opponent])
        final = env.steps[-1]
        p0_rew = final[0].reward or 0.0
        p1_rew = final[1].reward or 0.0
        p0_status = final[0].status
        p1_status = final[1].status
        
        rewards_p0.append(p0_rew)
        rewards_p1.append(p1_rew)
        if p0_rew > p1_rew:
            wins += 1
            result = "WIN"
        elif p0_rew < p1_rew:
            result = "LOSS"
        else:
            result = "TIE"
            
        print(f"Episode {i+1:2d} (Seed {s:5d}) | Our Agent: {p0_rew:8.1f} ({p0_status}) | Opponent: {p1_rew:8.1f} ({p1_status}) | {result}")

    avg_p0 = sum(rewards_p0) / len(rewards_p0)
    avg_p1 = sum(rewards_p1) / len(rewards_p1)
    win_rate = (wins / len(seeds)) * 100

    print(f"------------------------------------------------------------")
    print(f" Summary: Win Rate: {wins}/{len(seeds)} ({win_rate:.1f}%) | Our Avg: {avg_p0:8.1f} | Opponent Avg: {avg_p1:8.1f}")
    print(f"============================================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Kaggriculture Agent")
    parser.add_argument("--opponent", type=str, default="starter", choices=["starter", "random", "pass"], help="Opponent baseline agent")
    parser.add_argument("--episodes", type=int, default=5, help="Number of evaluation episodes")
    args = parser.parse_args()

    evaluate(agent, opponent=args.opponent, episodes=args.episodes)
