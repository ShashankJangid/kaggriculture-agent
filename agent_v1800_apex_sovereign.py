"""
🌾 Autonomous Industrial Farm Agent v1800 — Apex Sovereign (Precision Fertilize)
Author: Shashank Jangid

Architectural Improvements:
1. PROXIMITY-BOUND FERTILIZER APPLICATION:
   - Workers carrying FERTILIZER only accept FERTILIZE tasks within a close radius (dist <= 4),
     preventing long treks that delay planting or watering.
2. PLANTING PRIORITY RESTORATION:
   - Planting tasks maintain higher priority than distant fertilizing, ensuring full 75-tile land utilization.
3. RETENTION OF V1600 BREAKTHROUGH:
   - Strawberry fertilization doubling yields (+100% per harvest) on Days 11-24.
   - 100% fertilizer cash generation on Days 0-10 and Days 25-29.
   - Proven V1000 water-first core.
"""

from collections import defaultdict

CROPS = {
    "WHEAT":      {"seed": 10,  "max_yield_day": 4,  "ongoing": False, "base_price": 25},
    "CARROT":     {"seed": 20,  "max_yield_day": 3,  "ongoing": False, "base_price": 35},
    "STRAWBERRY": {"seed": 100, "max_yield_day": 10, "ongoing": True,  "base_price": 120},
    "MELON":      {"seed": 80,  "max_yield_day": 12, "ongoing": False, "base_price": 250},
}

LAND_PRICES = [1000, 2000, 4000]


def get_shed_access_tiles(board_size=10):
    half = board_size // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]


