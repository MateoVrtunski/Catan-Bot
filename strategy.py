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
    neighbors = intersections[start].get("neighbors", [])

    road_target = None
    best_score = -1

    for n in neighbors:
        if not (0 <= n < len(intersections)):
            continue

        iv_n = intersections[n]
        occ = iv_n.get("occupiedBy")

        # must be empty
        if occ not in (None, "None"):
            continue

        s = scores[n]
        if s > best_score:
            best_score = s
            road_target = n


    return winner, road_target

def robber_decision(player_id, players, board, intersections, robber_tile=None):
    
    DICE_PROB = {
    2: 1, 3: 2, 4: 3, 5: 4, 6: 5,
    8: 5, 9: 4, 10: 3, 11: 2, 12: 1}
    # --- 1. Find strongest opponent ---
    opponents = [
        (i, p) for i, p in enumerate(players)
        if i != player_id
    ]

    if not opponents:
        return None

    target_id, target_player = max(
        opponents,
        key=lambda x: x[1].get("victory_points", 0)
    )

    # --- 2. Score tiles ---
    tile_scores = {}

    for iv in intersections:
        occ = iv.get("occupiedBy")
        if occ != target_id:
            continue

        building = iv.get("type")
        if building not in ("settlement", "city"):
            continue

        weight = 2 if building == "city" else 1

        for tile_idx in iv.get("adjacentHexes", []):
            if tile_idx == robber_tile:
                continue

            tile = board[tile_idx]
            number = tile.get("number")

            if number not in DICE_PROB:
                continue

            # skip tiles where current player also benefits
            skip = False
            for iv2 in intersections:
                if (
                    iv2.get("occupiedBy") == player_id
                    and tile_idx in iv2.get("adjacentHexes", [])
                ):
                    skip = True
                    break

            if skip:
                continue

            score = DICE_PROB[number] * weight
            tile_scores[tile_idx] = tile_scores.get(tile_idx, 0) + score

    if not tile_scores:
        return None

    best_tile = max(tile_scores, key=tile_scores.get)
    tile = board[best_tile]

    return best_tile, tile.get("type"), tile.get("number")




players=data.players_in_game
intersections = data.int_in_game
roads = data.roads_in_game

print(robber_decision(0,players,bo,intersections,9))

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


def in_game_strat(players, player_id, intersections, roads, board):

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
    
    if can_afford(player, settlement_cost) == True and player["settlements_left"] > 0 and t == True:
        strategy_1 = {"settlement or road to": set_loc}
        trad = {"i_need":None, "i_give": None}
        return strategy_1, trad
    
    missing_city, extra_city = compute_missing_and_extra(city_cost)
    if (player["settlements_left"] < 5 and list(missing_city.values())[0] == 1 and len(extra_city) > 0) or player["settlements_left"] == 0:
        strategy_1 = {"city": city_loc}
        trad = {"i_need": missing_city, "i_give": extra_city}
        return strategy_1, trad

    missing_set, extra_set = compute_missing_and_extra(settlement_cost)
    if player["settlements_left"] > 0 and t == True and list(missing_set.values())[0] == 1 and len(extra_set) > 0:
        strategy_1 = {"settlement or road to": set_loc}
        trad = {"i_need": missing_set, "i_give": extra_set}
        return strategy_1, trad
    
    if can_afford(player, card_cost) == True:
        strategy_1 = {"card": None}
        trad = {"i_need":None, "i_give": None}
        return strategy_1, trad
    
    missing_card, extra_card = compute_missing_and_extra(card_cost)
    if player["settlements_left"] < 5 and list(missing_card.values())[0] == 1 and len(extra_card) > 0:
        strategy_1 = {"card": None}
        trad = {"i_need": missing_card, "i_give": extra_card}
        return strategy_1, trad
    
    if can_afford(player, road_cost) == True:
        strategy_1 = {"road": set_loc}
        trad = {"i_need":None, "i_give": None}
        return strategy_1, trad
    
    missing_road, extra_road = compute_missing_and_extra(road_cost)
    if player["settlements_left"] < 5 and list(missing_road.values())[0] == 1 and len(extra_road) > 0:
        strategy_1 = {"road": set_loc}
        trad = {"i_need": missing_road, "i_give": extra_road}
        return strategy_1, trad

    
    return strategy_1, trad

    

    
    
    
