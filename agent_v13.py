import math
from collections import defaultdict

CROPS = {
    "WHEAT": {"seed": 10, "base_price": 25, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT": {"seed": 20, "base_price": 35, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "base_price": 60, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "base_price": 120, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "base_price": 250, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}

TARGET_HARVEST_AGE = {
    "MELON": 10,
    "CARROT": 3,
    "WHEAT": 4,
    "STRAWBERRY": 10,
    "TOMATO": 8
}

LAND_PRICES = [1000, 2000, 4000]

def get_shed_access_tiles(board_size=10):
    half = board_size // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]

def get_best_move(cur_pos, target_pos, board_size=10):
    cx, cy = cur_pos
    tx, ty = target_pos
    if cx == tx and cy == ty:
        return None
    dx = tx - cx
    dy = ty - cy

    moves = []
    if dx > 0:
        moves.append(("EAST", abs(dx)))
    elif dx < 0:
        moves.append(("WEST", abs(dx)))
    if dy > 0:
        moves.append(("SOUTH", abs(dy)))
    elif dy < 0:
        moves.append(("NORTH", abs(dy)))

    moves.sort(key=lambda m: m[1], reverse=True)
    return moves[0][0] if moves else None

def manhattan_dist(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def assign_units_to_tasks(units, tasks, urgency_weight=1.5):
    if not units or not tasks:
        return {}
    unassigned_units = set(range(len(units)))
    assignments = {}
    sorted_tasks = sorted(tasks, key=lambda t: t["urgency"], reverse=True)
    
    for task in sorted_tasks:
        if not unassigned_units:
            break
        best_u = None
        best_cost = 99999
        tpos = task["pos"]
        
        for u_idx in unassigned_units:
            upos = units[u_idx]
            dist = manhattan_dist(upos, tpos)
            cost = dist - (urgency_weight * task["urgency"])
            if cost < best_cost:
                best_cost = cost
                best_u = u_idx
                
        if best_u is not None:
            assignments[best_u] = task
            unassigned_units.remove(best_u)
            
    return assignments

def agent(obs):
    player = obs.get("player", 0)
    farms = obs.get("farms", [])
    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    farm = farms[player]
    private = obs.get("private", {}) or {}
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    board_size = len(farm["tiles"])
    shed_tiles = get_shed_access_tiles(board_size)

    money = farm.get("money", 0)
    shed = private.get("shed", {}) or {}
    seeds = private.get("seeds", {}) or {}
    inventories = private.get("inventories", [{}]) or [{}]

    market_orders = []

    # 1. 100% Immediate Market Liquidation
    for item, qty in list(shed.items()):
        if qty > 0:
            market_orders.append(["SELL", item, qty])

    # 2. Maximum Labor Scaling (up to 12 hands)
    hires_today = farm.get("hires_today", 0)
    unlocked_quads = len(farm.get("unlocked_quadrants", ["NW"]))

    if day >= 29:
        target_hires = 0
    elif day >= 27:
        target_hires = 4
    elif unlocked_quads == 1:
        target_hires = 6
    elif unlocked_quads == 2:
        target_hires = 8
    elif unlocked_quads == 3:
        target_hires = 10
    else:
        target_hires = 12

    if hires_today < target_hires and money >= 5:
        to_hire = target_hires - hires_today
        for _ in range(to_hire):
            market_orders.append(["HIRE"])

    # Guaranteed Reserve
    hiring_reserve = 150 if day < 26 else 0
    spendable_money = max(0, money - hiring_reserve)

    # 3. Progressive Fast Quadrant Expansion
    if unlocked_quads < 4 and day <= 18:
        next_cost = LAND_PRICES[unlocked_quads - 1]
        buffer = 350 if day == 0 else 200
        if spendable_money >= next_cost + buffer:
            market_orders.append(["BUY_LAND"])
            spendable_money -= next_cost
            money -= next_cost
            unlocked_quads += 1

    total_unlocked_tiles = unlocked_quads * 25
    crop_counts = defaultdict(int)

    for y in range(board_size):
        for x in range(board_size):
            t = farm["tiles"][y][x]
            if isinstance(t, dict):
                crop = t.get("crop")
                if crop:
                    crop_counts[crop] += 1

    # 4. Phase-Based High-Velocity Seed Purchasing
    if hour < 19:
        if day <= 17:
            # Phase 1: Heavy Melon + Carrot Scaling
            melon_alloc = spendable_money * 0.70
            carrot_alloc = spendable_money * 0.30

            if spendable_money >= 80:
                buy_m = min(60, int(melon_alloc // 80))
                if buy_m > 0:
                    market_orders.append(["BUY_SEED", "MELON", buy_m])
                    spendable_money -= buy_m * 80

            if spendable_money >= 20:
                buy_c = min(50, int(spendable_money // 20))
                if buy_c > 0:
                    market_orders.append(["BUY_SEED", "CARROT", buy_c])
                    spendable_money -= buy_c * 20

        elif day <= 24:
            # Phase 2: Carrot Sweep
            if spendable_money >= 20:
                buy_c = min(60, int(spendable_money // 20))
                if buy_c > 0:
                    market_orders.append(["BUY_SEED", "CARROT", buy_c])
                    spendable_money -= buy_c * 20

        elif day <= 27:
            # Phase 3: Wheat Final Turnaround
            if spendable_money >= 10:
                buy_w = min(40, int(spendable_money // 10))
                if buy_w > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                    spendable_money -= buy_w * 10

    # 5. Build Global Priority Task Queue
    all_units = [farm["farmer"]] + farm.get("hands", [])
    num_units = len(all_units)
    tasks = []

    for y in range(board_size):
        for x in range(board_size):
            tile = farm["tiles"][y][x]
            if tile == "LOCKED":
                continue

            if tile is None:
                if day < 28 and hour < 20:
                    tasks.append({"type": "PLANT", "pos": (x, y), "urgency": 40})
            elif isinstance(tile, dict):
                kind = tile.get("kind")
                if kind == "WEED":
                    tasks.append({"type": "DIG", "pos": (x, y), "urgency": 55})
                elif kind == "PLANT":
                    crop = tile.get("crop")
                    crop_data = CROPS.get(crop, {})
                    age = day - tile.get("planted_day", 0)
                    yield_units = tile.get("yield_units", 0)
                    watered = tile.get("watered_today", False)
                    target_age = TARGET_HARVEST_AGE.get(crop, 10)

                    # Determine if it's time to harvest
                    should_harvest = False
                    if crop_data.get("ongoing", False):
                        if yield_units > 0:
                            should_harvest = True
                    else:
                        if age >= target_age or day >= 29:
                            should_harvest = True

                    if should_harvest:
                        tasks.append({"type": "HARVEST", "pos": (x, y), "urgency": 95})
                    elif not watered:
                        urg = 100 if tile.get("consecutive_unwatered", 0) >= 1 else 90
                        tasks.append({"type": "WATER", "pos": (x, y), "urgency": urg})

    # 6. Global Spatial Assignment
    unit_actions = [None] * num_units
    assigned_tiles = set()
    local_seeds = dict(seeds)
    unassigned_units = list(range(num_units))

    # Pass 1: Immediate Execution (Zero Travel)
    for u_idx in list(unassigned_units):
        ux, uy = all_units[u_idx]
        u_inv = inventories[u_idx] if u_idx < len(inventories) else {}
        u_tile = farm["tiles"][uy][ux]
        is_shed_adj = (ux, uy) in shed_tiles

        if sum(u_inv.values()) > 0 and is_shed_adj:
            unit_actions[u_idx] = ["DROP"]
            unassigned_units.remove(u_idx)
            continue

        curr_act = None
        if u_tile is not None and u_tile != "LOCKED" and isinstance(u_tile, dict):
            kind = u_tile.get("kind")
            if kind == "WEED":
                curr_act = ["DIG"]
            elif kind == "PLANT":
                crop = u_tile.get("crop")
                crop_data = CROPS.get(crop, {})
                age = day - u_tile.get("planted_day", 0)
                yield_units = u_tile.get("yield_units", 0)
                watered = u_tile.get("watered_today", False)
                target_age = TARGET_HARVEST_AGE.get(crop, 10)

                should_harvest = False
                if crop_data.get("ongoing", False):
                    if yield_units > 0:
                        should_harvest = True
                else:
                    if age >= target_age or day >= 29:
                        should_harvest = True

                if should_harvest:
                    curr_act = ["HARVEST"]
                elif not watered:
                    curr_act = ["WATER"]

        elif u_tile is None and (ux, uy) not in assigned_tiles and hour < 20:
            if local_seeds.get("MELON", 0) > 0 and day <= 17:
                curr_act = ["PLANT", "MELON"]
                local_seeds["MELON"] -= 1
            elif local_seeds.get("CARROT", 0) > 0 and day < 28:
                curr_act = ["PLANT", "CARROT"]
                local_seeds["CARROT"] -= 1
            elif local_seeds.get("WHEAT", 0) > 0 and day < 28:
                curr_act = ["PLANT", "WHEAT"]
                local_seeds["WHEAT"] -= 1

        if curr_act is not None:
            unit_actions[u_idx] = curr_act
            assigned_tiles.add((ux, uy))
            unassigned_units.remove(u_idx)
            continue

        if sum(u_inv.values()) >= 4:
            closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
            mv = get_best_move((ux, uy), closest_shed, board_size)
            if mv:
                unit_actions[u_idx] = [mv]
                unassigned_units.remove(u_idx)
                continue

    # Pass 2: Spatial Matcher
    remaining_units_list = [all_units[i] for i in unassigned_units]
    active_tasks = [t for t in tasks if t["pos"] not in assigned_tiles]
    
    assignments = assign_units_to_tasks(remaining_units_list, active_tasks)

    for sub_idx, u_idx in enumerate(unassigned_units):
        ux, uy = all_units[u_idx]
        task = assignments.get(sub_idx)

        if task:
            mv = get_best_move((ux, uy), task["pos"], board_size)
            if mv:
                unit_actions[u_idx] = [mv]
            else:
                ttype = task["type"]
                if ttype == "WATER":
                    unit_actions[u_idx] = ["WATER"]
                elif ttype == "HARVEST":
                    unit_actions[u_idx] = ["HARVEST"]
                elif ttype == "DIG":
                    unit_actions[u_idx] = ["DIG"]
                elif ttype == "PLANT":
                    if local_seeds.get("MELON", 0) > 0 and day <= 17:
                        unit_actions[u_idx] = ["PLANT", "MELON"]
                        local_seeds["MELON"] -= 1
                    elif local_seeds.get("CARROT", 0) > 0 and day < 28:
                        unit_actions[u_idx] = ["PLANT", "CARROT"]
                        local_seeds["CARROT"] -= 1
                    elif local_seeds.get("WHEAT", 0) > 0 and day < 28:
                        unit_actions[u_idx] = ["PLANT", "WHEAT"]
                        local_seeds["WHEAT"] -= 1
                    else:
                        unit_actions[u_idx] = ["PASS"]
                else:
                    unit_actions[u_idx] = ["PASS"]
        else:
            is_shed_adj = (ux, uy) in shed_tiles
            if not is_shed_adj:
                closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
                mv = get_best_move((ux, uy), closest_shed, board_size)
                unit_actions[u_idx] = [mv] if mv else ["PASS"]
            else:
                unit_actions[u_idx] = ["PASS"]

    farmer_action = unit_actions[0] if unit_actions and unit_actions[0] is not None else ["PASS"]
    hands_actions = [a if a is not None else ["PASS"] for a in unit_actions[1:]]

    return {
        "farmer": farmer_action,
        "hands": hands_actions,
        "market": market_orders[:10]
    }
