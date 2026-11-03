"""
Example for sending data to MQTT server

By default it talks to the course broker on localhost:1883 with the demo
account from course.env (start it with `docker compose up -d broker`).
Set MQTT_HOST (and MQTT_USERNAME / MQTT_PASSWORD if needed) to use another
broker, e.g. MQTT_HOST=test.mosquitto.org for Eclipse's public test broker.
"""
import sys
from pathlib import Path

from mqttUtils import BrokerSettings, MqttSender

# Login for the course broker; ignored once MQTT_HOST points elsewhere.
COURSE_ENV = Path(__file__).resolve().with_name('course.env')

if __name__ == "__main__":

    broker = BrokerSettings.from_env(defaults_file=COURSE_ENV)
    login = {'username': broker.username, 'password': broker.password}

    # sender test
    yee_sender = MqttSender('yee', broker.host, broker.port, **login)
    yoo_sender = MqttSender('yoo', broker.host, broker.port, **login)

    try:
        yee_sender.send({'test1': 1234, 'test2': 'yee'})
        yoo_sender.send(1234)
        yoo_sender.send(b'ABCDEFG')
        yoo_sender.send(['1', 'a', 'b'])
    except OSError as error:
        sys.exit(broker.unreachable(error))
    print(f'Sent 4 messages to {broker.describe()}')
