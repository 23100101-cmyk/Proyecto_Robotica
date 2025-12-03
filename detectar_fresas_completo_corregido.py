# detectar_fresas_completo_corregido.py

import cv2
from ultralytics import YOLO
import sqlite3
from datetime import datetime
import os
import sys
from paho.mqtt import client as mqtt     # <-- MQTT agregado

# ==============================
# CONFIGURACIÓN
# ==============================
MODEL_ENFERMEDADES = "best.pt"
MODEL_SANAS = "sano.pt"
DB_NAME = "detecciones_fresa.db"

# ==============================
# MQTT - USANDO MOSQUITTO LOCAL EN RASPBERRY PI 5
# ==============================
MQTT_BROKER = "127.0.0.1"       # Mosquitto local
MQTT_TOPIC = "robot/fresa"

mqttc = mqtt.Client()
mqttc.connect(MQTT_BROKER, 1883, 60)
print("📡 MQTT conectado al broker Mosquitto LOCAL (127.0.0.1)")

# ==============================
# 1. VERIFICAR ARCHIVOS Y MODELOS
# ==============================
print("🔍 VERIFICANDO ARCHIVOS...")
print(f"Directorio actual: {os.getcwd()}")
print(f"Archivos: {os.listdir('.')}")

if not os.path.exists(MODEL_ENFERMEDADES):
    print(f"❌ ERROR: No se encontró '{MODEL_ENFERMEDADES}'")
    sys.exit(1)

if not os.path.exists(MODEL_SANAS):
    print(f"❌ ERROR: No se encontró '{MODEL_SANAS}'")
    sys.exit(1)

print("✅ Archivos de modelos encontrados")

# ==============================
# 2. CARGAR MODELOS YOLO
# ==============================
print("\n🤖 CARGANDO MODELOS...")
model_enfermedades = YOLO(MODEL_ENFERMEDADES)
model_sanas = YOLO(MODEL_SANAS)

print("📊 Clases enfermedades:", model_enfermedades.names)
print("📊 Clases sanas:", model_sanas.names)
print("✅ Modelos cargados")

