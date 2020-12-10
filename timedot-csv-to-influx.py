#!/usr/bin/env nix-shell
#! nix-shell -i python -p "python3.withPackages (ps: [ps.influxdb])"

import csv
import influxdb
import os
import sys

from decimal import Decimal

aggregated = {}
first = True
for row in csv.reader(sys.stdin):
    if first:
        first = False
        continue

    _, date, _, _, tag, value, _ = row
    tag_bits = tag.replace("(", "").replace(")", "").split(":")

    aggregated[date] = aggregated.get(date, {})

    all_tags = ["__"]
    if tag_bits[0] == "work":
        if tag_bits[-1] in ["active", "meetings"]:
            all_tags.append(f"work:__{tag_bits[-1]}")
        else:
            all_tags.append("work:__other")

    current_tag = None
    for bit in tag_bits:
        if current_tag is None:
            current_tag = bit
        else:
            current_tag = f"{current_tag}:{bit}"
        all_tags.append(current_tag)

    for current_tag in all_tags:
        aggregated[date][current_tag] = aggregated[date].get(current_tag, Decimal("0")) + Decimal(value)

data = []
for date, values in aggregated.items():
    data.append({
        "measurement": "timedot",
        "time": f"{date}T00:00:00Z",
        "fields": { tag: float(duration) for tag, duration in values.items() },
    })

influx = influxdb.InfluxDBClient(database=os.environ["INFLUX_DB"])
influx.write_points(data)
