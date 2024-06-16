import json
import os
import signal
import threading

from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS, cross_origin

from models import MqttReciever

from utils import Config

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins=['http://localhost:5173'], async_mode='threading')
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

config = Config()

reciever = MqttReciever(
    config.reciever_config,
    config.mqtt_host,
    config.mqtt_port,
    config.mqtt_topic)

socketio.start_background_task(reciever.infinite_sender, socketio)

@app.route('/data')
@cross_origin()
def get_data():
    """
    :return: all data
    """
    return json.dumps(reciever.data, default=vars)


@app.route('/charts/origins')
@cross_origin()
def get_origins():
    """
    :return: List of origins
    """
    return json.dumps(reciever.get_origins())


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
    emit('origins', reciever.get_origins(), namespace='/', to=request.sid)


@socketio.on('disconnect')
def my_disconnect():
    reciever.sessions.pop(request.sid)


print(config)

if __name__ == '__main__':
    socketio_thread = threading.Thread(
        target=socketio.run,
        args=(app,),
        kwargs={"debug": False, "host": "0.0.0.0", "port": config.pcc_port},
        daemon=True)
    socketio_thread.start()
    try:
        while True:
            input()
    except KeyboardInterrupt:
        print("Wyłączanie")

        os.kill(os.getpid(), signal.SIGINT)
