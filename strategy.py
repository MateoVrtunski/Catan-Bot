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
        # find settlements owned by this player (type == 'settlement')
        owned_settlements = [
            iv for iv in intersections
            if iv.get("occupiedBy") == player and iv.get("type") == "settlement"
        ]
        if len(owned_settlements) >= 1:
            # use the first found settlement (no placement order tracked here)
            first_iv = owned_settlements[0]
            for hi in first_iv.get("adjacentHexes", []):
                if 0 <= hi < len(board):
                    tile = board[hi]
                    if tile and tile.get("type") in local_strategy:
                        local_strategy[tile["type"]] = local_strategy.get(tile["type"], 0) - 2

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
        # neighbors of neighbor → distance 2
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

print(first_two_settlements(strategy, data.test,bo,0))