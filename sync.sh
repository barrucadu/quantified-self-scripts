#!/usr/bin/env nix-shell
#! nix-shell -i bash -p hledger influxdb

set -e

export PATH="$(pwd):$PATH"

TODAY="$(date +%Y-%m-%d)"

WORK_DIR="$(mktemp -d)"
trap "{ rm -rf $WORK_DIR; }" EXIT
cd "$WORK_DIR"

QSELF_DIR=~/s/qself

source $QSELF_DIR/credentials

export INFLUX_DB="quantified_self"
echo "drop database ${INFLUX_DB}; create database ${INFLUX_DB};" | influx

# timedot
LEDGER_FILE="${QSELF_DIR}/t.timedot" hledger reg -O csv | timedot-csv-to-influx.py

# weight (+ backup the API response)
if [[ -e "${QSELF_DIR}/weight.tar.xz" ]]; then
  tar xf "${QSELF_DIR}/weight.tar.xz"
  mv "${QSELF_DIR}/weight.tar.xz" "${QSELF_DIR}/weight.tar.xz.1"
else
  mkdir weight
fi

curl "https://www.beeminder.com/api/v1/users/barrucadu/goals/weight.json?datapoints=true&auth_token=${BEEMINDER_AUTH_TOKEN}" > "weight/${TODAY}.json"
beeminder-weight-to-influx.py < "weight/${TODAY}.json"
tar c weight | xz -9e > "${QSELF_DIR}/weight.tar.xz"

# trello (+ backup the API response)
if [[ -e "${QSELF_DIR}/trello.tar.xz" ]]; then
  tar xf "${QSELF_DIR}/trello.tar.xz"
  mv "${QSELF_DIR}/trello.tar.xz" "${QSELF_DIR}/trello.tar.xz.1"
else
  mkdir trello
fi

TRELLO_KEY="$TRELLO_KEY" TRELLO_TOKEN="$TRELLO_TOKEN" scrape-trello.py > "trello/${TODAY}.json"
ls trello | sed 's:^:./trello/:' | sort | trello-to-influx.py
tar c trello | xz -9e > "${QSELF_DIR}/trello.tar.xz"
