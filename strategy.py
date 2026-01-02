# Here are the bot decisions made
import data, data2
import pulp as pl


prob = pl.LpProblem("City_Optimized_Weights", pl.LpMaximize)

a = pl.LpVariable("ore",   lowBound=0, upBound=10)
b = pl.LpVariable("wheat", lowBound=0, upBound=10)
c = pl.LpVariable("sheep", lowBound=0, upBound=10)
d = pl.LpVariable("wood",  lowBound=0, upBound=10)
e = pl.LpVariable("brick", lowBound=0, upBound=10)


prob += 3*a + 2*b - c - d - e, "City_Strategy_Objective"

# Done by examples of decisions

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


# Deciding the first two settlment is the most important part in Catan, the bot decision is based on the strategy chosen for the game
def first_two_settlements(strategy, intersections, board, player=None):
   
    local_strategy = dict(strategy)

    if player is not None:
        owned_settlements = [
        iv for iv in intersections
        if iv.get("occupiedBy") == player and iv.get("type") == "settlement"
        ]
    
    # Penalty for the resources already occupied
    if len(owned_settlements) >= 1:
        first_iv = owned_settlements[0]

        for hi in first_iv.get("adjacentHexes", []):
            if 0 <= hi < len(board):
                tile = board[hi]
                if tile and tile.get("type") in local_strategy:

                    num = tile.get("number")
                    if num is not None and 2 <= num <= 12:
                        p = (6 - abs(num - 7)) / 36 
                    else:
                        p = 0

                    penalty = 27 * p
                    local_strategy[tile["type"]] = (local_strategy.get(tile["type"], 0) - penalty)

    # Calculating the scores of each intersection
    intersection_tiles = []
    for iv in intersections:
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

        intersection_tiles.append(tiles)

    scores = []
    for idx, tiles in enumerate(intersection_tiles):

        if tiles == [None, None, None]:
            scores.append(0)
            continue

        total = 0

        iv = intersections[idx]
        hv = iv.get("harbor", iv.get("harbour", None))
        if hv is not None and hv != "None":
            total += 15

        for tile in tiles:
            if tile is None or tile.get("type") == "desert":
                continue

            num = tile.get("number")
            typ = tile.get("type")

            if num in (2, 12): num_score = 1
            elif num in (3, 11): num_score = 2
            elif num in (4, 10): num_score = 3
            elif num in (5, 9): num_score = 4
            elif num in (6, 8): num_score = 5
            else: num_score = 0

            type_weight = local_strategy.get(typ, 0)
            total += type_weight * num_score

        scores.append(total)


    if not scores:
        return 0
    winner = max(range(len(scores)), key=lambda i: scores[i])

    # Road decision
    start = winner
    neighbors = intersections[start].get("neighbors", [])

    road_target = None
    best_score = -1

    for n in neighbors:
        if not (0 <= n < len(intersections)):
            continue

        iv_n = intersections[n]
        occ = iv_n.get("occupiedBy")

        if occ not in (None, "None"):
            continue

        s = scores[n]
        if s > best_score:
            best_score = s
            road_target = n


    return winner, road_target

