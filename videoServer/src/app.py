from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from time import sleep
import cv2
import base64



app = Flask(__name__)
app.config['SECRET_KEY'] = 'remote-lab-W!'
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

############################################################ Video Streaming #############################################################

def send_frames(json, methods=['GET', 'POST']):
    socketio.emit('/v1.0/iot-control/res_video_stream', json, broadcast=True)    


@socketio.on('/v1.0/iot-control/video_stream')
def video_stream(msg):
    camera=cv2.VideoCapture(0) # Posicion adecuada :0 Debe estar dentro de una funcion!
    while camera.isOpened():
        ret, frame = camera.read()
        if ret:
            img = cv2.resize(frame, (300, 200))
            frame = cv2.imencode('.jpg', img)[1].tobytes()
            frame = base64.encodebytes(frame).decode('utf-8')
            send_frames(frame)
        else:
            camera.release()
            break

##############################################################################################################################

    
    
@app.route('/')
def index():
    return render_template('index.html')

if __name__=="__main__":
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