# ==============================
# 3. CONFIGURAR BASE DE DATOS
# ==============================
print(f"\n🗄️ Configurando base de datos '{DB_NAME}'")
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS detecciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora TEXT NOT NULL,
    tipo TEXT NOT NULL,
    nombre TEXT NOT NULL,
    confianza REAL NOT NULL
)
""")
conn.commit()

print(f"✔ Base de datos ubicada en: {os.path.abspath(DB_NAME)}")

# ==============================
# FUNCIÓN: VER REGISTROS
# ==============================
def ver_registros():
    print("\n========== REGISTROS EN BD ==========")
    cursor.execute("SELECT COUNT(*) FROM detecciones")
    total = cursor.fetchone()[0]

    print(f"Total registros: {total}")

    if total > 0:
        cursor.execute("SELECT * FROM detecciones ORDER BY fecha_hora DESC LIMIT 10")
        registros = cursor.fetchall()
        for reg in registros:
            print(f"\nID: {reg[0]} | Fecha: {reg[1]}")
            print(f"Tipo: {reg[2]} | Nombre: {reg[3]} | Confianza: {reg[4]:.2f}")

    print("=====================================")

# ==============================
# 5. INICIAR CÁMARA
# ==============================
print("\n📷 Iniciando cámara...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    conn.close()
    print("❌ No se pudo abrir la cámara.")
    sys.exit(1)

print("✅ Cámara OK")

# ==============================
# INTERFAZ DE USUARIO
# ==============================
print("\n========== CONTROLES ==========")
print("G = Guardar detección actual")
print("V = Ver registros")
print("S = Solo fresas sanas")
print("E = Solo enfermedades")
print("A = Todas las detecciones")
print("C = Limpiar consola")
print("Q = Salir")
print("================================\n")

modo_actual = "todos"
COLORES = {"enfermedad": (0, 0, 255), "sana": (0, 255, 0)}
font = cv2.FONT_HERSHEY_SIMPLEX

# ==============================
# BUCLE PRINCIPAL
# ==============================
frame_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    frame_display = frame.copy()
    todas_detecciones = []

    # ==========================
    # DETECCIÓN ENFERMEDADES
    # ==========================
    if modo_actual in ["todos", "enfermedades"]:
        r_enf = model_enfermedades(frame, conf=0.25, verbose=False)
        for box in r_enf[0].boxes:
            x1,y1,x2,y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])
            nombre = model_enfermedades.names[cls]
            conf = float(box.conf[0])

            todas_detecciones.append({
                "tipo": "enfermedad",
                "nombre": nombre,
                "confianza": conf,
                "bbox": (x1,y1,x2,y2),
                "color": COLORES["enfermedad"]
            })

    # ==========================
    # DETECCIÓN SANAS
    # ==========================
    if modo_actual in ["todos", "sanas"]:
        r_sanas = model_sanas(frame, conf=0.20, verbose=False)
        for box in r_sanas[0].boxes:
            x1,y1,x2,y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])
            nombre = model_sanas.names[cls]
            conf = float(box.conf[0])

            todas_detecciones.append({
                "tipo": "sana",
                "nombre": nombre,
                "confianza": conf,
                "bbox": (x1,y1,x2,y2),
                "color": COLORES["sana"]
            })

    # ==========================
    # DIBUJAR RESULTADOS
    # ==========================
    contador_enf = 0
    contador_sanas = 0

    for det in todas_detecciones:
        x1,y1,x2,y2 = det["bbox"]
        cv2.rectangle(frame_display, (x1,y1),(x2,y2), det["color"], 2)

        abreviado = "ENF" if det["tipo"] == "enfermedad" else "SNA"
        texto = f"{abreviado}: {det['nombre']} {det['confianza']:.2f}"

        cv2.putText(frame_display, texto, (x1, max(20,y1-5)), font, 0.6, det["color"], 2)

        if det["tipo"] == "enfermedad":
            contador_enf += 1
        else:
            contador_sanas += 1

    # ==========================
    # PANEL SUPERIOR
    # ==========================
    overlay = frame_display.copy()
    cv2.rectangle(overlay, (5,5), (300,100), (0,0,0), -1)
    cv2.addWeighted(overlay, 0.5, frame_display, 0.5, 0)

    cv2.putText(frame_display, f"MODO: {modo_actual.upper()}", (10,30), font, 0.7, (255,255,255), 2)
    cv2.putText(frame_display, f"SANAS: {contador_sanas}", (10,60), font, 0.7, COLORES["sana"], 2)
    cv2.putText(frame_display, f"ENF: {contador_enf}", (10,90), font, 0.7, COLORES["enfermedad"], 2)

    cv2.imshow("Detector Fresas - Sanas y Enfermedades", frame_display)

    # ==========================
    # TECLAS
    # ==========================
    key = cv2.waitKey(1) & 0xFF

    # ========= GUARDAR =========
    if key == ord('g'):
        if todas_detecciones:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n💾 Guardando {len(todas_detecciones)} detecciones...")

            for det in todas_detecciones:

                # ===============================
                # **MQTT: enviar mensaje al Pico W**
                # ===============================
                mensaje = f"{det['tipo']}|{det['nombre']}|{det['confianza']:.2f}"
                mqttc.publish(MQTT_TOPIC, mensaje)
                print(f"📡 Enviado al Pico W → {mensaje}")

                cursor.execute("""
                INSERT INTO detecciones (fecha_hora, tipo, nombre, confianza)
                VALUES (?, ?, ?, ?)
                """, (fecha, det["tipo"], det["nombre"], det["confianza"]))

            conn.commit()
            print("✔ Guardado en la base de datos")

    elif key == ord('v'):
        ver_registros()

    elif key == ord('s'):
        modo_actual = "sanas"
        print("\n🔵 Modo: SOLO SANAS")

    elif key == ord('e'):
        modo_actual = "enfermedades"
        print("\n🔴 Modo: SOLO ENFERMEDADES")

    elif key == ord('a'):
        modo_actual = "todos"
        print("\n🟡 Modo: TODAS LAS DETECCIONES")

    elif key == ord('c'):
        os.system("clear")
        print("🔄 Consola limpiada")

    elif key == ord('q'):
        print("\n👋 Cerrando programa…")
        break

# ==============================
# FINALIZAR
# ==============================
cap.release()
cv2.destroyAllWindows()
ver_registros()
conn.close()
print("\n✅ Programa terminado correctamente")
