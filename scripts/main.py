import gc
gc.collect()
free_memory = gc.mem_free()
print(f'Free memory: {free_memory} bytes')
from machine import Pin, SPI, SoftI2C, I2C
from ili9341 import Display, color565
import random
import time

ROTATION = 180

spi = SPI(1, baudrate=30000000, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
display = Display(spi, cs=Pin(5), dc=Pin(2), rst=Pin(4), rotation=ROTATION)
print('w=',display.width,'h=',display.height)

gc.collect()
free_memory = gc.mem_free()
print(f'Free memory: {free_memory} bytes')
st=time.ticks_us()
display.draw_circle(120,160,100,color565(0,255,0))
display.fill_circle(120,160,80,color565(250,255,0))
ed=time.ticks_us()
print('esp32 -->',(ed-st)/1e6,'sec')
