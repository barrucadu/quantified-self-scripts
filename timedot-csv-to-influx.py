#!/usr/bin/env nix-shell
#! nix-shell -i python -p "python3.withPackages (ps: [ps.influxdb])"

import csv
import influxdb
import os
import sys

from datetime import datetime
from decimal import Decimal


def is_weekend_day(yyyy_mm_dd):
    # 0 = monday .. 6 = sunday
    return datetime.strptime(yyyy_mm_dd, "%Y-%m-%d").weekday() >= 5


aggregated = {}
first = True
work_tags = set()
for row in csv.reader(sys.stdin):
    if first:
        first = False
        continue

    _, date, _, _, tag, value, _ = row
    tag_bits = tag.replace("(", "").replace(")", "").split(":")

    aggregated[date] = aggregated.get(date, { "hours": {} })

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
        if current_tag.startswith("work:"):
            work_tags.add(current_tag)

        aggregated[date]["hours"][current_tag] = aggregated[date]["hours"].get(current_tag, Decimal("0")) + Decimal(value)

yesterday = None
prior_week_day = None
for date in sorted(aggregated.keys()):
    aggregated[date]["streaks"] = {}

    for tag in aggregated[date]["hours"].keys():
        if yesterday is None:
            aggregated[date]["streaks"][tag] = 1
        else:
            aggregated[date]["streaks"][tag] = aggregated[yesterday]["streaks"].get(tag, 0) + 1

    if is_weekend_day(date):
        # don't break work streaks over the weekend, only an actual
        # day off will do that
        if prior_week_day is not None:
            for tag in work_tags:
                if tag in aggregated[prior_week_day]["streaks"]:
                    aggregated[date]["streaks"][tag] = aggregated[prior_week_day]["streaks"]
    else:
        prior_week_day = date

    yesterday = date

data = []
for date, measurements in aggregated.items():
    for key, values in measurements.items():
        data.append({
            "measurement": f"timedot.{key}",
            "time": f"{date}T00:00:00Z",
            "fields": { tag: float(duration) for tag, duration in values.items() },
        })

influx = influxdb.InfluxDBClient(database=os.environ["INFLUX_DB"])
influx.write_points(data)
