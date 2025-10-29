# Flask backend to serve the editor and provide a simple JSON API to store/load board & players
from flask import Flask, render_template, jsonify, request, send_from_directory
import json
import os

app = Flask(__name__, template_folder='templates')
DATA_FILE = 'data.json'

# helper - load data file (board, players)
def load_data():
    if not os.path.exists(DATA_FILE):
        return {'board': None, 'players': []}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return {'board': None, 'players': []}

# helper - save data file
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

# Basic board endpoints
@app.route('/api/board', methods=['GET'])
def get_board():
    data = load_data()
    if data.get('board') is None:
        return jsonify({'error': 'no board saved'}), 404
    return jsonify(data['board'])

@app.route('/api/board', methods=['POST'])
def post_board():
    try:
        board = request.get_json()
        if not isinstance(board, list) or len(board) != 19:
            return 'Board must be an array of 19 tile objects', 400
        data = load_data()
        data['board'] = board
        save_data(data)
        return 'ok'
    except Exception as e:
        return str(e), 400

# Players endpoints
@app.route('/api/players', methods=['GET'])
def get_players():
    data = load_data()
    return jsonify(data.get('players', []))

@app.route('/api/players', methods=['POST'])
def post_players():
    try:
        players = request.get_json()
        if not isinstance(players, list):
            return 'players must be a list', 400
        data = load_data()
        data['players'] = players
        save_data(data)
        return 'ok'
    except Exception as e:
        return str(e), 400

# Simple start-game endpoint (placeholder for further logic)
@app.route('/api/start', methods=['POST'])
def start_game():
    # Here you would implement initial placement, turn order etc.
    data = load_data()
    players = data.get('players', [])
    if not players:
        return 'no players set', 400
    # placeholder response
    return jsonify({'status':'started','players':players})

if __name__ == '__main__':
    # create data file if missing
    if not os.path.exists(DATA_FILE):
        save_data({'board': None, 'players': []})
    app.run(host='0.0.0.0', port=5000, debug=True)

