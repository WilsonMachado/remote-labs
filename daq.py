# Librerías del sistema

import busio
import digitalio
import board
import threading
import time
import sys
# Librerías para los perifericos

import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import Adafruit_MCP4725
from gpiozero import LED

#--------------------------------------------------------------------------------------------------------#

# Objeto para el ADC
adc = MCP.MCP3008(busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI), digitalio.DigitalInOut(board.D5))
channel_0 = AnalogIn(adc, MCP.P0) # Canal 0 del ADC

# Objeto para el DAC
dac = Adafruit_MCP4725.MCP4725(address=0x60, busnum=1) # Tener en cuenta la dirección. Para A0 = GND, addr = 0x60. Para A0 = VCC, addr = 0x62.

#Objeto para el LED

led_1 = LED(4)

# Hilo para la adqusición de los datos

set_point = 0

def theard_adc_get_data():
  dac_voltage = (3/20) * (set_point + 10)
  dac.set_voltage(int((dac_voltage*4096)/3.255))    
  while True:
    sum = 0
    for i in range (10):
      adc_voltage = (20/3) * (channel_0.voltage - 1.5)
      sum += adc_voltage
    sum = sum / 10
    print("La planta está en: {:.2f} V".format(sum)) # Establecer decimales: "{:.2f}".format(variable)
    time.sleep(0.01)  

# Hilo para el LED

def theard_led_1():    
    while True:      
      led_1.on()
      time.sleep(3)
      led_1.off()
      time.sleep(3)

theard_adc_get_data_manager = threading.Thread(target=theard_adc_get_data)
theard_led_1_manager = threading.Thread(target=theard_led_1)


theard_adc_get_data_manager.daemon = True 
theard_led_1_manager.daemon = True

theard_adc_get_data_manager.start()
theard_led_1_manager.start()

theard_adc_get_data_manager.join()
theard_led_1_manager.join()

print("Pille el multímetro papá...")

