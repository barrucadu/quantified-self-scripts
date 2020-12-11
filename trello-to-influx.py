#!/usr/bin/env nix-shell
#! nix-shell -i python -p "python3.withPackages (ps: [ps.influxdb])"

import json
import influxdb
import os
import sys


def list_name_type(list_name):
    if list_name == "Routines":
        return None
    elif list_name in ["Has Prerequisites", "Backlog", "Upcoming", "This Sprint"]:
        return "TODO"
    elif list_name in ["Doing", "Waiting / Blocked"]:
        return "IN_PROGRESS"
    else:
        return "DONE"

data = []

for fname in sys.stdin:
    fname = fname.strip()
    date = os.path.splitext(os.path.basename(fname))[0]
    with open(fname) as f:
        today = json.load(f)

    measurements = {}

    for trello_list in today:
        for list_name in [trello_list["metadata"]["name"], list_name_type(trello_list["metadata"]["name"])]:
            if list_name is None:
                continue

            measurements["count"] = measurements.get("count", 0) + len(trello_list["cards"])
            measurements[f"list.{list_name}.count"] = measurements.get(f"list.{list_name}.count", 0) + len(trello_list["cards"])

            for card in trello_list["cards"]:
                for label in card["labels"]:
                    label_name = label["name"]
                    measurements[f"count.{label_name}"] = measurements.get(f"count.{label_name}", 0) + 1
                    measurements[f"list.{list_name}.count.{label_name}"] = measurements.get(f"list.{list_name}.count.{label_name}", 0) + 1

    data.extend([
        {
            "measurement": f"trello.{key}",
            "time": f"{date}T00:00:00Z",
            "fields": { "value": value },
        }
        for key, value in measurements.items()
    ])

influx = influxdb.InfluxDBClient(database=os.environ["INFLUX_DB"])
influx.write_points(data)
