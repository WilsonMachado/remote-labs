# Librerías del sistema

from socket import socket
from datetime import datetime
import busio
import digitalio
import board
import threading
import time
import sys

# Librerías para el servidor Web

from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Librerías para los perifericos

import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import Adafruit_MCP4725
from gpiozero import LED

############################################## DEFINICIÓN DE CONSTATES #################################

relay_1 = LED(25)
relay_2 = LED(24)
relay_3 = LED(23)

dac_voltage = 0 # Este valor estará entre -10 y +10 V, arranca en cero para garantizar la seguridad de la planta
streaming_data = False # Esta variable indica si el servidor está en modo streaming de datos o no

#########################################################################################################

app = Flask(__name__)
app.config['SECRET_KEY'] = 'remote-lab-W!'
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

@socketio.on('/v1.0/iot-control/change_relay') # Control de salidas por relé
def control_relay(relay): 
  if(relay['message'] == '1'):    
    relay_1.toggle()
  elif (relay['message'] == '2'):
    relay_2.toggle()
  elif (relay['message'] == '3'):
    relay_3.toggle()

  socketio.emit('/v1.0/iot-control/get_status_relay', {
    'status_relay_1': relay_1.value,
    'status_relay_2': relay_2.value,
    'status_relay_3': relay_3.value}, broadcast=True)

@socketio.on('/v1.0/iot-control/get_status_relay') # Obtener cambios en los relevadores y enviar a todos
def get_status_relay():
  socketio.emit('/v1.0/iot-control/get_status_relay', {
    'status_relay_1': relay_1.value,
    'status_relay_2': relay_2.value,
    'status_relay_3': relay_3.value}, broadcast=True)

@socketio.on('/v1.0/iot-control/set_reference') # Establecer el voltaje del DAC
def change_dac_output(reference):
  global dac_voltage
  dac_voltage = (20 * (int(reference['message']) - 2048)) / 4095 
  dac.set_voltage(int((((3/20) * (dac_voltage + 10)))*4095/3.255)) 
  
@app.route("/")
def home_route():
  return "Esta es la API de la planta :)"

@socketio.on('/v1.0/iot-control/get_status_controller') # Iniciar modo de adqusición de datos
def get_satus_controller(message):
  global streaming_data, array_voltage, now
  streaming_data = True  
  while streaming_data:
    array_voltage = [] # Este array guardará los valores de la tensión de la planta    
    for i in range (9):
        array_voltage.append(round(((20/3) * (channel_0.voltage - 1.5)), 2))
        time.sleep(0.001)
    array_voltage.sort()
    now += 0.01
    socketio.emit('/v1.0/iot-control/get_status_controller', {  
      'status_relay_1': relay_1.value,
      'status_relay_2': relay_2.value,
      'status_relay_3': relay_3.value,    
      'adc_value'      : array_voltage[4],
      'dac_value'      : round(dac_voltage, 2),
      'transmition_status' : streaming_data
    }, broadcast=True)


@socketio.on('/v1.0/iot-control/stop_get_status_controller') # Detener modo de adqusición de datos
def stop_get_satus_controller(message):
  global streaming_data
  streaming_data = False 

if __name__ == '__main__':
  # Objeto para el ADC
  adc = MCP.MCP3008(busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI), digitalio.DigitalInOut(board.D5))
  channel_0 = AnalogIn(adc, MCP.P0) # Canal 0 del ADC

  # Objeto para el DAC
  dac = Adafruit_MCP4725.MCP4725(address=0x60, busnum=1) # Tener en cuenta la dirección. Para A0 = GND, addr = 0x60. Para A0 = VCC, addr = 0x62.

  # Valor inicial del DAC  en 0:
  dac.set_voltage(int((((3/20) * (dac_voltage + 10)))*4095/3.255)) 
  
  # Ejecución de la aplicación
  #app.run(debug=True, host='0.0.0.0', port=5001)
  socketio.run(app, debug=True, host='0.0.0.0', port=5001)
    