import argparse
import boto3
import numpy as np
import os
import socket
import time

import RPi.GPIO as gpio


AWS_REGION = os.environ.get("AWSREGION", "ap-northeast-2")
TABLE_NAME = os.environ.get("TABLE_NAME", "restroom-rooms-demo")

ROOM_ID = os.environ.get("ROOM_ID", "MZ_6F_M_01")

GPIO_OUT = os.environ.get("GPIO_OUT", "17")
GPIO_IN = os.environ.get("GPIO_IN", "27")

INTERVAL = os.environ.get("INTERVAL", "1.0")

BOUNDARY = os.environ.get("BOUNDARY", "80.0")


def parse_args():
    p = argparse.ArgumentParser(description="restroom")
    p.add_argument("--room-id", default=ROOM_ID, help="room id")
    p.add_argument("--gpio-out", type=int, default=GPIO_OUT, help="gpio out pin no")
    p.add_argument("--gpio-in", type=int, default=GPIO_IN, help="gpio in pin no")
    p.add_argument("--interval", type=float, default=INTERVAL, help="interval")
    p.add_argument("--boundary", type=float, default=BOUNDARY, help="boundary")
    return p.parse_args()


def internet(host="8.8.8.8", port=53, timeout=1):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        print(ex)
        return False


class Room:
    def __init__(self, args):
        self.args = args

        self.dist_list = []
        self.dist_max = 10
        self.dist_sum = 0
        self.dist_avg = 0

        self.available = "x"
        self.latest = int(round(time.time() * 1000))

        ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
        self.tbl = ddb.Table(TABLE_NAME)

    def set_distance(self, distance):
        prev_avg = self.dist_avg

        self.dist_list.append(distance)

        if len(self.dist_list) > self.dist_max:
            del self.dist_list[0]

        dist_sum = np.sum(self.dist_list)

        self.dist_avg = dist_sum / len(self.dist_list)

        if prev_avg > self.args.boundary and self.dist_avg < self.args.boundary:
            self.available = "x"
            self.latest = int(round(time.time() * 1000))

            self.put_item(self.dist_avg, "x")
        elif prev_avg < self.args.boundary and self.dist_avg > self.args.boundary:
            self.available = "o"
            self.latest = int(round(time.time() * 1000))

            self.put_item(self.dist_avg, "o")

        return self.dist_avg

    def put_item(self, distance, available):
        # ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
        # tbl = ddb.Table(TABLE_NAME)

        latest = int(round(time.time() * 1000))

        item = {
            "room_id": self.args.room_id,
            "distance": int(distance),
            "available": available,
            "latest": latest,
        }
        print("put_item", item)

        if internet():
            try:
                res = self.tbl.put_item(Item=item)
            except Exception as ex:
                print("Error:", ex, ROOM_ID, distance)
                res = []

            print("put_item", res)

        return res


def main():
    args = parse_args()

    # room
    room = Room(args)

    avg_max = 0
    avg_min = 100

    boundary = args.boundary

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

            avg = room.set_distance(distance)
            avg = round(avg, 2)

            if avg > avg_max:
                avg_max = avg
            if avg < avg_min:
                avg_min = avg

            print("Distance", distance, avg_min, avg, avg_max)

            f = open("log.out", "w")
            f.write("{} : {} < {} < {} ".format(distance, avg_min, avg, avg_max))
            f.close()
    except:
        gpio.cleanup()


if __name__ == "__main__":
    main()
