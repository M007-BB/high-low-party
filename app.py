import random
import string
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'party_secret_key_123'
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {}
DECK = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

@app.route('/')
def index():
    # สุ่มรหัสห้องให้ทันทีเมื่อเข้าหน้าแรก
    room_code = generate_room_code()
    return redirect(url_for('room_view', room_id=room_code))

@app.route('/room/<room_id>')
def room_view(room_id):
    return render_template('index.html', room_id=room_id)

@socketio.on('join_game')
def handle_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    
    if room not in rooms:
        rooms[room] = {
            'players': {},
            'base_card': None,
            'status': 'waiting'
        }
    
    rooms[room]['players'][request.sid] = {
        'name': username,
        'choice': None,
        'dealt_card': None,
        'is_wrong': False
    }

@socketio.on('start_round')
def handle_start_round(data):
    room = data['room']
    if room in rooms:
        base_card = random.choice(DECK)
        rooms[room]['base_card'] = base_card
        rooms[room]['status'] = 'guessing'
        
        for sid in rooms[room]['players']:
            rooms[room]['players'][sid]['choice'] = None
            rooms[room]['players'][sid]['dealt_card'] = None
            rooms[room]['players'][sid]['is_wrong'] = False
            
        emit('round_started', {'base_card': base_card, 'time_limit': 5}, room=room)

@socketio.on('submit_choice')
def handle_choice(data):
    room = data['room']
    choice = data['choice']
    if room in rooms and request.sid in rooms[room]['players']:
        rooms[room]['players'][request.sid]['choice'] = choice

@socketio.on('time_up')
def handle_time_up(data):
    room = data['room']
    if room not in rooms or rooms[room]['status'] != 'guessing':
        return
        
    rooms[room]['status'] = 'result'
    base_card = rooms[room]['base_card']
    wrong_players = []
    survived_players = []

    for sid, player in rooms[room]['players'].items():
        dealt_card = random.choice(DECK)
        player['dealt_card'] = dealt_card
        choice = player['choice']
        
        is_wrong = False
        if choice is None:
            is_wrong = True
        elif choice == 'HIGH' and dealt_card <= base_card:
            is_wrong = True
        elif choice == 'LOW' and dealt_card >= base_card:
            is_wrong = True
            
        player['is_wrong'] = is_wrong
        if is_wrong:
            wrong_players.append({
                'name': player['name'],
                'card': dealt_card,
                'choice': choice
            })
        else:
            survived_players.append({
                'name': player['name'],
                'card': dealt_card,
                'choice': choice
            })

    emit('show_results', {
        'wrong_players': wrong_players,
        'survived_players': survived_players
    }, room=room)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    #python app.py