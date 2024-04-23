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

RELAY_PIN = 2  

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

adc = ADC(Pin(34))
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
            machine.Pin(RELAY_PIN, machine.Pin.OUT).value(0) 
        else:
            geyser_on = True
            machine.Pin(RELAY_PIN, machine.Pin.OUT).value(1)  
        client.sendall("HTTP/1.1 303 See Other\nLocation: /temperature\n\n")
    client.close()

while True:
    client = server.accept()
    if client:
        handle_client(client)

    if calculateCoefficients:
        for i in range(numSensors):
            measured_pd = adc.read()

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

        if previousCurrents[0][0] > GEYSER_THRESHOLD:
            if not geyser_on:
                geyser_on = True
                machine.Pin(RELAY_PIN, machine.Pin.OUT).value(1)  
        else:
            if geyser_on:
                geyser_on = False
                machine.Pin(RELAY_PIN, machine.Pin.OUT).value(0)  

        calculateCoefficients = False

    sleep(600)  
