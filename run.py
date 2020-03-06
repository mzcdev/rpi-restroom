import argparse
import time

import RPi.GPIO as gpio


def parse_args():
    p = argparse.ArgumentParser(description="restroom")
    p.add_argument("--trigger", default=17, help="trigger")
    p.add_argument("--echo", default=27, help="echo")
    p.add_argument("--interval", default=0.5, help="interval")


def main():
    print("start")

    args = parse_args()

    gpio.setmode(gpio.BCM)

    gpio.setup(args.trigger, gpio.OUT)
    gpio.setup(args.echo, gpio.IN)

    try:
        while True:
            gpio.output(args.trigger, False)
            time.sleep(args.interval)

            gpio.output(args.trigger, True)
            time.sleep(0.00001)
            gpio.output(args.trigger, False)

            while gpio.input(args.echo) == 0:
                continue
            pulse_start = time.time()

            while gpio.input(args.echo) == 1:
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
