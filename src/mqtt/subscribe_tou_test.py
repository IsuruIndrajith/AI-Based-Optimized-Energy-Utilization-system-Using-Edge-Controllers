import paho.mqtt.client as mqtt

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC = "power/tou_domestic"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to Mosquitto broker!")
        client.subscribe(MQTT_TOPIC, qos=1)
        print(f"Subscribed to {MQTT_TOPIC}")
    else:
        print("Failed to connect, return code:", rc)

def on_message(client, userdata, msg):
    print(f"{msg.topic}: {msg.payload.decode()}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("Connecting to broker...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
