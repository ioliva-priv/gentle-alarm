import network
from machine import Pin, PWM
import time
from umqtt.robust import MQTTClient
import ssl
import ntptime

#URL: 699cc49993cd475aaad044788016c778.s1.eu.hivemq.cloud
#Username: cornerstone
#Password: Cornerstone1
#Topic: Alarm
#Port: 8883
#Websocket port: 8884

wlan = network.WLAN(network.STA_IF)
wlan.active(True)


onboard_led = Pin('LED', Pin.OUT)
onboard_led.value(1)

button = Pin(15, Pin.IN, Pin.PULL_DOWN)

buzzer = Pin(6, Pin.OUT)
buzzer.value(0)

def try_connect(username, password):
    wlan.connect(username, password)
    time.sleep(5)
    connected = wlan.isconnected()
    print(connected)
    return connected

if not try_connect("Chris","JJ1700BB"):
    try_connect("FOUND Study", "FSTurtlebay")

ntptime.settime()

mqtt_server = '699cc49993cd475aaad044788016c778.s1.eu.hivemq.cloud'
client_id = "picouniqueid123"
topic_sub = b'Alarm'


def sub_cb(topic, msg):
    topic_decoded = topic.decode("utf-8")
    print(f"New message on topic {topic_decoded}")
    msg_decoded = msg.decode('utf-8')
    print(msg)
    if topic_decoded != "Alarm":
        return
    try:
        timestamp = int(msg_decoded)
        global alarm_times
        alarm_times.append(timestamp)
        print(f"Alarm time added: {timestamp}")
    except ValueError:
        print("Invalid timestamp: {msg_decoded}")
    
    
def mqtt_connect():
    client = MQTTClient(client_id, mqtt_server, keepalive=60, port=8883, user="picow", password="Cornerstone1", ssl=True
                        , ssl_params={"server_hostname": mqtt_server, "cert_reqs": ssl.CERT_NONE})
    client.set_callback(sub_cb)
    client.connect()
    print('Connected to %s MQTT Broker'%(mqtt_server))
    
    for i in range(10):
        onboard_led.value(1)
        time.sleep(0.05)
        onboard_led.value(0)
        time.sleep(0.05)
    
    return client

def reconnect():
    print('Failed to connect to MQTT Broker. Reconnecting...')
    time.sleep(5)
    machine.reset()
    
try:
    client = mqtt_connect()
except OSError as e:
    reconnect()

alarm_times = []
next_alarm_time = None

current_time = time.time()
while True:
    while not next_alarm_time or current_time < next_alarm_time:
        current_time = time.time()
        
        alarm_times = list(filter(lambda alarm_time: alarm_time >= current_time - 10, alarm_times))
        
        next_alarm_time = min(alarm_times) if alarm_times else None
        client.subscribe(topic_sub)
        
        if next_alarm_time:
            time_until_alarm = next_alarm_time - current_time
            alarm_message = f"Alarm set for {time_until_alarm} seconds from now."
            print(alarm_message)
            client.publish("Updates", alarm_message.encode("utf-8"))
        else:
            print("Alarm not set. Send an alarm time to the server to begin.")
        
        time.sleep(1)

    button_pressed = False
    print("Alarm!")

    next_buzzer_switch_time = current_time
    buzzer_value = 1
    while not button_pressed:
        current_time = time.time()
        if button.value() == 1:
            button_pressed = True
            break
        elif current_time >= next_buzzer_switch_time:
            next_buzzer_switch_time += 1
            buzzer_value = -buzzer_value + 1
            buzzer.value(buzzer_value)
            
        time.sleep(0.001)

    buzzer.value(0)
    print("Alarm disabled.")
    button_pressed = False
    alarm_times = list(filter(lambda alarm_time: alarm_time >= current_time, alarm_times))
    next_alarm_time = min(alarm_times) if alarm_times else None


