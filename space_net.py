#!/usr/bin/env python3


import sys
import time
import random
from PIL import Image

sat_distance = 2

while True:
    #if sat distance is less than 3 units engage capture sequence. Let's hope this works boss.
    if sat_distance < 3:
        print("engaging capture sequence...")
        time.sleep(1)
        print("opening net hatch...")
        time.sleep(1)
        print("locking on to target...")
        time.sleep(1)
        for i in range(random.randint(1,15)):
            print("steady...")
            time.sleep(.1)
        print("FIRE NET")
        firing = random.randint(1,10)
        while firing != 1:
            firing = random.randint(1,50)
            print("we missed, relaunching assault")
            time.sleep(.1)
        print("Ladies and gentlemen. We got him.")
        img = Image.open("georgy.jpg")
        for i in range (0,random.randint(10,100)):
            img.rotate(int(15*i)).show()
            time.sleep(.2)
            # img.close()

        
        time.sleep(10)
        sat_distance = random.randint(1,255)
    else:
        print("We're too far away. Moving closer...")
        sat_distance = sat_distance - 1
