import os, time, csv, json, struct, fcntl, subprocess
from datetime import datetime

SENSOR_ID        = os.getenv("SENSOR_ID", "1")
SENSOR_NAME      = os.getenv("SENSOR_NAME", "BME280")
SENSOR_LOCATION  = os.getenv("SENSOR_LOCATION", "Serverraum")
INTERVAL         = int(os.getenv("SENSOR_INTERVAL", "10"))
DATA_PATH        = os.getenv("DATA_PATH", "/app/data/sensor_data.csv")
TEMP_THRESHOLD   = float(os.getenv("TEMP_THRESHOLD", "27.0"))
HARDWARE_ENABLED = os.getenv("HARDWARE_ENABLED", "true").lower() == "true"
RELAY_PIN        = int(os.getenv("RELAY_PIN", "17"))
PWM_PIN          = int(os.getenv("PWM_PIN", "18"))
PWM_FREQ         = int(os.getenv("PWM_FREQ", "25000"))
TEMP_SOURCE      = os.getenv("TEMP_SOURCE", "mock")
TEMP_MOCK_VALUE  = float(os.getenv("TEMP_MOCK_VALUE", "28.5"))
TEMP_FILE_PATH   = os.getenv("TEMP_FILE_PATH", "/app/data/temp.txt")

GPIO_BASE = "/sys/class/gpio"
PWM_BASE  = "/sys/class/pwm/pwmchip0"
I2C_SLAVE = 0x0703


# Datei-Helfer

# Schreibt einen Wert als Text in eine Datei
def write_file(path, val):
    with open(path, "w") as f:
        f.write(str(val))

# Liest den Inhalt einer Datei als String
def read_file(path):
    with open(path) as f:
        return f.read().strip()


# GPIO / PWM

# Initialisiert den GPIO-Pin des Relais als Ausgang
def setup_relay(pin):
    gpio = f"{GPIO_BASE}/gpio{pin}"
    if not os.path.exists(gpio):
        write_file(f"{GPIO_BASE}/export", pin)
        time.sleep(0.1)
    write_file(f"{gpio}/direction", "out")
    write_file(f"{gpio}/value", "1")

# Schaltet das Relais ein oder aus
def set_relay(on):
    write_file(f"{GPIO_BASE}/gpio{RELAY_PIN}/value", "0" if on else "1")

# Initialisiert den Hardware-PWM-Kanal mit Frequenz und 0% Duty Cycle
def setup_pwm(pin, freq):
    ch = {18: 0, 19: 1}.get(pin)
    if ch is None:
        raise ValueError("Nur BCM 18 oder 19 für Hardware-PWM unterstützt.")
    pwm = f"{PWM_BASE}/pwm{ch}"
    if not os.path.exists(pwm):
        write_file(f"{PWM_BASE}/export", ch)
        time.sleep(0.1)
    period = int(1_000_000_000 / freq)
    try: write_file(f"{pwm}/enable", 0)
    except Exception: pass
    write_file(f"{pwm}/period", period)
    write_file(f"{pwm}/duty_cycle", 0)
    write_file(f"{pwm}/enable", 1)
    return ch, pwm, period

# Setzt den PWM Duty Cycle in Prozent (0-100)
def set_pwm_duty(percent, pwm, period):
    dc = int(period * max(0.0, min(100.0, float(percent))) / 100.0)
    write_file(f"{pwm}/duty_cycle", max(0, min(dc, period - 1)))

# Fährt PWM und Relais sicher herunter beim Beenden
def cleanup(relay_pin, pwm_ch, pwm_path, period):
    for fn in [
        lambda: set_pwm_duty(0, pwm_path, period),
        lambda: set_relay(False),
        lambda: write_file(f"{PWM_BASE}/pwm{pwm_ch}/enable", 0),
        lambda: write_file(f"{GPIO_BASE}/unexport", relay_pin),
    ]:
        try: fn()
        except Exception: pass


# Sensor

# Berechnet die Lüfter-Drehzahl in Prozent basierend auf der Temperatur
def berechne_drehzahl(temp):
    if temp < TEMP_THRESHOLD: return 0
    if temp >= 35:            return 100
    return round(30 + (temp - TEMP_THRESHOLD) * (70 / (35 - TEMP_THRESHOLD)), 1)

