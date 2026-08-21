import math

CROPS = {
    "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT": {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}

ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP", "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW": {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
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

    # 1. Continuous Market Selling: Sell all produced goods (keep 10 wheat in shed for animal feeding)
    wheat_in_shed = shed.get("WHEAT", 0)
    wheat_needed_for_animals = 8 if day < 28 else 0
    wheat_to_sell = max(0, wheat_in_shed - wheat_needed_for_animals)

    for item, qty in list(shed.items()):
        if item == "WHEAT":
            if wheat_to_sell > 0:
                market_orders.append(["SELL", "WHEAT", wheat_to_sell])
        elif qty > 0:
            market_orders.append(["SELL", item, qty])

    # 2. Quadrant Expansion: Unlock NE on Day 0, SW and SE when cash allows
    unlocked_quads = len(farm.get("unlocked_quadrants", ["NW"]))
    if unlocked_quads < 4:
        next_cost = LAND_PRICES[unlocked_quads - 1]
        buffer = 300 if day == 0 else 500
        if money >= next_cost + buffer and day <= 20:
            market_orders.append(["BUY_LAND"])
            money -= next_cost
            unlocked_quads += 1

    # 3. Dynamic Labor Scaling: Hire farm hands every morning
    hires_today = farm.get("hires_today", 0)
    if day >= 28:
        target_hires = 0
    elif day >= 25:
        target_hires = 4
    elif day < 4:
        target_hires = 6 if unlocked_quads >= 2 else 4
    else:
        if money < 200:
            target_hires = 4
        elif money < 600:
            target_hires = 6
        elif money < 1500:
            target_hires = 8
        else:
            target_hires = 10 if unlocked_quads >= 3 else 8

    if hour == 0 and hires_today < target_hires and money >= 40:
        for _ in range(target_hires - hires_today):
            market_orders.append(["HIRE"])

    # 4. Count Farm State (Pastures, Coops, Animals, Plants)
    pastures_count = 0
    animals_count = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    empty_pastures = 0
    strawberries_count = 0
    wheat_count = 0
    melon_count = 0
    empty_tiles = 0

    for y in range(board_size):
        for x in range(board_size):
            t = farm["tiles"][y][x]
            if t == "LOCKED":
                continue
            if t is None:
                empty_tiles += 1
            elif isinstance(t, dict):
                kind = t.get("kind")
                if kind == "PASTURE":
                    pastures_count += 1
                    anim = t.get("animal")
                    if anim in animals_count:
                        animals_count[anim] += 1
                    else:
                        empty_pastures += 1
                elif kind == "PLANT":
                    crop = t.get("crop")
                    if crop == "STRAWBERRY":
                        strawberries_count += 1
                    elif crop == "WHEAT":
                        wheat_count += 1
                    elif crop == "MELON":
                        melon_count += 1

    # 5. Strategic Purchasing: Animals & High-Value Crops
    town_shops = obs.get("town", {}).get("unlocked_shops", [])
    pet_cafes = town_shops.count("PET_CAFE")

    # Day 0-14: Buy Cows and Sheep if we have empty pastures or shed capacity
    target_cows = 6 if unlocked_quads >= 2 else 3
    target_sheep = 4 if unlocked_quads >= 2 else 2
    cows_in_shed = shed.get("COW", 0)
    sheep_in_shed = shed.get("SHEEP", 0)

    if day <= 14:
        if (animals_count["COW"] + cows_in_shed) < target_cows and money >= 500:
            market_orders.append(["BUY_ANIMAL", "COW", 1])
            money -= 400
        elif (animals_count["SHEEP"] + sheep_in_shed) < target_sheep and money >= 600:
            market_orders.append(["BUY_ANIMAL", "SHEEP", 1])
            money -= 500

    # Crop Seeds: Wheat (to feed animals), Strawberries (multiharvest cash cow), Melons, Carrots
    if day <= 18:
        # High value Strawberries & Melons
        target_strawberries = 14 if unlocked_quads >= 2 else 6
        desired_strawberries = max(0, target_strawberries - strawberries_count - seeds.get("STRAWBERRY", 0))
        if desired_strawberries > 0 and money >= 100:
            buy_s = min(desired_strawberries, int(money // 100), 6)
            if buy_s > 0:
                market_orders.append(["BUY_SEED", "STRAWBERRY", buy_s])
                money -= buy_s * 100

        target_melons = 10 if unlocked_quads >= 2 else 4
        desired_melons = max(0, target_melons - melon_count - seeds.get("MELON", 0))
        if desired_melons > 0 and money >= 80:
            buy_m = min(desired_melons, int(money // 80), 6)
            if buy_m > 0:
                market_orders.append(["BUY_SEED", "MELON", buy_m])
                money -= buy_m * 80

        # Wheat for feed
        if seeds.get("WHEAT", 0) < 15 and money >= 10:
            buy_w = min(15 - seeds.get("WHEAT", 0), int(money // 10), 10)
            if buy_w > 0:
                market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                money -= buy_w * 10

        # Carrots for immediate liquidity
        if seeds.get("CARROT", 0) < 15 and money >= 20:
            buy_c = min(15 - seeds.get("CARROT", 0), int(money // 20), 10)
            if buy_c > 0:
                market_orders.append(["BUY_SEED", "CARROT", buy_c])
                money -= buy_c * 20

    elif day <= 24:
        # Mid-Late: Fast Carrots + Wheat
        target_c = 25 + (pet_cafes * 15)
        if seeds.get("CARROT", 0) < target_c and money >= 20:
            buy_c = min(target_c - seeds.get("CARROT", 0), int(money // 20), 10)
            if buy_c > 0:
                market_orders.append(["BUY_SEED", "CARROT", buy_c])
                money -= buy_c * 20
        if seeds.get("WHEAT", 0) < 15 and money >= 10:
            buy_w = min(15 - seeds.get("WHEAT", 0), int(money // 10), 10)
            if buy_w > 0:
                market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                money -= buy_w * 10

    elif day <= 27:
        # Late Sprint: Carrots only
        if seeds.get("CARROT", 0) < 20 and money >= 20:
            buy_c = min(20 - seeds.get("CARROT", 0), int(money // 20), 10)
            if buy_c > 0:
                market_orders.append(["BUY_SEED", "CARROT", buy_c])
                money -= buy_c * 20

    # 6. Task Generation & Priority Queue
    all_units = [farm["farmer"]] + farm.get("hands", [])
    num_units = len(all_units)

    tasks = []
    # Priority:
    # 0: FEED unfed animals (Prevents escape!)
    # 1: WATER unwatered plants (Prevents weeds!)
    # 2: HARVEST ripe plants & animal products (Milk/Wool/Eggs/Strawberries/Melons)
    # 3: COLLECT_FERTILIZER from animals
    # 4: PLACE animal from inventory onto pasture
    # 5: DIG weeds
    # 6: BUILD_PASTURE (if we need more pastures early game)
    # 7: PLANT empty tiles

    target_total_pastures = 10 if unlocked_quads >= 2 else 5

    for y in range(board_size):
        for x in range(board_size):
            tile = farm["tiles"][y][x]
            if tile == "LOCKED":
                continue

            if tile is None:
                # Decide what to build/plant on empty tile
                if day <= 6 and pastures_count < target_total_pastures and (x >= 5 or y < 5):
                    tasks.append({"type": "BUILD_PASTURE", "pos": (x, y), "prio": 5})
                    pastures_count += 1
                elif day < 28:
                    tasks.append({"type": "PLANT", "pos": (x, y), "prio": 7})

            elif isinstance(tile, dict):
                kind = tile.get("kind")
                if kind == "WEED":
                    tasks.append({"type": "DIG", "pos": (x, y), "prio": 4})
                elif kind == "PASTURE":
                    if "animal" in tile and tile["animal"] is not None:
                        # Animal tasks
                        if not tile.get("fed_today", False):
                            tasks.append({"type": "FEED", "pos": (x, y), "prio": 0})
                        if tile.get("yield_units", 0) > 0:
                            tasks.append({"type": "HARVEST", "pos": (x, y), "prio": 2})
                        if tile.get("fertilizer_available", False):
                            tasks.append({"type": "COLLECT_FERTILIZER", "pos": (x, y), "prio": 3})
                    else:
                        # Empty pasture waiting for animal placement
                        tasks.append({"type": "PLACE_ANIMAL", "pos": (x, y), "prio": 4})
                elif kind == "PLANT":
                    crop = tile.get("crop")
                    crop_data = CROPS.get(crop, {})
                    age = day - tile.get("planted_day", 0)
                    yield_units = tile.get("yield_units", 0)
                    watered = tile.get("watered_today", False)

                    if not watered:
                        tasks.append({"type": "WATER", "pos": (x, y), "prio": 1})

                    if crop_data.get("ongoing", False):
                        if yield_units > 0:
                            tasks.append({"type": "HARVEST", "pos": (x, y), "prio": 2})
                    else:
                        if age >= crop_data.get("max_yield_day", 4) or day >= 29:
                            tasks.append({"type": "HARVEST", "pos": (x, y), "prio": 2})

    tasks.sort(key=lambda t: t["prio"])

    # Worker Units Assignment
    unit_actions = []
    assigned_tiles = set()
    local_seeds = dict(seeds)

    for idx, unit_pos in enumerate(all_units):
        ux, uy = unit_pos
        u_inv = inventories[idx] if idx < len(inventories) else {}
        u_tile = farm["tiles"][uy][ux]
        is_shed_adj = (ux, uy) in shed_tiles

        # If carrying produce/fertilizer and near shed -> DROP
        has_produce = any(u_inv.get(k, 0) > 0 for k in ["EGG", "MILK", "WOOL", "FERTILIZER", "STRAWBERRY", "MELON", "CARROT"])
        if has_produce and is_shed_adj:
            unit_actions.append(["DROP"])
            continue

        # If carrying animal in inventory and on empty pasture -> PLACE
        if isinstance(u_tile, dict) and u_tile.get("kind") == "PASTURE" and "animal" not in u_tile:
            if u_inv.get("COW", 0) > 0:
                unit_actions.append(["PLACE", "COW"])
                continue
            elif u_inv.get("SHEEP", 0) > 0:
                unit_actions.append(["PLACE", "SHEEP"])
                continue

        # If near shed and shed has animals but unit has none -> PICKUP animal
        if is_shed_adj:
            if shed.get("COW", 0) > 0 and u_inv.get("COW", 0) == 0:
                unit_actions.append(["PICKUP", "COW", 1])
                continue
            elif shed.get("SHEEP", 0) > 0 and u_inv.get("SHEEP", 0) == 0:
                unit_actions.append(["PICKUP", "SHEEP", 1])
                continue
            elif u_inv.get("WHEAT", 0) < 3 and shed.get("WHEAT", 0) > 0 and day < 28:
                # Pick up wheat to feed animals
                take_w = min(3 - u_inv.get("WHEAT", 0), shed.get("WHEAT", 0))
                unit_actions.append(["PICKUP", "WHEAT", take_w])
                continue

        # Immediate Tile Action on Current Tile
        curr_action = None
        if u_tile is not None and u_tile != "LOCKED" and isinstance(u_tile, dict):
            kind = u_tile.get("kind")
            if kind == "WEED":
                curr_action = ["DIG"]
            elif kind == "PASTURE":
                if "animal" in u_tile and u_tile["animal"] is not None:
                    if not u_tile.get("fed_today", False) and u_inv.get("WHEAT", 0) > 0:
                        curr_action = ["FEED"]
                    elif u_tile.get("yield_units", 0) > 0:
                        curr_action = ["HARVEST"]
                    elif u_tile.get("fertilizer_available", False):
                        curr_action = ["COLLECT_FERTILIZER"]
            elif kind == "PLANT":
                crop = u_tile.get("crop")
                crop_data = CROPS.get(crop, {})
                age = day - u_tile.get("planted_day", 0)
                yield_units = u_tile.get("yield_units", 0)
                watered = u_tile.get("watered_today", False)

                if not watered:
                    curr_action = ["WATER"]
                elif (crop_data.get("ongoing") and yield_units > 0) or (not crop_data.get("ongoing") and age >= crop_data.get("max_yield_day", 4)) or day >= 29:
                    curr_action = ["HARVEST"]

        elif u_tile is None:
            # Plant on empty tile
            if day <= 6 and pastures_count < target_total_pastures and (ux >= 5 or uy < 5):
                curr_action = ["BUILD_PASTURE"]
            elif local_seeds.get("STRAWBERRY", 0) > 0 and day <= 18:
                curr_action = ["PLANT", "STRAWBERRY"]
                local_seeds["STRAWBERRY"] -= 1
            elif local_seeds.get("MELON", 0) > 0 and day <= 18:
                curr_action = ["PLANT", "MELON"]
                local_seeds["MELON"] -= 1
            elif local_seeds.get("WHEAT", 0) > 0 and day < 28:
                curr_action = ["PLANT", "WHEAT"]
                local_seeds["WHEAT"] -= 1
            elif local_seeds.get("CARROT", 0) > 0 and day < 28:
                curr_action = ["PLANT", "CARROT"]
                local_seeds["CARROT"] -= 1

        if curr_action is not None:
            unit_actions.append(curr_action)
            assigned_tiles.add((ux, uy))
            continue

        # If carrying heavy goods and not near shed, move to shed
        if sum(u_inv.values()) >= 4:
            closest_shed = min(shed_tiles, key=lambda s: abs(s[0] - ux) + abs(s[1] - uy))
            mv = get_best_move((ux, uy), closest_shed, board_size)
            if mv:
                unit_actions.append([mv])
                continue

        # Select Best Task from Queue
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
                ttype = best_task["type"]
                if ttype == "WATER":
                    unit_actions.append(["WATER"])
                elif ttype == "HARVEST":
                    unit_actions.append(["HARVEST"])
                elif ttype == "FEED":
                    if u_inv.get("WHEAT", 0) > 0:
                        unit_actions.append(["FEED"])
                    else:
                        unit_actions.append(["PASS"])
                elif ttype == "COLLECT_FERTILIZER":
                    unit_actions.append(["COLLECT_FERTILIZER"])
                elif ttype == "DIG":
                    unit_actions.append(["DIG"])
                elif ttype == "BUILD_PASTURE":
                    unit_actions.append(["BUILD_PASTURE"])
                elif ttype == "PLANT":
                    if local_seeds.get("STRAWBERRY", 0) > 0 and day <= 18:
                        unit_actions.append(["PLANT", "STRAWBERRY"])
                        local_seeds["STRAWBERRY"] -= 1
                    elif local_seeds.get("MELON", 0) > 0 and day <= 18:
                        unit_actions.append(["PLANT", "MELON"])
                        local_seeds["MELON"] -= 1
                    elif local_seeds.get("WHEAT", 0) > 0 and day < 28:
                        unit_actions.append(["PLANT", "WHEAT"])
                        local_seeds["WHEAT"] -= 1
                    elif local_seeds.get("CARROT", 0) > 0 and day < 28:
                        unit_actions.append(["PLANT", "CARROT"])
                        local_seeds["CARROT"] -= 1
                    else:
                        unit_actions.append(["PASS"])
                else:
                    unit_actions.append(["PASS"])
        else:
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
