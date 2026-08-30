"""
🌾 Autonomous Industrial Farm Agent v1000 — Sovereign Prime
Author: Shashank Jangid

Reverse-Engineered 114k SOTA Architecture (Fernando GH H 114k & hidsaito 109k):
1. Precision Opening (Day 0-1):
   - 2 Cows + 2 Sheep (4 animals) on inner pasture cluster.
   - 12 Melons + 7 Wheat. (0 Carrots - eliminates low-yield crop dilution).
2. Quad 2 Expansion & Animal Scale (Days 6-8):
   - Unlock Quad 2 on Day 6-7.
   - Expand herd to 10-12 animals (6 Cows + 4-6 Sheep).
   - Begin planting early Strawberries (12-16 tiles).
3. Quad 3 SOTA Compounding Engine (Day 11 Melon Harvest ~$17k):
   - Unlock Quad 3 (75 tiles total - optimal travel efficiency, no Q4 dilution).
   - Ramp Strawberries to 38 tiles.
   - Maintain 20-25 Wheat tiles to 100% feed the 12-animal herd.
4. Endgame Passive Cash Flow:
   - 12 animals produce ~$2,500/day in Milk, Wool, and Fertilizer.
   - 38 Strawberries yield recurring harvests every 2 days from Day 21 to Day 28.
   - Target Score: $90,000 - $110,000+.
"""
import math
from collections import defaultdict

