import time
# Import the MCP4725 module.
import Adafruit_MCP4725

# Create a DAC instance.
dac = Adafruit_MCP4725.MCP4725(address=0x60, busnum=1) # Tener en cuenta la dirección. Para A0 = GND, addr = 0x60. Para A0 = VCC, addr = 0x62.


# Loop forever alternating through different voltage outputs.
print('Press Ctrl-C to quit...')
while True:
    print('Setting voltage to 0!')
    dac.set_voltage(0)
    time.sleep(2.0)
    print('Setting voltage to 1/2 Vdd!')
    dac.set_voltage(2048)  # 2048 = half of 4096
    time.sleep(2.0)
    print('Setting voltage to Vdd!')
    dac.set_voltage(4096, True)
    time.sleep(2.0)