def get_best_move(cur_pos, target_pos):
    cx, cy = cur_pos
    tx, ty = target_pos
    if cx == tx and cy == ty:
        return None
    dx, dy = tx - cx, ty - cy
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

    # ── 1. MARKET: Sell Products ──────────────────────────────────────────────
    for item, qty in list(shed.items()):
        if qty > 0 and item in ("MILK", "WOOL", "EGG", "MELON", "STRAWBERRY", "CARROT", "TOMATO"):
            market_orders.append(["SELL", item, qty])
        elif qty > 18 and item == "WHEAT":
            market_orders.append(["SELL", "WHEAT", qty - 18])
        elif qty > 0 and item == "FERTILIZER":
            if day <= 10 or day >= 25:
                market_orders.append(["SELL", "FERTILIZER", qty])
            elif qty > 6:
                market_orders.append(["SELL", "FERTILIZER", qty - 6])

    # ── 2. HIRING: Optimal Labor Ramp ──────────────────────────────────────────
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
    elif day >= 15:
        target_hires = 11
    else:
        target_hires = 10

    if hires_today < target_hires and money >= 5:
        for _ in range(target_hires - hires_today):
            market_orders.append(["HIRE"])

    hiring_reserve = 150 if day < 25 else 0
    spendable = max(0, money - hiring_reserve)

    # ── 3. LAND: Unlock up to 3 Quadrants (75 Tiles) ──────────────────────────
    if unlocked_quads < 3 and day <= 15:
        cost = LAND_PRICES[unlocked_quads - 1]
        buffer = 300 if day <= 7 else 500
        if spendable >= cost + buffer:
            market_orders.append(["BUY_LAND"])
            spendable -= cost
            money -= cost
            unlocked_quads += 1

    # ── 4. TILE SURVEY ────────────────────────────────────────────────────────
    pasture_positions = []
    animal_positions = []
    empty_pasture_pos = []
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
                        empty_pasture_pos.append((x, y))
                elif kind == "PLANT":
                    crop_counts[t.get("crop")] += 1

    num_animals = len(animal_positions)
    num_cows = sum(1 for a in animal_positions if a[2] == "COW")
    num_sheep = sum(1 for a in animal_positions if a[2] == "SHEEP")

    designated_pastures = [
        (4, 4), (5, 4), (4, 5), (5, 5),
        (4, 3), (5, 3), (3, 4), (3, 5),
        (4, 6), (5, 6), (6, 4), (6, 5),
    ]

    max_pastures = min(len([p for p in designated_pastures if farm["tiles"][p[1]][p[0]] != "LOCKED"]), 11)

    # ── 5. PURCHASING ─────────────────────────────────────────────────────────
    if hour < 20:
        if day == 0 and hour == 0:
            if spendable >= 1800:
                market_orders.append(["BUY_ANIMAL", "COW", 2])
                market_orders.append(["BUY_ANIMAL", "SHEEP", 2])
                spendable -= 1800
            if spendable >= 50:
                market_orders.append(["BUY_PRODUCT", "WHEAT", 4])
                spendable -= 50

        elif day <= 10 and shed.get("COW", 0) == 0 and shed.get("SHEEP", 0) == 0:
            total_animals = num_cows + num_sheep
            if num_cows < 6 and len(pasture_positions) > total_animals and spendable >= 800:
                market_orders.append(["BUY_ANIMAL", "COW", 1])
                spendable -= 400
            elif day >= 2 and num_sheep < 5 and len(pasture_positions) > total_animals and spendable >= 900:
                market_orders.append(["BUY_ANIMAL", "SHEEP", 1])
                spendable -= 500

        if shed.get("WHEAT", 0) < 4 and num_animals > 0 and spendable >= 50:
            market_orders.append(["BUY_PRODUCT", "WHEAT", 4])
            spendable -= 50

        # SEEDS
        if day <= 5:
            desired_melons = max(0, 12 - crop_counts["MELON"] - seeds.get("MELON", 0))
            if desired_melons > 0 and spendable >= 80:
                bm = min(desired_melons, int(spendable // 80), 6)
                if bm > 0:
                    market_orders.append(["BUY_SEED", "MELON", bm])
                    spendable -= bm * 80

            desired_wheat = max(0, 7 - crop_counts["WHEAT"] - seeds.get("WHEAT", 0))
            if desired_wheat > 0 and spendable >= 10:
                bw = min(desired_wheat, int(spendable // 10), 7)
                if bw > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", bw])
                    spendable -= bw * 10

        elif day <= 15:
            target_strawberries = 38
            desired_sb = max(0, target_strawberries - crop_counts["STRAWBERRY"] - seeds.get("STRAWBERRY", 0))
            if desired_sb > 0 and spendable >= 100:
                bs = min(desired_sb, int(spendable // 100), 10)
                if bs > 0:
                    market_orders.append(["BUY_SEED", "STRAWBERRY", bs])
                    spendable -= bs * 100

            target_wheat = 20
            desired_wh = max(0, target_wheat - crop_counts["WHEAT"] - seeds.get("WHEAT", 0))
            if desired_wh > 0 and spendable >= 10:
                bw = min(desired_wh, int(spendable // 10), 10)
                if bw > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", bw])
                    spendable -= bw * 10

        elif day <= 22:
            target_wheat = 22
            desired_wh = max(0, target_wheat - crop_counts["WHEAT"] - seeds.get("WHEAT", 0))
            if desired_wh > 0 and spendable >= 10:
                bw = min(desired_wh, int(spendable // 10), 10)
                if bw > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", bw])
                    spendable -= bw * 10

        elif day <= 27:
            target_wheat = 40
            desired_wh = max(0, target_wheat - seeds.get("WHEAT", 0))
            if desired_wh > 0 and spendable >= 10:
                bw = min(desired_wh, int(spendable // 10), 20)
                if bw > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", bw])
                    spendable -= bw * 10

    # ── 6. TASK GENERATION ────────────────────────────────────────────────────
    all_units = [farm["farmer"]] + farm.get("hands", [])
    num_units = len(all_units)

    tasks_animal_chores = []
    tasks_watering = []
    tasks_harvesting = []
    tasks_digging = []
    tasks_planting = []
    tasks_build_pasture = []
    tasks_fertilize = []

    for px, py in designated_pastures:
        t = farm["tiles"][py][px]
        if t == "LOCKED":
            continue
        if t is None and len(pasture_positions) < max_pastures:
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
                    fertilized = tile.get("fertilized_until_day", -1) >= day

                    if not watered:
                        tasks_watering.append({"type": "WATER", "pos": (x, y)})

                    if not crop_data.get("ongoing"):
                        if age >= crop_data.get("max_yield_day", 4) or day >= 29:
                            tasks_harvesting.append({"type": "HARVEST", "pos": (x, y)})
                    else:
                        if yield_units > 0:
                            tasks_harvesting.append({"type": "HARVEST", "pos": (x, y)})

                    if crop == "STRAWBERRY" and not fertilized and 11 <= day <= 24:
                        tasks_fertilize.append({"type": "FERTILIZE", "pos": (x, y)})

    ordered_tasks = (
        tasks_animal_chores
        + tasks_watering
        + tasks_harvesting
        + tasks_digging
        + tasks_planting
        + tasks_fertilize
        + tasks_build_pasture
    )

    # ── 7. SPATIAL DISPATCHER ─────────────────────────────────────────────────
    unit_actions = [None] * num_units
    assigned_tiles = set()
    local_seeds = dict(seeds)
    unassigned_units = list(range(num_units))

    # Pass 1: Immediate on-tile execution
    for u_idx in list(unassigned_units):
        ux, uy = all_units[u_idx]
        u_inv = inventories[u_idx] if u_idx < len(inventories) else {}
        u_tile = farm["tiles"][uy][ux]
        is_at_shed = (ux, uy) in shed_tiles
        carrying_items = sum(u_inv.values())

        sellable = sum(u_inv.get(p, 0) for p in ("MILK", "WOOL", "EGG", "MELON", "STRAWBERRY", "CARROT", "TOMATO"))
        if is_at_shed and (sellable > 0 or carrying_items >= 4 or (day >= 28 and carrying_items > 0)):
            unit_actions[u_idx] = ["DROP"]
            unassigned_units.remove(u_idx)
            continue

        if is_at_shed and len(empty_pasture_pos) > 0:
            if shed.get("COW", 0) > 0 and u_inv.get("COW", 0) == 0:
                unit_actions[u_idx] = ["PICKUP", "COW", 1]
                unassigned_units.remove(u_idx)
                continue
            if shed.get("SHEEP", 0) > 0 and u_inv.get("SHEEP", 0) == 0:
                unit_actions[u_idx] = ["PICKUP", "SHEEP", 1]
                unassigned_units.remove(u_idx)
                continue

        if u_tile not in (None, "LOCKED") and isinstance(u_tile, dict):
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
            elif kind == "PASTURE":
                if u_inv.get("COW", 0) > 0:
                    unit_actions[u_idx] = ["PLACE", "COW"]
                    unassigned_units.remove(u_idx)
                    continue
                if u_inv.get("SHEEP", 0) > 0:
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
                fertilized = u_tile.get("fertilized_until_day", -1) >= day

                if not watered:
                    unit_actions[u_idx] = ["WATER"]
                    assigned_tiles.add((ux, uy))
                    unassigned_units.remove(u_idx)
                    continue
                if crop_data.get("ongoing"):
                    if yield_units > 0:
                        unit_actions[u_idx] = ["HARVEST"]
                        assigned_tiles.add((ux, uy))
                        unassigned_units.remove(u_idx)
                        continue
                    if u_inv.get("FERTILIZER", 0) > 0 and not fertilized and 11 <= day <= 24:
                        unit_actions[u_idx] = ["FERTILIZE"]
                        assigned_tiles.add((ux, uy))
                        unassigned_units.remove(u_idx)
                        continue
                else:
                    if age >= crop_data.get("max_yield_day", 4) or day >= 29:
                        unit_actions[u_idx] = ["HARVEST"]
                        assigned_tiles.add((ux, uy))
                        unassigned_units.remove(u_idx)
                        continue

        elif u_tile is None and (ux, uy) not in assigned_tiles and hour < 20:
            if (ux, uy) in designated_pastures and len(pasture_positions) < max_pastures:
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

        if is_at_shed and u_inv.get("WHEAT", 0) == 0 and shed.get("WHEAT", 0) > 0 and num_animals > 0:
            pickup_qty = min(2, shed.get("WHEAT", 0))
            unit_actions[u_idx] = ["PICKUP", "WHEAT", pickup_qty]
            unassigned_units.remove(u_idx)
            continue

        if (carrying_items >= 4 or (day >= 28 and carrying_items > 0)) and not is_at_shed:
            closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
            move = get_best_move((ux, uy), closest_shed)
            if move:
                unit_actions[u_idx] = [move]
                unassigned_units.remove(u_idx)
                continue

    # Pass 2: Spatial auction matching
    for u_idx in list(unassigned_units):
        ux, uy = all_units[u_idx]
        best_task = None
        best_dist = 999

        for task in ordered_tasks:
            if task["pos"] in assigned_tiles:
                continue
            # Distance restriction for fertilize tasks: only nearby tasks (dist <= 3) to prevent wandering
            if task["type"] == "FERTILIZE":
                if inventories[u_idx].get("FERTILIZER", 0) == 0:
                    continue
                d = manhattan_dist((ux, uy), task["pos"])
                if d > 3:
                    continue
            dist = manhattan_dist((ux, uy), task["pos"])
            if dist < best_dist:
                best_dist = dist
                best_task = task

        if best_task:
            assigned_tiles.add(best_task["pos"])
            move = get_best_move((ux, uy), best_task["pos"])
            if move:
                unit_actions[u_idx] = [move]
            else:
                ttype = best_task["type"]
                if ttype == "BUILD_PASTURE":
                    unit_actions[u_idx] = ["BUILD_PASTURE"]
                elif ttype == "WATER":
                    unit_actions[u_idx] = ["WATER"]
                elif ttype == "HARVEST":
                    unit_actions[u_idx] = ["HARVEST"]
                elif ttype == "FERTILIZE":
                    unit_actions[u_idx] = ["FERTILIZE"]
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
        else:
            is_at_shed = (ux, uy) in shed_tiles
            if not is_at_shed:
                closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
                move = get_best_move((ux, uy), closest_shed)
                unit_actions[u_idx] = [move] if move else ["PASS"]
            else:
                unit_actions[u_idx] = ["PASS"]
        unassigned_units.remove(u_idx)

    farmer_action = unit_actions[0] if unit_actions[0] else ["PASS"]
    hands_actions = [a if a else ["PASS"] for a in unit_actions[1:]]

    return {
        "farmer": farmer_action,
        "hands": hands_actions,
        "market": market_orders[:10],
    }
