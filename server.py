# Librerías del sistema

from socket import socket
from datetime import datetime
import busio
import digitalio
import board
import threading
import time
import sys
import numpy as np
from scipy import signal            # Librería para procesamiento de señales

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
out_old = 0 # Esta variable almacena el valor de la salida anterior
closed_loop = True # Esta variable indica si la planta estará en lazo cerrado o no
referencia = 0 # Esta variable almacena la referencia de la planta

tau_d= 0 # Constante de control del lazo cerrado
tau_i = 0 # Constante de control del lazo cerrado
kc = 0 # Constante de control del lazo cerrado

vectorCoeff = []
vectorRef   = []
vectorOut   = []
defVector   = []
numD = []
denD = []

contRef  = 0
contOut  = 0
#########################################################################################################

app = Flask(__name__)
app.config['SECRET_KEY'] = 'remote-lab-W!'
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

############################### Controlador #############################################################

############################################## FUNCIONES ##############################################

def discretePlant(num, den, Ts):        # Función para discretizar la planta

    global vectorCoeff, vectorRef, vectorOut, defVector, numD, denD, contOut, contRef

    # Discretización del sistema

    sysD = signal.cont2discrete([num, den], Ts, method='bilinear', alpha=None)

    # Obtención de los vectores del polinomio característico en Z

    numD = sysD[0][0]
    denD = sysD[1]

    # Inversión de los vector (equivalente a evaluar en Z^{-1})

    numD = numD[::-1]                      
    denD = denD[::-1]

    # Vector de coeficientes para obtener la salida de forma recurrente

    vectorCoeff = np.concatenate((numD, -1 * denD)) 

    vectorCoeff = np.delete(vectorCoeff, (vectorCoeff.size - 1))

    vectorCoeff = (1 / denD[(len(denD) - 1)] ) * np.array(vectorCoeff) # Hasta aquí está el vector de coeficientes

    # Vectores para la ecuación en diferencias tanto de salida como de entrada

    vectorRef = np.zeros((vectorCoeff.size // 2))

    if (vectorCoeff.size % 2 != 0):
        vectorRef = np.zeros((vectorCoeff.size // 2) + 1)

    vectorOut = np.zeros((vectorCoeff.size // 2)) 
def calcOut():                          # Función para el cálculo de la salida

    global vectorCoeff, vectorRef, vectorOut, defVector, denD, contOut, contRef

    vectorRef = vectorRef[::-1] # Organización de referencia (Setpoint)

    difVector = np.concatenate((vectorRef, vectorOut)) # Creación del vector completo, con la referencia y la salida       
    
    out = np.dot(vectorCoeff, difVector) # Cálculo de la salida: producto punto entre el vector de coeficientes discretizado y el vector de completo

    if(contRef < vectorRef.size - 1): # Registro para almacenar los estados de la entrada

        vectorRef[(vectorRef.size - 2) - contRef] = vectorRef[(vectorRef.size - 1) - contRef]
        contRef += 1       

    else:

        contRef = 0

    # Registro para almacenar los estados de la salida

    if((contOut <= vectorOut.size - 1) and (denD.size == 2)): # Si es de primer orden

        vectorOut[contOut] = vectorOut[vectorOut.size - 1]
        vectorOut = vectorOut[::-1]
        vectorOut[vectorOut.size - 1] = out       
        contOut += 1
        

    if((contOut < vectorOut.size - 1) and (denD.size >= 3)): # Si es de orden superior

        for i in range (0, vectorOut.size - 1):
            vectorOut[i] = vectorOut[i + 1]
        
        vectorOut[vectorOut.size - 1] = out
        
        contOut += 2

    else:
        contOut = 0

    return out
#######################################################################################################

@socketio.on('/v1.0/iot-control/set_controller_parameters')
def set_controller_parameters(data):
  global tau_d, tau_i, kc
  
  alfa = tau_d / 100

  kc = data['kc']
  tau_i = data['tau_i']
  tau_d = data['tau_d'] 

  if (tau_d != 0):
    num = kc * np.array([((tau_i * alfa) + (tau_i * tau_d)), (tau_i + alfa), 1])
  else:
    num = kc * np.array([(tau_i), 1])
    
  den = [tau_i * alfa, tau_i, 0]   
  
  discretePlant(num, den, 0.01)


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
def get_status_relay(msg):
  socketio.emit('/v1.0/iot-control/get_status_relay', {
    'status_relay_1': relay_1.value,
    'status_relay_2': relay_2.value,
    'status_relay_3': relay_3.value}, broadcast=True)

@socketio.on('/v1.0/iot-control/set_reference') # Establecer el voltaje del DAC
def change_dac_output(reference):
  global referencia
  referencia = (20 * (int(reference['message']) - 2048)) / 4095    
  
@app.route("/")
def home_route():
  return "Esta es la API de la planta :)"

@socketio.on('/v1.0/iot-control/set_closed_loop') # Saber si el experimento será en lazo cerrado o no
def set_closed_loop(close_loop):
  global closed_loop
  closed_loop = not closed_loop
  socketio.emit('/v1.0/iot-control/get_closed_loop', {
    'closed_loop': closed_loop}, broadcast=True)


@socketio.on('/v1.0/iot-control/get_closed_loop') # Obtener el estado del lazo cerrado
def get_closed_loop(msg):
  socketio.emit('/v1.0/iot-control/get_closed_loop', {
    'closed_loop': closed_loop}, broadcast=True)

@socketio.on('/v1.0/iot-control/get_status_controller') # Iniciar modo de adqusición de datos
def get_satus_controller(message):
  
  global streaming_data, array_voltage, vectorRef, vectorOut
  
  streaming_data = True  
  while streaming_data:
    array_voltage = np.array([]) # Este array guardará los valores de la tensión de la planta    
    for i in range (10):
        array_voltage = np.append(array_voltage, round(((20/3) * (channel_0.voltage - 1.5)), 2))
        time.sleep(0.001)
    
    # Obtener la mediana del vector array_voltage
   
    voltage = np.percentile(array_voltage, 50) # Esta es la salida de la planta

    if closed_loop and ((kc != 0) or (tau_i != 0)):
      vectorRef[0] = referencia - voltage # Esta es la salida de la planta
      out = calcOut()     
    elif closed_loop:
      out = referencia - voltage
    else:
      out = referencia
    
    dac.set_voltage(int((((3/20) * (out + 10)))*4095/3.255))

    socketio.emit('/v1.0/iot-control/get_status_controller', {  
      'status_relay_1': relay_1.value,
      'status_relay_2': relay_2.value,
      'status_relay_3': relay_3.value,    
      'adc_value'      : round(voltage, 2),
      'dac_value'      : round(out, 2),
      'referencia'     : referencia,
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
    