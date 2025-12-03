import network
import time
import urequests as requests 

# ===========================
# CONFIGURACIÓN WIFI
# ===========================
WIFI_SSID = "iPhone de Braulio"
WIFI_PASS = "braulio060621"

# ===========================
# CONFIGURACIÓN SERVIDOR FLASK
# ===========================
SERVER_IP = "172.20.10.2"          # <-- cambia por tu IP real del RPi5
SERVER_URL = f"http://{SERVER_IP}:5000/nuevo"


# ===========================
# CONECTAR AL WIFI
# ===========================
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print("Conectando al WiFi...")
    wlan.connect(WIFI_SSID, WIFI_PASS)

    while not wlan.isconnected():
        print("...")
        time.sleep(0.5)

    print("✅ Conectado al WiFi")
    print("IP Pico W:", wlan.ifconfig()[0])


# ===========================
# FUNCIÓN PARA ENVIAR DATOS
# ===========================
def enviar_deteccion(tipo, nombre, conf):
    try:
        payload = f"tipo={tipo}&nombre={nombre}&conf={conf}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        print("📡 Enviando detección al servidor...")
        res = requests.post(SERVER_URL, data=payload, headers=headers)

        print("📥 Respuesta del servidor:", res.text)
        res.close()

    except Exception as e:
        print("❌ Error enviando detección:", e)


# ===========================
# MAIN
# ===========================
conectar_wifi()

# EJEMPLO: puedes enviar detecciones desde el Pico W
while True:
    # Aquí tú decides cuándo enviar
    enviar_deteccion("sana", "fresa_demo", "0.88")
    time.sleep(5)     # envía cada 5 segundos

