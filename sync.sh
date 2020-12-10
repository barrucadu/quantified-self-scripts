#!/usr/bin/env nix-shell
#! nix-shell -i bash -p hledger influxdb

set -e

QSELF_DIR=~/s/qself

source $QSELF_DIR/credentials

export INFLUX_DB="quantified_self"
echo "drop database ${INFLUX_DB}; create database ${INFLUX_DB};" | influx

# timedot
LEDGER_FILE="${QSELF_DIR}/t.timedot" hledger reg -O csv | ./timedot-csv-to-influx.py
