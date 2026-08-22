"""
🌾 Kaggriculture Master SOTA Agent — Hyper-Compounding Engine (V120)
Author: Shashank Jangid
"""
import math
from collections import defaultdict

ANIMALS = ["COW", "SHEEP", "GOOSE"]

CROPS = {
    "WHEAT": {"seed": 10, "base_price": 25, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT": {"seed": 20, "base_price": 35, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
    "STRAWBERRY": {"seed": 100, "base_price": 120, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "base_price": 250, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}

LAND_PRICES = [1000, 2000, 4000]

def get_shed_access_tiles(board_size=10):
    half = board_size // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]

def manhattan_dist(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

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

def _is_owned(farm, x, y, board_size):
    half = board_size // 2
    quad = "NW" if (x < half and y < half) else ("NE" if (x >= half and y < half) else ("SW" if (x < half and y >= half) else "SE"))
    return quad in farm.get("unlocked_quadrants", ["NW"])

PASTURE_RING = [
    # NW Inner ring (Day 0)
    (4, 4), (3, 4), (4, 3), (3, 3),
    # NE ring (Day 6)
    (5, 4), (6, 4), (5, 3), (6, 3), (5, 2), (6, 2),
    # SW ring (Day 11)
    (4, 5), (3, 5), (4, 6), (3, 6), (2, 4), (2, 3), (3, 2), (4, 2),
]

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

    # 1. Market Sales: Keep safe Wheat reserve for animals, sell all high-value items
    wheat_in_shed = shed.get("WHEAT", 0)
    feed_reserve = 20 if day >= 11 else 4
    for item, qty in list(shed.items()):
        if qty > 0:
            if item == "WHEAT":
                surplus = max(0, qty - feed_reserve)
                if surplus > 0:
                    market_orders.append(["SELL", "WHEAT", surplus])
            elif item in ANIMALS:
                continue
            else:
                market_orders.append(["SELL", item, qty])

    # 2. Dynamic Workforce Hiring
    hires_today = farm.get("hires_today", 0)
    unlocked_quads = len(farm.get("unlocked_quadrants", ["NW"]))

    if day >= 29:
        target_hires = 8
    elif day >= 27:
        target_hires = 10
    elif day == 0:
        target_hires = 5
    elif day == 1:
        target_hires = 1 if money < 100 else 2
    elif day <= 4:
        target_hires = 2 if money < 200 else 4
    elif unlocked_quads == 1:
        target_hires = 6
    elif unlocked_quads == 2:
        target_hires = 8
    else:
        target_hires = 12

    if hires_today < target_hires and money >= 5:
        to_hire = target_hires - hires_today
        for _ in range(to_hire):
            market_orders.append(["HIRE"])

    # 3. Progressive Land Expansion (Optimal 75% Land Cap = 3 Quads max)
    # Buy Quad 2 as soon as money >= 1050 on Day 5+; Buy Quad 3 as soon as money >= 2100 on Day 10+
    if unlocked_quads == 1 and day >= 5 and money >= 1050:
        market_orders.append(["BUY_LAND"])
        money -= 1000
        unlocked_quads = 2
    elif unlocked_quads == 2 and day >= 10 and money >= 2150:
        market_orders.append(["BUY_LAND"])
        money -= 2000
        unlocked_quads = 3

    spendable_money = max(0, money - (300 if day >= 10 else 50))

    # 4. Count Farm State
    total_unlocked_tiles = unlocked_quads * 25
    melon_tiles = 0
    strawberry_tiles = 0
    wheat_tiles = 0
    pasture_count = 0
    cow_count = 0
    sheep_count = 0
    empty_pastures = []

    for y in range(board_size):
        for x in range(board_size):
            t = farm["tiles"][y][x]
            if t == "LOCKED":
                continue
            if isinstance(t, dict):
                k = t.get("kind")
                if k == "PASTURE":
                    pasture_count += 1
                    anim = t.get("animal")
                    if anim == "COW": cow_count += 1
                    elif anim == "SHEEP": sheep_count += 1
                    elif anim is None: empty_pastures.append((x, y))
                elif k == "PLANT":
                    crop = t.get("crop")
                    if crop == "MELON": melon_tiles += 1
                    elif crop == "STRAWBERRY": strawberry_tiles += 1
                    elif crop == "WHEAT": wheat_tiles += 1

    cows_in_shed = shed.get("COW", 0)
    sheep_in_shed = shed.get("SHEEP", 0)
    total_cows = cow_count + cows_in_shed
    total_sheep = sheep_count + sheep_in_shed

    # 5. Market Purchases (Executed on Hour 1)
    if hour == 1:
        if day == 0:
            if total_sheep < 2:
                market_orders.append(["BUY_ANIMAL", "SHEEP", 2])
                total_sheep += 2
            if total_cows < 2:
                market_orders.append(["BUY_ANIMAL", "COW", 2])
                total_cows += 2
            market_orders.append(["BUY_SEED", "MELON", 11])
            market_orders.append(["BUY_SEED", "WHEAT", 6])
            market_orders.append(["BUY_PRODUCT", "WHEAT", 4])
            wheat_in_shed += 4

        else:
            # Strawberries scale up to 28 (Days 4 to 12)
            if day >= 4 and day <= 12:
                target_straw = 28 if unlocked_quads >= 2 else 10
                desired_straw = max(0, target_straw - strawberry_tiles - seeds.get("STRAWBERRY", 0))
                if desired_straw > 0 and spendable_money >= 100:
                    buy_s = min(desired_straw, int(spendable_money // 100), 8)
                    if buy_s > 0:
                        market_orders.append(["BUY_SEED", "STRAWBERRY", buy_s])
                        spendable_money -= buy_s * 100

            # Wheat maintenance (continuous feed + cash)
            if day <= 27:
                target_wheat = 28 if unlocked_quads >= 3 else (14 if unlocked_quads >= 2 else 6)
                desired_wheat = max(0, target_wheat - wheat_tiles - seeds.get("WHEAT", 0))
                if desired_wheat > 0 and spendable_money >= 10:
                    buy_w = min(desired_wheat, int(spendable_money // 10), 8)
                    if buy_w > 0:
                        market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                        spendable_money -= buy_w * 10

            # Paced Cow Purchases (At most 1 Cow per day, with strict feed & cash reserves)
            if day >= 6 and day <= 22:
                max_cows_target = 14 if unlocked_quads >= 3 else (5 if unlocked_quads >= 2 else 2)
                if total_cows < max_cows_target and spendable_money >= 400 + 800 and (wheat_tiles + wheat_in_shed) >= (total_cows + total_sheep + 4):
                    market_orders.append(["BUY_ANIMAL", "COW", 1])
                    spendable_money -= 400
                    total_cows += 1

            # Safety feed backup
            total_animals = total_cows + total_sheep
            if total_animals > 0 and wheat_in_shed < (total_animals + 2) and spendable_money >= 25:
                feed_needed = (total_animals + 2) - wheat_in_shed
                buy_feed = min(feed_needed, int(spendable_money // 25), 6)
                if buy_feed > 0:
                    market_orders.append(["BUY_PRODUCT", "WHEAT", buy_feed])
                    spendable_money -= buy_feed * 25
                    wheat_in_shed += buy_feed

    # 6. Global Task Queue
    tasks_watering_critical = []
    tasks_watering = []
    tasks_harvesting = []
    tasks_fertilizer = []
    tasks_caring = []
    tasks_feeding = []
    tasks_build_pasture = []
    tasks_place_animal = []
    tasks_digging = []
    tasks_planting = []

    held_animals = sum(u.get("COW", 0) + u.get("SHEEP", 0) for u in inventories)
    animals_need_homes = (cows_in_shed + sheep_in_shed + held_animals) - len(empty_pastures)
    if animals_need_homes > 0:
        for pos in PASTURE_RING:
            px, py = pos
            if farm["tiles"][py][px] is None and _is_owned(farm, px, py, board_size):
                tasks_build_pasture.append({"type": "BUILD_PASTURE", "pos": (px, py)})
                if len(tasks_build_pasture) >= animals_need_homes:
                    break

    for y in range(board_size):
        for x in range(board_size):
            tile = farm["tiles"][y][x]
            if tile == "LOCKED":
                continue

            if tile is None:
                if (x, y) not in [t["pos"] for t in tasks_build_pasture]:
                    if day < 28 and hour < 20:
                        tasks_planting.append({"type": "PLANT", "pos": (x, y)})
            elif isinstance(tile, dict):
                kind = tile.get("kind")
                if kind == "WEED":
                    tasks_digging.append({"type": "DIG", "pos": (x, y)})
                elif kind == "PASTURE":
                    if "animal" not in tile:
                        if cows_in_shed > 0 or sheep_in_shed > 0 or held_animals > 0:
                            tasks_place_animal.append({"type": "PLACE", "pos": (x, y)})
                    else:
                        if not tile.get("fed_today"):
                            tasks_feeding.append({"type": "FEED", "pos": (x, y)})
                        if tile.get("fertilizer_available"):
                            tasks_fertilizer.append({"type": "COLLECT_FERTILIZER", "pos": (x, y)})
                        if not tile.get("cared_today"):
                            tasks_caring.append({"type": "CARE", "pos": (x, y)})
                elif kind == "PLANT":
                    crop = tile.get("crop")
                    crop_data = CROPS.get(crop, {})
                    age = day - tile.get("planted_day", 0)
                    yield_units = tile.get("yield_units", 0)
                    watered = tile.get("watered_today", False)

                    if not watered:
                        if crop in ["STRAWBERRY", "MELON"] or tile.get("consecutive_unwatered", 0) >= 1:
                            tasks_watering_critical.append({"type": "WATER", "pos": (x, y)})
                        else:
                            tasks_watering.append({"type": "WATER", "pos": (x, y)})

                    if crop_data.get("ongoing", False):
                        if yield_units > 0:
                            tasks_harvesting.append({"type": "HARVEST", "pos": (x, y)})
                    else:
                        if age >= crop_data.get("max_yield_day", 4) or day >= 29:
                            tasks_harvesting.append({"type": "HARVEST", "pos": (x, y)})

    ordered_tasks = (
        tasks_watering_critical +
        tasks_watering +
        tasks_feeding +
        tasks_harvesting +
        tasks_fertilizer +
        tasks_caring +
        tasks_place_animal +
        tasks_build_pasture +
        tasks_digging +
        tasks_planting
    )

    all_units = [farm["farmer"]] + farm.get("hands", [])
    num_units = len(all_units)

    unit_actions = [None] * num_units
    assigned_tiles = set()
    local_seeds = dict(seeds)
    local_shed_wheat = shed.get("WHEAT", 0)
    local_cows_in_shed = shed.get("COW", 0)
    local_sheep_in_shed = shed.get("SHEEP", 0)
    unassigned_units = list(range(num_units))

    # Pass 1: Handle shed drop-offs & Morning Pickup
    for u_idx in list(unassigned_units):
        ux, uy = all_units[u_idx]
        u_inv = inventories[u_idx] if u_idx < len(inventories) else {}
        is_shed_adj = (ux, uy) in shed_tiles
        
        sellables = sum(qty for item, qty in u_inv.items() if item != "WHEAT" and item not in ANIMALS)
        if sellables > 0 and is_shed_adj:
            unit_actions[u_idx] = ["DROP"]
            unassigned_units.remove(u_idx)
            continue

        if is_shed_adj and u_inv.get("WHEAT", 0) == 0 and local_shed_wheat > 0 and len(tasks_feeding) > 0 and hour <= 8:
            pickup_qty = min(2, local_shed_wheat)
            unit_actions[u_idx] = ["PICKUP", "WHEAT", pickup_qty]
            local_shed_wheat -= pickup_qty
            unassigned_units.remove(u_idx)
            continue

        if sum(u_inv.values()) >= 4 and not is_shed_adj:
            closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
            mv = get_best_move((ux, uy), closest_shed, board_size)
            if mv:
                unit_actions[u_idx] = [mv]
                unassigned_units.remove(u_idx)
                continue

    # Pass 2: Assign tasks to closest units
    for task in ordered_tasks:
        if not unassigned_units:
            break
        tpos = task["pos"]
        if tpos in assigned_tiles:
            continue

        ttype = task["type"]
        best_u = None
        best_dist = 9999
        for u_idx in unassigned_units:
            dist = manhattan_dist(all_units[u_idx], tpos)
            if dist < best_dist:
                best_dist = dist
                best_u = u_idx

        if best_u is not None:
            ux, uy = all_units[best_u]
            u_inv = inventories[best_u] if best_u < len(inventories) else {}
            is_shed_adj = (ux, uy) in shed_tiles

            if ttype == "FEED":
                if u_inv.get("WHEAT", 0) > 0:
                    mv = get_best_move((ux, uy), tpos, board_size)
                    unit_actions[best_u] = [mv] if mv else ["FEED"]
                    assigned_tiles.add(tpos)
                    unassigned_units.remove(best_u)
                else:
                    if is_shed_adj and local_shed_wheat > 0:
                        pickup_qty = min(2, local_shed_wheat)
                        unit_actions[best_u] = ["PICKUP", "WHEAT", pickup_qty]
                        local_shed_wheat = max(0, local_shed_wheat - pickup_qty)
                    else:
                        closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
                        mv = get_best_move((ux, uy), closest_shed, board_size)
                        unit_actions[best_u] = [mv] if mv else ["PASS"]
                    unassigned_units.remove(best_u)

            elif ttype == "PLACE":
                anim_to_place = "COW" if (u_inv.get("COW", 0) > 0 or local_cows_in_shed > 0) else "SHEEP"
                if u_inv.get(anim_to_place, 0) > 0:
                    mv = get_best_move((ux, uy), tpos, board_size)
                    unit_actions[best_u] = [mv] if mv else ["PLACE", anim_to_place]
                    assigned_tiles.add(tpos)
                    unassigned_units.remove(best_u)
                else:
                    if is_shed_adj:
                        if local_cows_in_shed > 0:
                            unit_actions[best_u] = ["PICKUP", "COW", 1]
                            local_cows_in_shed -= 1
                        elif local_sheep_in_shed > 0:
                            unit_actions[best_u] = ["PICKUP", "SHEEP", 1]
                            local_sheep_in_shed -= 1
                        else:
                            unit_actions[best_u] = ["PASS"]
                    else:
                        closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
                        mv = get_best_move((ux, uy), closest_shed, board_size)
                        unit_actions[best_u] = [mv] if mv else ["PASS"]
                    unassigned_units.remove(best_u)

            elif ttype == "BUILD_PASTURE":
                mv = get_best_move((ux, uy), tpos, board_size)
                unit_actions[best_u] = [mv] if mv else ["BUILD_PASTURE"]
                assigned_tiles.add(tpos)
                unassigned_units.remove(best_u)

            elif ttype == "PLANT":
                mv = get_best_move((ux, uy), tpos, board_size)
                if mv:
                    unit_actions[best_u] = [mv]
                else:
                    if local_seeds.get("STRAWBERRY", 0) > 0 and day <= 12:
                        unit_actions[best_u] = ["PLANT", "STRAWBERRY"]
                        local_seeds["STRAWBERRY"] -= 1
                    elif local_seeds.get("MELON", 0) > 0 and day <= 8:
                        unit_actions[best_u] = ["PLANT", "MELON"]
                        local_seeds["MELON"] -= 1
                    elif local_seeds.get("WHEAT", 0) > 0 and day < 28:
                        unit_actions[best_u] = ["PLANT", "WHEAT"]
                        local_seeds["WHEAT"] -= 1
                    else:
                        unit_actions[best_u] = ["PASS"]
                assigned_tiles.add(tpos)
                unassigned_units.remove(best_u)

            else:
                mv = get_best_move((ux, uy), tpos, board_size)
                if mv:
                    unit_actions[best_u] = [mv]
                else:
                    unit_actions[best_u] = [ttype]
                assigned_tiles.add(tpos)
                unassigned_units.remove(best_u)

    # Pass 3: Idle units move towards shed
    for u_idx in unassigned_units:
        ux, uy = all_units[u_idx]
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
