import machine
from machine import ADC, Pin
import network
from time import sleep
import ubluetooth as bluetooth
import math

SSID = "GoSolr"
PASSWORD = "#PoweredByTheSun"

currentSensor_SIG = [34, 35, 36, 39]
numSensors = 4
numIterations = 12
previousCurrents = [[0] * numSensors for _ in range(numIterations)]
numTerms = 3
sineCoefficients = [[0] * numTerms for _ in range(numSensors)]
sensitivity = 66.0
calculateCoefficients = False

GEYSER_THRESHOLD = 2.0  
geyser_on = False

MAX_TEMPERATURE = 70
MIN_TEMPERATURE = 30

RELAY_PINS = [2, 3, 4, 5]  
original_relay_states = [0] * len(RELAY_PINS)

def ble_callback(event, data):
    global SSID, PASSWORD

    if event == bluetooth.EVT_GAP_CONNECTED:
        pass
    elif event == bluetooth.EVT_GAP_DISCONNECTED:
        pass
    elif event == bluetooth.EVT_GATTS_WRITE:
        received_data = data.decode().split(",")
        if len(received_data) == 2:
            SSID, PASSWORD = received_data

bluetooth.active(True)
bluetooth.set_advertisement(name="GS BRAIN", connectable=True)
bluetooth.gatts_register_callback(ble_callback)
bluetooth.advertise(1000)

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)
while not wifi.isconnected():
    sleep(1)

adc = [ADC(Pin(pin)) for pin in currentSensor_SIG]
server = network.Server()

def predict_temperature(coefficients, phase, time):
    temperature = 0
    for i in range(len(coefficients)):
        temperature += coefficients[i] * math.sin(2 * math.pi * (i + 1) * time + phase)
    return temperature

def handle_client(client):
    request = client.recv(1024)
    if b"GET /calculate" in request:
        calculateCoefficients = True
    elif b"GET /temperature" in request:
        if geyser_on:
            time = 0  
            temperature = predict_temperature(sineCoefficients[0], 0, time)
        else:
            temperature = MAX_TEMPERATURE  
        response = "HTTP/1.1 200 OK\nContent-Type: text/html\n\n"
        response += "<!DOCTYPE html>\n<html>\n<head><title>Geyser Temperature</title></head>\n<body>"
        response += "<h1>Current Geyser Temperature</h1>"
        response += "<p>{:.2f} &deg;C</p>".format(temperature)
        response += "<form action=\"/switch\" method=\"post\">"
        response += "<input type=\"submit\" name=\"switch\" value=\"{}\">".format("Turn OFF" if geyser_on else "Turn ON")
        response += "</form>"
        response += "</body>\n</html>\n"
        client.sendall(response)
    elif b"POST /switch" in request:
        if geyser_on:
            geyser_on = False
            for idx, pin in enumerate(RELAY_PINS):
                machine.Pin(pin, machine.Pin.OUT).value(original_relay_states[idx])  
        else:
            geyser_on = True
            for pin in RELAY_PINS:
                machine.Pin(pin, machine.Pin.OUT).value(1)  
        client.sendall("HTTP/1.1 303 See Other\nLocation: /temperature\n\n")
    client.close()

while True:
    client = server.accept()
    if client:
        handle_client(client)

    if calculateCoefficients:
        for i, pin in enumerate(currentSensor_SIG):
            measured_pd = adc[i].read()

            voltage = measured_pd * (5000.0 / 4095)

            current = voltage / sensitivity

            for j in range(numIterations - 1, 0, -1):
                previousCurrents[j][i] = previousCurrents[j - 1][i]

            previousCurrents[0][i] = current

            sum_sin = [0] * numTerms
            sum_y = 0
            sum_y_sin = [0] * numTerms
            sum_y_sin2 = [0] * numTerms
            for k in range(numIterations):
                sum_y += previousCurrents[k][i]
                for n in range(numTerms):
                    sin_val = math.sin(2 * math.pi * (n + 1) * k / numIterations)
                    sum_sin[n] += sin_val
                    sum_y_sin[n] += previousCurrents[k][i] * sin_val
                    sum_y_sin2[n] += sin_val * sin_val
            for n in range(numTerms):
                sineCoefficients[i][n] = (sum_y_sin[n] * numIterations - sum_y * sum_sin[n]) / (
                        sum_y_sin2[n] * numIterations - sum_sin[n] * sum_sin[n])

        if geyser_on:
            total_current = sum(previousCurrents[0])
            if total_current > 5:
                max_current_index = previousCurrents[0].index(max(previousCurrents[0]))
                for idx, pin in enumerate(RELAY_PINS):
                    if idx != max_current_index:
                        machine.Pin(pin, machine.Pin.OUT).value(0)  

        if previousCurrents[0][0] > GEYSER_THRESHOLD:
            if not geyser_on:
                geyser_on = True
                for idx, pin in enumerate(RELAY_PINS):
                    original_relay_states[idx] = machine.Pin(pin).value()
                    machine.Pin(pin, machine.Pin.OUT).value(1)  
        else:
            if geyser_on:
                geyser_on = False
                for idx, pin in enumerate(RELAY_PINS):
                    machine.Pin(pin, machine.Pin.OUT).value(original_relay_states[idx])  

        calculateCoefficients = False

    sleep(600)  
