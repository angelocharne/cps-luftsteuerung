import os
import time
import json
import struct
import subprocess
import smbus2
from datetime import datetime, timedelta


SENSOR_ID        = os.getenv("SENSOR_ID", "1")
SENSOR_NAME      = os.getenv("SENSOR_NAME", "BME280")
SENSOR_LOCATION  = os.getenv("SENSOR_LOCATION", "Serverraum")
INTERVAL         = int(os.getenv("SENSOR_INTERVAL", "10"))
DATA_PATH        = os.getenv("DATA_PATH", "/app/data/sensor_data.json")
TEMP_THRESHOLD   = float(os.getenv("TEMP_THRESHOLD", "27.0"))
HARDWARE_ENABLED = os.getenv("HARDWARE_ENABLED", "true").lower() == "true"

RELAY_PIN        = int(os.getenv("RELAY_PIN", "17"))
PWM_PIN          = int(os.getenv("PWM_PIN", "18"))
PWM_FREQ         = int(os.getenv("PWM_FREQ", "25000"))

TEMP_SOURCE      = os.getenv("TEMP_SOURCE", "mock")
TEMP_MOCK_VALUE  = float(os.getenv("TEMP_MOCK_VALUE", "28.5"))
TEMP_FILE_PATH   = os.getenv("TEMP_FILE_PATH", "/app/data/temp.txt")

GPIO_SYSFS_BASE  = "/sys/class/gpio"
PWM_SYSFS_BASE   = "/sys/class/pwm/pwmchip0"


def write_file(path, value):
    with open(path, "w") as f:
        f.write(str(value))


def read_file(path):
    with open(path, "r") as f:
        return f.read().strip()


def ensure_gpio_exported(pin):
    gpio_path = f"{GPIO_SYSFS_BASE}/gpio{pin}"
    if not os.path.exists(gpio_path):
        write_file(f"{GPIO_SYSFS_BASE}/export", pin)
        time.sleep(0.1)
    return gpio_path


def setup_relay(pin):
    gpio_path = ensure_gpio_exported(pin)
    write_file(f"{gpio_path}/direction", "out")
    write_file(f"{gpio_path}/value", "1")


def set_relay(on):
    gpio_path = f"{GPIO_SYSFS_BASE}/gpio{RELAY_PIN}"
    write_file(f"{gpio_path}/value", "0" if on else "1")


def get_pwm_channel_for_pin(pin):
    if pin == 18:
        return 0
    elif pin == 19:
        return 1
    raise ValueError("Nur BCM 18 oder 19 für Hardware-PWM unterstützt.")


def ensure_pwm_exported(channel):
    pwm_path = f"{PWM_SYSFS_BASE}/pwm{channel}"
    if not os.path.exists(pwm_path):
        write_file(f"{PWM_SYSFS_BASE}/export", channel)
        time.sleep(0.1)
    return pwm_path


def setup_pwm(pin, frequency_hz):
    channel = get_pwm_channel_for_pin(pin)
    pwm_path = ensure_pwm_exported(channel)
    period_ns = int(1_000_000_000 / frequency_hz)
    try:
        write_file(f"{pwm_path}/enable", 0)
    except Exception:
        pass
    write_file(f"{pwm_path}/period", period_ns)
    write_file(f"{pwm_path}/duty_cycle", 0)
    write_file(f"{pwm_path}/enable", 1)
    return channel, pwm_path, period_ns


def set_pwm_duty_cycle(percent, pwm_path, period_ns):
    percent = max(0.0, min(100.0, float(percent)))
    duty_ns = int(period_ns * (percent / 100.0))
    if duty_ns >= period_ns:
        duty_ns = period_ns - 1
    if duty_ns < 0:
        duty_ns = 0
    write_file(f"{pwm_path}/duty_cycle", duty_ns)


def cleanup_pwm(channel):
    pwm_path = f"{PWM_SYSFS_BASE}/pwm{channel}"
    if os.path.exists(pwm_path):
        try:
            write_file(f"{pwm_path}/enable", 0)
        except Exception:
            pass


def cleanup_gpio(pin):
    gpio_path = f"{GPIO_SYSFS_BASE}/gpio{pin}"
    if os.path.exists(gpio_path):
        try:
            write_file(f"{GPIO_SYSFS_BASE}/unexport", pin)
        except Exception:
            pass


