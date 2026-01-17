# Here are the bot decisions made
import data, data2
import linear_program




# Deciding the first two settlment is the most important part in Catan, the bot decision is based on the strategy chosen for the game
def first_two_settlements(intersections, board, player=None):
   
    local_strategy = dict(linear_program.choose_strategy_from_board(board)["winner"])

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
            total += 10

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

    road_nodes = set()
    for r in player_roads:
        a = r.get("a"); b = r.get("b")
        if a is not None:
            road_nodes.add(a)
        if b is not None:
            road_nodes.add(b)

    def is_occupied_by_any(iv):
        occ = iv.get("occupiedBy")
        return occ is not None and occ != "None"

    def is_occupied_by_player(iv, pid):
        occ = iv.get("occupiedBy")
        return occ == pid

    endpoints = {n for n in road_nodes if 0 <= n < len(intersections) and not is_occupied_by_player(intersections[n], player_id)}

    buildable_now = []
    scored_future_candidates = []

    for node in sorted(endpoints):
        if not (0 <= node < len(intersections)):
            continue
        iv = intersections[node]

        if is_occupied_by_any(iv):
            pass

        neighbor_blocked = False
        for n in iv.get("neighbors", []):
            if 0 <= n < len(intersections):
                if is_occupied_by_any(intersections[n]):
                    neighbor_blocked = True
                    break

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

    neighbor_candidates = set()
    for node in endpoints:
        iv = intersections[node]
        for n2 in iv.get("neighbors", []):
            if 0 <= n2 < len(intersections):
                neighbor_candidates.add(n2)

    neighbor_candidates = {n for n in neighbor_candidates if 0 <= n < len(intersections) and n not in endpoints}

    def score_and_filter(candidate_nodes):
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

    for start in road_nodes:
        if not (0 <= start < len(intersections)):
            continue

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
                    if nb not in road_nodes:
                        distance2_candidates.add(nb)
                else:
                    q.append((nb, nd))

    distance2_candidates = {n for n in distance2_candidates if n not in endpoints and n not in neighbor_candidates}

    scored_distance2 = score_and_filter(distance2_candidates)

    if scored_distance2:
        scored_distance2.sort(reverse=True, key=lambda x: (x[0], x[1]))
        return False, scored_distance2[0][1]

    if scored_future_candidates:
        scored_future_candidates.sort(reverse=True, key=lambda x: (x[0], x[1]))
        return False, scored_future_candidates[0][1]

    return False, None



def city_placement(player_id, intersections, board):
    
    def tile_probability(number):
        if number is None or number < 2 or number > 12:
            return 0
        return (6 - abs(number - 7)) / 36  

    best_score = -1
    best_intersection = None

    for iv in intersections:
        if iv.get("occupiedBy") == player_id and iv.get("type") == "settlement":
            
            total_prob = 0
            
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

# Main function for the bot decision

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

    if can_afford(player, city_cost) == True and player["settlements_left"] < 5:
        strategy_1 = {"city": city_loc}
        trad_1 = {"i_need":None, "i_give": None}
        return strategy_1, trad_1
    
    if can_afford(player, settlement_cost) == True and player["settlements_left"] > 0 and t == True:
        strategy_2 = {"settlement": set_loc}
        trad_2 = {"i_need":None, "i_give": None}
        return strategy_2, trad_2
    
    missing_city, extra_city = compute_missing_and_extra(city_cost)
    missing_set, extra_set = compute_missing_and_extra(settlement_cost)
    missing_card, extra_card = compute_missing_and_extra(card_cost)
    missing_road, extra_road = compute_missing_and_extra(road_cost)

    city_clause = (player["settlements_left"] < 5 and sum(missing_city.values()) == 1 and len(extra_city) > 0) or player["settlements_left"] == 0
    settlment_clause = player["settlements_left"] > 0 and t == True and sum(missing_set.values()) == 1 and len(extra_set) > 0
    road_clause = sum(missing_road.values()) == 1 and len(extra_road) > 0 and t == False
    card_clause = sum(missing_card.values()) == 1 and len(extra_card) > 0

    if city_clause and can_afford(player, card_cost) == True:
        strategy_1 = {"city": city_loc, "card": None}
        trad = {"i_need": missing_city, "i_give": extra_city}
        return strategy_1, trad
    
    if city_clause and can_afford(player, road_cost) == True and t == False:
        strategy_1 = {"city": city_loc, "road": set_loc}
        trad = {"i_need": missing_city, "i_give": extra_city}
        return strategy_1, trad
    
    if city_clause and card_clause:
        strategy_1 = {"city": city_loc, "card": None}
        trad = {"i_need": missing_city, "i_give": extra_city, "i_need_2": missing_card, "i_give_2": extra_card}
        return strategy_1, trad
    
    if city_clause and road_clause:
        strategy_1 = {"city": city_loc, "road": set_loc}
        trad = {"i_need": missing_city, "i_give": extra_city, "i_need_2": missing_road, "i_give_2": extra_road}
        return strategy_1, trad
    
    if city_clause:
        strategy_1 = {"city": city_loc}
        trad = {"i_need": missing_city, "i_give": extra_city}
        return strategy_1, trad
    
    if settlment_clause and can_afford(player, card_cost) == True:
        strategy_1 = {"settlement": set_loc, "card": None}
        trad = {"i_need": missing_set, "i_give": extra_set}
        return strategy_1, trad
    
    if settlment_clause and card_clause:
        strategy_1 = {"settlement": set_loc, "card": None}
        trad = {"i_need": missing_set, "i_give": extra_set, "i_need_2": missing_card, "i_give_2": extra_card}
        return strategy_1, trad
    
    if settlment_clause:
        strategy_1 = {"settlement": set_loc}
        trad = {"i_need": missing_set, "i_give": extra_set}
        return strategy_1, trad
    
    if can_afford(player, card_cost) == True:
        strategy_1 = {"card": None}
        trad = {"i_need": None, "i_give": None}
        return strategy_1, trad
    
    if card_clause and can_afford(player, road_cost) and t == False:
        strategy_1 = {"card": None, "road": set_loc}
        trad = {"i_need": missing_card, "i_give": extra_card}
        return strategy_1, trad
    
    if card_clause and road_clause:
        strategy_1 = {"card": None, "road": set_loc}
        trad = {"i_need": missing_card, "i_give": extra_card, "i_need_2": missing_road, "i_give_2": extra_road}
        return strategy_1, trad
    
    if card_clause:
        strategy_1 = {"card": None}
        trad = {"i_need": missing_card, "i_give": extra_card}
        return strategy_1, trad
    
    if can_afford(player, road_cost) and t == False:
        strategy_1 = {"road": set_loc}
        trad = {"i_need": None, "i_give": None}
        return strategy_1, trad
    
    if road_clause:
        strategy_1 = {"road": set_loc}
        trad = {"i_need": missing_road, "i_give": extra_road}
        return strategy_1, trad
    
    total_res = sum(resources.values())

    if total_res > 2:
        i_give = {}
        i_need = {}

        for res, amt in resources.items():
            if amt > 3:
                i_give[res] = min(amt - 3, 2)
            elif amt <= 1:
                i_need[res] = 1

        if i_give and i_need:
            return {}, {"i_need": i_need, "i_give": i_give}

    return {}, {"i_need": None, "i_give": None}

    