# Robber decisions finds the player with most VP and the location of the intersaction where he gains the most
def robber_decision(player_id, players, board, intersections, robber_tile=None):
    
    DICE_PROB = {
    2: 1, 3: 2, 4: 3, 5: 4, 6: 5,
    8: 5, 9: 4, 10: 3, 11: 2, 12: 1}

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

    def tile_probability(number):
        if number is None or number < 2 or number > 12:
            return 0.0
        return (6 - abs(number - 7)) / 36.0

    from collections import deque

    player_has_harbor = False
    for iv in intersections:
        if iv.get("occupiedBy") == player_id:
            hv = iv.get("harbor", iv.get("harbour", None))
            if hv not in (None, "None"):
                player_has_harbor = True
                break

    BASE_HARBOUR_VALUE = 3 / 36.0
    HARBOUR_VALUE = 0.0 if player_has_harbor else BASE_HARBOUR_VALUE

    player_roads = [r for r in roads if r.get("player") == player_id]

    if not player_roads:
        return False, None

    # collect all nodes that appear in any player's road (ignore None)
    road_nodes = set()
    for r in player_roads:
        a = r.get("a"); b = r.get("b")
        if a is not None:
            road_nodes.add(a)
        if b is not None:
            road_nodes.add(b)

    # helper: intersection occupied checks
    def is_occupied_by_any(iv):
        occ = iv.get("occupiedBy")
        return occ is not None and occ != "None"

    def is_occupied_by_player(iv, pid):
        occ = iv.get("occupiedBy")
        return occ == pid

    # endpoints used later (filter out indices out of range and nodes already occupied by player)
    endpoints = {n for n in road_nodes if 0 <= n < len(intersections) and not is_occupied_by_player(intersections[n], player_id)}

    # 1) Check buildable now from the road endpoints themselves
    buildable_now = []
    scored_future_candidates = []

    for node in sorted(endpoints):
        if not (0 <= node < len(intersections)):
            continue
        iv = intersections[node]

        if is_occupied_by_any(iv):
            # can't build on an occupied intersection
            pass

        # rule: no adjacent occupied intersections
        neighbor_blocked = False
        for n in iv.get("neighbors", []):
            if 0 <= n < len(intersections):
                if is_occupied_by_any(intersections[n]):
                    neighbor_blocked = True
                    break

        # compute score (tile probabilities + harbour)
        score = 0.0
        for hi in iv.get("adjacentHexes", []):
            if 0 <= hi < len(board):
                tile = board[hi]
                if tile:
                    score += tile_probability(tile.get("number"))

        hv = iv.get("harbor", iv.get("harbour", None))
        if hv not in (None, "None"):
            score += HARBOUR_VALUE

        scored_future_candidates.append((score, node))

        if (not is_occupied_by_any(iv)) and (not neighbor_blocked):
            buildable_now.append((score, node))

    if buildable_now:
        buildable_now.sort(reverse=True, key=lambda x: (x[0], x[1]))
        best_score, best_node = buildable_now[0]
        return True, best_node

    # 2) Look at distance-1 candidates (neighbors of endpoints, excluding endpoints themselves)
    neighbor_candidates = set()
    for node in endpoints:
        iv = intersections[node]
        for n2 in iv.get("neighbors", []):
            if 0 <= n2 < len(intersections):
                neighbor_candidates.add(n2)

    neighbor_candidates = {n for n in neighbor_candidates if 0 <= n < len(intersections) and n not in endpoints}

    def score_and_filter(candidate_nodes):
        """Given iterable of nodes, apply occupancy and adjacency rules and return scored list."""
        scored = []
        for node in sorted(candidate_nodes):
            iv = intersections[node]
            if is_occupied_by_any(iv):
                continue

            blocked_by_neighbor = False
            for nn in iv.get("neighbors", []):
                if 0 <= nn < len(intersections):
                    if is_occupied_by_any(intersections[nn]):
                        blocked_by_neighbor = True
                        break
            if blocked_by_neighbor:
                continue

            score = 0.0
            for hi in iv.get("adjacentHexes", []):
                if 0 <= hi < len(board):
                    tile = board[hi]
                    if tile:
                        score += tile_probability(tile.get("number"))
            hv = iv.get("harbor", iv.get("harbour", None))
            if hv not in (None, "None"):
                score += HARBOUR_VALUE

            scored.append((score, node))
        return scored

    scored_neighbors = score_and_filter(neighbor_candidates)

    if scored_neighbors:
        scored_neighbors.sort(reverse=True, key=lambda x: (x[0], x[1]))
        return False, scored_neighbors[0][1]

    # 3) FALLBACK: if no distance-1 candidates, try distance-2 (BFS up to depth 2 from road_nodes)
    # (this implements your "range of 2" fallback while keeping the same occupancy/neighbour rules)
    distance2_candidates = set()
    for start in road_nodes:
        if not (0 <= start < len(intersections)):
            continue
        # BFS up to depth 2
        q = deque([(start, 0)])
        visited = {start}
        while q:
            node, dist = q.popleft()
            if dist >= 2:
                continue
            iv = intersections[node]
            for nb in iv.get("neighbors", []):
                if not (0 <= nb < len(intersections)):
                    continue
                if nb in visited:
                    continue
                visited.add(nb)
                nd = dist + 1
                if nd == 2:
                    # exclude original road nodes (we want nodes two steps away, not the road nodes themselves)
                    if nb not in road_nodes:
                        distance2_candidates.add(nb)
                else:
                    q.append((nb, nd))

    # remove nodes already considered (endpoints or immediate neighbors)
    distance2_candidates = {n for n in distance2_candidates if n not in endpoints and n not in neighbor_candidates}

    scored_distance2 = score_and_filter(distance2_candidates)

    if scored_distance2:
        scored_distance2.sort(reverse=True, key=lambda x: (x[0], x[1]))
        return False, scored_distance2[0][1]

    # 4) final fallback: return best future candidate from the originally-scored endpoints
    if scored_future_candidates:
        scored_future_candidates.sort(reverse=True, key=lambda x: (x[0], x[1]))
        return False, scored_future_candidates[0][1]

    return False, None



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
        strategy_1 = {"settlement": set_loc}
        trad = {"i_need":None, "i_give": None}
        return strategy_1, trad
    
    missing_city, extra_city = compute_missing_and_extra(city_cost)
    if (player["settlements_left"] < 5 and sum(missing_city.values()) == 1 and len(extra_city) > 0) or player["settlements_left"] == 0:
        strategy_1 = {"city": city_loc}
        trad = {"i_need": missing_city, "i_give": extra_city}
        return strategy_1, trad

    missing_set, extra_set = compute_missing_and_extra(settlement_cost)
    if player["settlements_left"] > 0 and t == True and sum(missing_set.values()) == 1 and len(extra_set) > 0:
        strategy_1 = {"settlement": set_loc}
        trad = {"i_need": missing_set, "i_give": extra_set}
        return strategy_1, trad
    
    if can_afford(player, card_cost) == True:
        strategy_1 = {"card": None}
        trad = {"i_need":None, "i_give": None}
        return strategy_1, trad
    
    if can_afford(player, road_cost) == True and t == False:
        strategy_1 = {"road": set_loc}
        trad = {"i_need":None, "i_give": None}
        return strategy_1, trad
    
    missing_card, extra_card = compute_missing_and_extra(card_cost)
    if player["settlements_left"] < 5 and sum(missing_card.values()) == 1 and len(extra_card) > 0:
        strategy_1 = {"card": None}
        trad = {"i_need": missing_card, "i_give": extra_card}
        return strategy_1, trad
    
    missing_road, extra_road = compute_missing_and_extra(road_cost)
    if player["settlements_left"] < 5 and sum(missing_road.values()) == 1 and len(extra_road) > 0 and t == False:
        strategy_1 = {"road": set_loc}
        trad = {"i_need": missing_road, "i_give": extra_road}
        return strategy_1, trad
    
    total_res = sum(resources.values())

    if total_res > 7:
        i_give = {}
        i_need = {}

        for res, amt in resources.items():
            if amt > 3:
                # give surplus (cap to 2 per resource)
                i_give[res] = min(amt - 3, 2)
            elif amt <= 1:
                i_need[res] = 1

        # only suggest trade if it makes sense
        if i_give and i_need:
            return {}, {"i_need": i_need, "i_give": i_give}

    # ---------- 4) Do nothing ----------
    return {}, {"i_need": None, "i_give": None}

    