def berechne_drehzahl(temp):
    if temp < TEMP_THRESHOLD:
        return 0
    elif temp >= 35:
        return 100
    else:
        drehzahl = 30 + (temp - TEMP_THRESHOLD) * (70 / (35 - TEMP_THRESHOLD))
        return round(min(drehzahl, 100), 1)


def read_bme280_temperature():
    bus = smbus2.SMBus(1)
    address = 0x77

    cal = bus.read_i2c_block_data(address, 0x88, 24)
    dig_T1 = struct.unpack_from('<H', bytes(cal), 0)[0]
    dig_T2 = struct.unpack_from('<h', bytes(cal), 2)[0]
    dig_T3 = struct.unpack_from('<h', bytes(cal), 4)[0]

    bus.write_byte_data(address, 0xF4, 0x25)
    time.sleep(0.1)

    raw = bus.read_i2c_block_data(address, 0xFA, 3)
    adc_T = (raw[0] << 12) | (raw[1] << 4) | (raw[2] >> 4)

    var1 = (adc_T / 16384.0 - dig_T1 / 1024.0) * dig_T2
    var2 = ((adc_T / 131072.0 - dig_T1 / 8192.0) ** 2) * dig_T3

    bus.close()
    return round((var1 + var2) / 5120.0, 2)


def read_temperature():
    if TEMP_SOURCE == "mock":
        return round(TEMP_MOCK_VALUE, 2)

    if TEMP_SOURCE == "bme280":
        return read_bme280_temperature()

    if TEMP_SOURCE == "file":
        return round(float(read_file(TEMP_FILE_PATH)), 2)

    if TEMP_SOURCE == "command":
        cmd = os.getenv("TEMP_COMMAND", "").strip()
        if not cmd:
            raise RuntimeError("TEMP_COMMAND ist leer.")
        result = subprocess.check_output(cmd, shell=True, text=True).strip()
        return round(float(result) / 1000, 2)

    raise RuntimeError(f"Unbekannte TEMP_SOURCE: {TEMP_SOURCE}")


def load_history():
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r") as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except json.JSONDecodeError:
            return []
    return []


def save_history(history):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(history, f, indent=2)


print(f"Sensor '{SENSOR_NAME}' gestartet. Schwellenwert: {TEMP_THRESHOLD}°C")
print(f"Temperaturquelle: {TEMP_SOURCE}")
print(f"Hardware: {'aktiv' if HARDWARE_ENABLED else 'deaktiviert (Mock-Modus)'}")

pwm_channel = None
pwm_path = None
period_ns = None

try:
    if HARDWARE_ENABLED:
        setup_relay(RELAY_PIN)
        pwm_channel, pwm_path, period_ns = setup_pwm(PWM_PIN, PWM_FREQ)

    while True:
        historie = load_history()
        jetzt = datetime.now()
        temperature = read_temperature()
        drehzahl = berechne_drehzahl(temperature)

        if temperature >= TEMP_THRESHOLD:
            if HARDWARE_ENABLED:
                set_relay(True)
                set_pwm_duty_cycle(drehzahl, pwm_path, period_ns)
            print(f"⚠️  {temperature}°C → Lüfter AN @ {drehzahl}%")
        else:
            if HARDWARE_ENABLED:
                set_relay(False)
                set_pwm_duty_cycle(0, pwm_path, period_ns)
            print(f"✅  {temperature}°C → Lüfter AUS")

        eintrag = {
            "sensor_id": SENSOR_ID,
            "name": SENSOR_NAME,
            "location": SENSOR_LOCATION,
            "temperature": temperature,
            "relay": "AN" if temperature >= TEMP_THRESHOLD else "AUS",
            "drehzahl_prozent": drehzahl,
            "timestamp": jetzt.strftime("%Y-%m-%dT%H:%M:%S")
        }
        historie.append(eintrag)

        grenze = jetzt - timedelta(hours=24)
        historie = [
            e for e in historie
            if datetime.strptime(e["timestamp"], "%Y-%m-%dT%H:%M:%S") > grenze
        ]

        save_history(historie)
        time.sleep(INTERVAL)

finally:
    if HARDWARE_ENABLED:
        try:
            if pwm_path and period_ns is not None:
                set_pwm_duty_cycle(0, pwm_path, period_ns)
        except Exception:
            pass
        try:
            set_relay(False)
        except Exception:
            pass
        if pwm_channel is not None:
            cleanup_pwm(pwm_channel)
        cleanup_gpio(RELAY_PIN)