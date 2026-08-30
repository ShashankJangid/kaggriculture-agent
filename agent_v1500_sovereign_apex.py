"""
Autonomous Industrial Farm Agent v1500 — Sovereign Apex
Author: Shashank Jangid

V1500 = V1000 + fix animal balance (6 Cows + 5 Sheep vs stuck 7 Cows + 2 Sheep).

ROOT CAUSE: V1000's sheep purchasing never fires because there's always 1 Cow
in the speculative pipeline. The "shed empty" check requires shed.COW==0, but
a cow bought speculatively sits in shed waiting for placement. By the time it's
placed and shed empties, num_cows has hit the limit (6) so sheep condition
never triggers.

FIX: Use committed counts (placed + in-shed):
  total_cows_committed  = n_cows  + shed.get("COW",  0)
  total_sheep_committed = n_sheep + shed.get("SHEEP", 0)

  Buy cow  when: shed empty AND total_cows_committed  < 6
  Buy sheep when: shed empty AND total_cows_committed >= 6 AND total_sheep_committed < 5

Result: 6 Cows + 5 Sheep = 11 animals (vs 7 Cows + 2 Sheep = 9)
Income: $480 milk/day + $333 wool/day = $813/day (+$120/day, +$1,800 over 15 days)
Sheep start Day 6 vs cow Day 8 → extra $667 early yield income
"""
from collections import defaultdict

CROPS = {
    "WHEAT":      {"seed": 10,  "max_yield_day": 4,  "ongoing": False},
    "STRAWBERRY": {"seed": 100, "max_yield_day": 10, "ongoing": True},
    "MELON":      {"seed": 80,  "max_yield_day": 12, "ongoing": False},
    "CARROT":     {"seed": 20,  "max_yield_day": 3,  "ongoing": False},
}
LAND_PRICES = [1000, 2000, 4000]


def shed_adj(bs=10):
    h = bs // 2
    return [(h-1,h-1),(h,h-1),(h-1,h),(h,h)]


def best_mv(c, t):
    if c == t: return None
    cx,cy=c; tx,ty=t; dx,dy=tx-cx,ty-cy
    moves=[]
    if dx>0:  moves.append(("EAST",  abs(dx)))
    elif dx<0:moves.append(("WEST",  abs(dx)))
    if dy>0:  moves.append(("SOUTH", abs(dy)))
    elif dy<0:moves.append(("NORTH", abs(dy)))
    moves.sort(key=lambda x:x[1],reverse=True)
    return moves[0][0] if moves else None


def md(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])


