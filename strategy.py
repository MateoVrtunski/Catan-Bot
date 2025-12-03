import data
import pulp as pl

# Create LP problem: choose Maximize or Minimize
prob = pl.LpProblem("City_Optimized_Weights", pl.LpMaximize)

# Decision variables = resource weights
a = pl.LpVariable("ore",   lowBound=0, upBound=10)
b = pl.LpVariable("wheat", lowBound=0, upBound=10)
c = pl.LpVariable("sheep", lowBound=0, upBound=10)
d = pl.LpVariable("wood",  lowBound=0, upBound=10)
e = pl.LpVariable("brick", lowBound=0, upBound=10)


# Objective = prioritize city resources but not insanely
prob += 3*a + 2*b - c - d - e, "City_Strategy_Objective"

# Priority structure

prob += 5*d + 5*e + 5*c >= 4*a + 7*b
prob += 4*a + 7*b >= 5*c + 4*d + 4*e
prob += 5*a >= 5.5*b
prob += 5*c >= 2*d + 2*e
prob += d == e


prob.solve()


i = data.inter
bo = data.board
i2 = data.inter2
second = data.second



strategy = {
                "wheat": b.value(),
                "ore": a.value(),
                "wood": d.value(),
                "sheep": c.value(),
                "brick": e.value()
            }

def look_at_board(board):

    for i in board:
        if i["number"] in (2, 12):
            i["number"] = 1
        elif i["number"] in (3, 11):
            i["number"]= 2
        elif i["number"] in (4, 10):
            i["number"] = 3
        elif i["number"] in (5, 9):
            i["number"] = 4
        elif i["number"] in (6, 8):
            i["number"] = 5

    rarity = [[],[],[],[],[]]
    res = ["ore", "wheat", "sheep","brick","wood"]

    for i in range(len(res)):
        for j in range(len(board)):
            if board[j]["type"] == res[i]:
                rarity[i].append(board[j]["number"])

    res_on_turn = []
    for i in range(len(rarity)):
        res_on_turn.append(sum(rarity[i])/36)

    return res_on_turn



def first_two_settlements(strategy, intersections, board, player=None):
   
    local_strategy = dict(strategy)

    # --- If the player already has a settlement, reduce weights for resources
    #     adjacent to that settlement by 2 (to encourage complementary 2nd placement)
    if player is not None:
        owned_settlements = [
        iv for iv in intersections
        if iv.get("occupiedBy") == player and iv.get("type") == "settlement"
        ]
    
    if len(owned_settlements) >= 1:
        first_iv = owned_settlements[0]

        for hi in first_iv.get("adjacentHexes", []):
            if 0 <= hi < len(board):
                tile = board[hi]
                if tile and tile.get("type") in local_strategy:

                    # --- determine probability (based on tile number)
                    num = tile.get("number")
                    if num is not None and 2 <= num <= 12:
                        p = (6 - abs(num - 7)) / 36   # probability of rolling this number
                    else:
                        p = 0

                    # --- subtract 3/4 * probability * 36 = 27 * p
                    penalty = 27 * p
                    local_strategy[tile["type"]] = (local_strategy.get(tile["type"], 0) - penalty)
    # --- Build tile lists for each intersection (max 3 tiles; pad with None)
    intersection_tiles = []
    for iv in intersections:
        # if occupied or blocked by adjacent occupied → mark as unusable
        occ = iv.get("occupiedBy")
        if occ not in (None, "None"):
            intersection_tiles.append([None, None, None])
            continue


        blocked = False
        for nid in iv.get("neighbors", []):
            if 0 <= nid < len(intersections):
                occ_n = intersections[nid].get("occupiedBy")
                if occ_n not in (None, "None"):
                    blocked = True
                    break

        if blocked:
            intersection_tiles.append([None, None, None])
            continue

        adj = iv.get("adjacentHexes", [])
        tiles = []
        for hex_index in adj[:3]:
            if 0 <= hex_index < len(board):
                tiles.append(board[hex_index])
            else:
                tiles.append(None)
        while len(tiles) < 3:
            tiles.append(None)

        # If this intersection has a harbour (harbor / harbour) and the harbour value
        # is not the string "None", we'll treat missing tiles as a small harbor bonus.

        intersection_tiles.append(tiles)

    # --- Score each intersection ---
    # --- Score each intersection ---
    scores = []
    for idx, tiles in enumerate(intersection_tiles):

        # unusable intersection
        if tiles == [None, None, None]:
            scores.append(0)
            continue

        total = 0

        iv = intersections[idx]
        hv = iv.get("harbor", iv.get("harbour", None))
        if hv is not None and hv != "None":
            total += 15

        # score all real tiles
        for tile in tiles:
            if tile is None or tile.get("type") == "desert":
                continue

            num = tile.get("number")
            typ = tile.get("type")

            # number probabilities
            if num in (2, 12): num_score = 1
            elif num in (3, 11): num_score = 2
            elif num in (4, 10): num_score = 3
            elif num in (5, 9): num_score = 4
            elif num in (6, 8): num_score = 5
            else: num_score = 0

            type_weight = local_strategy.get(typ, 0)
            total += type_weight * num_score

        scores.append(total)


    # --- choose highest score index (ties -> first max)
    if not scores:
        return 0
    winner = max(range(len(scores)), key=lambda i: scores[i])


        # --------------------------------------------------
    # ROAD DECISION:
    # Pick the best intersection two steps away
    # --------------------------------------------------

    # winner is already defined above
    start = winner

    candidate_intersections = set()

    # neighbors of winner
    for n1 in intersections[start].get("neighbors", []):
        occ1 = intersections[n1].get("occupiedBy")
        if occ1 is not None and str(occ1).lower() != "None":
            continue

        for n2 in intersections[n1].get("neighbors", []):
            # exclude the winner itself and direct neighbors
            if n2 != start and n2 not in intersections[start].get("neighbors", []):
                candidate_intersections.add(n2)

    # remove invalid indices
    candidate_intersections = [
        c for c in candidate_intersections
        if 0 <= c < len(intersections)
    ]

    # if no valid candidates → fallback
    if not candidate_intersections:
        road_target = None
    else:
        # choose the best-scoring among distance-2 intersections
        road_target = max(candidate_intersections, key=lambda c: scores[c])


    return winner, road_target