# Liest die Temperatur direkt vom BME280-Sensor über I2C
def read_bme280():
    with open("/dev/i2c-1", "rb+", buffering=0) as bus:
        fcntl.ioctl(bus, I2C_SLAVE, 0x77)
        bus.write(bytes([0x88]))
        cal = bus.read(24)
        T1 = struct.unpack_from('<H', cal, 0)[0]
        T2 = struct.unpack_from('<h', cal, 2)[0]
        T3 = struct.unpack_from('<h', cal, 4)[0]
        bus.write(bytes([0xF4, 0x25]))
        time.sleep(0.1)
        bus.write(bytes([0xFA]))
        raw  = bus.read(3)
        adc  = (raw[0] << 12) | (raw[1] << 4) | (raw[2] >> 4)
        v1   = (adc / 16384.0 - T1 / 1024.0) * T2
        v2   = ((adc / 131072.0 - T1 / 8192.0) ** 2) * T3
        return round((v1 + v2) / 5120.0, 2)

# Gibt die Temperatur je nach konfigurierter Quelle zurück
def read_temperature():
    if TEMP_SOURCE == "mock":    return round(TEMP_MOCK_VALUE, 2)
    if TEMP_SOURCE == "bme280":  return read_bme280()
    if TEMP_SOURCE == "file":    return round(float(read_file(TEMP_FILE_PATH)), 2)
    if TEMP_SOURCE == "command":
        cmd = os.getenv("TEMP_COMMAND", "").strip()
        if not cmd: raise RuntimeError("TEMP_COMMAND ist leer.")
        return round(float(subprocess.check_output(cmd, shell=True, text=True).strip()) / 1000, 2)
    raise RuntimeError(f"Unbekannte TEMP_SOURCE: {TEMP_SOURCE}")


# Speichern

# Haengt den aktuellen Messwert als CSV-Zeile an (Excel-kompatibel)
def save_entry(entry):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    file_exists = os.path.exists(DATA_PATH)
    with open(DATA_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=entry.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(entry)


# Liest den manuellen Override-Status aus der Control-Datei (on/off/auto)
def read_override():
    path = os.path.join(os.path.dirname(DATA_PATH), "control.json")
    try:
        with open(path) as f:
            return json.load(f).get("override", "auto")
    except Exception:
        return "auto"


# Hauptprogramm

print(f"Sensor '{SENSOR_NAME}' gestartet. Schwellenwert: {TEMP_THRESHOLD}°C")
print(f"Temperaturquelle: {TEMP_SOURCE} | Hardware: {'aktiv' if HARDWARE_ENABLED else 'deaktiviert (PI 4)'}")

pwm_ch = pwm_path = period_ns = None

try:
    if HARDWARE_ENABLED:
        setup_relay(RELAY_PIN)
        try:
            pwm_ch, pwm_path, period_ns = setup_pwm(PWM_PIN, PWM_FREQ)
        except Exception as e:
            print(f"PWM nicht verfuegbar ({e}) — nur Relais aktiv")
            pwm_ch = pwm_path = period_ns = None

    while True:
        temp     = read_temperature()
        override = read_override()
        fan_on   = override == "on" or (override == "auto" and temp >= TEMP_THRESHOLD)
        drehzahl = berechne_drehzahl(temp) if temp >= TEMP_THRESHOLD else (30 if fan_on else 0)

        if HARDWARE_ENABLED:
            set_relay(fan_on)
            set_pwm_duty(drehzahl if fan_on else 0, pwm_path, period_ns)

        print(f"{'⚠️' if fan_on else '✅'}  {temp}°C → Lüfter {'AN @ ' + str(drehzahl) + '%' if fan_on else 'AUS'}")

        save_entry({
            "sensor_id":        SENSOR_ID,
            "name":             SENSOR_NAME,
            "location":         SENSOR_LOCATION,
            "temperature":      temp,
            "relay":            "AN" if fan_on else "AUS",
            "drehzahl_prozent": drehzahl,
            "timestamp":        datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        })
        time.sleep(INTERVAL)

finally:
    if HARDWARE_ENABLED:
        cleanup(RELAY_PIN, pwm_ch, pwm_path, period_ns)
