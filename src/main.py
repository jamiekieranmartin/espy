def read_rfid():
    import time

    from machine import Pin, SoftSPI

    from mfrc522 import MFRC522

    sck = Pin(39, Pin.OUT)
    mosi = Pin(38, Pin.OUT)
    miso = Pin(40, Pin.OUT)
    spi = SoftSPI(baudrate=100000, polarity=0, phase=0, sck=sck, mosi=mosi, miso=miso)

    sda = Pin(14, Pin.OUT)
    while True:
        rfid = MFRC522(spi, sda)
        status, _ = rfid.detect_card()
        if status == rfid.STATUS_OK:
            status, uid = rfid.get_card_uid()
            if status == rfid.STATUS_OK:
                print("Card detected, UID:", "".join([f"{x:02X}" for x in uid]))
                time.sleep_ms(100)


def blinker():
    import time

    from machine import PWM, Pin

    pwm = PWM(Pin(2, Pin.OUT), freq=10_000)

    try:
        while True:
            time.sleep_ms(100)
            for i in range(1024):
                pwm.duty(i)
                time.sleep_ms(1)
            for i in range(1023, -1, -1):
                pwm.duty(i)
                time.sleep_ms(1)
    except:
        pwm.deinit()


blinker()
