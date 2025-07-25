import network
import socket
import time
import json
from machine import I2C, SPI, Pin
from htu21d import HTU21D
from max31865 import MAX31865

# --- 🌐 Wi-Fi Bilgileri ---
SSID = 'my_wifi'
PASSWORD = '***********'

# --- Sensör Ayarları ---
RTD_NOMINAL = 100.0  # PT100 için 100.0, PT1000 için 1000.0
REF_RESISTOR = 430.0 # Harici referans direncinizin değeri (ohm)
RTD_WIRES = 2        # RTD'nizin tel sayısı (2, 3 veya 4)

# --- Donanım Pinleri ---
button_pin = 15
# LED ile ilgili pin tanımı kaldırıldı

# --- 📶 Wi-Fi Bağlantısı ---
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
print("Wi-Fi'ya bağlanılıyor...", end="")
max_attempts = 15 # Maksimum 15 saniye bekle
attempts = 0
wlan.connect(SSID, PASSWORD)
while not wlan.isconnected() and attempts < max_attempts:
    print(".", end="")
    time.sleep(1)
    attempts += 1

if wlan.isconnected():
    ip_address = wlan.ifconfig()[0]
    print(f"\n✅ Bağlandı! IP: {ip_address}")
else:
    print("\n❌ Wi-Fi bağlantısı başarısız oldu. Ağ ayarlarını kontrol edin.")
    ip_address = "N/A" # Bağlanamazsa IP'yi N/A olarak ayarla

# --- 📟 HTU21D (I2C) ---
# SDA: GPIO0 (Pin 1), SCL: GPIO1 (Pin 2)
i2c = I2C(scl=Pin(1), sda=Pin(0))
try:
    htu = HTU21D(i2c)
    print("HTU21D sensörü başlatıldı.")
except Exception as e:
    print(f"❌ HTU21D başlatma hatası: {e}. Sensör bağlı mı? Pinler doğru mu?")
    htu = None # Sensör başlatılamazsa None olarak ayarla

# --- 🌡️ RTD (SPI) ---
# SCK: GPIO2 (Pin 4), MOSI: GPIO3 (Pin 5), MISO: GPIO4 (Pin 6), CS: GPIO5 (Pin 7)
spi = SPI(0, baudrate=1_000_000, polarity=0, phase=1,
          sck=Pin(2), mosi=Pin(3), miso=Pin(4))
cs = Pin(5, Pin.OUT)
try:
    rtd = MAX31865(spi, cs, wires=RTD_WIRES, rtd_nominal=RTD_NOMINAL, ref_resistor=REF_RESISTOR)
    print("MAX31865 (RTD) sensörü başlatıldı.")
except Exception as e:
    print(f"❌ MAX31865 başlatma hatası: {e}. Sensör bağlı mı? Pinler doğru mu? RTD bağlı mı?")
    rtd = None # Sensör başlatılamazsa None olarak ayarla

# --- Buton ---
# LED ile ilgili pin tanımı kaldırıldı
button = Pin(button_pin, Pin.IN, Pin.PULL_UP)

# --- Loglar ---
htu_temp_log = []
hum_log = []
rtd_log = []
MAX_LOG = 20 # Grafikte gösterilecek maksimum veri noktası sayısı

# --- 📊 Sensör Okuma Fonksiyonu ---
def read_all_sensors():
    temp_htu = None
    humidity = None
    temp_rtd = None

    if htu: # HTU21D başlatıldıysa oku
        try:
            temp_htu = htu.read_temperature()
            humidity = htu.read_humidity()
        except Exception as e:
            print(f"Sensör (HTU21D) okuma hatası: {e}")

    if rtd: # MAX31865 başlatıldıysa oku
        try:
            rtd.clear_fault() # Önceki hataları temizle
            temp_rtd = rtd.read_temp()
            # Hata kodlarını da kontrol edebiliriz
            fault = rtd.read_fault()
            if fault != 0:
                print(f"MAX31865 hata kodu: {bin(fault)}. RTD bağlantısını kontrol edin.")
        except Exception as e:
            print(f"Sensör (MAX31865) okuma hatası: {e}")

    print(f"📥 Ölçüm ➤ HTU: {temp_htu if temp_htu is not None else 'N/A'}°C, Hum: {humidity if humidity is not None else 'N/A'}%, RTD: {temp_rtd if temp_rtd is not None else 'N/A'}°C")
    return temp_htu, humidity, temp_rtd

def log_data(t, h, r):
    # Sadece geçerli (None olmayan) verileri logla
    if t is not None:
        if len(htu_temp_log) >= MAX_LOG:
            htu_temp_log.pop(0)
        htu_temp_log.append(t)
    if h is not None:
        if len(hum_log) >= MAX_LOG:
            hum_log.pop(0)
        hum_log.append(h)
    if r is not None:
        if len(rtd_log) >= MAX_LOG:
            rtd_log.pop(0)
        rtd_log.append(r)

# LED toggle fonksiyonu kaldırıldı

