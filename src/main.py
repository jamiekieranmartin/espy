import time

from machine import PWM, Pin

pwm = PWM(Pin(2, Pin.OUT), freq=10_000)

try:
    while True:
        for i in range(1024):
            pwm.duty(i)
            time.sleep_ms(1)
        for i in range(1023, -1, -1):
            pwm.duty(i)
            time.sleep_ms(1)
except:
    pwm.deinit()
