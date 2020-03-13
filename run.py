import argparse
import boto3
import json
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

JSON_PATH = os.environ.get("JSON_PATH", "data.json")


def parse_args():
    p = argparse.ArgumentParser(description="restroom")
    p.add_argument("--room-id", default=ROOM_ID, help="room id")
    p.add_argument("--gpio-out", type=int, default=GPIO_OUT, help="gpio out pin no")
    p.add_argument("--gpio-in", type=int, default=GPIO_IN, help="gpio in pin no")
    p.add_argument("--interval", type=float, default=INTERVAL, help="interval")
    p.add_argument("--boundary", type=float, default=BOUNDARY, help="boundary")
    p.add_argument("--json-path", default=JSON_PATH, help="json path")
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

        ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
        self.tbl = ddb.Table(TABLE_NAME)

        self.load()

    def load(self):
        if os.path.isfile(self.args.json_path):
            f = open(self.args.json_path)
            self.data = json.load(f)
            f.close()
        else:
            self.data = {
                "history": [],
                "length": 10,
                "max": 10,
                "min": 0,
                "sum": 0,
                "avg": 0,
                "distance": 0,
                "available": "-",
                "latest": int(round(time.time() * 1000)),
            }

        print(json.dumps(self.data))

        self.save()

    def save(self):
        with open(self.args.json_path, "w") as f:
            json.dump(self.data, f)
        f.close()

    def set_distance(self, distance):
        prev = self.data["avg"]

        self.data["distance"] = round(distance, 2)

        self.data["history"].append(self.data["distance"])
        if len(self.data["history"]) > self.data["length"]:
            del self.data["history"][0]

        self.data["sum"] = round(np.sum(self.data["history"]), 2)
        self.data["avg"] = round(self.data["sum"] / len(self.data["history"]), 2)

        if self.data["avg"] < self.args.boundary:
            self.data["available"] = "x"
            if prev > self.args.boundary:
                self.data["latest"] = int(round(time.time() * 1000))
        else:
            self.data["available"] = "o"
            if prev < self.args.boundary:
                self.data["latest"] = int(round(time.time() * 1000))

        self.put_item()

        self.save()

        return self.data["avg"]

    def put_item(self):
        print("put_item", self.data["distance"])

        # ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
        # tbl = ddb.Table(TABLE_NAME)

        updated = int(round(time.time() * 1000))

        item = {
            "room_id": self.args.room_id,
            "available": self.data["available"],
            "distance": int(self.data["distance"]),
            "latest": self.data["latest"],
            "updated": updated,
        }
        print("put_item", item)

        if internet():
            try:
                res = self.tbl.put_item(Item=item)
            except Exception as ex:
                print("DDB Error:", ex, self.args.room_id, self.data["distance"])
                res = []

            print("put_item", res)
        else:
            res = []

        return res


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

            print("Distance", distance, avg)
    except:
        gpio.cleanup()


if __name__ == "__main__":
    main()
