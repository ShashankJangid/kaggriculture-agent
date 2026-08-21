import math
from collections import deque

CROPS = {
    "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT": {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
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

    # Primary direction choice
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

    # 1. Market Selling: Immediately sell all products in shed
    for item, qty in list(shed.items()):
        if qty > 0:
            market_orders.append(["SELL", item, qty])

    # 2. Aggressive Early Land Expansion
    unlocked_quads = len(farm.get("unlocked_quadrants", ["NW"]))
    if unlocked_quads < 4:
        next_cost = LAND_PRICES[unlocked_quads - 1]
        # Day 0: Buy NE immediately! (We start with 3000, NE costs 1000)
        # Later: Expand as soon as we have cost + buffer
        buffer = 300 if day == 0 else 500
        if money >= next_cost + buffer and day <= 20:
            market_orders.append(["BUY_LAND"])
            money -= next_cost
            unlocked_quads += 1

    # 3. Dynamic Scaling Labor (Hire farm hands every morning)
    hires_today = farm.get("hires_today", 0)
    if unlocked_quads == 1:
        target_hires = 3 if day < 25 else 1
    elif unlocked_quads == 2:
        target_hires = 6 if day < 25 else (3 if day < 28 else 0)
    elif unlocked_quads == 3:
        target_hires = 8 if day < 25 else (4 if day < 28 else 0)
    else:
        target_hires = 10 if day < 25 else (5 if day < 28 else 0)

    if hour == 0 and hires_today < target_hires and money >= 100:
        for _ in range(target_hires - hires_today):
            market_orders.append(["HIRE"])

    # 4. Count Empty & Active Tiles for Seed Planning
    empty_unlocked_tiles = 0
    melon_tiles = 0
    for y in range(board_size):
        for x in range(board_size):
            t = farm["tiles"][y][x]
            if t == "LOCKED":
                continue
            if t is None:
                empty_unlocked_tiles += 1
            elif isinstance(t, dict) and t.get("crop") == "MELON":
                melon_tiles += 1

    # 5. Proactive Seed Purchasing
    town_shops = obs.get("town", {}).get("unlocked_shops", [])
    pet_cafes = town_shops.count("PET_CAFE")
    bakeries = town_shops.count("BAKERY")

    total_seeds_available = sum(seeds.values())
    if day <= 18:
        max_melons = 20 if unlocked_quads >= 2 else 10
        desired_melon = max(0, max_melons - melon_tiles - seeds.get("MELON", 0))
        if desired_melon > 0 and money >= 80:
            buy_melon = min(desired_melon, int(money // 80), 10)
            if buy_melon > 0:
                market_orders.append(["BUY_SEED", "MELON", buy_melon])
                money -= buy_melon * 80

        # Carrots for fast cash
        if seeds.get("CARROT", 0) < 25 + (pet_cafes * 15) and money >= 20:
            buy_carrot = min(25 - seeds.get("CARROT", 0), int(money // 20), 10)
            if buy_carrot > 0:
                market_orders.append(["BUY_SEED", "CARROT", buy_carrot])
                money -= buy_carrot * 20

        # Wheat for baseline stability
        if seeds.get("WHEAT", 0) < 15 + (bakeries * 8) and money >= 10:
            buy_wheat = min(15 - seeds.get("WHEAT", 0), int(money // 10), 10)
            if buy_wheat > 0:
                market_orders.append(["BUY_SEED", "WHEAT", buy_wheat])
                money -= buy_wheat * 10

    elif day <= 24:
        # Mid-late: Transition to fast turnaround crops (Carrots / Wheat)
        if seeds.get("CARROT", 0) < 35 and money >= 20:
            buy_carrot = min(35 - seeds.get("CARROT", 0), int(money // 20), 10)
            if buy_carrot > 0:
                market_orders.append(["BUY_SEED", "CARROT", buy_carrot])
                money -= buy_carrot * 20
        if seeds.get("WHEAT", 0) < 20 and money >= 10:
            buy_wheat = min(20 - seeds.get("WHEAT", 0), int(money // 10), 10)
            if buy_wheat > 0:
                market_orders.append(["BUY_SEED", "WHEAT", buy_wheat])
                money -= buy_wheat * 10

    elif day <= 27:
        # Late game: Fast carrots only
        if seeds.get("CARROT", 0) < 25 and money >= 20:
            buy_carrot = min(25 - seeds.get("CARROT", 0), int(money // 20), 10)
            if buy_carrot > 0:
                market_orders.append(["BUY_SEED", "CARROT", buy_carrot])
                money -= buy_carrot * 20
    else:
        # Liquidation: No new seeds
        pass

    # 6. Worker Units Dispatching & Task Queue
    all_units = [farm["farmer"]] + farm.get("hands", [])
    num_units = len(all_units)

    tasks = []
    # Generate tasks across all tiles
    for y in range(board_size):
        for x in range(board_size):
            tile = farm["tiles"][y][x]
            if tile == "LOCKED":
                continue

            if tile is None:
                if day < 28:
                    tasks.append({"type": "PLANT", "pos": (x, y), "prio": 4})
            elif isinstance(tile, dict):
                kind = tile.get("kind")
                if kind == "WEED":
                    tasks.append({"type": "DIG", "pos": (x, y), "prio": 3})
                elif kind == "PLANT":
                    crop = tile.get("crop")
                    crop_data = CROPS.get(crop, {})
                    age = day - tile.get("planted_day", 0)
                    yield_units = tile.get("yield_units", 0)

                    # Harvest criteria
                    if crop_data.get("ongoing", False):
                        if yield_units > 0:
                            tasks.append({"type": "HARVEST", "pos": (x, y), "prio": 1})
                        elif not tile.get("watered_today", False):
                            tasks.append({"type": "WATER", "pos": (x, y), "prio": 2})
                    else:
                        # Non-ongoing: harvest at max yield day or late in game
                        if age >= crop_data.get("max_yield_day", 4) or day >= 29:
                            tasks.append({"type": "HARVEST", "pos": (x, y), "prio": 1})
                        elif not tile.get("watered_today", False):
                            tasks.append({"type": "WATER", "pos": (x, y), "prio": 2})

    # Sort tasks by priority
    tasks.sort(key=lambda t: t["prio"])

    # Worker Assignment
    unit_actions = []
    assigned_tiles = set()
    local_seeds = dict(seeds)

    for idx, unit_pos in enumerate(all_units):
        ux, uy = unit_pos
        u_inv = inventories[idx] if idx < len(inventories) else {}
        u_tile = farm["tiles"][uy][ux]

        # Check shed drop
        carrying_items = sum(u_inv.values()) > 0
        is_shed_adj = (ux, uy) in shed_tiles

        if carrying_items and is_shed_adj:
            unit_actions.append(["DROP"])
            continue

        # Immediate Tile Action
        curr_action = None
        if u_tile is not None and u_tile != "LOCKED" and isinstance(u_tile, dict):
            if u_tile.get("kind") == "WEED":
                curr_action = ["DIG"]
            elif u_tile.get("kind") == "PLANT":
                crop = u_tile.get("crop")
                crop_data = CROPS.get(crop, {})
                age = day - u_tile.get("planted_day", 0)
                yield_units = u_tile.get("yield_units", 0)
                if (crop_data.get("ongoing") and yield_units > 0) or (not crop_data.get("ongoing") and age >= crop_data.get("max_yield_day", 4)) or day >= 29:
                    curr_action = ["HARVEST"]
                elif not u_tile.get("watered_today", False):
                    curr_action = ["WATER"]

        elif u_tile is None:
            # Plant immediately on empty tile
            if local_seeds.get("MELON", 0) > 0 and day <= 18:
                curr_action = ["PLANT", "MELON"]
                local_seeds["MELON"] -= 1
            elif local_seeds.get("CARROT", 0) > 0 and day < 28:
                curr_action = ["PLANT", "CARROT"]
                local_seeds["CARROT"] -= 1
            elif local_seeds.get("WHEAT", 0) > 0 and day < 28:
                curr_action = ["PLANT", "WHEAT"]
                local_seeds["WHEAT"] -= 1

        if curr_action is not None:
            unit_actions.append(curr_action)
            assigned_tiles.add((ux, uy))
            continue

        # If carrying heavy inventory (e.g. >= 4 items), navigate to shed
        if sum(u_inv.values()) >= 4:
            closest_shed = min(shed_tiles, key=lambda s: abs(s[0] - ux) + abs(s[1] - uy))
            mv = get_best_move((ux, uy), closest_shed, board_size)
            if mv:
                unit_actions.append([mv])
                continue

        # Find best available task from queue
        best_task = None
        best_dist = 999
        for task in tasks:
            tpos = task["pos"]
            if tpos in assigned_tiles:
                continue
            dist = abs(tpos[0] - ux) + abs(tpos[1] - uy)
            if dist < best_dist:
                best_dist = dist
                best_task = task

        if best_task:
            assigned_tiles.add(best_task["pos"])
            mv = get_best_move((ux, uy), best_task["pos"], board_size)
            if mv:
                unit_actions.append([mv])
            else:
                # Already on the target tile
                if best_task["type"] == "WATER":
                    unit_actions.append(["WATER"])
                elif best_task["type"] == "HARVEST":
                    unit_actions.append(["HARVEST"])
                elif best_task["type"] == "DIG":
                    unit_actions.append(["DIG"])
                elif best_task["type"] == "PLANT":
                    if local_seeds.get("MELON", 0) > 0 and day <= 18:
                        unit_actions.append(["PLANT", "MELON"])
                        local_seeds["MELON"] -= 1
                    elif local_seeds.get("CARROT", 0) > 0 and day < 28:
                        unit_actions.append(["PLANT", "CARROT"])
                        local_seeds["CARROT"] -= 1
                    elif local_seeds.get("WHEAT", 0) > 0 and day < 28:
                        unit_actions.append(["PLANT", "WHEAT"])
                        local_seeds["WHEAT"] -= 1
                    else:
                        unit_actions.append(["PASS"])
                else:
                    unit_actions.append(["PASS"])
        else:
            # No task: wander toward center / shed or pass
            if not is_shed_adj:
                closest_shed = min(shed_tiles, key=lambda s: abs(s[0] - ux) + abs(s[1] - uy))
                mv = get_best_move((ux, uy), closest_shed, board_size)
                unit_actions.append([mv] if mv else ["PASS"])
            else:
                unit_actions.append(["PASS"])

    farmer_action = unit_actions[0] if unit_actions else ["PASS"]
    hands_actions = unit_actions[1:] if len(unit_actions) > 1 else []

    return {
        "farmer": farmer_action,
        "hands": hands_actions,
        "market": market_orders[:10]
    }
