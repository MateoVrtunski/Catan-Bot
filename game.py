# Flask backend for Catan (in-memory storage)
from flask import Flask, render_template, jsonify, request
from action import CatanGame

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
        "roads": ROADS
    })


# ========= PLACEMENT PHASE =========

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
        "intersection": int(intersection)
    })

    # Only update server intersections if we already have them
    for iv in INTERSECTIONS:
        if iv["id"] == int(intersection):
            iv["occupiedBy"] = int(player)
            iv["type"] = "settlement"
            break

    return jsonify({"ok": True})




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
        if not INTERSECTIONS:
            return jsonify({"error": "INTERSECTIONS not initialized"}), 400

        GAME = CatanGame(
            board=BOARD,
            harbours=HARBOURS,
            players=PLAYERS,
            intersections=INTERSECTIONS
        )

        events = GAME.distribute_initial_resources()
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

        if dice is None:
            # random roll
            result = GAME.roll_dice()
            # no need to update globals because GAME modifies PLAYERS/INTERSECTIONS in place
            return jsonify({"ok": True, "dice": result["dice"], "events": result["events"]})
        else:
            # manual dice -> just distribute resources for that number
            d = int(dice)
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

        # reflect back to global intersections (GAME.intersections references the same objects)
        for iv in INTERSECTIONS:
            if iv.get("id") == intersection or iv.get("id") is None and INTERSECTIONS.index(iv) == intersection:
                iv["occupiedBy"] = player
                iv["type"] = "settlement"
                break

        # record placement history (optional — keeps initial placement history too)
        PLACEMENTS.append({"player": player, "intersection": intersection})

        return jsonify({"ok": True, "message": msg}), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.post("/api/build/city")
def api_build_city():
    global GAME, INTERSECTIONS
    try:
        if GAME is None:
            return jsonify({"error": "game not started"}), 400
        data = request.get_json() or {}
        player = int(data.get("player"))
        intersection = int(data.get("intersection"))
        ok, msg = GAME.build_city(player, intersection)
        if not ok:
            return jsonify({"error": msg}), 400

        # update intersection type
        for iv in INTERSECTIONS:
            # handle stored ids or index
            if iv.get("id") == intersection or (iv.get("id") is None and INTERSECTIONS.index(iv) == intersection):
                iv["type"] = "city"
                break

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

