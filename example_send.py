"""
Example for sending data to MQTT server

Connects to test.mosquitto.org unless MQTT_HOST is set; inside the course
containers (docker compose run --rm python example_send.py) it uses
the course broker and its demo account.
"""

from mqttUtils import BrokerSettings, MqttSender

# Eclipse's public test broker: anyone can read and write every topic.
PUBLIC_TEST_BROKER = 'test.mosquitto.org'

if __name__ == "__main__":

    broker = BrokerSettings.from_env(default_host=PUBLIC_TEST_BROKER)
    login = {'username': broker.username, 'password': broker.password}

    # sender test
    yee_sender = MqttSender('yee', broker.host, broker.port, **login)
    yoo_sender = MqttSender('yoo', broker.host, broker.port, **login)

    yee_sender.send({'test1': 1234, 'test2': 'yee'})
    yoo_sender.send(1234)
    yoo_sender.send(b'ABCDEFG')
    yoo_sender.send(['1', 'a', 'b'])
    print(f'Sent 4 messages to {broker.describe()}')
