"""
Autonomous Industrial Farm Agent v1100b — Sovereign Elite (Precision Tuned)
Author: Shashank Jangid

Surgical fixes over V1000 only — avoids regressions from V1100:

ROOT CAUSE ANALYSIS:
- V1100 Seed 999 (-$22k): 5 Sheep stranded in shed from Day 13 onward. The strict
  "empty_pasture_pos > 0" guard fires AFTER animals are delivered, leaving SHEEP
  sitting in shed because all 9 pasture slots were Cow-filled. Fix: raise Sheep cap
  and allow shed to hold at most 1 unplaced animal at a time.
- V1100 Seed 777 (-$13k): Same pattern — 1 Sheep stuck in shed Day 7-29.
- V1000 Seed 42 (-$30k vs target): COW:1 in shed from Day 9-29 because max_pastures
  was exceeded. Fix: match animal orders strictly to built pasture count.

PRECISE CHANGES FROM V1000:
1. Animal buy guard: only buy if (total_animals_deployed + shed_animals) < pastures_built.
   Shed cap: max 1 unplaced animal at any time.
2. Wheat shed cap: lowered from 18 → 12. Excess sold.
3. Strawberry early start: Day 6 (instead of Day 9). Gives 3 extra days growing.
4. Melon harvest-first priority: overripe melons pulled before watering.
5. Keep V1000's land and hire logic unchanged.
"""
from collections import defaultdict

CROPS = {
    "WHEAT":      {"seed": 10,  "max_yield_day": 4,  "ongoing": False, "base_price": 25},
    "CARROT":     {"seed": 20,  "max_yield_day": 3,  "ongoing": False, "base_price": 35},
    "STRAWBERRY": {"seed": 100, "max_yield_day": 10, "ongoing": True,  "base_price": 120},
    "MELON":      {"seed": 80,  "max_yield_day": 12, "ongoing": False, "base_price": 250},
}
LAND_PRICES = [1000, 2000, 4000]


def shed_access(board_size=10):
    h = board_size // 2
    return [(h-1,h-1),(h,h-1),(h-1,h),(h,h)]


def best_move(cur, tgt):
    cx,cy = cur; tx,ty = tgt
    if cx==tx and cy==ty: return None
    dx,dy = tx-cx, ty-cy
    moves = []
    if dx>0: moves.append(("EAST",abs(dx)))
    elif dx<0: moves.append(("WEST",abs(dx)))
    if dy>0: moves.append(("SOUTH",abs(dy)))
    elif dy<0: moves.append(("NORTH",abs(dy)))
    moves.sort(key=lambda m:m[1],reverse=True)
    return moves[0][0] if moves else None


def mdist(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])