print(settlement_possible(0,data2.data["roads"],data2.data["intersection"], data2.data["board"]))


def card_decision(player_id, players, board, intersections, robber, roads=None):

    roads = roads or []
    player = players[player_id]
    cards = player.get("dev_cards", {}) or {}

    # helper: does robber sit next to one of our buildings?
    def robber_on_our_tile():
        if robber is None:
            return False
        for iv in intersections:
            if iv.get("occupiedBy") == player_id:
                if robber in iv.get("adjacentHexes", []):
                    return True
        return False

    # --- 1) KNIGHT logic ---
    try:
        knight_count = int(cards.get("knight", 0))
    except Exception:
        knight_count = 0

    try:
        if (knight_count == 1 and robber_on_our_tile()) or knight_count > 1:
            # move robber now to hurt strongest opponent
            if "robber_decision" in globals():
                rd = robber_decision(player_id, players, board, intersections, robber)
            else:
                rd = None
            if rd:
                tile_idx, ttype, num = rd
                return {"action": "play_knight", "target": tile_idx, "type": ttype, "number": num}
            else:
                return {"action": "play_knight", "reason": "no good target found"}
        if knight_count >= 2 and (not robber_on_our_tile()):
            # we have 2+ knights and robber isn't on our tiles -> proactively move robber
            if "robber_decision" in globals():
                rd = robber_decision(player_id, players, board, intersections, robber)
            else:
                rd = None
            if rd:
                tile_idx, ttype, num = rd
                return {"action": "play_knight", "target": tile_idx, "type": ttype, "number": num}
            else:
                return {"action": "play_knight", "reason": "no good target found"}
    except Exception:
        # don't crash; fall through to other cards
        pass

    # --- 2) YEAR OF PLENTY / MONOPOLY logic ---
    try:
        plenty_count = int(cards.get("plenty", 0))
    except Exception:
        plenty_count = 0
    try:
        monopoly_count = int(cards.get("monopoly", 0))
    except Exception:
        monopoly_count = 0

    # Ask in_game_strat whether it suggests a trade (we pass empty roads if not available)
    trad = None
    try:
        if "in_game_strat" in globals():
            # some implementations of in_game_strat expect (players, player_id, intersections, roads, board)
            # but you may have a different signature — adjust if needed.
            strat_result = in_game_strat(players, player_id, intersections, roads, board)
            if strat_result is not None:
                _, trad = strat_result
    except Exception:
        trad = None

    if (plenty_count > 0 or monopoly_count > 0) and trad:
        i_need = trad.get("i_need") if isinstance(trad, dict) else None
        # i_need expected to be a dict like {"wheat":1} or similar
        if i_need:
            # pick the first missing resource
            missing_res = None
            if isinstance(i_need, dict):
                for k in i_need:
                    missing_res = k
                    break
            elif isinstance(i_need, list) and i_need:
                missing_res = i_need[0]

            # pick the resource we have the least of (for plenty second pick)
            resources = player.get("resources", {}) or {}
            # ensure all standard keys exist with 0 default
            _keys = ["wood", "brick", "sheep", "wheat", "ore"]
            for kk in _keys:
                resources.setdefault(kk, 0)
            least_res = min(resources.items(), key=lambda kv: kv[1])[0]

            if plenty_count > 0:
                # Year of Plenty gives two resources: we pick the missing and our least held resource
                return {"action": "play_plenty", "take": [missing_res, least_res]}
            else:
                # Monopoly: choose the missing resource (takes all of that type)
                return {"action": "play_monopoly", "take": missing_res}

           # --- 3) TWO ROADS logic (CORRECT, settlement-aligned) ---
    try:
        road_card_count = int(cards.get("road", 0))
    except Exception:
        road_card_count = 0

    if road_card_count <= 0:
        return None

    # settlement_possible already encodes legality + best target
    try:
        can_build, target = settlement_possible(player_id, roads, intersections, board)
    except Exception:
        return None

    if target is None or can_build:
        return None

    from collections import deque

    # build adjacency graph from intersections
    adj = {
        i: set(iv.get("neighbors", []))
        for i, iv in enumerate(intersections)
    }

    # collect player road nodes + existing edges
    player_nodes = set()
    existing_edges = set()
    for r in roads:
        a, b = r.get("a"), r.get("b")
        if a is None or b is None:
            continue
        existing_edges.add(tuple(sorted((a, b))))
        if r.get("player") == player_id:
            player_nodes.update([a, b])

    def edge_free(a, b):
        return tuple(sorted((a, b))) not in existing_edges

    def passable(n):
        occ = intersections[n].get("occupiedBy")
        return occ in (None, "None", player_id)

    def blocked_by_neighbor(n):
        for nb in intersections[n].get("neighbors", []):
            if 0 <= nb < len(intersections):
                occ = intersections[nb].get("occupiedBy")
                if occ not in (None, "None", player_id):
                    return True
        return False

    # --- BFS from player's road network (depth ≤ 2) ---
    q = deque()
    parent = {}
    dist = {}

    for s in player_nodes:
        q.append(s)
        dist[s] = 0
        parent[s] = None

    found = False
    while q:
        cur = q.popleft()
        if dist[cur] == 2:
            continue
        for nb in adj[cur]:
            if nb in dist:
                continue
            if not edge_free(cur, nb):
                continue
            if not passable(nb):
                continue
            if blocked_by_neighbor(nb):
                continue
            dist[nb] = dist[cur] + 1
            parent[nb] = cur
            if nb == target:
                found = True
                q.clear()
                break
            q.append(nb)

    if not found:
        return None

    # --- reconstruct path ---
    path = []
    n = target
    while parent[n] is not None:
        path.append((parent[n], n))
        n = parent[n]
    path.reverse()

    # path length determines behavior
    if len(path) == 2:
        # perfect: exactly two roads to target
        return {
            "action": "play_two_roads",
            "edges": [{"a": a, "b": b} for a, b in path]
        }

    if len(path) == 1:
        # one road to target → add best second road
        first_edge = path[0]
        new_nodes = set(player_nodes)
        new_nodes.add(first_edge[1])
        new_edges = set(existing_edges)
        new_edges.add(tuple(sorted(first_edge)))

        best_second = None
        best_score = -1

        def settlement_score(n):
            score = 0.0
            for hi in intersections[n].get("adjacentHexes", []):
                if 0 <= hi < len(board):
                    tile = board[hi]
                    if tile and tile.get("number"):
                        score += (6 - abs(tile["number"] - 7)) / 36.0
            if intersections[n].get("harbor") not in (None, "None"):
                score += 3 / 36.0
            return score

        for a in new_nodes:
            for b in adj[a]:
                if tuple(sorted((a, b))) in new_edges:
                    continue
                if not passable(b):
                    continue
                if blocked_by_neighbor(b):
                    continue
                sc = settlement_score(b)
                if sc > best_score:
                    best_score = sc
                    best_second = (a, b)

        if best_second:
            return {
                "action": "play_two_roads",
                "edges": [
                    {"a": first_edge[0], "b": first_edge[1]},
                    {"a": best_second[0], "b": best_second[1]},
                ]
            }

    return None




print(card_decision(0,data2.data["players"], data2.data["board"], data2.data["intersection"], data2.data["robber_tile"], data2.data["roads"]))

    
