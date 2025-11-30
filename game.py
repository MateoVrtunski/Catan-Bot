# Flask backend for Catan (in-memory storage)
from flask import Flask, render_template, jsonify, request
from action import CatanGame
from strategy import first_two_settlements, strategy as STRATEGY

GAME = None

app = Flask(__name__, template_folder='templates')

# === In-memory state ===
BOARD = []           # List of 19 tile objects
HARBOURS = []        # List of 9 harbour objects
PLAYERS = []         # [{name, color}, ...]
PLACEMENTS = []      # placement records
ROADS = []   # list of {player:int, a:int, b:int}
INTERSECTIONS = []
# ========== ROUTES ==========

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/players")
def players_page():
    return render_template("players.html")

@app.route("/placement")
def placement_page():
    return render_template("placement.html")

@app.route("/catan")
def catan_page():
    return render_template("catan.html")

# ========= BOARD API =========

@app.get("/api/board")
def api_get_board():
    if not BOARD:
        return jsonify({"error": "no board saved"}), 404
    return jsonify({"board": BOARD, "harbours": HARBOURS})

@app.post("/api/board")
def api_save_board():
    try:
        data = request.get_json()
        board = data.get("board")
        harbours = data.get("harbours", [])

        if not isinstance(board, list) or len(board) != 19:
            return "Board must be an array of 19 tiles", 400
        if not isinstance(harbours, list) or len(harbours) != 9:
            return "Harbours must be an array of 9 objects", 400

        BOARD.clear()
        BOARD.extend(board)

        HARBOURS.clear()
        HARBOURS.extend(harbours)

        return jsonify({"ok": True}), 200

    except Exception as e:
        return str(e), 400



# ========= PLAYERS API =========

@app.get("/api/players")
def api_get_players():
    return jsonify(PLAYERS)

@app.post("/api/players")
def api_save_players():
    global PLAYERS
    data = request.get_json()
    players_raw = data.get("players") if isinstance(data, dict) else data

    if not isinstance(players_raw, list):
        return "Invalid payload", 400

    cleaned = []
    for p in players_raw:
        name = p.get("name")
        color = p.get("color", "gray")
        if name:
            cleaned.append(CatanGame.create_player(name, color))

    PLAYERS = cleaned
    return jsonify({"ok": True, "players": PLAYERS}), 200


# ========= GAME STATE =========

@app.get("/api/state")
def api_state():
    return jsonify({
        "board": BOARD,
        "harbours": HARBOURS,
        "players": PLAYERS,
        "placements": PLACEMENTS,
        "roads": ROADS,
        "intersection": INTERSECTIONS
    })


# ========= PLACEMENT PHASE =========
@app.get("/api/decision")
def api_decision():
    """
    Return decision for initial placement for a given player.
    Query param: player (int)
    Calls strategy.first_two_settlements(strategy, INTERSECTIONS, BOARD, player)
    Returns JSON: {"ok": True, "settlement": <idx>, "road": <idx|null>, "error": <msg?>}
    """
    global BOARD, INTERSECTIONS
    if first_two_settlements is None:
        return jsonify({"ok": False, "error": "strategy module or function not available on server"}), 500

    player = request.args.get("player", None)
    if player is None:
        return jsonify({"ok": False, "error": "player query parameter required"}), 400

    try:
        player_id = int(player)
    except Exception:
        return jsonify({"ok": False, "error": "player must be an integer"}), 400

    # Defensive: ensure we have board and intersections
    if not isinstance(BOARD, list) or not isinstance(INTERSECTIONS, list):
        return jsonify({"ok": False, "error": "server board or intersections not ready"}), 500

    # Call the strategy function. We pass STRATEGY dict (if available) and the server lists.
    try:
        # strategy function signature expected: (strategy, intersections, board, player=None)
        result = first_two_settlements(STRATEGY, INTERSECTIONS, BOARD, player=player_id)
        # result expected as (settlement_idx, road_idx) or similar
        if isinstance(result, tuple) or isinstance(result, list):
            settlement_idx = result[0]
            road_idx = result[1] if len(result) > 1 else None
        else:
            # allow functions that return dict
            settlement_idx = result.get("settlement") if isinstance(result, dict) else None
            road_idx = result.get("road") if isinstance(result, dict) else None

        print("=== DEBUG ===")
        print("PLAYER:", player_id)
        print("BOARD FROM SERVER:", BOARD)
        print("INTERSECTIONS FROM SERVER:", INTERSECTIONS[:5], "... total =", len(INTERSECTIONS))
        print("STRATEGY:", STRATEGY)
        print("=== END DEBUG ===")
        
        return jsonify({"ok": True, "settlement": settlement_idx, "road": road_idx})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/api/place")
def api_place():
    global PLACEMENTS, INTERSECTIONS

    data = request.get_json()
    player = data.get("player")
    intersection = data.get("intersection")

    if player is None or intersection is None:
        return "player and intersection required", 400

    # Save placement
    PLACEMENTS.append({
        "player": int(player),
        "intersection": int(intersection),
        "type": "settlement"
    })

    # Only update server intersections if we already have them
    for iv in INTERSECTIONS:
        if iv["id"] == int(intersection):
            iv["occupiedBy"] = int(player)
            iv["type"] = "settlement"
            break

    return jsonify({"ok": True})

