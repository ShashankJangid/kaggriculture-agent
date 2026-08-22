import math
from collections import defaultdict

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

# Designate specific pasture coordinates around the shed (NW, NE, SW quadrants)
PASTURE_LOCATIONS = [
    (3, 3), (4, 3), (3, 4), (4, 4),  # NW adjacent ring
    (5, 3), (6, 3), (5, 4), (6, 4),  # NE adjacent ring
    (3, 5), (4, 5), (3, 6), (4, 6),  # SW adjacent ring
    (2, 3), (3, 2), (4, 2), (5, 2),  # Expanded ring
    (2, 4), (6, 2), (2, 5), (5, 5),
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

    # 1. Market Sales: Sell high value items smoothly; keep Wheat reserve for feed
    wheat_in_shed = shed.get("WHEAT", 0)
    for item, qty in list(shed.items()):
        if qty > 0:
            if item == "WHEAT":
                # Keep up to 25 Wheat for animal feed, sell the rest
                surplus = max(0, qty - 25)
                if surplus > 0:
                    market_orders.append(["SELL", "WHEAT", surplus])
            elif item in ["COW", "SHEEP", "GOOSE"]:
                # Animals in shed should not be sold; they will be placed
                continue
            else:
                market_orders.append(["SELL", item, qty])

    # 2. Hiring Strategy
    hires_today = farm.get("hires_today", 0)
    unlocked_quads = len(farm.get("unlocked_quadrants", ["NW"]))

    if day >= 29:
        target_hires = 8
    elif day >= 27:
        target_hires = 10
    elif unlocked_quads == 1:
        target_hires = 5 if day < 4 else 6
    elif unlocked_quads == 2:
        target_hires = 8
    else:
        target_hires = 12

    if hires_today < target_hires and money >= 5:
        to_hire = target_hires - hires_today
        for _ in range(to_hire):
            market_orders.append(["HIRE"])

    # 3. Progressive Land Expansion (75% land cap = 3 quadrants max)
    hiring_reserve = 150 if day < 28 else 0
    spendable_money = max(0, money - hiring_reserve)

    if unlocked_quads < 3 and day <= 18:
        next_cost = LAND_PRICES[unlocked_quads - 1]
        buffer = 400 if day == 0 else 600
        if spendable_money >= next_cost + buffer:
            market_orders.append(["BUY_LAND"])
            spendable_money -= next_cost
            money -= next_cost
            unlocked_quads += 1

    # 4. Count Farm State
    total_unlocked_tiles = unlocked_quads * 25
    melon_tiles = 0
    strawberry_tiles = 0
    wheat_tiles = 0
    carrot_tiles = 0
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
                    elif crop == "CARROT": carrot_tiles += 1

    cows_in_shed = shed.get("COW", 0)
    sheep_in_shed = shed.get("SHEEP", 0)
    total_cows = cow_count + cows_in_shed
    total_sheep = sheep_count + sheep_in_shed

    # 5. Market Purchases: Seed & Animal Acquisition
    if hour < 20:
        # Animal Purchasing
        if day == 0:
            if total_sheep < 1 and spendable_money >= 300:
                market_orders.append(["BUY_ANIMAL", "SHEEP"])
                spendable_money -= 300
                total_sheep += 1
            if total_cows < 1 and spendable_money >= 400:
                market_orders.append(["BUY_ANIMAL", "COW"])
                spendable_money -= 400
                total_cows += 1
        elif day >= 6 and day <= 20:
            # Scale Cows up to 15
            max_cows_target = 15 if unlocked_quads >= 3 else (8 if unlocked_quads >= 2 else 3)
            if total_cows < max_cows_target and spendable_money >= 400 + (300 if day < 12 else 100):
                market_orders.append(["BUY_ANIMAL", "COW"])
                spendable_money -= 400
                total_cows += 1

        # Feed emergency: if wheat in shed is critically low and we have animals
        if total_cows + total_sheep > 0 and wheat_in_shed < 10 and spendable_money >= 50:
            buy_feed = min(15, int(spendable_money // 30), 15 - wheat_in_shed)
            if buy_feed > 0:
                market_orders.append(["BUY_PRODUCT", "WHEAT", buy_feed])
                spendable_money -= buy_feed * 30
                wheat_in_shed += buy_feed

        # Crop Seeds Strategy
        if day == 0:
            # Opening: 8-10 Melons, 5-8 Wheat
            desired_melons = max(0, 10 - melon_tiles - seeds.get("MELON", 0))
            if desired_melons > 0 and spendable_money >= 80:
                buy_m = min(desired_melons, int(spendable_money // 80), 8)
                if buy_m > 0:
                    market_orders.append(["BUY_SEED", "MELON", buy_m])
                    spendable_money -= buy_m * 80

            desired_wheat = max(0, 8 - wheat_tiles - seeds.get("WHEAT", 0))
            if desired_wheat > 0 and spendable_money >= 10:
                buy_w = min(desired_wheat, int(spendable_money // 10), 8)
                if buy_w > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                    spendable_money -= buy_w * 10

        elif day <= 10:
            # Shift heavily into Strawberries (20-25) and Wheat (15-20)
            target_strawberries = 25 if unlocked_quads >= 2 else 12
            desired_strawberries = max(0, target_strawberries - strawberry_tiles - seeds.get("STRAWBERRY", 0))
            if desired_strawberries > 0 and spendable_money >= 100:
                buy_s = min(desired_strawberries, int(spendable_money // 100), 6)
                if buy_s > 0:
                    market_orders.append(["BUY_SEED", "STRAWBERRY", buy_s])
                    spendable_money -= buy_s * 100

            target_wheat = 20
            desired_wheat = max(0, target_wheat - wheat_tiles - seeds.get("WHEAT", 0))
            if desired_wheat > 0 and spendable_money >= 10:
                buy_w = min(desired_wheat, int(spendable_money // 10), 8)
                if buy_w > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                    spendable_money -= buy_w * 10

        elif day <= 24:
            # Maintain Wheat fields for animal feed + surplus cash
            target_wheat = 25
            desired_wheat = max(0, target_wheat - wheat_tiles - seeds.get("WHEAT", 0))
            if desired_wheat > 0 and spendable_money >= 10:
                buy_w = min(desired_wheat, int(spendable_money // 10), 10)
                if buy_w > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                    spendable_money -= buy_w * 10

    # 6. Global Task Queue Prioritization
    tasks_watering = []
    tasks_harvesting = []
    tasks_feeding = []
    tasks_caring = []
    tasks_fertilizer = []
    tasks_build_pasture = []
    tasks_place_animal = []
    tasks_digging = []
    tasks_planting = []

    # Check pasture builds needed
    animals_need_homes = (cows_in_shed + sheep_in_shed) - len(empty_pastures)
    if animals_need_homes > 0:
        for pos in PASTURE_LOCATIONS:
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
                        if cows_in_shed > 0 or sheep_in_shed > 0:
                            tasks_place_animal.append({"type": "PLACE", "pos": (x, y)})
                    else:
                        if not tile.get("fed_today"):
                            tasks_feeding.append({"type": "FEED", "pos": (x, y)})
                        if not tile.get("cared_today"):
                            tasks_caring.append({"type": "CARE", "pos": (x, y)})
                        if tile.get("fertilizer_available"):
                            tasks_fertilizer.append({"type": "COLLECT_FERTILIZER", "pos": (x, y)})
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

    ordered_tasks = (
        tasks_fertilizer +
        tasks_caring +
        tasks_feeding +
        tasks_watering +
        tasks_harvesting +
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

    # Pass 1: Handle units standing on shed access or ready for immediate action
    for u_idx in list(unassigned_units):
        ux, uy = all_units[u_idx]
        u_inv = inventories[u_idx] if u_idx < len(inventories) else {}
        is_shed_adj = (ux, uy) in shed_tiles
        
        # If carrying sellables/fertilizer/milk/wool -> Drop at shed
        sellable_items = sum(qty for item, qty in u_inv.items() if item != "WHEAT" and item not in ANIMALS)
        if sellable_items > 0 and is_shed_adj:
            unit_actions[u_idx] = ["DROP"]
            unassigned_units.remove(u_idx)
            continue

        # If holding high inventory in field -> Return to shed
        total_inv = sum(u_inv.values())
        if total_inv >= 4 and not is_shed_adj:
            closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
            mv = get_best_move((ux, uy), closest_shed, board_size)
            if mv:
                unit_actions[u_idx] = [mv]
                unassigned_units.remove(u_idx)
                continue

    # Pass 2: Assign tasks
    for task in ordered_tasks:
        if not unassigned_units:
            break
        tpos = task["pos"]
        if tpos in assigned_tiles:
            continue

        ttype = task["type"]
        
        # Find best unit for task
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
                    # Need wheat! Go to shed or pickup
                    if is_shed_adj and local_shed_wheat > 0:
                        pickup_qty = min(8, local_shed_wheat)
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
                    elif local_seeds.get("CARROT", 0) > 0 and day < 28:
                        unit_actions[best_u] = ["PLANT", "CARROT"]
                        local_seeds["CARROT"] -= 1
                    else:
                        unit_actions[best_u] = ["PASS"]
                assigned_tiles.add(tpos)
                unassigned_units.remove(best_u)

            else:
                # Direct action on tile: WATER, HARVEST, CARE, COLLECT_FERTILIZER, DIG
                mv = get_best_move((ux, uy), tpos, board_size)
                if mv:
                    unit_actions[best_u] = [mv]
                else:
                    unit_actions[best_u] = [ttype]
                assigned_tiles.add(tpos)
                unassigned_units.remove(best_u)

    # Pass 3: Remaining idle units return towards shed
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

def _is_owned(farm, x, y, board_size):
    # Check if quadrant is in unlocked_quadrants
    half = board_size // 2
    quad = "NW" if (x < half and y < half) else ("NE" if (x >= half and y < half) else ("SW" if (x < half and y >= half) else "SE"))
    return quad in farm.get("unlocked_quadrants", ["NW"])

