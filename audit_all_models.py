import kaggle_environments
import time
import importlib

MODELS_TO_AUDIT = [
    ("Agent V3", "agent_v3"),
    ("Agent V5", "agent_v5"),
    ("Agent V8 (Kaggle Peak 492.6)", "agent_v8"),
    ("Agent V9 (75% Land)", "agent_v9"),
    ("Agent V10 Ultimate", "agent_v10_ultimate"),
    ("Agent V15 Final", "agent_v15_final"),
    ("Agent V17 Melon Lord", "agent_v17_melon_lord"),
    ("Agent V31 Perfect", "agent_v31_perfect"),
    ("Agent V40 Super SOTA", "agent_v40_super_sota"),
    ("Agent V50 (Current Submission)", "submission"),
]

SEEDS = [42, 100, 2026, 777, 1234]

results = []

print("==========================================================================================")
print("🌾 COMPREHENSIVE MODEL AUDIT: Benchmarking All Historical Antigravity Models")
print("==========================================================================================")
print(f"{'Model Name':32s} | {'Avg Score':10s} | {'Peak Score':10s} | {'Min Score':10s} | {'Win Rate':8s}")
print("-" * 90)

for label, mod_name in MODELS_TO_AUDIT:
    try:
        mod = importlib.import_module(mod_name)
        agent_fn = getattr(mod, "agent")
        
        scores = []
        wins = 0
        
        for seed in SEEDS:
            env = kaggle_environments.make("kaggriculture", configuration={"boardSize": 10, "seed": seed})
            env.reset()
            env.run([agent_fn, "starter"])
            
            r0 = env.steps[-1][0]["reward"]
            r1 = env.steps[-1][1]["reward"]
            scores.append(r0)
            if r0 > r1:
                wins += 1
                
        avg_s = sum(scores) / len(scores)
        max_s = max(scores)
        min_s = min(scores)
        win_pct = wins / len(scores) * 100
        
        results.append({
            "name": label,
            "module": mod_name,
            "avg": avg_s,
            "max": max_s,
            "min": min_s,
            "win_rate": win_pct,
            "scores": scores
        })
        
        print(f"{label:32s} | ${avg_s:9,.1f} | ${max_s:9,.1f} | ${min_s:9,.1f} | {win_pct:6.1f}%")
    except Exception as e:
        print(f"{label:32s} | ERROR: {e}")

# Sort by Average Score
results.sort(key=lambda x: x["avg"], reverse=True)

print("\n" + "=" * 90)
print("🏆 FINAL AUDIT LEADERBOARD (Ranked by Average Coin Generation)")
print("=" * 90)
for rank, r in enumerate(results, 1):
    print(f"Rank {rank:2d}: {r['name']:32s} -> Avg: ${r['avg']:9,.1f} | Peak: ${r['max']:9,.1f} | Win Rate: {r['win_rate']:.1f}%")
print("=" * 90)

