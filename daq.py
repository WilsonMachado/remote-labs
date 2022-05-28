# Librerías del sistema

import busio
import digitalio
import board
import threading
import time

# Librerías para los perifericos

import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import Adafruit_MCP4725

#--------------------------------------------------------------------------------------------------------#

# Objeto para el ADC
adc = MCP.MCP3008(busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI), digitalio.DigitalInOut(board.D5))
channel_0 = AnalogIn(adc, MCP.P0) # Canal 0 del ADC

# Objeto para el DAC
dac = Adafruit_MCP4725.MCP4725(address=0x60, busnum=1) # Tener en cuenta la dirección. Para A0 = GND, addr = 0x60. Para A0 = VCC, addr = 0x62.

# Hilo para la adqusición de los datos

def theard_adc_get_data():
    while True:
        dac.set_voltage(int(4*(channel_0.voltage*1023)/3.3))
        print(channel_0.voltage)
        time.sleep(0.1)

theard_adc_get_data_manager = threading.Thread(target=theard_adc_get_data)
theard_adc_get_data_manager.daemon = True 
theard_adc_get_data_manager.start()

theard_adc_get_data_manager.join()

print("Pille el multímetro papá...")

while True:
  try:
    pass
  except KeyboardInterrupt:
    print('\nExiting...')
    break