# --- 🌐 Web Sunucusu ---
PORT = 450
try:
    addr = socket.getaddrinfo('0.0.0.0', PORT)[0][-1]
    server = socket.socket()
    server.bind(addr)
    server.listen(1)
    server.settimeout(1) # Bağlantı gelmezse 1 saniye sonra hata fırlat
    print(f"🌍 Web sunucusu: http://{ip_address}:{PORT}")
except Exception as e:
    print(f"❌ Web sunucusu başlatma hatası: {e}")
    server = None # Sunucu başlatılamazsa None olarak ayarla

# --- 📄 HTML Şablon ---
def generate_html(temp_htu, hum, temp_rtd):
    # Veriler None ise 'N/A' olarak göster
    temp_htu_str = f"{temp_htu:.2f}" if temp_htu is not None else "N/A"
    hum_str = f"{hum:.2f}" if hum is not None else "N/A"
    temp_rtd_str = f"{temp_rtd:.2f}" if temp_rtd is not None else "N/A"

    return f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <title>Sensor Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{ background-color: #1e1e2f; color: #f0f0f5; font-family: sans-serif; text-align: center; padding: 2rem; }}
    h1 {{ color: #ff89bb; }}
    canvas {{ background: #ffffff10; border-radius: 10px; margin-top: 20px; }}
    button {{ background: #ff5f87; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; margin: 10px; }}
  </style>
</head>
<body>
  <h1>Sensor Dashboard 🌡️📈</h1>
  <p>Sıcaklık (HTU21D): <strong>{temp_htu_str}°C</strong></p>
  <p>Nem (HTU21D): <strong>{hum_str}%</strong></p>
  <p>RTD Sıcaklık (MAX31865): <strong>{temp_rtd_str}°C</strong></p>

  <form action="/refresh"><button>Yenile 🔄</button></form>
  <canvas id="chart" width="400" height="200"></canvas>
  <script>
    const htuTemp = {json.dumps(htu_temp_log)};
    const hum = {json.dumps(hum_log)};
    const rtdTemp = {json.dumps(rtd_log)};
    // Etiketleri en son 20 veriye göre dinamik oluştur
    const labels = htuTemp.map((_, i) => i + 1);

    new Chart(document.getElementById('chart').getContext('2d'), {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [
          {{
            label: 'HTU Sıcaklık (°C)',
            data: htuTemp,
            borderColor: '#ff6384',
            backgroundColor: 'rgba(255,99,132,0.2)',
            fill: true
          }},
          {{
            label: 'Nem (%)',
            data: hum,
            borderColor: '#36a2eb',
            backgroundColor: 'rgba(54,162,235,0.2)',
            fill: true
          }},
          {{
            label: 'RTD Sıcaklık (°C)',
            data: rtdTemp,
            borderColor: '#ffcc00',
            backgroundColor: 'rgba(255,204,0,0.2)',
            fill: true
          }}
        ]
      }},
      options: {{
        responsive: true,
        scales: {{
          y: {{ beginAtZero: false }}
        }}
      }}
    }});
    // Her 5 saniyede bir otomatik yenileme
    setInterval(() => location.reload(), 5000);
  </script>
</body>
</html>
"""

# --- 🔁 Ana Döngü ---
last_button_press_time = 0
button_debounce_delay = 0.2 # Buton için debounce süresi

while True:
    current_time = time.time()

    # Buton kontrolü (debounce ile)
    if button.value() == 0 and (current_time - last_button_press_time) > button_debounce_delay:
        print("👆 Butona basıldı, sensörler okunuyor...")
        # LED toggle çağrısı kaldırıldı
        t, h, r = read_all_sensors()
        log_data(t, h, r)
        last_button_press_time = current_time # Son buton basış zamanını güncelle

    # Web sunucusu işlemleri
    if server: # Sunucu başlatıldıysa devam et
        try:
            client, addr = server.accept()
            print("💻 İstek alındı:", addr)
            request = client.recv(1024).decode()
            print(f"Gelen İstek: {request.splitlines()[0]}") # İlk satırı göster

            if "GET /refresh" in request:
                print("Web yenileme isteği.")
                # Her yenilemede sensörleri oku
                t, h, r = read_all_sensors()
                log_data(t, h, r)
            # elif "GET /led" in request: # LED kontrol isteği kaldırıldı
            #    print("LED değiştirme isteği.")
            #    toggle_led()
            #    t, h, r = read_all_sensors()
            #    log_data(t, h, r)
            else:
                # Ana sayfaya ilk erişim veya diğer bilinmeyen istekler
                print("Ana sayfa veya bilinmeyen istek.")
                t, h, r = read_all_sensors() # Sensörleri oku
                log_data(t, h, r)

            html = generate_html(t, h, r)
            client.send(html.encode('utf-8'))
            client.close()

        except OSError as e:
            # print(f"Web sunucusu hatası (normal kabul edilebilir timeout): {e}")
            pass # Socket timeout (bağlantı yoksa) veya diğer geçici hatalar için

    # time.sleep(1) # Bu, sunucunun daha yavaş tepki vermesine neden olabilir, dikkatli kullan.
