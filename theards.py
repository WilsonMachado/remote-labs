import time
import threading
import sys
from gpiozero import LED

t_1 = 1
t_2 = 5

led_1 = LED(4)
led_2 = LED(17)

def theard_led_1():
    
    while True:      
      led_1.on()
      time.sleep(t_1)
      led_1.off()
      time.sleep(t_1)
     

def theard_led_2():
    
    while True:      
      led_2.on()
      time.sleep(t_2)
      led_2.off()
      time.sleep(t_2)
      

theard_led_1_manager = threading.Thread(target=theard_led_1)
theard_led_2_manager = threading.Thread(target=theard_led_2)

theard_led_1_manager.daemon = True # Si no se pone esto, el hilo permanece en ejecución. Si se pone, el hilo se cierra al salir del programa.
theard_led_2_manager.daemon = True

theard_led_1_manager.start()
theard_led_2_manager.start()

theard_led_1_manager.join()
theard_led_2_manager.join()

while True:
  try:
    pass
  except KeyboardInterrupt:
    print("\nExiting...")
    sys.exit()