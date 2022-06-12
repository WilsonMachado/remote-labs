from gpiozero import Button
from gpiozero import LED
import time

button = Button(26)
led = LED(4)

while True:
    if button.is_pressed:
        print("Pressed")
        led.on()
    else:
        print("Released")
        led.off()
    time.sleep(0.1)



