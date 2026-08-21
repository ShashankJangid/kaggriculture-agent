import math
from collections import defaultdict, deque

# ---------------------------------------------------------------------------
# 1. Economic Specifications & Asset Profiles
# ---------------------------------------------------------------------------
CROPS = {
    "WHEAT": {"seed": 10, "base_price": 25, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT": {"seed": 20, "base_price": 35, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "base_price": 60, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "base_price": 120, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "base_price": 250, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}

ANIMALS = {
    "COW": {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK", "base_price": 160},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL", "base_price": 200},
    "GOOSE": {"cost": 300, "structure": "COOP", "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG", "base_price": 50},
}

LAND_PRICES = [1000, 2000, 4000]
SEASON_DAYS = 30

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

# ---------------------------------------------------------------------------
# 2. Market Model & Shadow Price Profitability Engine
# ---------------------------------------------------------------------------
class MarketTracker:
    def __init__(self):
        self.history = defaultdict(list)

    def update(self, market_dict):
        prices = market_dict.get("prices", {})
        for item, p in prices.items():
            if p is not None:
                self.history[item].append(float(p))
                if len(self.history[item]) > 30:
                    self.history[item].pop(0)

    def current_price(self, item):
        h = self.history.get(item)
        if h:
            return h[-1]
        if item in CROPS:
            return CROPS[item]["base_price"]
        if item in ANIMALS:
            return ANIMALS[item]["base_price"]
        if item == "FERTILIZER":
            return 100
        return 25

    def moving_avg(self, item):
        h = self.history.get(item)
        if not h:
            return self.current_price(item)
        return sum(h) / len(h)

    def get_sell_fraction(self, item, day_remaining, shed_total_items):
        if day_remaining <= 2 or shed_total_items >= 65:
            return 1.0  # Force dump to prevent 100-cap discard or at season end
        cur = self.current_price(item)
        avg = self.moving_avg(item)
        if avg <= 0:
            return 0.5
        ratio = cur / avg
        if ratio >= 1.15:
            return 0.85  # Huge price surge -> sell 85%
        elif ratio >= 1.0:
            return 0.50  # Fair price -> sell 50%
        else:
            return 0.25  # Lower than average -> drip 25% for cashflow

MARKET_MODEL = MarketTracker()

def calculate_crop_profit_per_day(crop_name, day_remaining, live_price):
    info = CROPS[crop_name]
    seed_cost = info["seed"]
    first_yield = info["first_yield_day"]
    max_yield_day = info["max_yield_day"]
    ongoing = info["ongoing"]
    
    if first_yield > day_remaining:
        return -seed_cost / max(1, day_remaining)

    if ongoing:
        # Scheduled yields
        events = 0
        d = first_yield
        step = info["interval"] if info["interval"] > 0 else 1
        while d <= min(max_yield_day + 4, day_remaining):
            events += 1
            d += step
        total_units = events * 1.5  # average base + care
        revenue = total_units * live_price
        cycle_len = max(first_yield, min(day_remaining, max_yield_day + 4))
    else:
        # One time yield (Melon, Carrot, Wheat)
        expected_units = info["max_yield"]
        revenue = expected_units * live_price
        cycle_len = max_yield_day

    profit = revenue - seed_cost
    return profit / max(1, cycle_len)

# ---------------------------------------------------------------------------
# 3. High-Performance Spatial Assignment Algorithm (Fast Pure Python)
# ---------------------------------------------------------------------------
def assign_units_to_tasks(units, tasks, urgency_weight=0.75):
    """Bipartite spatial matching minimizing travel distance - urgency score."""
    if not units or not tasks:
        return {}

    unassigned_units = set(range(len(units)))
    assignments = {}
    
    # Sort tasks by urgency descending
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

# ---------------------------------------------------------------------------
# 4. Master Agent Decision Loop
# ---------------------------------------------------------------------------
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
    day_remaining = SEASON_DAYS - day

    money = farm.get("money", 0)
    shed = private.get("shed", {}) or {}
    seeds = private.get("seeds", {}) or {}
    inventories = private.get("inventories", [{}]) or [{}]

    # Update Market Price Tracker
    if "market" in obs:
        MARKET_MODEL.update(obs["market"])

    market_orders = []
    total_shed_items = sum(shed.values())

    # 1. Market Selling: Smart Drip & Surge Selling with Capacity Protection
    for item, qty in list(shed.items()):
        if qty > 0:
            frac = MARKET_MODEL.get_sell_fraction(item, day_remaining, total_shed_items)
            sell_qty = max(1, int(math.ceil(qty * frac)))
            sell_qty = min(qty, sell_qty)
            if sell_qty > 0:
                market_orders.append(["SELL", item, sell_qty])

    # 2. Maximum Labor Scaling (6 to 12 hands daily)
    hires_today = farm.get("hires_today", 0)
    unlocked_quads = len(farm.get("unlocked_quadrants", ["NW"]))

    if day >= 28:
        target_hires = 0
    elif day >= 25:
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

    # Guaranteed reserve to fund tomorrow morning's full workforce
    hiring_reserve = 150 if day < 25 else 0
    spendable_money = max(0, money - hiring_reserve)

    # 3. Fast Quadrant Expansion (NE on Day 0, SW Day 3-4, SE Day 6-8)
    if unlocked_quads < 4 and day <= 18:
        next_cost = LAND_PRICES[unlocked_quads - 1]
        buffer = 250 if day == 0 else 350
        if spendable_money >= next_cost + buffer:
            market_orders.append(["BUY_LAND"])
            spendable_money -= next_cost
            money -= next_cost
            unlocked_quads += 1

    # 4. Count Farm State (Pastures, Livestock, High-Value Crops)
    total_unlocked_tiles = unlocked_quads * 25
    pastures_count = 0
    animals_count = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    crop_counts = defaultdict(int)
    empty_unlocked_tiles = 0

    for y in range(board_size):
        for x in range(board_size):
            t = farm["tiles"][y][x]
            if t == "LOCKED":
                continue
            if t is None:
                empty_unlocked_tiles += 1
            elif isinstance(t, dict):
                kind = t.get("kind")
                if kind == "PASTURE":
                    pastures_count += 1
                    anim = t.get("animal")
                    if anim in animals_count:
                        animals_count[anim] += 1
                elif kind == "PLANT":
                    crop = t.get("crop")
                    if crop:
                        crop_counts[crop] += 1

    # 5. Strategic Investment in High-Ticket Assets
    # Livestock: Buy Cows (Milk @ $160-$320 + Daily Free Fertilizer) on Days 0-8
    target_cows = 4 if unlocked_quads >= 2 else 2
    cows_in_shed = shed.get("COW", 0)
    
    if day <= 8 and (animals_count["COW"] + cows_in_shed) < target_cows and spendable_money >= 500:
        market_orders.append(["BUY_ANIMAL", "COW", 1])
        spendable_money -= 400

    # Dynamic Crop Ranking based on Live Market Profit-per-Tile-Day
    crop_scores = []
    for c_name in CROPS:
        live_px = MARKET_MODEL.current_price(c_name)
        score = calculate_crop_profit_per_day(c_name, day_remaining, live_px)
        crop_scores.append((score, c_name))
    crop_scores.sort(reverse=True)
    best_high_value_crop = crop_scores[0][1] if crop_scores else "MELON"

    # Seed Purchasing (Only before hour 20 to guarantee same-day watering)
    if hour < 20:
        if day <= 18:
            # High-Ticket Melons ($1,500/tile)
            target_melons = max(16, int(total_unlocked_tiles * 0.45))
            desired_melons = max(0, target_melons - crop_counts["MELON"] - seeds.get("MELON", 0))
            if desired_melons > 0 and spendable_money >= 80:
                buy_m = min(desired_melons, int(spendable_money // 80), 8)
                if buy_m > 0:
                    market_orders.append(["BUY_SEED", "MELON", buy_m])
                    spendable_money -= buy_m * 80

            # High-Ticket Strawberries / Tomatoes ($960-$1920/tile)
            target_strawberries = max(8, int(total_unlocked_tiles * 0.20))
            desired_strawberries = max(0, target_strawberries - crop_counts["STRAWBERRY"] - seeds.get("STRAWBERRY", 0))
            if desired_strawberries > 0 and spendable_money >= 100:
                buy_s = min(desired_strawberries, int(spendable_money // 100), 6)
                if buy_s > 0:
                    market_orders.append(["BUY_SEED", "STRAWBERRY", buy_s])
                    spendable_money -= buy_s * 100

            # Rapid Cashflow Carrots
            target_carrots = max(15, int(total_unlocked_tiles * 0.25))
            desired_carrots = max(0, target_carrots - crop_counts["CARROT"] - seeds.get("CARROT", 0))
            if desired_carrots > 0 and spendable_money >= 20:
                buy_c = min(desired_carrots, int(spendable_money // 20), 10)
                if buy_c > 0:
                    market_orders.append(["BUY_SEED", "CARROT", buy_c])
                    spendable_money -= buy_c * 20

            # Wheat for animal feed & buffer
            if seeds.get("WHEAT", 0) < 15 and spendable_money >= 10:
                buy_w = min(15 - seeds.get("WHEAT", 0), int(spendable_money // 10), 10)
                if buy_w > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                    spendable_money -= buy_w * 10

        elif day <= 24:
            # Phase 2 (Days 19-24): Transition to Fast Turnaround Carrots & Wheat
            target_carrots = int(total_unlocked_tiles * 0.80)
            desired_carrots = max(0, target_carrots - crop_counts["CARROT"] - seeds.get("CARROT", 0))
            if desired_carrots > 0 and spendable_money >= 20:
                buy_c = min(desired_carrots, int(spendable_money // 20), 10)
                if buy_c > 0:
                    market_orders.append(["BUY_SEED", "CARROT", buy_c])
                    spendable_money -= buy_c * 20

            if seeds.get("WHEAT", 0) < 15 and spendable_money >= 10:
                buy_w = min(15 - seeds.get("WHEAT", 0), int(spendable_money // 10), 10)
                if buy_w > 0:
                    market_orders.append(["BUY_SEED", "WHEAT", buy_w])
                    spendable_money -= buy_w * 10

        elif day <= 27:
            # Phase 3 (Days 25-27): Final 3-Day Sprint (Carrots Only)
            desired_carrots = max(0, 25 - seeds.get("CARROT", 0))
            if desired_carrots > 0 and spendable_money >= 20:
                buy_c = min(desired_carrots, int(spendable_money // 20), 10)
                if buy_c > 0:
                    market_orders.append(["BUY_SEED", "CARROT", buy_c])
                    spendable_money -= buy_c * 20

    # 6. Global Prioritized Task Queue Formulation
    all_units = [farm["farmer"]] + farm.get("hands", [])
    num_units = len(all_units)
    tasks = []

    target_total_pastures = 4 if unlocked_quads >= 2 else 2

    for y in range(board_size):
        for x in range(board_size):
            tile = farm["tiles"][y][x]
            if tile == "LOCKED":
                continue

            if tile is None:
                # Build pastures in top corners early game
                if day <= 4 and pastures_count < target_total_pastures and (x >= 8 or y <= 1):
                    tasks.append({"type": "BUILD_PASTURE", "pos": (x, y), "urgency": 65})
                    pastures_count += 1
                elif day < 28 and hour < 20:
                    tasks.append({"type": "PLANT", "pos": (x, y), "urgency": 40})

            elif isinstance(tile, dict):
                kind = tile.get("kind")
                if kind == "WEED":
                    tasks.append({"type": "DIG", "pos": (x, y), "urgency": 55})
                elif kind == "PASTURE":
                    if "animal" in tile and tile["animal"] is not None:
                        # Animal Needs
                        if not tile.get("fed_today", False):
                            tasks.append({"type": "FEED", "pos": (x, y), "urgency": 100})
                        if tile.get("yield_units", 0) > 0:
                            tasks.append({"type": "HARVEST", "pos": (x, y), "urgency": 85})
                        if tile.get("fertilizer_available", False):
                            tasks.append({"type": "COLLECT_FERTILIZER", "pos": (x, y), "urgency": 70})
                    else:
                        tasks.append({"type": "PLACE_COW", "pos": (x, y), "urgency": 60})

                elif kind == "PLANT":
                    crop = tile.get("crop")
                    crop_data = CROPS.get(crop, {})
                    age = day - tile.get("planted_day", 0)
                    yield_units = tile.get("yield_units", 0)
                    watered = tile.get("watered_today", False)

                    # Top priority: guaranteed daily hydration
                    if not watered:
                        urgency_w = 95 if tile.get("consecutive_unwatered", 0) >= 1 else 90
                        tasks.append({"type": "WATER", "pos": (x, y), "urgency": urgency_w})

                    # High-value harvest
                    if crop_data.get("ongoing", False):
                        if yield_units > 0:
                            tasks.append({"type": "HARVEST", "pos": (x, y), "urgency": 80})
                    else:
                        if age >= crop_data.get("max_yield_day", 4) or day >= 29:
                            tasks.append({"type": "HARVEST", "pos": (x, y), "urgency": 85})

    # 7. Assignment & Routing
    unit_actions = [None] * num_units
    local_seeds = dict(seeds)
    unassigned_units = list(range(num_units))

    # Pass 1: Immediate Tile Actions & Shed Drop/Pickup
    for u_idx in list(unassigned_units):
        ux, uy = all_units[u_idx]
        u_inv = inventories[u_idx] if u_idx < len(inventories) else {}
        u_tile = farm["tiles"][uy][ux]
        is_shed_adj = (ux, uy) in shed_tiles

        # If carrying produce/fertilizer and standing adjacent to shed -> DROP
        has_produce = any(u_inv.get(k, 0) > 0 for k in ["EGG", "MILK", "WOOL", "FERTILIZER", "STRAWBERRY", "MELON", "CARROT"])
        if has_produce and is_shed_adj:
            unit_actions[u_idx] = ["DROP"]
            unassigned_units.remove(u_idx)
            continue

        # If carrying cow in inventory and standing on empty pasture -> PLACE
        if isinstance(u_tile, dict) and u_tile.get("kind") == "PASTURE" and "animal" not in u_tile:
            if u_inv.get("COW", 0) > 0:
                unit_actions[u_idx] = ["PLACE", "COW"]
                unassigned_units.remove(u_idx)
                continue

        # If adjacent to shed, pick up cow or wheat if needed
        if is_shed_adj:
            if shed.get("COW", 0) > 0 and u_inv.get("COW", 0) == 0:
                unit_actions[u_idx] = ["PICKUP", "COW", 1]
                unassigned_units.remove(u_idx)
                continue
            elif u_inv.get("WHEAT", 0) < 2 and shed.get("WHEAT", 0) > 0 and day < 28:
                take_w = min(2 - u_inv.get("WHEAT", 0), shed.get("WHEAT", 0))
                unit_actions[u_idx] = ["PICKUP", "WHEAT", take_w]
                unassigned_units.remove(u_idx)
                continue

        # Immediate Tile Execution
        curr_act = None
        if u_tile is not None and u_tile != "LOCKED" and isinstance(u_tile, dict):
            kind = u_tile.get("kind")
            if kind == "WEED":
                curr_act = ["DIG"]
            elif kind == "PASTURE":
                if "animal" in u_tile and u_tile["animal"] is not None:
                    if not u_tile.get("fed_today", False) and u_inv.get("WHEAT", 0) > 0:
                        curr_act = ["FEED"]
                    elif u_tile.get("yield_units", 0) > 0:
                        curr_act = ["HARVEST"]
                    elif u_tile.get("fertilizer_available", False):
                        curr_act = ["COLLECT_FERTILIZER"]
            elif kind == "PLANT":
                crop = u_tile.get("crop")
                crop_data = CROPS.get(crop, {})
                age = day - u_tile.get("planted_day", 0)
                yield_units = u_tile.get("yield_units", 0)
                watered = u_tile.get("watered_today", False)

                if not watered:
                    curr_act = ["WATER"]
                elif (crop_data.get("ongoing") and yield_units > 0) or (not crop_data.get("ongoing") and age >= crop_data.get("max_yield_day", 4)) or day >= 29:
                    curr_act = ["HARVEST"]

        elif u_tile is None and hour < 20:
            if day <= 4 and pastures_count < target_total_pastures and (ux >= 8 or uy <= 1):
                curr_act = ["BUILD_PASTURE"]
            elif local_seeds.get("MELON", 0) > 0 and day <= 18:
                curr_act = ["PLANT", "MELON"]
                local_seeds["MELON"] -= 1
            elif local_seeds.get("STRAWBERRY", 0) > 0 and day <= 18:
                curr_act = ["PLANT", "STRAWBERRY"]
                local_seeds["STRAWBERRY"] -= 1
            elif local_seeds.get("CARROT", 0) > 0 and day < 28:
                curr_act = ["PLANT", "CARROT"]
                local_seeds["CARROT"] -= 1
            elif local_seeds.get("WHEAT", 0) > 0 and day < 28:
                curr_act = ["PLANT", "WHEAT"]
                local_seeds["WHEAT"] -= 1

        if curr_act is not None:
            unit_actions[u_idx] = curr_act
            unassigned_units.remove(u_idx)
            continue

        # If carrying heavy goods, navigate to shed
        if sum(u_inv.values()) >= 4:
            closest_shed = min(shed_tiles, key=lambda s: manhattan_dist((ux, uy), s))
            mv = get_best_move((ux, uy), closest_shed, board_size)
            if mv:
                unit_actions[u_idx] = [mv]
                unassigned_units.remove(u_idx)
                continue

    # Pass 2: Global Spatial Matching
    remaining_units_list = [all_units[i] for i in unassigned_units]
    assignments = assign_units_to_tasks(remaining_units_list, tasks)

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
                elif ttype == "FEED":
                    if inventories[u_idx].get("WHEAT", 0) > 0:
                        unit_actions[u_idx] = ["FEED"]
                    else:
                        unit_actions[u_idx] = ["PASS"]
                elif ttype == "COLLECT_FERTILIZER":
                    unit_actions[u_idx] = ["COLLECT_FERTILIZER"]
                elif ttype == "DIG":
                    unit_actions[u_idx] = ["DIG"]
                elif ttype == "BUILD_PASTURE":
                    unit_actions[u_idx] = ["BUILD_PASTURE"]
                elif ttype == "PLANT":
                    if local_seeds.get("MELON", 0) > 0 and day <= 18:
                        unit_actions[u_idx] = ["PLANT", "MELON"]
                        local_seeds["MELON"] -= 1
                    elif local_seeds.get("STRAWBERRY", 0) > 0 and day <= 18:
                        unit_actions[u_idx] = ["PLANT", "STRAWBERRY"]
                        local_seeds["STRAWBERRY"] -= 1
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
