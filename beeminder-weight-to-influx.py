#!/usr/bin/env nix-shell
#! nix-shell -i python -p "python3.withPackages (ps: [ps.influxdb])"

import json
import influxdb
import os
import sys

api_response = json.load(sys.stdin)

data = [
    {
        "measurement": "weight",
        "time": datapoint["timestamp"],
        "fields": { "value": datapoint["value"] },
    }
    for datapoint in api_response["datapoints"]
]

influx = influxdb.InfluxDBClient(database=os.environ["INFLUX_DB"])
influx.write_points(data, time_precision="s")
