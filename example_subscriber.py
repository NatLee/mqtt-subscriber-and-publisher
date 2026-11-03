"""
Example for building MQTT Subscriber

By default it talks to the course broker on localhost:1883 with the demo
account from course.env (start it with `docker compose up -d broker`).
Set MQTT_HOST (and MQTT_USERNAME / MQTT_PASSWORD if needed) to use another
broker, e.g. MQTT_HOST=test.mosquitto.org for Eclipse's public test broker.
"""
import sys
import time
from pathlib import Path

from mqttUtils import BrokerSettings, MqttSubscriber

# Login for the course broker; ignored once MQTT_HOST points elsewhere.
COURSE_ENV = Path(__file__).resolve().with_name('course.env')

if __name__ == "__main__":

    broker = BrokerSettings.from_env(defaults_file=COURSE_ENV)
    # Set topics we subscribe
    #   yoo
    #   yee
    TOPICS = ['yoo', 'yee']

    try:
        mc = MqttSubscriber(
            broker.host, TOPICS, broker.port, username=broker.username, password=broker.password
        )
    except OSError as error:
        sys.exit(broker.unreachable(error))

    mc.client.loop_start()  # official way to run in background!

    # The network thread does the work; the main thread just waits for Ctrl+C.
    # (Sleeping instead of `while True: pass` keeps the CPU idle.)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Exit!')
    finally:
        mc.client.disconnect()
        mc.client.loop_stop()
