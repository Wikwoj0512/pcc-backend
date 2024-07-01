import json
import os
import signal
import threading

from flask import Flask, request, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS, cross_origin

from models import MqttReceiver

from utils import Config

app = Flask(__name__)

if not os.path.isdir('maps'):
    os.mkdir('maps')

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins=['http://localhost:5173'], async_mode='threading')
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

config = Config()

receiver = MqttReceiver(
    config.receiver_config,
    config.mqtt_host,
    config.mqtt_port,
    config.mqtt_topic)

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


@socketio.on('configure')
def my_event(data):
    session = receiver.get_session(request.sid)
    try:
        session.configure(data)
    except Exception as e:
        print(e)


@socketio.on('connect')
def my_connect():
    receiver.create_session(request.sid)
    emit('origins', receiver.get_origins(), namespace='/', to=request.sid)
    emit("location_history", receiver.get_location_history())


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
            pass
    except KeyboardInterrupt:
        print("Wyłączanie")

        os.kill(os.getpid(), signal.SIGINT)
