import argparse
import boto3
import numpy as np
import os
import time

import RPi.GPIO as gpio


AWS_REGION = os.environ.get("AWSREGION", "ap-northeast-2")
TABLE_NAME = os.environ.get("TABLE_NAME", "restroom-demo")

ROOM_ID = os.environ.get("ROOM_ID", "MZ_6F_M_01")

GPIO_OUT = os.environ.get("GPIO_OUT", "17")
GPIO_IN = os.environ.get("GPIO_IN", "27")

INTERVAL = os.environ.get("INTERVAL", "1.0")


ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
tbl = ddb.Table(TABLE_NAME)

distance_list = []
distance_len = 10


def parse_args():
    p = argparse.ArgumentParser(description="restroom")
    p.add_argument("--room-id", default=ROOM_ID, help="room id")
    p.add_argument("--gpio-out", type=int, default=GPIO_OUT, help="gpio out pin no")
    p.add_argument("--gpio-in", type=int, default=GPIO_IN, help="gpio in pin no")
    p.add_argument("--interval", type=float, default=INTERVAL, help="interval")
    return p.parse_args()


def put_item(args, distance):
    # ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
    # tbl = ddb.Table(TABLE_NAME)

    latest = int(round(time.time() * 1000))

    try:
        res = tbl.put_item(
            Item={"room_id": args.room_id, "distance": int(distance), "latest": latest}
        )
    except Exception as ex:
        print("Error:", ex, ROOM_ID, distance)
        res = []

    print("put_item", res)

    return res


def put_distance(args, distance):
    distance_list.append(distance)
    if len(distance_list) > distance_len:
        del distance_list[0]
    distance_sum = np.sum(distance_list)
    distance_avg = distance_sum / len(distance_list)

    put_item(args, distance_avg)


def main():
    args = parse_args()

    gpio.setmode(gpio.BCM)

    gpio.setup(args.gpio_out, gpio.OUT)
    gpio.setup(args.gpio_in, gpio.IN)

    try:
        while True:
            gpio.output(args.gpio_out, False)
            time.sleep(args.interval)

            gpio.output(args.gpio_out, True)
            time.sleep(0.00001)
            gpio.output(args.gpio_out, False)

            while gpio.input(args.gpio_in) == 0:
                continue
            pulse_start = time.time()

            while gpio.input(args.gpio_in) == 1:
                continue
            pulse_end = time.time()

            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17000
            distance = round(distance, 2)

            put_distance(args, distance)

            print("Distance", distance, "cm")
    except:
        gpio.cleanup()


if __name__ == "__main__":
    main()