@app.post("/api/road")
def api_save_road():
    global ROADS

    data = request.get_json()
    player = data.get("player")
    a = data.get("a")
    b = data.get("b")

    if player is None or a is None or b is None:
        return jsonify({"error": "player, a, b required"}), 400

    road = {
        "player": int(player),
        "a": int(a),
        "b": int(b)
    }

    # Prevent duplicates
    for r in ROADS:
        if (r["a"] == road["a"] and r["b"] == road["b"]) or (r["a"] == road["b"] and r["b"] == road["a"]):
            return jsonify({"error": "road already exists"}), 400

    ROADS.append(road)

    return jsonify({"ok": True, "road": road})



@app.post("/api/placements/finalize")
def api_finalize_placements():
    return jsonify({"ok": True, "placements": PLACEMENTS}), 200

@app.post("/api/intersections")
def api_save_intersections():
    global INTERSECTIONS
    data = request.get_json()
    inter = data.get("intersections")

    if not isinstance(inter, list):
        return "intersections must be a list", 400

    INTERSECTIONS = inter
    return jsonify({"ok": True})


@app.post("/api/start_game")
def api_start_game():
    global GAME

    try:
        # FIX: ensure placements & roads are included
        if not PLACEMENTS:
            return jsonify({"error": "No starting settlements"}), 400
        if not ROADS:
            return jsonify({"error": "No starting roads"}), 400

        GAME = CatanGame(
            board=BOARD,
            harbours=HARBOURS,
            players=PLAYERS,
            intersections=INTERSECTIONS,
            placements=PLACEMENTS,
            roads=ROADS
        )

        events = GAME.distribute_initial_resources(PLACEMENTS)
        return jsonify({"ok": True, "events": events})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------- Game action endpoints ----------

@app.post("/api/roll")
def api_roll():
    """Roll the dice or distribute based on provided dice value."""
    global GAME
    try:
        data = request.get_json() or {}
        dice = data.get("dice")

        if GAME is None:
            return jsonify({"error": "game not started"}), 400

        if isinstance(dice, str):
            dice = dice.strip()
            if not dice.isdigit():
                return jsonify({"error": "Dice must be an integer 2–12"}), 400

        d = int(dice)

        if d < 2 or d > 12:
            return jsonify({"error": "Dice must be between 2 and 12"}), 400

        events = GAME.distribute_resources(d)
        return jsonify({"ok": True, "dice": d, "events": events})

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.post("/api/build/settlement")
def api_build_settlement():
    global GAME, INTERSECTIONS, PLACEMENTS
    try:
        if GAME is None:
            return jsonify({"error": "game not started"}), 400

        data = request.get_json() or {}
        player = int(data.get("player"))
        intersection = int(data.get("intersection"))

        ok, msg = GAME.build_settlement(player, intersection)
        if not ok:
            return jsonify({"error": msg}), 400

        # --- Update INTERSECTIONS (always correct) ---
        # We assume server intersections ALWAYS use id == index
        iv = INTERSECTIONS[intersection]
        iv["occupiedBy"] = player
        iv["type"] = "settlement"
        iv["building"] = "settlement"   # ensures frontend sees it!

        # --- Update PLACEMENTS with correct type ---
        PLACEMENTS.append({
            "player": player,
            "intersection": intersection,
            "type": "settlement"
        })

        return jsonify({"ok": True, "message": msg}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.post("/api/build/city")
def api_build_city():
    global GAME, INTERSECTIONS, PLACEMENTS
    try:
        if GAME is None:
            return jsonify({"error": "game not started"}), 400

        data = request.get_json() or {}
        player = int(data.get("player"))
        intersection = int(data.get("intersection"))

        ok, msg = GAME.build_city(player, intersection)
        if not ok:
            return jsonify({"error": msg}), 400

        # --- Update intersection state ---
        iv = INTERSECTIONS[intersection]
        iv["type"] = "city"
        iv["building"] = "city"

        # --- Update PLACEMENTS entry for that intersection ---
        updated = False
        for p in PLACEMENTS:
            if p["intersection"] == intersection and p["player"] == player:
                p["type"] = "city"
                updated = True
                break

        # If, for some reason, no placement existed, add it
        if not updated:
            PLACEMENTS.append({
                "player": player,
                "intersection": intersection,
                "type": "city"
            })

        return jsonify({"ok": True, "message": msg}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.post("/api/build/road")
@app.post("/api/road")   # accept both for placement and in-game
def api_build_road():
    """Build a road: body {player:int, a:int, b:int}"""
    global GAME, ROADS
    try:
        if GAME is None:
            return jsonify({"error": "game not started"}), 400
        data = request.get_json() or {}
        player = int(data.get("player"))
        a = int(data.get("a"))
        b = int(data.get("b"))

        ok, msg = GAME.build_road(player, a, b)
        if not ok:
            return jsonify({"error": msg}), 400

        # append to global ROADS so /api/state shows them
        ROADS.append({"player": player, "a": a, "b": b})
        return jsonify({"ok": True, "road": {"player": player, "a": a, "b": b}, "message": msg}), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

