# htu21d.py

import time
from machine import I2C

class HTU21D:
    def __init__(self, i2c):
        self.i2c = i2c
        self.addr = 0x40

    def read_temperature(self):
        self.i2c.writeto(self.addr, b'\xF3')
        time.sleep(0.05)
        data = self.i2c.readfrom(self.addr, 2)
        temp_raw = data[0] << 8 | data[1]
        temp = -46.85 + 175.72 * temp_raw / 65536.0
        return temp

    def read_humidity(self):
        self.i2c.writeto(self.addr, b'\xF5')
        time.sleep(0.05)
        data = self.i2c.readfrom(self.addr, 2)
        humid_raw = data[0] << 8 | data[1]
        humid = -6.0 + 125.0 * humid_raw / 65536.0
        return humid

