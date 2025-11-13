# Flask backend for Catan board editor (in-memory storage)
from flask import Flask, render_template, jsonify, request

app = Flask(__name__, template_folder='templates')

# === In-memory storage ===
saved_games = []  # list of boards (each = dict with 'board' and 'harbours')
current_board = None
current_harbours = None
players = []

@app.route('/')
def index():
    return render_template('index.html')

# === Board API ===
@app.route('/api/board', methods=['GET'])
def get_board():
    global current_board, current_harbours
    if current_board is None:
        return jsonify({'error': 'no board saved'}), 404
    return jsonify({
        'board': current_board,
        'harbours': current_harbours
    })

@app.route('/api/board', methods=['POST'])
def post_board():
    global current_board, current_harbours, saved_games
    try:
        payload = request.get_json()
        board = payload.get('board')
        harbours = payload.get('harbours', [])

        if not isinstance(board, list) or len(board) != 19:
            return 'Board must be an array of 19 tile objects', 400
        if not isinstance(harbours, list) or len(harbours) != 9:
            return 'Harbours must be an array of 9 objects', 400

        current_board = board
        current_harbours = harbours
        saved_games.append({'board': board, 'harbours': harbours})
        return 'ok'
    except Exception as e:
        return str(e), 400


# === Players API ===
@app.route('/api/players', methods=['GET'])
def get_players():
    return jsonify(players)

@app.route('/api/players', methods=['POST'])
def post_players():
    global players
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return 'players must be a list', 400
        players = data
        return 'ok'
    except Exception as e:
        return str(e), 400


# === Start game endpoint ===
@app.route('/api/start', methods=['POST'])
def start_game():
    if not players:
        return 'no players set', 400
    if current_board is None:
        return 'no board set', 400
    return jsonify({'status': 'started', 'players': players})


# === Optional: view saved boards ===
@app.route('/api/saved', methods=['GET'])
def get_saved_games():
    """Returns a list of all saved boards in this server session."""
    return jsonify(saved_games)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
