import data

strategy = ["base"]

i = data.inter
b = data.board
def first_two_settlements(intersections, board):
    weight_ore = 12
    weight_wheat = 11
    weight_sheep = 6
    weight_brick = 9
    weight_wood = 9

    result = []

    for iv in intersections:
        adj = iv.get("adjacentHexes", [])
        tiles = []

        # add existing adjacent hex tiles
        for hex_index in adj[:3]:               # take at most 3
            if 0 <= hex_index < len(board):
                tiles.append(board[hex_index])
            else:
                tiles.append(None)

        # if fewer than 3, pad with None
        while len(tiles) < 3:
            tiles.append(None)

        result.append(tiles)

    best = []

    for i in range(len(result)):
        scores = []  # store computed values instead of replacing j

        for j in result[i]:
            if j is None or j["type"] == "desert":
                scores.append(0)
                continue

            # number weight
            if j["number"] in (2, 12):
                num_score = 1
            elif j["number"] in (3, 11):
                num_score = 2
            elif j["number"] in (4, 10):
                num_score = 3
            elif j["number"] in (5, 9):
                num_score = 4
            elif j["number"] in (6, 8):
                num_score = 5
            else:
                num_score = 0

            # type weight
            type_weights = {
                "wheat": weight_wheat,
                "ore": weight_ore,
                "wood": weight_wood,
                "sheep": weight_sheep,
                "brick": weight_brick
            }

            type_score = type_weights[j["type"]]

            # final score
            scores.append(type_score * num_score)

        best.append(sum(scores))

        winner = 0

        for i in range(len(best)):
            if best[i] == max(best):
                winner = i

    return winner




    





print(first_two_settlements(i,b))