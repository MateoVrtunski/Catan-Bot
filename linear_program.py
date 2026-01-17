
import data2

import pulp as pl

RESOURCE_ORDER = ["ore", "wheat", "sheep", "brick", "wood"]

# Here is the linear program for the 2 most common startegy in Catan, based on the results the strategy is chosen

def _rarity_from_board(board):

    def num_score(num):
        if num in (2, 12): return 1
        if num in (3, 11): return 2
        if num in (4, 10): return 3
        if num in (5, 9): return 4
        if num in (6, 8): return 5
        return 0

    rarity = {r: 0 for r in RESOURCE_ORDER}

    for t in board:
        typ = t.get("type")
        num = t.get("number")
        if typ in rarity:
            rarity[typ] += num_score(num)

    return {r: rarity[r] / 36.0 for r in RESOURCE_ORDER}


def _solve_city_lp(freq, var_bounds=(0, 10)):

    low, high = var_bounds
    prob = pl.LpProblem("City_Strategy", pl.LpMaximize)

    a = pl.LpVariable("ore", lowBound=low, upBound=high)
    b = pl.LpVariable("wheat", lowBound=low, upBound=high)
    c = pl.LpVariable("sheep", lowBound=low, upBound=high)
    d = pl.LpVariable("wood", lowBound=low, upBound=high)
    e = pl.LpVariable("brick", lowBound=low, upBound=high)

    prob += (
        3* freq["ore"] * a +
        2* freq["wheat"] * b -
        freq["sheep"] * c -
        freq["wood"]  * d -
        freq["brick"] * e
    )

    prob += 5*d + 5*e + 5*c >= 4*a + 7*b
    prob += 4*a + 7*b >= 5*c + 4*d + 4*e
    prob += 5*a >= 5.5*b
    prob += 5*b >= 5.5*c
    prob += 5*b >= 5.5*d
    prob += 5*c >= 3*d + 3*e
    prob += d == e

    prob.solve(pl.PULP_CBC_CMD(msg=False))

    return {
        "ore": float(a.value()),
        "wheat": float(b.value()),
        "sheep": float(c.value()),
        "brick": float(e.value()),
        "wood": float(d.value()),
    }


def _solve_settlement_lp(freq, var_bounds=(0, 10)):

    low, high = var_bounds
    prob = pl.LpProblem("Settlement_Strategy", pl.LpMaximize)

    a = pl.LpVariable("ore", lowBound=low, upBound=high)
    b = pl.LpVariable("wheat", lowBound=low, upBound=high)
    c = pl.LpVariable("sheep", lowBound=low, upBound=high)
    d = pl.LpVariable("wood", lowBound=low, upBound=high)
    e = pl.LpVariable("brick", lowBound=low, upBound=high)

    prob += (
        freq["wood"]  * d +
        freq["brick"] * e +
        freq["wheat"] * b +
        freq["sheep"] * c -
        freq["ore"]   * a
    )

    prob += 5*d + 5*e + 5*c + 5*b >= 12*a + 8*b
    prob += 4*d + 4*e + 4*c + 4*b <= 11*a + 9*b
    prob += 4*d + 4*e >= 9*b
    prob += 8*b >= 9*c
    prob += d == e

    prob.solve(pl.PULP_CBC_CMD(msg=False))

    return {
        "ore": float(a.value()),
        "wheat": float(b.value()),
        "sheep": float(c.value()),
        "brick": float(e.value()),
        "wood": float(d.value()),
    }


def choose_strategy_from_board(board):

    freq_1 = _rarity_from_board(board)
    freq={}
    freq["ore"] = freq_1["ore"]/3
    freq["brick"] = freq_1["brick"]/3
    freq["wood"] = freq_1["wood"]/4
    freq["wheat"] = freq_1["wheat"]/4
    freq["sheep"] = freq_1["sheep"]/4

    city_w = _solve_city_lp(freq)
    sett_w = _solve_settlement_lp(freq)

    def score(weights):
        return sum(weights[r] * freq[r] for r in freq)

    city_score = score(city_w)
    sett_score = score(sett_w)

    strategy_choice = "city" if city_score <= sett_score else "settlement"
    if strategy_choice == "city":
        winner = city_w
    else:
        winner = sett_w

    return {
        "strategy_choice": strategy_choice,
        "winner": winner
    }


board = data2.data["board"]

#print(_solve_settlement_lp(_rarity_from_board(board)))