def agent(obs):
    player = obs.get("player",0)
    farms  = obs.get("farms",[])
    if not farms or player>=len(farms):
        return {"farmer":["PASS"],"hands":[],"market":[]}

    farm    = farms[player]
    private = obs.get("private",{}) or {}
    day     = obs.get("day",0)
    hour    = obs.get("hour",0)
    bs      = len(farm["tiles"])
    sheds   = shed_adj(bs)
    money   = farm.get("money",0)
    shed    = private.get("shed",{})  or {}
    seeds   = private.get("seeds",{}) or {}
    invs    = private.get("inventories",[{}]) or [{}]
    mkt     = []

    # ── 1. SELL ───────────────────────────────────────────────────────────────
    for item, qty in list(shed.items()):
        if qty > 0 and item in ("MILK","WOOL","EGG","FERTILIZER","MELON",
                                 "STRAWBERRY","CARROT","TOMATO"):
            mkt.append(["SELL", item, qty])
        elif qty > 12 and item == "WHEAT":
            mkt.append(["SELL", "WHEAT", qty-12])

    # ── 2. HIRE ───────────────────────────────────────────────────────────────
    quads    = len(farm.get("unlocked_quadrants",["NW"]))
    hired    = farm.get("hires_today",0)
    tgt_hire = (6 if day>=28 else 8 if day>=25 else
                5 if quads==1 else 7 if quads==2 else 10)
    if hired < tgt_hire and money >= 5:
        for _ in range(tgt_hire - hired):
            mkt.append(["HIRE"])

    spnd = max(0, money - 150)

    # ── 3. LAND (cap 3 quads) ─────────────────────────────────────────────────
    if quads < 3 and day <= 14:
        cost = LAND_PRICES[quads-1]
        buf  = 300 if day <= 7 else 500
        if spnd >= cost + buf:
            mkt.append(["BUY_LAND"]); spnd -= cost; money -= cost; quads += 1

    # ── 4. TILE SURVEY ────────────────────────────────────────────────────────
    pasture_pos=[]; animal_pos=[]; empty_past=[]; crop_ct=defaultdict(int)
    for y in range(bs):
        for x in range(bs):
            t = farm["tiles"][y][x]
            if t in ("LOCKED", None): continue
            if isinstance(t,dict):
                k = t.get("kind")
                if k == "PASTURE":
                    pasture_pos.append((x,y))
                    if "animal" in t: animal_pos.append((x,y,t["animal"],t))
                    else:             empty_past.append((x,y))
                elif k == "PLANT": crop_ct[t.get("crop")] += 1

    n_cows  = sum(1 for a in animal_pos if a[2]=="COW")
    n_sheep = sum(1 for a in animal_pos if a[2]=="SHEEP")
    n_anim  = len(animal_pos)

    PASTURE_SLOTS = [(4,4),(5,4),(4,5),(5,5),(4,3),(5,3),(3,4),(3,5),(4,6),(5,6),(6,4)]
    max_past = min(sum(1 for p in PASTURE_SLOTS
                       if farm["tiles"][p[1]][p[0]] != "LOCKED"), 11)

    # ── 5. PURCHASING ─────────────────────────────────────────────────────────
    if hour < 20:
        # ★ FIX: Use committed counts (placed + in-shed) to decide what to buy
        total_cows_c  = n_cows  + shed.get("COW",  0)
        total_sheep_c = n_sheep + shed.get("SHEEP", 0)
        shed_any      = shed.get("COW",0) + shed.get("SHEEP",0)

        # Day 0: 2 Cows + 2 Sheep immediately
        if day == 0 and hour == 0:
            if spnd >= 1800:
                mkt.append(["BUY_ANIMAL","COW",  2])
                mkt.append(["BUY_ANIMAL","SHEEP",2])
                spnd -= 1800
            if spnd >= 50:
                mkt.append(["BUY_PRODUCT","WHEAT",4]); spnd -= 50

        # ★ DEFINITIVE BALANCE GUARD:
        # shed must be fully empty (no pending placements) AND within purchase window
        elif day <= 12 and shed_any == 0:
            if total_cows_c < 6 and spnd >= 800:
                # Still need more cows
                mkt.append(["BUY_ANIMAL","COW",1]); spnd -= 400
            elif total_cows_c >= 6 and total_sheep_c < 5 and spnd >= 900:
                # Cows done → buy sheep to fill remaining pastures
                mkt.append(["BUY_ANIMAL","SHEEP",1]); spnd -= 500

        # Feed safety net
        if shed.get("WHEAT",0) < 4 and n_anim > 0 and spnd >= 50:
            mkt.append(["BUY_PRODUCT","WHEAT",4]); spnd -= 50

        # ── SEEDS (same as V1000) ─────────────────────────────────────────────
        if day <= 5:
            bm = min(max(0, 12 - crop_ct["MELON"]  - seeds.get("MELON",0)),  int(spnd//80),  6)
            if bm>0: mkt.append(["BUY_SEED","MELON",bm]);  spnd -= bm*80
            bw = min(max(0,  8 - crop_ct["WHEAT"]  - seeds.get("WHEAT",0)),  int(spnd//10),  8)
            if bw>0: mkt.append(["BUY_SEED","WHEAT",bw]);  spnd -= bw*10

        elif day <= 15:
            bs_ = min(max(0, 38 - crop_ct["STRAWBERRY"] - seeds.get("STRAWBERRY",0)), int(spnd//100), 10)
            if bs_>0: mkt.append(["BUY_SEED","STRAWBERRY",bs_]); spnd -= bs_*100
            bw  = min(max(0, 20 - crop_ct["WHEAT"] - seeds.get("WHEAT",0)), int(spnd//10), 10)
            if bw>0: mkt.append(["BUY_SEED","WHEAT",bw]);         spnd -= bw*10

        elif day <= 22:
            bw = min(max(0, 22 - crop_ct["WHEAT"] - seeds.get("WHEAT",0)), int(spnd//10), 10)
            if bw>0: mkt.append(["BUY_SEED","WHEAT",bw]); spnd -= bw*10

        elif day <= 27:
            bw = min(max(0, 40 - seeds.get("WHEAT",0)), int(spnd//10), 20)
            if bw>0: mkt.append(["BUY_SEED","WHEAT",bw]); spnd -= bw*10

    # ── 6. TASK QUEUE (identical to V1000) ────────────────────────────────────
    all_units = [farm["farmer"]] + farm.get("hands",[])
    N = len(all_units)
    t_anim=[]; t_harv=[]; t_water=[]; t_dig=[]; t_plant=[]; t_build=[]

    for px,py in PASTURE_SLOTS:
        t = farm["tiles"][py][px]
        if t == "LOCKED": continue
        if t is None and len(pasture_pos) < max_past:
            t_build.append({"type":"BUILD_PASTURE","pos":(px,py)})
        elif isinstance(t,dict) and t.get("kind")=="PASTURE":
            if "animal" in t:
                if not t.get("fed_today",False):         t_anim.append({"type":"FEED","pos":(px,py)})
                if not t.get("cared_today",False):        t_anim.append({"type":"CARE","pos":(px,py)})
                if t.get("yield_units",0)>0:              t_anim.append({"type":"HARVEST","pos":(px,py)})
                if t.get("fertilizer_available",False):   t_anim.append({"type":"COLLECT_FERTILIZER","pos":(px,py)})
            else:
                if shed.get("COW",0)>0 or shed.get("SHEEP",0)>0:
                    t_anim.append({"type":"PLACE_ANIMAL","pos":(px,py)})

    for y in range(bs):
        for x in range(bs):
            tile = farm["tiles"][y][x]
            if tile == "LOCKED": continue
            if tile is None:
                if (x,y) not in PASTURE_SLOTS and day<28 and hour<20:
                    t_plant.append({"type":"PLANT","pos":(x,y)})
            elif isinstance(tile,dict):
                k = tile.get("kind")
                if k == "WEED":
                    t_dig.append({"type":"DIG","pos":(x,y)})
                elif k == "PLANT":
                    crop    = tile.get("crop")
                    cd      = CROPS.get(crop,{})
                    age     = day - tile.get("planted_day",0)
                    yld     = tile.get("yield_units",0)
                    watered = tile.get("watered_today",False)
                    ripe    = (not cd.get("ongoing") and age>=cd.get("max_yield_day",4)) or day>=29
                    has_yld = cd.get("ongoing") and yld>0
                    if ripe or has_yld: t_harv.append({"type":"HARVEST","pos":(x,y)})
                    elif not watered:   t_water.append({"type":"WATER","pos":(x,y)})

    # V1000 original ordering: water before harvest
    ordered = t_anim + t_water + t_harv + t_dig + t_plant + t_build

    # ── 7. DISPATCH (identical to V1000) ─────────────────────────────────────
    acts=[None]*N; used=set(); lseed=dict(seeds); todo=list(range(N))

    def assign(u,a): acts[u]=a; todo.remove(u)

    for u in list(todo):
        ux,uy  = all_units[u]
        uinv   = invs[u] if u<len(invs) else {}
        utile  = farm["tiles"][uy][ux]
        is_sh  = (ux,uy) in sheds
        carry  = sum(uinv.values())

        sell = sum(uinv.get(p,0) for p in ("MILK","WOOL","EGG","FERTILIZER",
                                             "MELON","STRAWBERRY","CARROT","TOMATO"))
        if is_sh and (sell>0 or carry>=4 or (day>=28 and carry>0)):
            assign(u,["DROP"]); continue

        if utile not in (None,"LOCKED") and isinstance(utile,dict):
            k = utile.get("kind")
            if "animal" in utile:
                if utile.get("yield_units",0)>0:                  assign(u,["HARVEST"]); continue
                if uinv.get("WHEAT",0)>0 and not utile.get("fed_today",False): assign(u,["FEED"]); continue
                if not utile.get("cared_today",False):             assign(u,["CARE"]); continue
                if utile.get("fertilizer_available",False):        assign(u,["COLLECT_FERTILIZER"]); continue
            elif k=="PASTURE":
                if uinv.get("COW",0)>0:   assign(u,["PLACE","COW"]);  continue
                if uinv.get("SHEEP",0)>0: assign(u,["PLACE","SHEEP"]); continue
            elif k=="WEED":
                assign(u,["DIG"]); used.add((ux,uy)); continue
            elif k=="PLANT":
                crop=utile.get("crop"); cd=CROPS.get(crop,{})
                age=day-utile.get("planted_day",0)
                ripe=(not cd.get("ongoing") and age>=cd.get("max_yield_day",4)) or day>=29
                has_yld=cd.get("ongoing") and utile.get("yield_units",0)>0
                if ripe or has_yld: assign(u,["HARVEST"]); used.add((ux,uy)); continue
                elif not utile.get("watered_today",False): assign(u,["WATER"]); used.add((ux,uy)); continue

        elif utile is None and (ux,uy) not in used and hour<20:
            if (ux,uy) in PASTURE_SLOTS and len(pasture_pos)<max_past:
                assign(u,["BUILD_PASTURE"]); used.add((ux,uy)); continue
            elif lseed.get("MELON",0)>0 and day<=10:
                assign(u,["PLANT","MELON"]); lseed["MELON"]-=1; used.add((ux,uy)); continue
            elif lseed.get("STRAWBERRY",0)>0 and day<=15:
                assign(u,["PLANT","STRAWBERRY"]); lseed["STRAWBERRY"]-=1; used.add((ux,uy)); continue
            elif lseed.get("WHEAT",0)>0 and day<28:
                assign(u,["PLANT","WHEAT"]); lseed["WHEAT"]-=1; used.add((ux,uy)); continue

        if is_sh and uinv.get("WHEAT",0)==0 and shed.get("WHEAT",0)>0 and n_anim>0:
            assign(u,["PICKUP","WHEAT",min(2,shed.get("WHEAT",0))]); continue
        if is_sh and empty_past:
            if shed.get("COW",0)>0  and uinv.get("COW",0)==0:
                assign(u,["PICKUP","COW",1]);   continue
            if shed.get("SHEEP",0)>0 and uinv.get("SHEEP",0)==0:
                assign(u,["PICKUP","SHEEP",1]); continue
        if (carry>=4 or (day>=28 and carry>0)) and not is_sh:
            cs = min(sheds, key=lambda s: md((ux,uy),s))
            mv = best_mv((ux,uy), cs)
            if mv: assign(u,[mv]); continue

    for u in list(todo):
        ux,uy=all_units[u]
        bt,bd=None,999
        for task in ordered:
            if task["pos"] in used: continue
            d=md((ux,uy),task["pos"])
            if d<bd: bd=d; bt=task

        if bt:
            used.add(bt["pos"])
            mv=best_mv((ux,uy),bt["pos"])
            if mv:
                acts[u]=[mv]
            else:
                tp=bt["type"]
                if   tp=="BUILD_PASTURE":      acts[u]=["BUILD_PASTURE"]
                elif tp=="WATER":              acts[u]=["WATER"]
                elif tp=="HARVEST":            acts[u]=["HARVEST"]
                elif tp=="DIG":                acts[u]=["DIG"]
                elif tp=="FEED":               acts[u]=["FEED"]
                elif tp=="CARE":               acts[u]=["CARE"]
                elif tp=="COLLECT_FERTILIZER": acts[u]=["COLLECT_FERTILIZER"]
                elif tp=="PLANT":
                    if lseed.get("MELON",0)>0 and day<=10:
                        acts[u]=["PLANT","MELON"]; lseed["MELON"]-=1
                    elif lseed.get("STRAWBERRY",0)>0 and day<=15:
                        acts[u]=["PLANT","STRAWBERRY"]; lseed["STRAWBERRY"]-=1
                    elif lseed.get("WHEAT",0)>0 and day<28:
                        acts[u]=["PLANT","WHEAT"]; lseed["WHEAT"]-=1
                    else: acts[u]=["PASS"]
                else: acts[u]=["PASS"]
        else:
            if (ux,uy) not in sheds:
                cs=min(sheds,key=lambda s:md((ux,uy),s))
                mv=best_mv((ux,uy),cs)
                acts[u]=[mv] if mv else ["PASS"]
            else:
                acts[u]=["PASS"]
        todo.remove(u)

    return {"farmer": acts[0] if acts[0] else ["PASS"],
            "hands":  [a if a else ["PASS"] for a in acts[1:]],
            "market": mkt[:10]}