def card_decision(player_id, players, board, intersections, robber, roads=None):

    roads = roads or []
    player = players[player_id]
    cards = player.get("dev_cards", {}) or {}

    def robber_on_our_tile():
        if robber is None:
            return False
        for iv in intersections:
            if iv.get("occupiedBy") == player_id:
                if robber in iv.get("adjacentHexes", []):
                    return True
        return False

    # Card: Knight, we play the knight if we have 2 of them, the robber is on our land or we already played 2 so we play it to get largest army
    played = player["knights_played"]
    try:
        knight_count = int(cards.get("knight", 0))
    except Exception:
        knight_count = 0

    try:
        if (knight_count == 1 and robber_on_our_tile()) or knight_count > 1 or played > 1:
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
        pass
    

    t,set_loc = settlement_possible(player_id, roads, intersections, board)

    #Cards: Years of plenty and monopoly, looks at what we are missing for next big decision and asks for it

    try:
        plenty_count = int(cards.get("plenty", 0))
    except Exception:
        plenty_count = 0
    try:
        monopoly_count = int(cards.get("monopoly", 0))
    except Exception:
        monopoly_count = 0

    trad = None
    try:
        if "in_game_strat" in globals():
            strat_result = in_game_strat(players, player_id, intersections, roads, board)
            if strat_result is not None:
                _, trad = strat_result
    except Exception:
        trad = None

    if (plenty_count > 0 or monopoly_count > 0):
        i_need = None

        if trad and isinstance(trad, dict):
            i_need = trad.get("i_need")

        if not i_need:
            if t:
                target_cost = settlement_cost
            else:
                target_cost = city_cost

            i_need = {}
            for res, need in target_cost.items():
                have = player["resources"].get(res, 0)
                if have < need:
                    i_need[res] = need - have

        if isinstance(i_need, dict) and i_need:
            missing_resources = []
            for res, amt in i_need.items():
                missing_resources.extend([res] * amt)

            if 1 <= len(missing_resources) <= 2:
                resources = player.get("resources", {}) or {}
                _keys = ["wood", "brick", "sheep", "wheat", "ore"]
                for kk in _keys:
                    resources.setdefault(kk, 0)

                missing_resources.sort(key=lambda r: resources.get(r, 0))

                if plenty_count > 0:
                    take = missing_resources[:2]

                    if len(take) == 1:
                        least_res = min(resources.items(), key=lambda kv: kv[1])[0]
                        take.append(least_res)

                    return {
                        "action": "play_plenty",
                        "take": take
                    }
                
                if monopoly_count > 0:
                    return {
                        "action": "play_monopoly",
                        "take": missing_resources[0]
                    }


    # Card: Two Road, searches the best two roads to build.
    try:
        road_card_count = int(cards.get("road", 0))
    except Exception:
        road_card_count = 0

    if road_card_count <= 0:
        return None

    try:
        can_build, target = settlement_possible(player_id, roads, intersections, board)
    except Exception:
        return None

    if target is None or can_build:
        return None

    from collections import deque

    adj = {
        i: set(iv.get("neighbors", []))
        for i, iv in enumerate(intersections)
    }

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

    path = []
    n = target
    while parent[n] is not None:
        path.append((parent[n], n))
        n = parent[n]
    path.reverse()

    if len(path) == 2:
        return {
            "action": "play_two_roads",
            "edges": [{"a": a, "b": b} for a, b in path]
        }

    if len(path) == 1:
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


    
