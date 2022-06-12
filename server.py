# Librerías del sistema

import busio
import digitalio
import board
import threading
import time
import sys

# Librerías para el servidor We

from flask import Flask, jsonify
from flask_cors import CORS

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

app = Flask(__name__)
CORS(app)

@app.route('/v1.0/iot-control/get_satus_controller') # Obtener el estado de los perifericos del controlador
def get_satus_controller():
  global channel_0
  sum = 0
  for i in range (10):
      adc_voltage = (20/3) * (channel_0.voltage - 1.5)
      sum += adc_voltage
  sum = sum / 10
  return(jsonify(
    status_relay_1 = relay_1.value,
    status_relay_2 = relay_2.value,
    status_relay_3 = relay_3.value,
    adc_value      = round(sum, 2),
    dac_value      = round(dac_voltage, 2) 
  ))

@app.route('/v1.0/iot-control/change-relay/<relay>') # Control de salidas por relé
def control_relay(relay):
  if(relay == '1'):    
    relay_1.toggle()
  elif (relay == '2'):
    relay_2.toggle()
  elif (relay == '3'):
    relay_3.toggle()
  return("Relevador ;)")

@app.route('/v1.0/iot-control/change_dac_output/<set_dac_voltage>') # Control de salidas por relé
def change_dac_output(set_dac_voltage):
  global dac_voltage
  dac_voltage = (20 * (int(set_dac_voltage) - 2048)) / 4095 
  dac.set_voltage(int((((3/20) * (dac_voltage + 10)))*4095/3.255)) 
  return("DAC ;)")

@app.route("/")
def home_route():
  return "Esta es la API de la planta :)"

if __name__ == '__main__':
  # Objeto para el ADC
  adc = MCP.MCP3008(busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI), digitalio.DigitalInOut(board.D5))
  channel_0 = AnalogIn(adc, MCP.P0) # Canal 0 del ADC

  # Objeto para el DAC
  dac = Adafruit_MCP4725.MCP4725(address=0x60, busnum=1) # Tener en cuenta la dirección. Para A0 = GND, addr = 0x60. Para A0 = VCC, addr = 0x62.

  # Valor inicial del DAC  en 0:
  dac.set_voltage(int((((3/20) * (dac_voltage + 10)))*4095/3.255))
  
  # Ejecución de la aplicación
  app.run(debug=True, host='0.0.0.0', port=5001)