import json
import os
import signal
import threading
import time

from flask import Flask, request, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS, cross_origin

from models import MqttReceiver

from utils import Config

app = Flask(__name__)

if not os.path.isdir('maps'):
    os.mkdir('maps')

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins=['http://localhost', 'http://localhost:5173', 'http://192.168.1.0'],
                    async_mode='threading')
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

config = Config()

receiver = MqttReceiver(
    config.receiver_config,
    config.mqtt_host,
    config.mqtt_port,
    config.mqtt_topic,
    config.status_app)

socketio.start_background_task(receiver.infinite_sender, socketio)


@app.route('/data')
@cross_origin()
def get_data():
    """
    :return: all data
    """
    return json.dumps(receiver.data, default=vars)


@app.route('/charts/origins')
@cross_origin()
def get_origins():
    """
    :return: List of origins
    """
    return json.dumps(receiver.get_origins())


@app.route('/maps')
@cross_origin()
def get_maps():
    return json.dumps(os.listdir('maps'))


@app.route('/maps/origins')
@cross_origin()
def get_map_origins():
    return json.dumps(receiver.get_location_origins())


@app.route('/maps/<path:pars>')
def paths(pars):
    if '..' in pars:
        return "Not ok"
    path = os.path.join('maps', *pars.split('/'))
    if not os.path.isfile(path):
        return f"Path {path} is not file"
    return send_file(path)


@socketio.on('charts/configure')
def configure_session(data):
    session = receiver.get_session(request.sid)
    try:
        session.configure(data)
    except Exception as e:
        print(e)


@socketio.on('maps/configure')
def configure_maps(data):
    session_id = request.sid
    session = receiver.get_session(session_id)
    try:
        history = session.configure_locations(data, receiver.location_history)
        socketio.emit('maps/history', history, to=session_id)
    except Exception as e:
        print(e)


@socketio.on('request')
def get_origins(value):
    session_id = request.sid
    if value == 'charts/origins':
        socketio.emit('charts/origins', receiver.get_origins(), to=session_id)
    if value == 'maps/origins':
        socketio.emit('maps/origins', receiver.get_location_origins(), to=session_id)


@socketio.on('connect')
def my_connect():
    receiver.create_session(request.sid)


@socketio.on('disconnect')
def my_disconnect():
    receiver.sessions.pop(request.sid)


print(config)

if __name__ == '__main__':
    socketio_thread = threading.Thread(
        target=socketio.run,
        args=(app,),
        kwargs={"debug": False, "host": "0.0.0.0", "port": config.pcc_port, "allow_unsafe_werkzeug": True},
        daemon=True)
    socketio_thread.start()

    try:
        while True:
            input()
    except KeyboardInterrupt:
        print("Wyłączanie")

        os.kill(os.getpid(), signal.SIGINT)
