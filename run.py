import argparse
import time

import RPi.GPIO as gpio


TRIG = 17
ECHO = 27

INTERVAL = 0.5


def parse_args():
    p = argparse.ArgumentParser(description="restroom")
    p.add_argument("--trigger", type=None, default=17, help="trigger")
    p.add_argument("--echo", type=None, default=27, help="echo")
    p.add_argument("--interval", type=float, default=0.5, help="interval")


def main():
    print("start")

    # args = parse_args()

    gpio.setmode(gpio.BCM)

    gpio.setup(TRIG, gpio.OUT)
    gpio.setup(ECHO, gpio.IN)

    try:
        while True:
            gpio.output(TRIG, False)
            time.sleep(INTERVAL)

            gpio.output(TRIG, True)
            time.sleep(0.00001)
            gpio.output(TRIG, False)

            while gpio.input(ECHO) == 0:
                continue
            pulse_start = time.time()

            while gpio.input(ECHO) == 1:
                continue
            pulse_end = time.time()

            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17000
            distance = round(distance, 2)

            print("Distance", distance, "cm")
    except:
        gpio.cleanup()


if __name__ == "__main__":
    main()