def agent(obs):
    player = obs.get("player",0)
    farms  = obs.get("farms",[])
    if not farms or player>=len(farms):
        return {"farmer":["PASS"],"hands":[],"market":[]}

    farm     = farms[player]
    private  = obs.get("private",{}) or {}
    day      = obs.get("day",0)
    hour     = obs.get("hour",0)
    bs       = len(farm["tiles"])
    shed_adj = shed_access(bs)

    money  = farm.get("money",0)
    shed   = private.get("shed",{})  or {}
    seeds  = private.get("seeds",{}) or {}
    invs   = private.get("inventories",[{}]) or [{}]

    mkt = []

    # ── 1. SELL ───────────────────────────────────────────────────────────────
    for item,qty in list(shed.items()):
        if qty>0 and item in ("MILK","WOOL","EGG","FERTILIZER","MELON",
                               "STRAWBERRY","CARROT","TOMATO"):
            mkt.append(["SELL",item,qty])
        elif qty>12 and item=="WHEAT":                     # FIX: cap 18→12
            mkt.append(["SELL","WHEAT",qty-12])

    # ── 2. HIRE ───────────────────────────────────────────────────────────────
    hires  = farm.get("hires_today",0)
    quads  = len(farm.get("unlocked_quadrants",["NW"]))
    if day>=28:          tgt_hire=6
    elif day>=25:        tgt_hire=8
    elif quads==1:       tgt_hire=5
    elif quads==2:       tgt_hire=7
    else:                tgt_hire=10
    if hires<tgt_hire and money>=5:
        for _ in range(tgt_hire-hires): mkt.append(["HIRE"])

    spnd = max(0, money-150)

    # ── 3. LAND (cap 3 quads) ─────────────────────────────────────────────────
    if quads<3 and day<=14:
        cost = LAND_PRICES[quads-1]
        buf  = 300 if day<=7 else 500
        if spnd>=cost+buf:
            mkt.append(["BUY_LAND"]); spnd-=cost; money-=cost; quads+=1

    # ── 4. TILE SURVEY ────────────────────────────────────────────────────────
    pasture_pos=[]; animal_pos=[]; empty_past=[]; crop_ct=defaultdict(int)
    for y in range(bs):
        for x in range(bs):
            t = farm["tiles"][y][x]
            if t=="LOCKED" or t is None: continue
            if isinstance(t,dict):
                k=t.get("kind")
                if k=="PASTURE":
                    pasture_pos.append((x,y))
                    if "animal" in t: animal_pos.append((x,y,t["animal"],t))
                    else:             empty_past.append((x,y))
                elif k=="PLANT": crop_ct[t.get("crop")]+=1

    num_cows  = sum(1 for a in animal_pos if a[2]=="COW")
    num_sheep = sum(1 for a in animal_pos if a[2]=="SHEEP")
    num_animals = len(animal_pos)

    # 11-pasture cluster around shed
    desg_past = [(4,4),(5,4),(4,5),(5,5),(4,3),(5,3),(3,4),(3,5),(4,6),(5,6),(6,4)]
    max_past  = min(sum(1 for p in desg_past if farm["tiles"][p[1]][p[0]]!="LOCKED"), 11)

    # ── 5. PURCHASING ─────────────────────────────────────────────────────────
    if hour<20:
        tot_cows  = num_cows  + shed.get("COW",0)
        tot_sheep = num_sheep + shed.get("SHEEP",0)
        tot_ordered = tot_cows+tot_sheep     # placed + in-shed

        # Day 0: 2 Cows + 2 Sheep
        if day==0 and hour==0:
            if spnd>=1800:
                mkt.append(["BUY_ANIMAL","COW",2]); mkt.append(["BUY_ANIMAL","SHEEP",2]); spnd-=1800
            if spnd>=50: mkt.append(["BUY_PRODUCT","WHEAT",4]); spnd-=50

        # FIX: only buy if shed has <=1 unplaced animal AND total ordered < built pastures
        elif day<=12:
            shed_animals = shed.get("COW",0)+shed.get("SHEEP",0)
            if shed_animals<=1 and tot_ordered<len(pasture_pos) and spnd>=800:
                if tot_cows<6:
                    mkt.append(["BUY_ANIMAL","COW",1]); spnd-=400
                elif tot_sheep<5 and spnd>=900:
                    mkt.append(["BUY_ANIMAL","SHEEP",1]); spnd-=500

        if shed.get("WHEAT",0)<4 and num_animals>0 and spnd>=50:
            mkt.append(["BUY_PRODUCT","WHEAT",4]); spnd-=50

        # ── SEEDS ──
        if day<=5:
            bm=min(max(0,12-crop_ct["MELON"]-seeds.get("MELON",0)),int(spnd//80),6)
            if bm>0: mkt.append(["BUY_SEED","MELON",bm]); spnd-=bm*80
            bw=min(max(0,8-crop_ct["WHEAT"]-seeds.get("WHEAT",0)),int(spnd//10),8)
            if bw>0: mkt.append(["BUY_SEED","WHEAT",bw]); spnd-=bw*10

        elif day<=15:    # FIX: strawberries from Day 6 (not Day 9)
            bs_=min(max(0,38-crop_ct["STRAWBERRY"]-seeds.get("STRAWBERRY",0)),int(spnd//100),10)
            if bs_>0: mkt.append(["BUY_SEED","STRAWBERRY",bs_]); spnd-=bs_*100
            bw=min(max(0,20-crop_ct["WHEAT"]-seeds.get("WHEAT",0)),int(spnd//10),10)
            if bw>0: mkt.append(["BUY_SEED","WHEAT",bw]); spnd-=bw*10

        elif day<=22:
            bw=min(max(0,22-crop_ct["WHEAT"]-seeds.get("WHEAT",0)),int(spnd//10),10)
            if bw>0: mkt.append(["BUY_SEED","WHEAT",bw]); spnd-=bw*10

        elif day<=27:
            bw=min(max(0,35-seeds.get("WHEAT",0)),int(spnd//10),20)
            if bw>0: mkt.append(["BUY_SEED","WHEAT",bw]); spnd-=bw*10

    # ── 6. TASKS ──────────────────────────────────────────────────────────────
    all_units = [farm["farmer"]]+farm.get("hands",[])
    N = len(all_units)

    t_animal=[]; t_harv=[]; t_water=[]; t_dig=[]; t_plant=[]; t_build=[]

    for px,py in desg_past:
        t = farm["tiles"][py][px]
        if t=="LOCKED": continue
        if t is None and len(pasture_pos)<max_past:
            t_build.append({"type":"BUILD_PASTURE","pos":(px,py)})
        elif isinstance(t,dict) and t.get("kind")=="PASTURE":
            if "animal" in t:
                if not t.get("fed_today",False):        t_animal.append({"type":"FEED","pos":(px,py)})
                if not t.get("cared_today",False):      t_animal.append({"type":"CARE","pos":(px,py)})
                if t.get("yield_units",0)>0:            t_animal.append({"type":"HARVEST","pos":(px,py)})
                if t.get("fertilizer_available",False): t_animal.append({"type":"COLLECT_FERTILIZER","pos":(px,py)})
            else:
                if shed.get("COW",0)>0 or shed.get("SHEEP",0)>0:
                    t_animal.append({"type":"PLACE_ANIMAL","pos":(px,py)})

    for y in range(len(farm["tiles"])):
        for x in range(len(farm["tiles"][y])):
            tile = farm["tiles"][y][x]
            if tile=="LOCKED": continue
            if tile is None:
                if (x,y) not in desg_past and day<28 and hour<20:
                    t_plant.append({"type":"PLANT","pos":(x,y)})
            elif isinstance(tile,dict):
                k=tile.get("kind")
                if k=="WEED":
                    t_dig.append({"type":"DIG","pos":(x,y)})
                elif k=="PLANT":
                    crop     = tile.get("crop")
                    cd       = CROPS.get(crop,{})
                    age      = day-tile.get("planted_day",0)
                    yld      = tile.get("yield_units",0)
                    watered  = tile.get("watered_today",False)
                    overripe = (not cd.get("ongoing") and age>=cd.get("max_yield_day",4)) or day>=29
                    has_yld  = cd.get("ongoing") and yld>0
                    if overripe or has_yld: t_harv.append({"type":"HARVEST","pos":(x,y)})
                    elif not watered:       t_water.append({"type":"WATER","pos":(x,y)})

    ordered = t_animal+t_harv+t_water+t_dig+t_plant+t_build

    # ── 7. DISPATCH ───────────────────────────────────────────────────────────
    acts    = [None]*N
    used    = set()
    lseeds  = dict(seeds)
    pending = list(range(N))

    for u in list(pending):
        ux,uy  = all_units[u]
        uinv   = invs[u] if u<len(invs) else {}
        utile  = farm["tiles"][uy][ux]
        is_shd = (ux,uy) in shed_adj
        carry  = sum(uinv.values())

        sellable = sum(uinv.get(p,0) for p in ("MILK","WOOL","EGG","FERTILIZER","MELON","STRAWBERRY","CARROT","TOMATO"))
        if is_shd and (sellable>0 or carry>=4 or (day>=28 and carry>0)):
            acts[u]=["DROP"]; pending.remove(u); continue

        if utile not in (None,"LOCKED") and isinstance(utile,dict):
            k=utile.get("kind")
            if "animal" in utile:
                if utile.get("yield_units",0)>0:              acts[u]=["HARVEST"]; pending.remove(u); continue
                if uinv.get("WHEAT",0)>0 and not utile.get("fed_today",False): acts[u]=["FEED"]; pending.remove(u); continue
                if not utile.get("cared_today",False):        acts[u]=["CARE"];    pending.remove(u); continue
                if utile.get("fertilizer_available",False):   acts[u]=["COLLECT_FERTILIZER"]; pending.remove(u); continue
            elif k=="PASTURE":
                if uinv.get("COW",0)>0:   acts[u]=["PLACE","COW"];  pending.remove(u); continue
                if uinv.get("SHEEP",0)>0: acts[u]=["PLACE","SHEEP"]; pending.remove(u); continue
            elif k=="WEED": acts[u]=["DIG"]; used.add((ux,uy)); pending.remove(u); continue
            elif k=="PLANT":
                crop=utile.get("crop"); cd=CROPS.get(crop,{})
                age=day-utile.get("planted_day",0); yld=utile.get("yield_units",0)
                watered=utile.get("watered_today",False)
                overripe=(not cd.get("ongoing") and age>=cd.get("max_yield_day",4)) or day>=29
                has_yld=cd.get("ongoing") and yld>0
                if overripe or has_yld: acts[u]=["HARVEST"]; used.add((ux,uy)); pending.remove(u); continue
                elif not watered:       acts[u]=["WATER"];   used.add((ux,uy)); pending.remove(u); continue

        elif utile is None and (ux,uy) not in used and hour<20:
            if (ux,uy) in desg_past and len(pasture_pos)<max_past:
                acts[u]=["BUILD_PASTURE"]; used.add((ux,uy)); pending.remove(u); continue
            elif lseeds.get("MELON",0)>0 and day<=10:
                acts[u]=["PLANT","MELON"]; lseeds["MELON"]-=1; used.add((ux,uy)); pending.remove(u); continue
            elif lseeds.get("STRAWBERRY",0)>0 and day<=15:
                acts[u]=["PLANT","STRAWBERRY"]; lseeds["STRAWBERRY"]-=1; used.add((ux,uy)); pending.remove(u); continue
            elif lseeds.get("WHEAT",0)>0 and day<28:
                acts[u]=["PLANT","WHEAT"]; lseeds["WHEAT"]-=1; used.add((ux,uy)); pending.remove(u); continue

        if is_shd and uinv.get("WHEAT",0)==0 and shed.get("WHEAT",0)>0 and num_animals>0:
            acts[u]=["PICKUP","WHEAT",min(2,shed.get("WHEAT",0))]; pending.remove(u); continue
        if is_shd and empty_past:
            if shed.get("COW",0)>0 and uinv.get("COW",0)==0:
                acts[u]=["PICKUP","COW",1]; pending.remove(u); continue
            if shed.get("SHEEP",0)>0 and uinv.get("SHEEP",0)==0:
                acts[u]=["PICKUP","SHEEP",1]; pending.remove(u); continue
        if (carry>=4 or (day>=28 and carry>0)) and not is_shd:
            cs=min(shed_adj,key=lambda s:mdist((ux,uy),s))
            mv=best_move((ux,uy),cs)
            if mv: acts[u]=[mv]; pending.remove(u); continue

    for u in list(pending):
        ux,uy=all_units[u]
        best_t,best_d=None,999
        for task in ordered:
            if task["pos"] in used: continue
            d=mdist((ux,uy),task["pos"])
            if d<best_d: best_d=d; best_t=task

        if best_t:
            used.add(best_t["pos"])
            mv=best_move((ux,uy),best_t["pos"])
            if mv:
                acts[u]=[mv]
            else:
                tp=best_t["type"]
                if   tp=="BUILD_PASTURE":       acts[u]=["BUILD_PASTURE"]
                elif tp=="WATER":               acts[u]=["WATER"]
                elif tp=="HARVEST":             acts[u]=["HARVEST"]
                elif tp=="DIG":                 acts[u]=["DIG"]
                elif tp=="FEED":                acts[u]=["FEED"]
                elif tp=="CARE":                acts[u]=["CARE"]
                elif tp=="COLLECT_FERTILIZER":  acts[u]=["COLLECT_FERTILIZER"]
                elif tp=="PLANT":
                    if lseeds.get("MELON",0)>0 and day<=10:
                        acts[u]=["PLANT","MELON"]; lseeds["MELON"]-=1
                    elif lseeds.get("STRAWBERRY",0)>0 and day<=15:
                        acts[u]=["PLANT","STRAWBERRY"]; lseeds["STRAWBERRY"]-=1
                    elif lseeds.get("WHEAT",0)>0 and day<28:
                        acts[u]=["PLANT","WHEAT"]; lseeds["WHEAT"]-=1
                    else: acts[u]=["PASS"]
                else: acts[u]=["PASS"]
        else:
            if (ux,uy) not in shed_adj:
                cs=min(shed_adj,key=lambda s:mdist((ux,uy),s))
                mv=best_move((ux,uy),cs)
                acts[u]=[mv] if mv else ["PASS"]
            else: acts[u]=["PASS"]
        pending.remove(u)

    return {"farmer": acts[0] if acts[0] else ["PASS"],
            "hands":  [a if a else ["PASS"] for a in acts[1:]],
            "market": mkt[:10]}
