# Flask backend for Catan (in-memory storage)
from flask import Flask, render_template, jsonify, request

app = Flask(__name__, template_folder='templates')

# === In-memory state ===
BOARD = []           # List of 19 tile objects
HARBOURS = []        # List of 9 harbour objects
PLAYERS = []         # [{name, color}, ...]
PLACEMENTS = []      # placement records

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
            cleaned.append({"name": name, "color": color})

    PLAYERS = cleaned
    return jsonify({"ok": True, "players": PLAYERS}), 200


# ========= GAME STATE =========

@app.get("/api/state")
def api_state():
    return jsonify({
        "board": BOARD,
        "harbours": HARBOURS,
        "players": PLAYERS,
        "placements": PLACEMENTS
    })


# ========= PLACEMENT PHASE =========

@app.post("/api/place")
def api_place():
    try:
        data = request.get_json()
        player = data.get("player")
        intersection = data.get("intersection")

        if player is None or intersection is None:
            return "player and intersection required", 400

        PLACEMENTS.append({
            "player": int(player),
            "intersection": int(intersection)
        })

        return jsonify({"ok": True}), 200

    except Exception as e:
        return str(e), 400


@app.post("/api/placements/finalize")
def api_finalize_placements():
    return jsonify({"ok": True, "placements": PLACEMENTS}), 200


# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
