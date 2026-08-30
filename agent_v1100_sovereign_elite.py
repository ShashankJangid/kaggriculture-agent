"""
Autonomous Industrial Farm Agent v1100 — Sovereign Elite
Author: Shashank Jangid

Critical Fixes over v1000 (Bug Analysis on Seeds 42, 555, 777):
1. FIXED: Shed Animal Overflow — Animals were bought faster than pastures built,
   leaving 2-4 animals stranded in shed for 15+ days.
   → Now: Buy only 1 animal per day if pasture capacity is fully utilized first.
2. FIXED: Wheat Shed Accumulation — Up to 18 Wheat hoarded in shed while empty
   crop tiles sat idle because workers couldn't plant.
   → Now: Shed wheat cap set to 10. Workers plant wheat from seeds, not haul.
3. FIXED: Melon Harvest Lag — Melons sitting on tiles past Day 12 due to worker
   contention. → Harvest priority boosted above watering for overripe crops.
4. IMPROVED: Strawberry Ramp — Start seeding at Day 6 (not Day 9) to get 38
   tiles planted a full week earlier, compounding yields from Day 16 onwards.
5. IMPROVED: Endgame Wheat Sweep — All non-animal tiles seeded with Wheat on
   Days 23-27 for a final rapid harvest wave in the last 48 hours.
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
    return [(half-1, half-1), (half, half-1), (half-1, half), (half, half)]


def get_best_move(cur_pos, target_pos):
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
    return abs(p1[0]-p2[0]) + abs(p1[1]-p2[1])


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

    # ── 1. MARKET: Sell all products, cap wheat in shed at 10 ────────────────
    for item, qty in list(shed.items()):
        if qty > 0 and item in ("MILK", "WOOL", "EGG", "FERTILIZER", "MELON", "STRAWBERRY", "CARROT", "TOMATO"):
            market_orders.append(["SELL", item, qty])
        elif qty > 10 and item == "WHEAT":
            market_orders.append(["SELL", "WHEAT", qty - 10])

    # ── 2. HIRING ─────────────────────────────────────────────────────────────
    hires_today = farm.get("hires_today", 0)
    unlocked_quads = len(farm.get("unlocked_quadrants", ["NW"]))

    if day >= 28:   target_hires = 6
    elif day >= 25: target_hires = 8
    elif unlocked_quads == 1: target_hires = 5
    elif unlocked_quads == 2: target_hires = 7
    else:           target_hires = 10

    if hires_today < target_hires and money >= 5:
        for _ in range(target_hires - hires_today):
            market_orders.append(["HIRE"])

    spendable = max(0, money - 150)

    # ── 3. LAND (cap at 3 quadrants / 75 tiles) ──────────────────────────────
    if unlocked_quads < 3 and day <= 14:
        cost = LAND_PRICES[unlocked_quads - 1]
        buf  = 300 if day <= 7 else 500
        if spendable >= cost + buf:
            market_orders.append(["BUY_LAND"])
            spendable -= cost; money -= cost; unlocked_quads += 1

    # ── 4. TILE SURVEY ────────────────────────────────────────────────────────
    pasture_positions   = []
    animal_positions    = []
    empty_pasture_pos   = []
    crop_counts         = defaultdict(int)

    for y in range(board_size):
        for x in range(board_size):
            t = farm["tiles"][y][x]
            if t == "LOCKED" or t is None: continue
            if isinstance(t, dict):
                kind = t.get("kind")
                if kind == "PASTURE":
                    pasture_positions.append((x, y))
                    if "animal" in t: animal_positions.append((x, y, t["animal"], t))
                    else:             empty_pasture_pos.append((x, y))
                elif kind == "PLANT":
                    crop_counts[t.get("crop")] += 1

    num_animals = len(animal_positions)
    num_cows    = sum(1 for a in animal_positions if a[2] == "COW")
    num_sheep   = sum(1 for a in animal_positions if a[2] == "SHEEP")

    # 11 pastures tightly ringing the central shed
    designated_pastures = [
        (4,4),(5,4),(4,5),(5,5),
        (4,3),(5,3),(3,4),(3,5),
        (4,6),(5,6),(6,4),
    ]

    max_pastures = min(len([p for p in designated_pastures
                             if farm["tiles"][p[1]][p[0]] != "LOCKED"]), 11)

    # ── 5. PURCHASING ─────────────────────────────────────────────────────────
    if hour < 20:
        total_cows  = num_cows  + shed.get("COW",  0)
        total_sheep = num_sheep + shed.get("SHEEP", 0)
        total_animals_ordered = total_cows + total_sheep

        # Day 0: seed 2 Cows + 2 Sheep + wheat immediately
        if day == 0 and hour == 0:
            if spendable >= 1800:
                market_orders.append(["BUY_ANIMAL", "COW",   2])
                market_orders.append(["BUY_ANIMAL", "SHEEP", 2])
                spendable -= 1800
            if spendable >= 50:
                market_orders.append(["BUY_PRODUCT", "WHEAT", 4])
                spendable -= 50

        # FIX: ONLY buy when there is an EMPTY built pasture waiting + no animals in shed
        elif day <= 12 and shed.get("COW",0) == 0 and shed.get("SHEEP",0) == 0:
            has_empty_pasture = len(empty_pasture_pos) > 0
            if has_empty_pasture and spendable >= 800:
                if total_cows < 6:
                    market_orders.append(["BUY_ANIMAL", "COW", 1])
                    spendable -= 400
                elif total_sheep < 5 and spendable >= 900:
                    market_orders.append(["BUY_ANIMAL", "SHEEP", 1])
                    spendable -= 500

        # Feed safety net
        if shed.get("WHEAT",0) < 4 and num_animals > 0 and spendable >= 50:
            market_orders.append(["BUY_PRODUCT", "WHEAT", 4])
            spendable -= 50

        # ── SEEDS ──
        if day <= 5:
            # Opening: 12 Melons + 8 Wheat. No carrots.
            bm = min(max(0, 12 - crop_counts["MELON"] - seeds.get("MELON",0)),
                     int(spendable//80), 6)
            if bm > 0: market_orders.append(["BUY_SEED","MELON",bm]); spendable -= bm*80

            bw = min(max(0, 8 - crop_counts["WHEAT"] - seeds.get("WHEAT",0)),
                     int(spendable//10), 8)
            if bw > 0: market_orders.append(["BUY_SEED","WHEAT",bw]); spendable -= bw*10

        elif day <= 15:
            # FIX: Start strawberries EARLY from Day 6 (not 9)
            target_sb = 38
            bs = min(max(0, target_sb - crop_counts["STRAWBERRY"] - seeds.get("STRAWBERRY",0)),
                     int(spendable//100), 10)
            if bs > 0: market_orders.append(["BUY_SEED","STRAWBERRY",bs]); spendable -= bs*100

            # Wheat buffer for animals (target 20 on field, not in shed)
            bw = min(max(0, 20 - crop_counts["WHEAT"] - seeds.get("WHEAT",0)),
                     int(spendable//10), 10)
            if bw > 0: market_orders.append(["BUY_SEED","WHEAT",bw]); spendable -= bw*10

        elif day <= 22:
            bw = min(max(0, 22 - crop_counts["WHEAT"] - seeds.get("WHEAT",0)),
                     int(spendable//10), 10)
            if bw > 0: market_orders.append(["BUY_SEED","WHEAT",bw]); spendable -= bw*10

        elif day <= 27:
            # Endgame sweep: plant wheat on every empty tile for final harvest
            bw = min(max(0, 35 - seeds.get("WHEAT",0)),
                     int(spendable//10), 20)
            if bw > 0: market_orders.append(["BUY_SEED","WHEAT",bw]); spendable -= bw*10

    # ── 6. TASK GENERATION ────────────────────────────────────────────────────
    all_units = [farm["farmer"]] + farm.get("hands", [])
    num_units = len(all_units)

    tasks_animal = []
    tasks_water  = []
    tasks_harvest= []
    tasks_dig    = []
    tasks_plant  = []
    tasks_build  = []

    for px, py in designated_pastures:
        t = farm["tiles"][py][px]
        if t == "LOCKED": continue
        if t is None and len(pasture_positions) < max_pastures:
            tasks_build.append({"type":"BUILD_PASTURE","pos":(px,py)})
        elif isinstance(t, dict) and t.get("kind") == "PASTURE":
            if "animal" in t:
                if not t.get("fed_today",    False): tasks_animal.append({"type":"FEED",               "pos":(px,py)})
                if not t.get("cared_today",  False): tasks_animal.append({"type":"CARE",               "pos":(px,py)})
                if t.get("yield_units",  0)  > 0:   tasks_animal.append({"type":"HARVEST",             "pos":(px,py)})
                if t.get("fertilizer_available",False): tasks_animal.append({"type":"COLLECT_FERTILIZER","pos":(px,py)})
            else:
                if shed.get("COW",0) > 0 or shed.get("SHEEP",0) > 0:
                    tasks_animal.append({"type":"PLACE_ANIMAL","pos":(px,py)})

    for y in range(board_size):
        for x in range(board_size):
            tile = farm["tiles"][y][x]
            if tile == "LOCKED": continue
            if tile is None:
                if (x,y) not in designated_pastures and day < 28 and hour < 20:
                    tasks_plant.append({"type":"PLANT","pos":(x,y)})
            elif isinstance(tile, dict):
                kind = tile.get("kind")
                if kind == "WEED":
                    tasks_dig.append({"type":"DIG","pos":(x,y)})
                elif kind == "PLANT":
                    crop      = tile.get("crop")
                    crop_data = CROPS.get(crop, {})
                    age       = day - tile.get("planted_day", 0)
                    yld       = tile.get("yield_units", 0)
                    watered   = tile.get("watered_today", False)
                    is_ripe   = (not crop_data.get("ongoing") and age >= crop_data.get("max_yield_day", 4)) or day >= 29
                    has_yield = crop_data.get("ongoing") and yld > 0

                    # FIX: Harvest overripe / yielding crops BEFORE watering
                    if is_ripe or has_yield:
                        tasks_harvest.append({"type":"HARVEST","pos":(x,y)})
                    elif not watered:
                        tasks_water.append({"type":"WATER","pos":(x,y)})

    ordered_tasks = tasks_animal + tasks_harvest + tasks_water + tasks_dig + tasks_plant + tasks_build

    # ── 7. SPATIAL DISPATCHER ─────────────────────────────────────────────────
    unit_actions     = [None] * num_units
    assigned_tiles   = set()
    local_seeds      = dict(seeds)
    unassigned_units = list(range(num_units))

    for u_idx in list(unassigned_units):
        ux, uy   = all_units[u_idx]
        u_inv    = inventories[u_idx] if u_idx < len(inventories) else {}
        u_tile   = farm["tiles"][uy][ux]
        is_shed  = (ux, uy) in shed_tiles
        carrying = sum(u_inv.values())

        sellable = sum(u_inv.get(p,0) for p in ("MILK","WOOL","EGG","FERTILIZER","MELON","STRAWBERRY","CARROT","TOMATO"))
        if is_shed and (sellable > 0 or carrying >= 4 or (day >= 28 and carrying > 0)):
            unit_actions[u_idx] = ["DROP"]; unassigned_units.remove(u_idx); continue

        if u_tile not in (None, "LOCKED") and isinstance(u_tile, dict):
            kind = u_tile.get("kind")
            if "animal" in u_tile:
                if u_tile.get("yield_units",0) > 0:
                    unit_actions[u_idx] = ["HARVEST"]; unassigned_units.remove(u_idx); continue
                if u_inv.get("WHEAT",0) > 0 and not u_tile.get("fed_today",False):
                    unit_actions[u_idx] = ["FEED"];    unassigned_units.remove(u_idx); continue
                if not u_tile.get("cared_today",False):
                    unit_actions[u_idx] = ["CARE"];    unassigned_units.remove(u_idx); continue
                if u_tile.get("fertilizer_available",False):
                    unit_actions[u_idx] = ["COLLECT_FERTILIZER"]; unassigned_units.remove(u_idx); continue
            elif kind == "PASTURE":
                if u_inv.get("COW",0)  > 0: unit_actions[u_idx] = ["PLACE","COW"];  unassigned_units.remove(u_idx); continue
                if u_inv.get("SHEEP",0)> 0: unit_actions[u_idx] = ["PLACE","SHEEP"];unassigned_units.remove(u_idx); continue
            elif kind == "WEED":
                unit_actions[u_idx] = ["DIG"]; assigned_tiles.add((ux,uy)); unassigned_units.remove(u_idx); continue
            elif kind == "PLANT":
                crop      = u_tile.get("crop")
                crop_data = CROPS.get(crop, {})
                age       = day - u_tile.get("planted_day", 0)
                yld       = u_tile.get("yield_units", 0)
                watered   = u_tile.get("watered_today", False)
                is_ripe   = (not crop_data.get("ongoing") and age >= crop_data.get("max_yield_day",4)) or day >= 29
                has_yield = crop_data.get("ongoing") and yld > 0
                if is_ripe or has_yield:
                    unit_actions[u_idx] = ["HARVEST"]; assigned_tiles.add((ux,uy)); unassigned_units.remove(u_idx); continue
                elif not watered:
                    unit_actions[u_idx] = ["WATER"];   assigned_tiles.add((ux,uy)); unassigned_units.remove(u_idx); continue

        elif u_tile is None and (ux,uy) not in assigned_tiles and hour < 20:
            if (ux,uy) in designated_pastures and len(pasture_positions) < max_pastures:
                unit_actions[u_idx] = ["BUILD_PASTURE"]; assigned_tiles.add((ux,uy)); unassigned_units.remove(u_idx); continue
            elif local_seeds.get("MELON",0) > 0 and day <= 10:
                unit_actions[u_idx] = ["PLANT","MELON"]; local_seeds["MELON"] -= 1; assigned_tiles.add((ux,uy)); unassigned_units.remove(u_idx); continue
            elif local_seeds.get("STRAWBERRY",0) > 0 and day <= 15:
                unit_actions[u_idx] = ["PLANT","STRAWBERRY"]; local_seeds["STRAWBERRY"] -= 1; assigned_tiles.add((ux,uy)); unassigned_units.remove(u_idx); continue
            elif local_seeds.get("WHEAT",0) > 0 and day < 28:
                unit_actions[u_idx] = ["PLANT","WHEAT"]; local_seeds["WHEAT"] -= 1; assigned_tiles.add((ux,uy)); unassigned_units.remove(u_idx); continue

        if is_shed and u_inv.get("WHEAT",0) == 0 and shed.get("WHEAT",0) > 0 and num_animals > 0:
            unit_actions[u_idx] = ["PICKUP","WHEAT", min(2, shed.get("WHEAT",0))]; unassigned_units.remove(u_idx); continue

        if is_shed and len(empty_pasture_pos) > 0:
            if shed.get("COW",0) > 0 and u_inv.get("COW",0) == 0:
                unit_actions[u_idx] = ["PICKUP","COW",1]; unassigned_units.remove(u_idx); continue
            if shed.get("SHEEP",0) > 0 and u_inv.get("SHEEP",0) == 0:
                unit_actions[u_idx] = ["PICKUP","SHEEP",1]; unassigned_units.remove(u_idx); continue

        if (carrying >= 4 or (day >= 28 and carrying > 0)) and not is_shed:
            cs = min(shed_tiles, key=lambda s: manhattan_dist((ux,uy), s))
            mv = get_best_move((ux,uy), cs)
            if mv: unit_actions[u_idx] = [mv]; unassigned_units.remove(u_idx); continue

    # Pass 2: Spatial auction
    for u_idx in list(unassigned_units):
        ux, uy = all_units[u_idx]
        best, best_d = None, 999
        for task in ordered_tasks:
            if task["pos"] in assigned_tiles: continue
            d = manhattan_dist((ux,uy), task["pos"])
            if d < best_d: best_d = d; best = task

        if best:
            assigned_tiles.add(best["pos"])
            mv = get_best_move((ux,uy), best["pos"])
            if mv:
                unit_actions[u_idx] = [mv]
            else:
                t = best["type"]
                if t == "BUILD_PASTURE":      unit_actions[u_idx] = ["BUILD_PASTURE"]
                elif t == "WATER":            unit_actions[u_idx] = ["WATER"]
                elif t == "HARVEST":          unit_actions[u_idx] = ["HARVEST"]
                elif t == "DIG":              unit_actions[u_idx] = ["DIG"]
                elif t == "FEED":             unit_actions[u_idx] = ["FEED"]
                elif t == "CARE":             unit_actions[u_idx] = ["CARE"]
                elif t == "COLLECT_FERTILIZER": unit_actions[u_idx] = ["COLLECT_FERTILIZER"]
                elif t == "PLANT":
                    if local_seeds.get("MELON",0) > 0 and day <= 10:
                        unit_actions[u_idx] = ["PLANT","MELON"]; local_seeds["MELON"] -= 1
                    elif local_seeds.get("STRAWBERRY",0) > 0 and day <= 15:
                        unit_actions[u_idx] = ["PLANT","STRAWBERRY"]; local_seeds["STRAWBERRY"] -= 1
                    elif local_seeds.get("WHEAT",0) > 0 and day < 28:
                        unit_actions[u_idx] = ["PLANT","WHEAT"]; local_seeds["WHEAT"] -= 1
                    else: unit_actions[u_idx] = ["PASS"]
                else: unit_actions[u_idx] = ["PASS"]
        else:
            is_shed = (ux,uy) in shed_tiles
            if not is_shed:
                cs = min(shed_tiles, key=lambda s: manhattan_dist((ux,uy), s))
                mv = get_best_move((ux,uy), cs)
                unit_actions[u_idx] = [mv] if mv else ["PASS"]
            else:
                unit_actions[u_idx] = ["PASS"]
        unassigned_units.remove(u_idx)

    farmer_action = unit_actions[0] if unit_actions[0] else ["PASS"]
    hands_actions = [a if a else ["PASS"] for a in unit_actions[1:]]
    return {"farmer": farmer_action, "hands": hands_actions, "market": market_orders[:10]}
