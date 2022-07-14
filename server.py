# Librerías del sistema

import busio
import digitalio
import board
import time
import numpy as np
from scipy import signal            # Librería para procesamiento de señales
import logging
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
closed_loop = False # Esta variable indica si la planta estará en lazo cerrado o no
referencia = 0 # Esta variable almacena la referencia de la planta

tau_d= 0 # Constante de control del lazo cerrado
tau_i = 0 # Constante de control del lazo cerrado
kc = 0 # Constante de control del lazo cerrado

vectorNum = [] # Vector de numerador de la planta
vectorDen = []  # Vector de denominador de la planta
vectorError = [] # Vector de error 
vectorMu   = [0] # Vector de acciones de control anteriores
b0 = 0 # Término independiente del denominador del controlador PID discreto

usuariosConectados = 0 # Variable que almacena el número de usuarios conectados
#########################################################################################################

app = Flask(__name__)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app.config['SECRET_KEY'] = 'remote-lab-W!'
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

############################### Controlador #############################################################

############################################## FUNCIONES ##############################################

def discretePlant(num, den, Ts):        # Función para discretizar la planta

    global vectorNum, vectorDen, vectorError, vectorMu, b0 

    # Obtención de los vectores del polinomio característico en Z

    if num.size == 1 and den.size == 1:
      vectorNum = num
      vectorDen = den
      b0 = 1
    else:
      sysD = signal.cont2discrete((num, den), Ts, method='bilinear', alpha=None)
      vectorNum = sysD[0][0]
      vectorDen = sysD[1]

      # Inversión de los vectores (equivalente a evaluar en Z^{-1})

      vectorNum = vectorNum[::-1]                      
      vectorDen = vectorDen[::-1]

      # Organización de los vectores para posterior usarlos en el cálculo de la salida
      b0 = vectorDen[vectorDen.size - 1]

      vectorDen = np.delete(vectorDen, (vectorDen.size - 1))
      
    vectorError = np.zeros(vectorNum.size)
    vectorMu = np.zeros(vectorDen.size)

def shift_register(arr, num, fill_value=np.nan): # Función para realizar el desplazamiento de registro (Shift Register)
  arr = np.roll(arr,num)
  if num < 0:
      arr[num:] = fill_value
  elif num > 0:
      arr[:num] = fill_value
  return arr

def calcOut():                          # Función para el cálculo de la salida

    global vectorNum, vectorDen, vectorError, vectorMu, b0

    if (vectorNum.size == 1):
      mu_k = kc*vectorError[0]
      if mu_k >= 10:
        mu_k = 10
      if mu_k <= -10:
        mu_k = -10
    else:

      mu_k = (np.dot(vectorNum, vectorError) - np.dot(vectorDen, vectorMu)) / b0
      if mu_k >= 10:
        mu_k = 10
      if mu_k <= -10:
        mu_k = -10
      vectorMu = shift_register(vectorMu, 1, mu_k)   

    return mu_k
#######################################################################################################

@socketio.on('/v1.0/iot-control/set_controller_parameters')
def set_controller_parameters(data):
  global tau_d, tau_i, kc 

  kc = data['kc']
  tau_i = data['tau_i']
  tau_d = data['tau_d'] 

  alfa = tau_d / 100

  print("Kc = {}, Tau_i = {}, Tau_d = {}".format(kc, tau_i, tau_d))

  if kc != 0 and tau_i == 0 and tau_d == 0:   # Controaldor P
    num = kc * np.array([1])
    den = np.array([1]) 

  elif kc != 0 and tau_i != 0 and tau_d == 0: # Controaldor PI
    num = kc * np.array([tau_i, 1])
    den = np.array([tau_i, 0])   
  
  elif kc != 0 and tau_i == 0 and tau_d != 0: # Controaldor PD
    num = kc * np.array([(alfa + tau_d), 1])
    den = np.array([alfa, 1])    

  elif kc != 0 and tau_i != 0 and tau_d != 0: # Controaldor PID
    num = kc * np.array([(tau_i*alfa + tau_i*tau_d), (tau_i + alfa), 1])
    den = np.array([(tau_i*alfa), tau_i, 0])
    
  else:
    num = np.array([0])
    den = np.array([1])

  discretePlant(num, den, 0.01)
  
  print("Vector Numerador: {}, Vector Error: {}, Vector Denominador: {}, Vector Mu: {}, b_0: {}".format(vectorNum, vectorError, vectorDen, vectorMu, b0))


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
  print(closed_loop)
  socketio.emit('/v1.0/iot-control/get_closed_loop', {
    'closed_loop': closed_loop}, broadcast=True)


@socketio.on('/v1.0/iot-control/get_closed_loop') # Obtener el estado del lazo cerrado
def get_closed_loop(msg):
  socketio.emit('/v1.0/iot-control/get_closed_loop', {
    'closed_loop': closed_loop}, broadcast=True)

@socketio.on('/v1.0/iot-control/get_status_controller') # Iniciar modo de adqusición de datos
def get_satus_controller(message):
  
  global streaming_data, array_voltage, vectorError
  
  streaming_data = True  
  while streaming_data:
    array_voltage = np.array([]) # Este array guardará los valores de la tensión de la planta    
    for i in range (9):
        array_voltage = np.append(array_voltage, round(((20/3) * (channel_0.voltage - 1.5))-0.15, 2))        
        time.sleep(0.001)
    
    # Obtener la mediana del vector array_voltage
    if array_voltage.std() <= 0.5:
      #print(array_voltage)
      voltage = np.percentile(array_voltage, 50) # Esta es la salida de la planta
      #print(voltage)
      if closed_loop:
        vectorError = shift_register(vectorError, 1, referencia - voltage)
        out = calcOut()
      else:
        out = referencia
        vectorMu[0] = 0
      
      dac.set_voltage(int((((3/20) * (out + 10)))*4095/3.255))

      socketio.emit('/v1.0/iot-control/get_status_controller', {  
        'status_relay_1': relay_1.value,
        'status_relay_2': relay_2.value,
        'status_relay_3': relay_3.value,    
        'adc_value'      : round(voltage, 2),
        'dac_value'      : round(out, 2),
        'mu_k'          : round(vectorMu[0], 2),
        'referencia'     : round(referencia, 2),
        'transmition_status' : streaming_data
      }, broadcast=True)


@socketio.on('/v1.0/iot-control/stop_get_status_controller') # Detener modo de adqusición de datos
def stop_get_satus_controller(message):
  global streaming_data
  streaming_data = False 

@socketio.on('connect')
def nuevo_usuario(socket):
  global usuariosConectados  
  usuariosConectados += 1
  

@socketio.on('disconnect')
def usuario_desconectado():
  global usuariosConectados, streaming_data, closed_loop
  usuariosConectados -= 1
  if usuariosConectados == 0:
    
    streaming_data = False 
    closed_loop = False

    for i in range (3):
      dac.set_voltage(int((((3/20) * (0 + 10)))*4095/3.255))
      time.sleep(1)
    

    relay_1.off()
    relay_2.off()
    relay_3.off()   


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
    