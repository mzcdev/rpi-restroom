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

INTERVAL = os.environ.get("INTERVAL", "3.0")

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

        self.avg_max = 0
        self.avg_min = 100

        self.available = "-"
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

        if self.dist_avg > self.avg_max:
            self.avg_max = self.dist_avg
        if self.dist_avg < self.avg_min:
            self.avg_min = self.dist_avg

        if self.dist_avg < self.args.boundary:
            self.available = "x"
            if prev_avg > self.args.boundary:
                self.latest = int(round(time.time() * 1000))
        else:
            self.available = "o"
            if prev_avg < self.args.boundary:
                self.latest = int(round(time.time() * 1000))

        self.put_item(distance)

        self.write_log(distance)

        return self.dist_avg

    def put_item(self, distance):
        # ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
        # tbl = ddb.Table(TABLE_NAME)

        updated = int(round(time.time() * 1000))

        item = {
            "room_id": self.args.room_id,
            "available": self.available,
            "distance": int(distance),
            "dist_avg": int(self.dist_avg),
            "avg_max": int(self.avg_max),
            "avg_min": int(self.avg_min),
            "latest": self.latest,
            "updated": updated,
        }
        print("put_item", item)

        if internet():
            try:
                res = self.tbl.put_item(Item=item)
            except Exception as ex:
                print("DDB Error:", ex, ROOM_ID, distance)
                res = []

            print("put_item", res)

        return res

    def write_log(self, distance):
        try:
            f = open("distance.out", "w")
            f.write(
                "{} : {} < {} < {} ".format(
                    int(distance), self.avg_min, self.dist_avg, self.avg_max
                )
            )
            f.close()
        except Exception as ex:
            print("File Error:", ex, ROOM_ID, distance)
            res = []


def main():
    args = parse_args()

    # room
    room = Room(args)

    # gpio
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
            # avg = round(avg, 2)

            print("Distance", distance, avg)
    except:
        gpio.cleanup()


if __name__ == "__main__":
    main()
