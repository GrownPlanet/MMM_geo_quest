import queue

import paho.mqtt.client as mqtt_client
from config import BROKER, IN_TOPIC, OUT_TOPIC, PORT
from geo import Point, parse_location


class MqttClient:
    def __init__(self):
        self.messages: queue.Queue[str] = queue.Queue()
        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        self.client.connect(BROKER, PORT)
        self.client.loop_start()

    def _on_connect(self, client, _userdata, _flags, _reason_code, _properties):
        print("Info: Connected to MQTT broker!")
        client.subscribe(IN_TOPIC)

    def _on_message(self, _client, _userdata, msg):
        message = msg.payload.decode()
        self.messages.put(message)
        print(f"Info: Received on {msg.topic}: {message}")

    def get_location(self) -> Point | None:
        try:
            message = self.messages.get_nowait()
        except queue.Empty:
            return None

        return parse_location(message)

    def send_next_location(self, point: Point):
        self.client.publish(OUT_TOPIC, f"NEXT{point[0]},{point[1]}")

    def send_last(self):
        self.client.publish(OUT_TOPIC, "LAST")

    def close(self):
        self.client.loop_stop()
        self.client.disconnect()
