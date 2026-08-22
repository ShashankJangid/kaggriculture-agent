"""
🌾 Kaggriculture SOTA Master Agent — Ultra-Precision Compounding Engine (V30)
Author: Shashank Jangid
Key Highlights:
- 75% Optimal Land Allocation (3 Quadrants)
- Spatial Collision Avoidance & Dynamic Route Arbitration
- Forward-Yield Crop Scheduling (Melons -> Fast Carrots -> Endgame Wheat Push)
- Instant Shed Liquidation & Zero-Decay Hydration Protocol
"""
import math
from collections import defaultdict

CROPS = {
    "WHEAT": {"seed": 10, "base_price": 25, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT": {"seed": 20, "base_price": 35, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "base_price": 60, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "base_price": 120, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "base_price": 250, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}

LAND_PRICES = [1000, 2000, 4000]

def get_shed_access_tiles(board_size=10):
    half = board_size // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]

def manhattan_dist(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def get_best_move(cur_pos, target_pos, board_size=10, reserved_positions=None):
    cx, cy = cur_pos
    tx, ty = target_pos
    if cx == tx and cy == ty:
        return None
    dx = tx - cx
    dy = ty - cy

    moves = []
    if dx > 0:
        moves.append(("EAST", (cx + 1, cy), abs(dx) + abs(dy)))
    elif dx < 0:
        moves.append(("WEST", (cx - 1, cy), abs(dx) + abs(dy)))
    if dy > 0:
        moves.append(("SOUTH", (cx, cy + 1), abs(dx) + abs(dy)))
    elif dy < 0:
        moves.append(("NORTH", (cx, cy - 1), abs(dx) + abs(dy)))

    # Secondary lateral moves
    if dx == 0:
        moves.append(("EAST", (cx + 1, cy), abs(dx) + abs(dy) + 2))
        moves.append(("WEST", (cx - 1, cy), abs(dx) + abs(dy) + 2))
    if dy == 0:
        moves.append(("SOUTH", (cx, cy + 1), abs(dx) + abs(dy) + 2))
        moves.append(("NORTH", (cx, cy - 1), abs(dx) + abs(dy) + 2))

    for mv, npos, dist in moves:
        nx, ny = npos
        if 0 <= nx < board_size and 0 <= ny < board_size:
            if reserved_positions is None or npos not in reserved_positions:
                return mv
    return moves[0][0] if moves else None

def _next_pos(pos, move):
    x, y = pos
    if move == "NORTH": return (x, y - 1)
    if move == "SOUTH": return (x, y + 1)
    if move == "EAST": return (x + 1, y)
    if move == "WEST": return (x - 1, y)
    return pos

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

    # 1. Market Liquidation (Sell outputs cleanly every turn)
    for item, qty in list(shed.items()):
        if qty > 0:
            market_orders.append(["SELL", item, qty])

    # 2. Dynamic Workforce Hiring
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

    # 3. Progressive Land Expansion (Optimal 75% Land Cap)
    hiring_reserve = 150 if day < 26 else 0
    spendable_money = max(0, money - hiring_reserve)

    if unlocked_quads < 3 and day <= 18:
        next_cost = LAND_PRICES[unlocked_quads - 1]
        buffer = 500 if day == 0 else 800
        if spendable_money >= next_cost + buffer:
            market_orders.append(["BUY_LAND"])
            spendable_money -= next_cost
            money -= next_cost
            unlocked_quads += 1

    # 4. Count Farm State
    total_unlocked_tiles = unlocked_quads * 25
    melon_tiles = 0
    carrot_tiles = 0
    wheat_tiles = 0

    for y in range(board_size):
        for x in range(board_size):
            t = farm["tiles"][y][x]
            if isinstance(t, dict):
                crop = t.get("crop")
                if crop == "MELON": melon_tiles += 1
                elif crop == "CARROT": carrot_tiles += 1
                elif crop == "WHEAT": wheat_tiles += 1

    # 5. Forward-Yield Seed Purchasing Strategy
    if hour < 20:
        if day <= 17:
            max_melons = 20 if unlocked_quads >= 2 else 10
            desired_melons = max(0, max_melons - melon_tiles - seeds.get("MELON", 0))
            if desired_melons > 0 and spendable_money >= 80:
                buy_m = min(desired_melons, int(spendable_money // 80), 8)
                if buy_m > 0:
                    market_orders.append(["BUY_SEED", "MELON", buy_m])
                    spendable_money -= buy_m * 80

            target_carrots = max(0, total_unlocked_tiles - max_melons)
            desired_carrots = max(0, target_carrots - carrot_tiles - seeds.get("CARROT", 0))
            if desired_carrots > 0 and spendable_money >= 20:
                buy_c = min(desired_carrots, int(spendable_money // 20), 10)
                if buy_c > 0:
                    market_orders.append(["BUY_SEED", "CARROT", buy_c])
                    spendable_money -= buy_c * 20

            if seeds.get("WHEAT", 0) < 5 and spendable_money >= 10:
                buy_w = min(5 - seeds.get("WHEAT", 0), int(spendable_money // 10), 10)
                if buy_w > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                    spendable_money -= buy_w * 10

        elif day <= 24:
            target_carrots = total_unlocked_tiles
            desired_carrots = max(0, target_carrots - carrot_tiles - seeds.get("CARROT", 0))
            if desired_carrots > 0 and spendable_money >= 20:
                buy_c = min(desired_carrots, int(spendable_money // 20), 10)
                if buy_c > 0:
                    market_orders.append(["BUY_SEED", "CARROT", buy_c])
                    spendable_money -= buy_c * 20

        elif day <= 27:
            if seeds.get("WHEAT", 0) < total_unlocked_tiles and spendable_money >= 10:
                buy_w = min(total_unlocked_tiles - seeds.get("WHEAT", 0), int(spendable_money // 10), 15)
                if buy_w > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                    spendable_money -= buy_w * 10

    # 6. Global Task Queue
    tasks_watering = []
    tasks_harvesting = []
    tasks_digging = []
    tasks_planting = []

    for y in range(board_size):
        for x in range(board_size):
            tile = farm["tiles"][y][x]
            if tile == "LOCKED":
                continue

            if tile is None:
                if day < 28 and hour < 20:
                    tasks_planting.append({"type": "PLANT", "pos": (x, y)})
            elif isinstance(tile, dict):
                kind = tile.get("kind")
                if kind == "WEED":
                    tasks_digging.append({"type": "DIG", "pos": (x, y)})
                elif kind == "PLANT":
                    crop = tile.get("crop")
                    crop_data = CROPS.get(crop, {})
                    age = day - tile.get("planted_day", 0)
                    yield_units = tile.get("yield_units", 0)
                    watered = tile.get("watered_today", False)

                    if not watered:
                        if tile.get("consecutive_unwatered", 0) >= 1:
                            tasks_watering.insert(0, {"type": "WATER", "pos": (x, y)})
                        else:
                            tasks_watering.append({"type": "WATER", "pos": (x, y)})

                    if crop_data.get("ongoing", False):
                        if yield_units > 0:
                            tasks_harvesting.append({"type": "HARVEST", "pos": (x, y)})
                    else:
                        if age >= crop_data.get("max_yield_day", 4) or day >= 29:
                            tasks_harvesting.append({"type": "HARVEST", "pos": (x, y)})

    ordered_tasks = tasks_watering + tasks_harvesting + tasks_digging + tasks_planting
    all_units = [farm["farmer"]] + farm.get("hands", [])
    num_units = len(all_units)

    unit_actions = [None] * num_units
    assigned_tiles = set()
    local_seeds = dict(seeds)
    unassigned_units = list(range(num_units))
    reserved_next_moves = set()

    # Pass 1: Standing Actions & Shed Deposits
    for u_idx in list(unassigned_units):
        ux, uy = all_units[u_idx]
        u_inv = inventories[u_idx] if u_idx < len(inventories) else {}
        u_tile = farm["tiles"][uy][ux]
        is_shed_adj = (ux, uy) in shed_tiles

        if sum(u_inv.values()) > 0 and is_shed_adj:
            unit_actions[u_idx] = ["DROP"]
            reserved_next_moves.add((ux, uy))
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

                if not watered:
                    curr_act = ["WATER"]
                else:
                    if crop_data.get("ongoing", False):
                        if yield_units > 0:
                            curr_act = ["HARVEST"]
                    else:
                        if age >= crop_data.get("max_yield_day", 4) or day >= 29:
                            curr_act = ["HARVEST"]

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
            reserved_next_moves.add((ux, uy))
            unassigned_units.remove(u_idx)
            continue

        if sum(u_inv.values()) >= 4 and not is_shed_adj:
            closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
            mv = get_best_move((ux, uy), closest_shed, board_size, reserved_next_moves)
            if mv:
                unit_actions[u_idx] = [mv]
                reserved_next_moves.add(_next_pos((ux, uy), mv))
                unassigned_units.remove(u_idx)
                continue

    # Pass 2: Spatial Assignment to Nearest Tasks
    for task in ordered_tasks:
        if not unassigned_units:
            break
        tpos = task["pos"]
        if tpos in assigned_tiles:
            continue

        best_u = None
        best_dist = 9999
        for u_idx in unassigned_units:
            dist = manhattan_dist(all_units[u_idx], tpos)
            if dist < best_dist:
                best_dist = dist
                best_u = u_idx

        if best_u is not None:
            ux, uy = all_units[best_u]
            mv = get_best_move((ux, uy), tpos, board_size, reserved_next_moves)
            if mv:
                unit_actions[best_u] = [mv]
                reserved_next_moves.add(_next_pos((ux, uy), mv))
            else:
                ttype = task["type"]
                if ttype == "PLANT":
                    if local_seeds.get("MELON", 0) > 0 and day <= 17:
                        unit_actions[best_u] = ["PLANT", "MELON"]
                        local_seeds["MELON"] -= 1
                    elif local_seeds.get("CARROT", 0) > 0 and day < 28:
                        unit_actions[best_u] = ["PLANT", "CARROT"]
                        local_seeds["CARROT"] -= 1
                    elif local_seeds.get("WHEAT", 0) > 0 and day < 28:
                        unit_actions[best_u] = ["PLANT", "WHEAT"]
                        local_seeds["WHEAT"] -= 1
                    else:
                        unit_actions[best_u] = ["PASS"]
                else:
                    unit_actions[best_u] = [ttype]
                reserved_next_moves.add((ux, uy))

            assigned_tiles.add(tpos)
            unassigned_units.remove(best_u)

    # Pass 3: Idle Units Return to Shed
    for u_idx in unassigned_units:
        ux, uy = all_units[u_idx]
        is_shed_adj = (ux, uy) in shed_tiles
        if not is_shed_adj:
            closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
            mv = get_best_move((ux, uy), closest_shed, board_size, reserved_next_moves)
            unit_actions[u_idx] = [mv] if mv else ["PASS"]
            reserved_next_moves.add(_next_pos((ux, uy), mv) if mv else (ux, uy))
        else:
            unit_actions[u_idx] = ["PASS"]
            reserved_next_moves.add((ux, uy))

    farmer_action = unit_actions[0] if unit_actions and unit_actions[0] is not None else ["PASS"]
    hands_actions = [a if a is not None else ["PASS"] for a in unit_actions[1:]]

    return {
        "farmer": farmer_action,
        "hands": hands_actions,
        "market": market_orders[:10]
    }
