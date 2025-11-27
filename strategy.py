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

λ = 0.2  # penalty for ignoring other resources

# Objective = prioritize city resources but not insanely
prob += 3*a + 2*b - c - d - e, "City_Strategy_Objective"

# Priority structure

prob += 5*d + 5*e + 5*c >= 4*a + 7*b
prob += 4*a + 7*b >= 5*c + 4*d + 4*e
prob += 5*a >= 5.5*b
prob += 5*c >= 2*d + 2*e
prob += d == e


prob.solve()

print("Status:", pl.LpStatus[prob.status])
print("---- Resulting weights ----")
print("ore =", a.value())
print("wheat =", b.value())
print("sheep =", c.value())
print("wood =", d.value())
print("brick =", e.value())

i = data.inter
bo = data.board
i2 = data.inter2



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



def first_two_settlements(strategy, intersections, board):
     
    result = []

    # -----------------------------------------
    # BUILD TILE-LIST FOR EACH INTERSECTION
    # -----------------------------------------
    for iv in intersections:

        # NEW RULE: if occupied, zero value
        if iv.get("occupiedBy") is not None:
            result.append([None, None, None])
            continue

        blocked = False
        for nid in iv.get("neighbors", []):
            if 0 <= nid < len(intersections) and intersections[nid].get("occupiedBy") is not None:
                blocked = True
                break

        if blocked:
            result.append([None, None, None])
            continue

        adj = iv.get("adjacentHexes", [])
        tiles = []

        # add existing adjacent hex tiles
        for hex_index in adj[:3]:  # take at most 3
            if 0 <= hex_index < len(board):
                tiles.append(board[hex_index])
            else:
                tiles.append(None)

        # if fewer than 3, pad with None
        while len(tiles) < 3:
            tiles.append(None)

        result.append(tiles)

    # -----------------------------------------
    # SCORE EACH INTERSECTION
    # -----------------------------------------
    best = []

    for i in range(len(result)):
        tiles = result[i]
        scores = []  # store tile scores

        # if occupied → we already forced [None,None,None]
        if tiles == [None, None, None]:
            best.append(0)
            continue

        for tile in tiles:
            if tile is None or tile["type"] == "desert":
                scores.append(0)
                continue

            # number weight
            if tile["number"] in (2, 12):
                num_score = 1
            elif tile["number"] in (3, 11):
                num_score = 2
            elif tile["number"] in (4, 10):
                num_score = 3
            elif tile["number"] in (5, 9):
                num_score = 4
            elif tile["number"] in (6, 8):
                num_score = 5
            else:
                num_score = 0

            # type weight
            weight = strategy[tile["type"]]

            # final tile score
            scores.append(weight * num_score)

        best.append(sum(scores))

    # -----------------------------------------
    # PICK HIGHEST-SCORING INDEX
    # -----------------------------------------
    winner = max(range(len(best)), key=lambda i: best[i])

    return winner



print(first_two_settlements(strategy, i, bo))