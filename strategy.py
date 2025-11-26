import data

strategy = ["city", "settlment", "cards"]

i = data.inter
b = data.board
i2 = data.inter2


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



def first_two_settlements(intersections, board):
    weight_ore = 12
    weight_wheat = 11
    weight_sheep = 6
    weight_brick = 9
    weight_wood = 9

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
            type_score = {
                "wheat": weight_wheat,
                "ore": weight_ore,
                "wood": weight_wood,
                "sheep": weight_sheep,
                "brick": weight_brick
            }[tile["type"]]

            # final tile score
            scores.append(type_score * num_score)

        best.append(sum(scores))

    # -----------------------------------------
    # PICK HIGHEST-SCORING INDEX
    # -----------------------------------------
    winner = max(range(len(best)), key=lambda i: best[i])

    return winner





print(look_at_board(b))