CROPS = {
    "WHEAT":      {"seed": 10,  "first_yield_day": 2,  "max_yield_day": 4,  "interval": 0, "max_yield": 6, "ongoing": False, "base_price": 25,  "cycle": 2},
    "CARROT":     {"seed": 20,  "first_yield_day": 2,  "max_yield_day": 3,  "interval": 0, "max_yield": 4, "ongoing": False, "base_price": 35,  "cycle": 3},
    "TOMATO":     {"seed": 50,  "first_yield_day": 8,  "max_yield_day": 8,  "interval": 1, "max_yield": 4, "ongoing": True,  "base_price": 60,  "cycle": 8},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True,  "base_price": 120, "cycle": 10},
    "MELON":      {"seed": 80,  "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False, "base_price": 250, "cycle": 12},
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
    dx, dy = tx - cx, ty - cy
    moves = []
    if dx > 0: moves.append(("EAST", abs(dx)))
    elif dx < 0: moves.append(("WEST", abs(dx)))
    if dy > 0: moves.append(("SOUTH", abs(dy)))
    elif dy < 0: moves.append(("NORTH", abs(dy)))
    moves.sort(key=lambda m: m[1], reverse=True)
    return moves[0][0] if moves else None


def manhattan_dist(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


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

    # 1. Market Liquidation (Sell high-value items immediately)
    for item, qty in list(shed.items()):
        if qty > 0 and item in ("MILK", "WOOL", "EGG", "FERTILIZER", "MELON", "STRAWBERRY", "CARROT", "TOMATO"):
            market_orders.append(["SELL", item, qty])
        elif qty > 18 and item == "WHEAT":
            market_orders.append(["SELL", "WHEAT", qty - 18])

    # 2. Workforce Dynamic Management
    hires_today = farm.get("hires_today", 0)
    unlocked_quads = len(farm.get("unlocked_quadrants", ["NW"]))

    if day >= 28:
        target_hires = 6
    elif day >= 25:
        target_hires = 8
    elif unlocked_quads == 1:
        target_hires = 5
    elif unlocked_quads == 2:
        target_hires = 7
    elif unlocked_quads >= 3:
        target_hires = 10

    if hires_today < target_hires and money >= 5:
        for _ in range(target_hires - hires_today):
            market_orders.append(["HIRE"])

    hiring_reserve = 150 if day < 25 else 0
    spendable_money = max(0, money - hiring_reserve)

    # 3. Dynamic Land Expansion (Cap at 3 Quads / 75 tiles for optimal 10-hand efficiency)
    if unlocked_quads < 3 and day <= 15:
        next_cost = LAND_PRICES[unlocked_quads - 1]
        buffer = 300 if day <= 7 else 500
        if spendable_money >= next_cost + buffer:
            market_orders.append(["BUY_LAND"])
            spendable_money -= next_cost
            money -= next_cost
            unlocked_quads += 1

    # 4. Count Structures & Crops
    pasture_positions = []
    animal_positions = []
    empty_pasture_positions = []
    crop_counts = defaultdict(int)

    for y in range(board_size):
        for x in range(board_size):
            t = farm["tiles"][y][x]
            if t == "LOCKED" or t is None:
                continue
            if isinstance(t, dict):
                kind = t.get("kind")
                if kind == "PASTURE":
                    pasture_positions.append((x, y))
                    if "animal" in t:
                        animal_positions.append((x, y, t["animal"], t))
                    else:
                        empty_pasture_positions.append((x, y))
                elif kind == "PLANT":
                    crop_counts[t.get("crop")] += 1

    num_animals = len(animal_positions)
    num_cows = sum(1 for a in animal_positions if a[2] == "COW")
    num_sheep = sum(1 for a in animal_positions if a[2] == "SHEEP")

    # 12 Clustered Pasture Slots tightly grouped around shed
    designated_pastures = [
        (4, 4), (5, 4), (4, 5), (5, 5),  # Inner ring (distance 0)
        (4, 3), (5, 3), (3, 4), (3, 5),  # Ring 1
        (4, 6), (5, 6), (6, 4), (6, 5),  # Ring 2
    ]

    # 5. Strategic Purchasing Schedule
    if hour < 20:
        # Day 0 Opening: 2 Cows + 2 Sheep + Feed
        if day == 0 and hour == 0:
            if spendable_money >= 1800:
                market_orders.append(["BUY_ANIMAL", "COW", 2])
                market_orders.append(["BUY_ANIMAL", "SHEEP", 2])
                spendable_money -= 1800
            if spendable_money >= 50:
                market_orders.append(["BUY_PRODUCT", "WHEAT", 4])
                spendable_money -= 50

        total_cows = num_cows + shed.get("COW", 0)
        total_sheep = num_sheep + shed.get("SHEEP", 0)
        total_animals = total_cows + total_sheep

        # Days 2 to 10: Ramp up to 6 Cows + 5 Sheep
        if day <= 10 and spendable_money >= 800 and shed.get("COW", 0) == 0 and shed.get("SHEEP", 0) == 0:
            if total_cows < 6 and len(pasture_positions) > total_animals:
                market_orders.append(["BUY_ANIMAL", "COW", 1])
                spendable_money -= 400
            elif day >= 2 and total_sheep < 5 and len(pasture_positions) > total_animals and spendable_money >= 900:
                market_orders.append(["BUY_ANIMAL", "SHEEP", 1])
                spendable_money -= 500

        # Feed assurance: Keep at least 4 wheat in shed
        if shed.get("WHEAT", 0) < 4 and spendable_money >= 50 and num_animals > 0:
            market_orders.append(["BUY_PRODUCT", "WHEAT", 4])
            spendable_money -= 50

        # Seed Purchasing:
        if day <= 5:
            # Melons: up to 12
            desired_melons = max(0, 12 - crop_counts["MELON"] - seeds.get("MELON", 0))
            if desired_melons > 0 and spendable_money >= 80:
                bm = min(desired_melons, int(spendable_money // 80), 6)
                if bm > 0:
                    market_orders.append(["BUY_SEED", "MELON", bm])
                    spendable_money -= bm * 80

            # Wheat: up to 8
            desired_wheat = max(0, 8 - crop_counts["WHEAT"] - seeds.get("WHEAT", 0))
            if desired_wheat > 0 and spendable_money >= 10:
                bw = min(desired_wheat, int(spendable_money // 10), 8)
                if bw > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", bw])
                    spendable_money -= bw * 10

        elif day <= 9:
            # Start early Strawberries! (up to 16)
            desired_strawberries = max(0, 16 - crop_counts["STRAWBERRY"] - seeds.get("STRAWBERRY", 0))
            if desired_strawberries > 0 and spendable_money >= 100:
                bs = min(desired_strawberries, int(spendable_money // 100), 6)
                if bs > 0:
                    market_orders.append(["BUY_SEED", "STRAWBERRY", bs])
                    spendable_money -= bs * 100

            # Wheat buffer:
            desired_wheat = max(0, 12 - crop_counts["WHEAT"] - seeds.get("WHEAT", 0))
            if desired_wheat > 0 and spendable_money >= 10:
                bw = min(desired_wheat, int(spendable_money // 10), 8)
                if bw > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", bw])
                    spendable_money -= bw * 10

        elif day <= 15:
            # The Massive 38-Strawberry Surge
            desired_strawberries = max(0, 38 - crop_counts["STRAWBERRY"] - seeds.get("STRAWBERRY", 0))
            if desired_strawberries > 0 and spendable_money >= 100:
                bs = min(desired_strawberries, int(spendable_money // 100), 10)
                if bs > 0:
                    market_orders.append(["BUY_SEED", "STRAWBERRY", bs])
                    spendable_money -= bs * 100

            desired_wheat = max(0, 22 - crop_counts["WHEAT"] - seeds.get("WHEAT", 0))
            if desired_wheat > 0 and spendable_money >= 10:
                bw = min(desired_wheat, int(spendable_money // 10), 10)
                if bw > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", bw])
                    spendable_money -= bw * 10

        elif day <= 24:
            desired_wheat = max(0, 24 - crop_counts["WHEAT"] - seeds.get("WHEAT", 0))
            if desired_wheat > 0 and spendable_money >= 10:
                bw = min(desired_wheat, int(spendable_money // 10), 10)
                if bw > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", bw])
                    spendable_money -= bw * 10

        elif day <= 27:
            desired_wheat = max(0, 30 - seeds.get("WHEAT", 0))
            if desired_wheat > 0 and spendable_money >= 10:
                bw = min(desired_wheat, int(spendable_money // 10), 15)
                if bw > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", bw])
                    spendable_money -= bw * 10

    # 6. Task Collection & Prioritization
    all_units = [farm["farmer"]] + farm.get("hands", [])
    num_units = len(all_units)

    tasks_animal_chores = []
    tasks_watering = []
    tasks_harvesting = []
    tasks_digging = []
    tasks_planting = []
    tasks_build_pasture = []

    # Check Pastures & Animal Chores
    max_pastures_allowed = 4 if unlocked_quads == 1 else (8 if unlocked_quads == 2 else 11)
    for px, py in designated_pastures:
        t = farm["tiles"][py][px]
        if t == "LOCKED":
            continue
        if t is None and len(pasture_positions) < max_pastures_allowed:
            tasks_build_pasture.append({"type": "BUILD_PASTURE", "pos": (px, py)})
        elif isinstance(t, dict) and t.get("kind") == "PASTURE":
            if "animal" in t:
                if not t.get("fed_today", False):
                    tasks_animal_chores.append({"type": "FEED", "pos": (px, py)})
                if not t.get("cared_today", False):
                    tasks_animal_chores.append({"type": "CARE", "pos": (px, py)})
                if t.get("yield_units", 0) > 0:
                    tasks_animal_chores.append({"type": "HARVEST", "pos": (px, py)})
                if t.get("fertilizer_available", False):
                    tasks_animal_chores.append({"type": "COLLECT_FERTILIZER", "pos": (px, py)})
            else:
                if shed.get("COW", 0) > 0 or shed.get("SHEEP", 0) > 0:
                    tasks_animal_chores.append({"type": "PLACE_ANIMAL", "pos": (px, py)})

    # Crop Tasks
    for y in range(board_size):
        for x in range(board_size):
            tile = farm["tiles"][y][x]
            if tile == "LOCKED":
                continue
            if tile is None:
                if (x, y) not in designated_pastures and day < 28 and hour < 20:
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
                        tasks_watering.append({"type": "WATER", "pos": (x, y)})
                    if crop_data.get("ongoing", False):
                        if yield_units > 0:
                            tasks_harvesting.append({"type": "HARVEST", "pos": (x, y)})
                    else:
                        if age >= crop_data.get("max_yield_day", 4) or day >= 29:
                            tasks_harvesting.append({"type": "HARVEST", "pos": (x, y)})

    ordered_tasks = tasks_animal_chores + tasks_watering + tasks_harvesting + tasks_digging + tasks_planting + tasks_build_pasture

    # 7. Spatial Unit Dispatcher
    unit_actions     = [None] * num_units
    assigned_tiles   = set()
    local_seeds      = dict(seeds)
    unassigned_units = list(range(num_units))

    for u_idx in list(unassigned_units):
        ux, uy = all_units[u_idx]
        u_inv = inventories[u_idx] if u_idx < len(inventories) else {}
        u_tile = farm["tiles"][uy][ux]
        is_shed_adj = (ux, uy) in shed_tiles
        carrying = sum(u_inv.values())

        # If carrying sellables and at shed -> DROP immediately
        sellable = sum(u_inv.get(p, 0) for p in ("MILK", "WOOL", "EGG", "FERTILIZER", "MELON", "STRAWBERRY", "CARROT", "TOMATO"))
        if is_shed_adj and (sellable > 0 or carrying >= 4 or (day >= 28 and carrying > 0)):
            unit_actions[u_idx] = ["DROP"]
            unassigned_units.remove(u_idx)
            continue

        # If standing on pasture with animal
        if u_tile is not None and u_tile != "LOCKED" and isinstance(u_tile, dict):
            kind = u_tile.get("kind")
            if "animal" in u_tile:
                if u_tile.get("yield_units", 0) > 0:
                    unit_actions[u_idx] = ["HARVEST"]
                    unassigned_units.remove(u_idx)
                    continue
                if u_inv.get("WHEAT", 0) > 0 and not u_tile.get("fed_today", False):
                    unit_actions[u_idx] = ["FEED"]
                    unassigned_units.remove(u_idx)
                    continue
                if not u_tile.get("cared_today", False):
                    unit_actions[u_idx] = ["CARE"]
                    unassigned_units.remove(u_idx)
                    continue
                if u_tile.get("fertilizer_available", False):
                    unit_actions[u_idx] = ["COLLECT_FERTILIZER"]
                    unassigned_units.remove(u_idx)
                    continue

            elif kind == "PASTURE" and "animal" not in u_tile:
                if u_inv.get("COW", 0) > 0:
                    unit_actions[u_idx] = ["PLACE", "COW"]
                    unassigned_units.remove(u_idx)
                    continue
                elif u_inv.get("SHEEP", 0) > 0:
                    unit_actions[u_idx] = ["PLACE", "SHEEP"]
                    unassigned_units.remove(u_idx)
                    continue

            elif kind == "WEED":
                unit_actions[u_idx] = ["DIG"]
                assigned_tiles.add((ux, uy))
                unassigned_units.remove(u_idx)
                continue

            elif kind == "PLANT":
                crop = u_tile.get("crop")
                crop_data = CROPS.get(crop, {})
                age = day - u_tile.get("planted_day", 0)
                yield_units = u_tile.get("yield_units", 0)
                watered = u_tile.get("watered_today", False)
                if not watered:
                    unit_actions[u_idx] = ["WATER"]
                    assigned_tiles.add((ux, uy))
                    unassigned_units.remove(u_idx)
                    continue
                elif (crop_data.get("ongoing") and yield_units > 0) \
                  or (not crop_data.get("ongoing") and age >= crop_data.get("max_yield_day", 4)) \
                  or day >= 29:
                    unit_actions[u_idx] = ["HARVEST"]
                    assigned_tiles.add((ux, uy))
                    unassigned_units.remove(u_idx)
                    continue

        elif u_tile is None and (ux, uy) not in assigned_tiles and hour < 20:
            if (ux, uy) in designated_pastures and len(pasture_positions) < max_pastures_allowed:
                unit_actions[u_idx] = ["BUILD_PASTURE"]
                assigned_tiles.add((ux, uy))
                unassigned_units.remove(u_idx)
                continue
            elif local_seeds.get("MELON", 0) > 0 and day <= 10:
                unit_actions[u_idx] = ["PLANT", "MELON"]
                local_seeds["MELON"] -= 1
                assigned_tiles.add((ux, uy))
                unassigned_units.remove(u_idx)
                continue
            elif local_seeds.get("STRAWBERRY", 0) > 0 and day <= 15:
                unit_actions[u_idx] = ["PLANT", "STRAWBERRY"]
                local_seeds["STRAWBERRY"] -= 1
                assigned_tiles.add((ux, uy))
                unassigned_units.remove(u_idx)
                continue
            elif local_seeds.get("WHEAT", 0) > 0 and day < 28:
                unit_actions[u_idx] = ["PLANT", "WHEAT"]
                local_seeds["WHEAT"] -= 1
                assigned_tiles.add((ux, uy))
                unassigned_units.remove(u_idx)
                continue

        # If at shed and need wheat for animal feed -> PICKUP WHEAT
        if is_shed_adj and u_inv.get("WHEAT", 0) == 0 and shed.get("WHEAT", 0) > 0 and num_animals > 0:
            unit_actions[u_idx] = ["PICKUP", "WHEAT", min(2, shed.get("WHEAT", 0))]
            unassigned_units.remove(u_idx)
            continue

        # If at shed and shed has animal to place -> PICKUP COW / SHEEP
        if is_shed_adj and len(empty_pasture_positions) > 0:
            if shed.get("COW", 0) > 0 and u_inv.get("COW", 0) == 0:
                unit_actions[u_idx] = ["PICKUP", "COW", 1]
                unassigned_units.remove(u_idx)
                continue
            elif shed.get("SHEEP", 0) > 0 and u_inv.get("SHEEP", 0) == 0:
                unit_actions[u_idx] = ["PICKUP", "SHEEP", 1]
                unassigned_units.remove(u_idx)
                continue

        drop_trigger = (carrying >= 4) or (day >= 28 and carrying > 0)
        if drop_trigger and not is_shed_adj:
            closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
            mv = get_best_move((ux, uy), closest_shed, board_size)
            if mv:
                unit_actions[u_idx] = [mv]
                unassigned_units.remove(u_idx)
                continue

    # Pass 2: Spatial Auction matching
    for u_idx in list(unassigned_units):
        ux, uy = all_units[u_idx]
        best_task = None
        best_dist = 999

        for task in ordered_tasks:
            tpos = task["pos"]
            if tpos in assigned_tiles:
                continue
            d = manhattan_dist((ux, uy), tpos)
            if d < best_dist:
                best_dist = d
                best_task = task

        if best_task:
            assigned_tiles.add(best_task["pos"])
            mv = get_best_move((ux, uy), best_task["pos"], board_size)
            if mv:
                unit_actions[u_idx] = [mv]
            else:
                ttype = best_task["type"]
                if ttype == "BUILD_PASTURE":
                    unit_actions[u_idx] = ["BUILD_PASTURE"]
                elif ttype == "WATER":
                    unit_actions[u_idx] = ["WATER"]
                elif ttype == "HARVEST":
                    unit_actions[u_idx] = ["HARVEST"]
                elif ttype == "DIG":
                    unit_actions[u_idx] = ["DIG"]
                elif ttype == "FEED":
                    unit_actions[u_idx] = ["FEED"]
                elif ttype == "CARE":
                    unit_actions[u_idx] = ["CARE"]
                elif ttype == "COLLECT_FERTILIZER":
                    unit_actions[u_idx] = ["COLLECT_FERTILIZER"]
                elif ttype == "PLANT":
                    if local_seeds.get("MELON", 0) > 0 and day <= 10:
                        unit_actions[u_idx] = ["PLANT", "MELON"]
                        local_seeds["MELON"] -= 1
                    elif local_seeds.get("STRAWBERRY", 0) > 0 and day <= 15:
                        unit_actions[u_idx] = ["PLANT", "STRAWBERRY"]
                        local_seeds["STRAWBERRY"] -= 1
                    elif local_seeds.get("WHEAT", 0) > 0 and day < 28:
                        unit_actions[u_idx] = ["PLANT", "WHEAT"]
                        local_seeds["WHEAT"] -= 1
                    else:
                        unit_actions[u_idx] = ["PASS"]
                else:
                    unit_actions[u_idx] = ["PASS"]
            unassigned_units.remove(u_idx)
        else:
            is_shed_adj = (ux, uy) in shed_tiles
            if not is_shed_adj:
                closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
                mv = get_best_move((ux, uy), closest_shed, board_size)
                unit_actions[u_idx] = [mv] if mv else ["PASS"]
            else:
                unit_actions[u_idx] = ["PASS"]
            unassigned_units.remove(u_idx)

    farmer_action = unit_actions[0] if unit_actions[0] is not None else ["PASS"]
    hands_actions = [a if a is not None else ["PASS"] for a in unit_actions[1:]]
    return {"farmer": farmer_action, "hands": hands_actions, "market": market_orders[:10]}
