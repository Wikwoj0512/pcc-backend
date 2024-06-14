import json
import os
import signal
import sys
import threading

from models import MqttReciever

from flask import Flask, request
from flask_socketio import SocketIO
from flask_cors import CORS, cross_origin

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins=['http://localhost:5173'], async_mode='threading')
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

reciever = MqttReciever()

socketio.start_background_task(reciever.infinite_sender, socketio)


@app.route('/')
@cross_origin()
def home():
    return f'Hello, World!, last message was {reciever.data}'


@app.route('/data')
@cross_origin()
def get_data():
    return json.dumps(reciever.data, default=vars)


@app.route('/charts/origins')
@cross_origin()
def get_origins():
    return json.dumps(reciever.get_origns())


@socketio.on('configure')
def my_event(data):
    session = reciever.get_session(request.sid)
    try:
        session.configure(data)
    except Exception as e:
        print(e)


@socketio.on('connect')
def my_connect():
    reciever.create_session(request.sid)


@socketio.on('disconnect')
def my_disconnect():
    reciever.sessions.pop(request.sid)


if __name__ == '__main__':
    socketio_thread = threading.Thread(target=socketio.run, args=(app,), kwargs={"debug": False, "host": "0.0.0.0"}, daemon=True)
    socketio_thread.start()
    try:
        while True:
            input()
    except KeyboardInterrupt:
        print("Wyłączanie")

        os.kill(os.getpid(), signal.SIGINT)
