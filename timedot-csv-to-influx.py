#!/usr/bin/env nix-shell
#! nix-shell -i python -p "python3.withPackages (ps: [ps.influxdb])"

import csv
import influxdb
import os
import sys

from datetime import datetime
from decimal import Decimal


def titlecase(s):
    return {
        "ttrpg": "TTRPGs",
        "line": "Line Management",
        "lunch": "Lunch Break",
        "foodprep": "Food Prep",
    }.get(s, s.title())


def to_sentence(ss):
    words = None
    for s in ss:
        if words is None:
            words = [titlecase(s)]
        else:
            words.append(f"({s})")
    return " ".join(words)


def tag_names(tag):
    tag_bits = tag.replace("(", "").replace(")", "").split(":")

    tags = [
        "__",
        f"raw.{tag}",
        f"top.{titlecase(tag_bits[0])}",
    ]

    if len(tag_bits) > 1:
        tags.append(f"tag.{tag_bits[0]}.is.{to_sentence(tag_bits[1:])}")
        tags.append(f"tag.{tag_bits[0]}.cat1.{titlecase(tag_bits[1])}")

        if len(tag_bits) > 2:
            tags.append(f"tag.{tag_bits[0]}.cat2.{titlecase(tag_bits[2])}")
        else:
            tags.append(f"tag.{tag_bits[0]}.cat2.Other")

    return tags


def is_work_tag(tag):
    return tag.startswith("raw.work") or tag.startswith("top.Work") or tag.startswith("tag.work")


def is_weekend_day(yyyy_mm_dd):
    # 0 = monday .. 6 = sunday
    return datetime.strptime(yyyy_mm_dd, "%Y-%m-%d").weekday() >= 5


aggregated = {}
first = True
all_tags = set()
work_tags = set()
for row in csv.reader(sys.stdin):
    if first:
        first = False
        continue

    _, date, _, _, tag, value, _ = row

    aggregated[date] = aggregated.get(date, { "hours": {} })

    for tag in tag_names(tag):
        all_tags.add(tag)
        if is_work_tag(tag):
            work_tags.add(tag)

        aggregated[date]["hours"][tag] = aggregated[date]["hours"].get(tag, Decimal("0")) + Decimal(value)

yesterday = None
prior_week_day = None
for date in sorted(aggregated.keys()):
    aggregated[date]["streaks"] = {}

    for tag in all_tags:
        aggregated[date]["hours"][tag] = aggregated[date]["hours"].get(tag, 0)

        if aggregated[date]["hours"][tag] == 0:
            if is_weekend_day(date) and tag in work_tags and prior_week_day is not None:
                # don't break work streaks over the weekend, only an actual
                # day off will do that
                aggregated[date]["streaks"][tag] = aggregated[prior_week_day]["streaks"][tag]
            else:
                aggregated[date]["streaks"][tag] = 0
        else:
            if yesterday is None:
                aggregated[date]["streaks"][tag] = 1
            else:
                aggregated[date]["streaks"][tag] = aggregated[yesterday]["streaks"][tag] + 1

    if not is_weekend_day(date):
        prior_week_day = date

    yesterday = date

data = []
for date, measurements in aggregated.items():
    for key1, values in measurements.items():
        # Storing all the measurements as both fields on
        # `{key1}.as_fields` and more specific measurements on
        # `{key2}` is kind of horrible... but:
        #
        # 1. InfluxQL is really limited and doesn't allow
        # cross-measurement maths, so having multiple fields in the
        # same measurement lets me calculate (eg) % leisure hours on
        # the dashboard without needing to do it in this script.
        #
        # 2. Grafana can only do alias patterns on measurement names,
        # not field names.  So to avoid hard-coding a big list of
        # names in the dashboard, it's convenient to use multiple
        # measurements which I can alias by.
        #
        # I think using Flux (the new InfluxDB query language) would
        # let me use measurements only, but I haven't got around to
        # learning that yet.
        for key2, value in values.items():
            data.append({
                "measurement": f"timedot.{key1}.{key2}",
                "time": f"{date}T00:00:00Z",
                "fields": { "value": float(value), "is_weekend_day": "yes" if is_weekend_day(date) else "no" },
            })

        fields = { key2: float(value) for key2, value in values.items() }
        fields["is_weekend_day"] = "yes" if is_weekend_day(date) else "no"
        data.append({
            "measurement": f"timedot.{key1}.as_fields",
            "time": f"{date}T00:00:00Z",
            "fields": fields,
        })

influx = influxdb.InfluxDBClient(database=os.environ["INFLUX_DB"])
influx.write_points(data)