import math
from copy import deepcopy

def in_game_start2(players, player_id, intersections, roads, board, strategy_weights=None):
    """
    Decide an in-game action for player `player_id`.

    Inputs:
      - players: list of player dicts (each must include 'resources', 'settlements_left', 'cities_left', 'roads_left')
      - player_id: int index of the player
      - intersections: list of intersection dicts (each has 'adjacentHexes', 'neighbors', 'occupiedBy', 'type', 'harbor' maybe)
      - roads: list of road dicts {a:int, b:int, player:int}
      - board: list of 19 tile dicts {'type','number'}
      - strategy_weights: optional dict mapping resource type -> weight (defaults provided)
      - config: optional dict to tune weights/bonuses/discounts

    Returns:
      one of:
        - "city on intersection: X"
        - "settlement on intersection: X"
        - "road from X to Y"
        - "buy card"
    """

    # ---------------- default parameters ----------------
    default_strategy = {
        "ore": 10.0,
        "wheat": 9.0,
        "wood": 7.4,
        "sheep": 5.9,
        "brick": 7.4
    }
    if strategy_weights is None:
        strategy_weights = dict(default_strategy)
    else:
        # make sure all keys exist
        temp = dict(default_strategy)
        temp.update(strategy_weights)
        strategy_weights = temp

    cfg = {
        "harbor_bonus": 15,       # user wanted a constant +20 for harbor placeholder
        "harbor_bonus_mode": "add", # 'add' adds fixed amount; other modes could be 'scale'
        "road_discount": 0.4,
        "priority_weights": {
            "city": 2.0,
            "settlement": 1.4,
            "road": 0.9,
            "card": 0.7
        },
        "piece_availability_boost": {
            "city_when_no_settlements_left": 8.0,
            "settlement_when_no_cities_left": 4.0
        },
        "dev_card_base_value": 5.0,
        "eps": 1e-9
    }
    

    # dice probabilities mapping (number -> relative freq)
    dice_prob_score = {
        2: 1/36, 12: 1/36,
        3: 2/36, 11: 2/36,
        4: 3/36, 10: 3/36,
        5: 4/36, 9: 4/36,
        6: 5/36, 8: 5/36
    }

    # ---------------- helpers ----------------
    def parse_occupied(x):
        # normalize occupiedBy values to None or int
        if x is None:
            return None
        if isinstance(x, str):
            if x.lower() == "none":
                return None
            try:
                return int(x)
            except Exception:
                return None
        return int(x)

    # normalize a local copy of intersections so we don't mutate outside
    inters = deepcopy(intersections)
    for iv in inters:
        iv['occupiedBy'] = parse_occupied(iv.get('occupiedBy'))

    # players safety
    if not (0 <= player_id < len(players)):
        return "buy card"   # can't find player -> safe fallback

    player = players[player_id]
    resources = player.get('resources', {})
    # ensure numeric resources
    resources = {k: int(v) if v is not None else 0 for k, v in resources.items()}

    # helper: intersection production value (settlement expected production)
    def intersection_value(iv):
        total = 0.0
        for hi in iv.get("adjacentHexes", []):
            if not (0 <= hi < len(board)):
                continue
            tile = board[hi]
            if not tile: continue
            ttype = tile.get("type")
            num = tile.get("number")
            if ttype == 'desert' or num is None:
                continue
            prob = dice_prob_score.get(num, 0)
            weight = strategy_weights.get(ttype, 0)
            total += weight * prob * 36.0   # multiply by 36 to use integer-like scores (optional)
            # NOTE: multiplication by 36 is merely scaling so scores are human-friendly
        # harbor bonus: if harbor exists and not "None" add fixed bonus
        hv = iv.get("harbor", iv.get("harbour", None))
        if hv is not None and hv != "None":
            if cfg["harbor_bonus_mode"] == "add":
                total += cfg["harbor_bonus"]
            else:
                total *= (1.0 + cfg["harbor_bonus"])
        return total

    # helper: is legal placement for intersection given current state
    def is_legal_settlement(iv_idx):
        iv = inters[iv_idx]
        if not iv.get("adjacentHexes"): return False
        if iv.get("occupiedBy") is not None: return False
        for nid in iv.get("neighbors", []):
            if 0 <= nid < len(inters) and inters[nid].get("occupiedBy") is not None:
                return False
        return True

    # helper: edge exists
    def edge_exists(a,b):
        for r in roads:
            if (r.get('a') == a and r.get('b') == b) or (r.get('a') == b and r.get('b') == a):
                return True
        return False

    # affordability function for cost dict
    def affordability(cost):
        # cost: {'ore':3, ...}
        parts = []
        for k, need in cost.items():
            have = int(resources.get(k, 0))
            if need <= 0:
                parts.append(1.0)
            else:
                parts.append(min(have / need, 1.0))
        if not parts:
            return 1.0
        return sum(parts) / len(parts)

    # ---------------- compute intersection values for all ----------------
    iv_values = [intersection_value(iv) for iv in inters]
    max_iv_value = max(iv_values) if iv_values else 0.0
    if max_iv_value <= 0:
        max_iv_value = cfg["eps"]

    # ---------------- City evaluation ----------------
    city_cost = {"wheat": 2, "ore": 3}
    best_city_score = 0.0
    best_city_idx = None
    # candidate cities are player's settlements
    for idx, iv in enumerate(inters):
        if iv.get("occupiedBy") == player_id and iv.get("type") in (None, "settlement", "settlement"):  # accept typical field names
            marginal_value = iv_values[idx]  # city doubles, marginal = settlement value
            aff = affordability(city_cost)
            # strategic term normalized
            strategic_term = marginal_value / (max_iv_value + cfg["eps"])
            # base score
            score = cfg["priority_weights"]["city"] * aff * (1.0 + strategic_term)
            if score > best_city_score:
                best_city_score = score
                best_city_idx = idx

    # ---------------- Settlement evaluation ----------------
    settlement_cost = {"brick":1, "wood":1, "sheep":1, "wheat":1}
    # choose best legal intersection (highest iv_value among legal)
    best_settlement_idx = None
    best_settlement_value = 0.0
    for idx, iv in enumerate(inters):
        if not is_legal_settlement(idx):
            continue
        val = iv_values[idx]
        if val > best_settlement_value:
            best_settlement_value = val
            best_settlement_idx = idx

    aff_settlement = affordability(settlement_cost)
    strategic_term_settlement = best_settlement_value / (max_iv_value + cfg["eps"])
    best_settlement_score = cfg["priority_weights"]["settlement"] * aff_settlement * (1.0 + strategic_term_settlement) if best_settlement_idx is not None else 0.0

    # ---------------- Road evaluation ----------------
    # We'll consider building a road adjacent to any owned intersection, and
    # look two steps out (via an unoccupied n1) for the best settle-able intersection.
    road_cost = {"brick":1, "wood":1}
    best_road_score = 0.0
    best_road_from = None
    best_road_to = None
    # precompute legal settlement mask
    legal_mask = [is_legal_settlement(i) for i in range(len(inters))]

    for base_idx, base_iv in enumerate(inters):
        if base_iv.get("occupiedBy") != player_id:
            continue
        # for each neighbor n1 we may build to
        for n1 in base_iv.get("neighbors", []):
            if not (0 <= n1 < len(inters)):
                continue
            # If n1 is occupied by any player, we cannot "go in this direction" per your requirement
            if inters[n1].get("occupiedBy") is not None:
                continue
            # skip if road already exists between base and n1
            if edge_exists(base_idx, n1):
                continue
            # now check neighbors of n1 (distance 2)
            best_reachable = 0.0
            best_reachable_idx = None
            for n2 in inters[n1].get("neighbors", []):
                if not (0 <= n2 < len(inters)):
                    continue
                # exclude the base itself and direct neighbors of base to avoid immediate adjacency rules
                if n2 == base_idx or n2 in base_iv.get("neighbors", []):
                    continue
                # candidate n2 must be a legal settlement spot
                if not legal_mask[n2]:
                    continue
                # prefer highest iv_values
                if iv_values[n2] > best_reachable:
                    best_reachable = iv_values[n2]
                    best_reachable_idx = n2
            if best_reachable_idx is None:
                continue
            # compute score for this road candidate
            aff_r = affordability(road_cost)
            strategic_r = (best_reachable / (max_iv_value + cfg["eps"])) * cfg["road_discount"]
            score_r = cfg["priority_weights"]["road"] * aff_r * (1.0 + strategic_r)
            if score_r > best_road_score:
                best_road_score = score_r
                best_road_from = base_idx
                best_road_to = n1  # road built from base to n1 (the immediate neighbor)
                # store reachable index as additional info (not required in return)
                best_road_reachable = best_reachable_idx

    # ---------------- Dev card evaluation ----------------
    card_cost = {"sheep":1, "wheat":1, "ore":1}
    aff_card = affordability(card_cost)
    # dev_card value baseline, but scale a bit with missing options
    dev_val = cfg["dev_card_base_value"]
    strategic_card_score = cfg["priority_weights"]["card"] * aff_card * (1.0 + dev_val / (max_iv_value + cfg["eps"]))
    best_card_score = strategic_card_score

    # ---------------- piece availability adjustments ----------------
    pw = cfg["priority_weights"]
    if player.get("settlements_left", 1) == 0:
        # must go city route almost always
        best_city_score *= cfg["piece_availability_boost"]["city_when_no_settlements_left"]
    if player.get("cities_left", 1) == 0:
        best_settlement_score *= cfg["piece_availability_boost"]["settlement_when_no_cities_left"]
    if player.get("roads_left", 1) == 0:
        best_road_score = 0.0

    # ---------------- choose best ----------------
    actions = [
        ("city", best_city_score, best_city_idx),
        ("settlement", best_settlement_score, best_settlement_idx),
        ("road", best_road_score, (best_road_from, best_road_to)),
        ("card", best_card_score, None)
    ]
    # sort by score desc, tie break by priority order city>settlement>road>card
    priority_order = {"city": 0, "settlement": 1, "road": 2, "card": 3}
    actions.sort(key=lambda x: (x[1], -priority_order[x[0]]), reverse=True)

    best_action, best_score, best_data = actions[0]

    # if no positive score at all, fall back to buy card or no-op
    if best_score <= 0:
        return "buy card"

    if best_action == "city":
        if best_city_idx is None:
            return "buy card"
        return f"city on intersection: {best_city_idx}"
    elif best_action == "settlement":
        if best_settlement_idx is None:
            return "buy card"
        return f"settlement on intersection: {best_settlement_idx}"
    elif best_action == "road":
        if best_road_from is None or best_road_to is None:
            return "buy card"
        return f"road from {best_road_from} to {best_road_to}"
    else:
        return "buy card"


