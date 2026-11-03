"""
Example for building MQTT Subscriber

Connects to test.mosquitto.org unless MQTT_HOST is set; inside the course
containers (docker compose run --rm python example_subscriber.py) it
uses the course broker and its demo account.
"""
import time

from mqttUtils import BrokerSettings, MqttSubscriber

# Eclipse's public test broker: anyone can read and write every topic.
# You can also run your own: `docker compose up -d broker` in this repo.
PUBLIC_TEST_BROKER = 'test.mosquitto.org'

if __name__ == "__main__":

    broker = BrokerSettings.from_env(default_host=PUBLIC_TEST_BROKER)
    # Set topics we subscribe
    #   yoo
    #   yee
    TOPICS = ['yoo', 'yee']

    mc = MqttSubscriber(
        broker.host, TOPICS, broker.port, username=broker.username, password=broker.password
    )

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
