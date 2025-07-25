from machine import Pin, SPI
import time

class MAX31865:
    # 🔧 Register adresleri
    REG_CONFIG = 0x00
    REG_RTD_MSB = 0x01
    REG_RTD_LSB = 0x02
    REG_FAULT_STATUS = 0x07

    # ⚙️ Konfigürasyon bayrakları
    CONFIG_BIAS = 0x80
    CONFIG_AUTO_CONVERT = 0x40
    CONFIG_1SHOT = 0x20
    CONFIG_3WIRE = 0x10
    CONFIG_FAULT_CLEAR = 0x02
    CONFIG_50HZ_FILTER = 0x01  # 50Hz için 1, 60Hz için 0

    def __init__(self, spi, cs_pin, rtd_nominal=100.0, ref_resistor=430.0, wires=2):
        self.cs = Pin(cs_pin, Pin.OUT)
        self.spi = spi
        self.rtd_nominal = rtd_nominal
        self.ref_resistor = ref_resistor

        self.cs.value(1)  # CS'i pasif yap

        # Başlangıç konfigürasyonu
        config = self.CONFIG_BIAS | self.CONFIG_AUTO_CONVERT | self.CONFIG_FAULT_CLEAR
        if wires == 3:
            config |= self.CONFIG_3WIRE
        self._write_register(self.REG_CONFIG, config)
        time.sleep(0.1)

    def _write_register(self, reg, value):
        self.cs.value(0)
        self.spi.write(bytearray([0x80 | reg, value]))  # 0x80 | reg = write
        self.cs.value(1)

    def _read_registers(self, reg, length):
        self.cs.value(0)
        self.spi.write(bytearray([reg & 0x7F]))  # 0x7F & reg = read
        data = self.spi.read(length)
        self.cs.value(1)
        return data

    def read_raw(self):
        """Ham RTD değerini oku (15 bit)"""
        data = self._read_registers(self.REG_RTD_MSB, 2)
        raw = ((data[0] << 8) | data[1]) >> 1  # LSB'nin son biti fault
        return raw

    def read_temp(self):
        """Sıcaklığı hesapla. Sensör hatası varsa None döner."""
        raw = self.read_raw()
        if raw == 0 or raw == 32767:  # 0 = kısa devre, 32767 = açık devre
            return None

        resistance = (raw * self.ref_resistor) / 32768.0

        # Callendar–Van Dusen denklemi (yaklaşık)
        temp = (-242.02 + 2.2228 * resistance +
                2.5859e-3 * resistance**2 - 4.8260e-6 * resistance**3)
        return temp

    def read_fault(self):
        """Hata durumunu oku"""
        return self._read_registers(self.REG_FAULT_STATUS, 1)[0]

    def clear_fault(self):
        """Sensör hatasını temizle"""
        current_config = self._read_registers(self.REG_CONFIG, 1)[0]
        self._write_register(self.REG_CONFIG, current_config | self.CONFIG_FAULT_CLEAR)