players=data.players_in_game
intersections = data.int_in_game
roads = data.roads_in_game



city_cost = {"wheat": 2, "ore": 3}
settlement_cost ={"wheat":1, "sheep":1, "wood":1,"brick":1}
card_cost = {"wheat":1, "ore":1, "sheep":1}
road_cost = {"brick":1, "wood":1}

def can_afford(player, cost):
   
    resources = player.get("resources", {})

    for res, amount in cost.items():
        if resources.get(res, 0) < amount:
            return False
    return True

def settlement_possible(player_id, roads, intersections, board):
    """
    Returns (True, best_location) if a settlement can be placed,
    where best_location is chosen by highest adjacent tile probability
    plus harbour bonus.
    Otherwise returns (False, None).
    """

    # --- helper: probability of a number token
    def tile_probability(number):
        if number is None or number < 2 or number > 12:
            return 0
        return (6 - abs(number - 7)) / 36   # normal Catan distribution

    # harbour value: acts like number 4 or 10 = 3/36
    HARBOUR_VALUE = 3 / 36

    # collect player's road endpoints
    player_edges = [(r["a"], r["b"]) for r in roads if r["player"] == player_id]

    if not player_edges:
        return False, None

    # adjacency map of player's own road network
    adjacency = {}
    for a, b in player_edges:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)

    possible_locations = []

    # examine each endpoint of each road
    for a, b in player_edges:
        for node in (a, b):

            I = intersections[node]

            # occupied?
            if I["occupiedBy"] != "None":
                continue

            # distance rule: neighbors must be empty
            blocked = False
            for n in I["neighbors"]:
                if intersections[n]["occupiedBy"] != "None":
                    blocked = True
                    break
            if blocked:
                continue

            # needs at least 2 connected roads
            if len(adjacency[node]) < 2:
                continue

            # valid placement → score it
            score = 0

            # sum adjacent tile probabilities
            for hi in I.get("adjacentHexes", []):
                if 0 <= hi < len(board):
                    tile = board[hi]
                    if tile:
                        score += tile_probability(tile.get("number"))

            # harbour bonus (adjust field name if different)
            if I.get("harbor") not in (None, "None"):
                score += HARBOUR_VALUE

            possible_locations.append((score, node))

    # no valid locations
    if not possible_locations:
        return False, None

    # pick location with highest score
    possible_locations.sort(reverse=True)  # highest score first
    best_score, best_node = possible_locations[0]

    return True, best_node


def city_placement(player_id, intersections, board):
    """
    Returns the intersection (settlement position) with the highest
    total probability of its adjacent hexes, for upgrading to a city.
    """

    # --- helper: probability of a number token
    def tile_probability(number):
        if number is None or number < 2 or number > 12:
            return 0
        return (6 - abs(number - 7)) / 36    # standard Catan distribution

    best_score = -1
    best_intersection = None

    for iv in intersections:
        # check if this is the player's settlement
        if iv.get("occupiedBy") == player_id and iv.get("type") == "settlement":
            
            total_prob = 0
            
            # sum probabilities of adjacent tiles
            for hi in iv.get("adjacentHexes", []):
                if 0 <= hi < len(board):
                    tile = board[hi]
                    if tile is not None:
                        num = tile.get("number")
                        total_prob += tile_probability(num)

            # check if this is the highest score so far
            if total_prob > best_score:
                best_score = total_prob
                best_intersection = iv.get("id")

    return best_intersection


def in_game_start(players, player_id, intersections, roads, board):

    player = players[player_id]
    resources = player["resources"]

    city_cost = {"wheat": 2, "ore": 3}
    settlement_cost ={"wheat":1, "sheep":1, "wood":1,"brick":1}
    card_cost = {"wheat":1, "ore":1, "sheep":1}
    road_cost = {"brick":1, "wood":1}

    t,set_loc = settlement_possible(player_id, roads, intersections, board)
    city_loc = city_placement(player_id,intersections, board)

    def compute_missing_and_extra(cost):
        missing = {}
        extra = {}

        for res, amount_needed in cost.items():
            have = resources.get(res, 0)
            if have < amount_needed:
                missing[res] = amount_needed - have

        for res, have in resources.items():
            spare = have - cost.get(res, 0)
            if spare > 0:
                extra[res] = spare

        return missing, extra

    strategy_1 = {}
    trad = {"i_need": None, "i_give": None}

    if can_afford(player, city_cost) == True and player["settlements_left"] < 5:
        strategy_1 = {"city": city_loc}
        trad = {"i_need":None, "i_give": None}
        return strategy_1, trad
    
    missing_city, extra_city = compute_missing_and_extra(city_cost)
    if player["settlements_left"] < 5 and len(missing_city) == 1 and len(extra_city) > 0:
        strategy_1 = {"city": city_loc}
        trad = {"i_need": missing_city, "i_give": extra_city}
        return strategy_1, trad

    if can_afford(player, settlement_cost) == True and player["settlements_left"] > 0 and t == True:
        strategy_1 = {"settlement": set_loc}
        trad = {"i_need":None, "i_give": None}
        return strategy_1, trad
    
    missing_set, extra_set = compute_missing_and_extra(settlement_cost)
    if player["settlements_left"] > 0 and t and len(missing_set) == 1 and len(extra_set) > 0:
        strategy_1 = {"settlement": set_loc}
        trad = {"i_need": missing_set, "i_give": extra_set}
        return strategy_1, trad
    
    return None

print(in_game_start(players,0,intersections,roads,bo))
    

    
    
    
