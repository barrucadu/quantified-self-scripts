#!/usr/bin/env nix-shell
#! nix-shell -i python -p "python3.withPackages (ps: [ps.requests])"

import json
import os
import requests

TRELLO_KEY = os.environ["TRELLO_KEY"]
TRELLO_TOKEN = os.environ["TRELLO_TOKEN"]


def get(endpoint):
    r = requests.get(f"https://api.trello.com{endpoint}?key={TRELLO_KEY}&token={TRELLO_TOKEN}")
    r.raise_for_status()
    return r.json()

boards = get("/1/members/me/boards")

todo_board_id = None
for board in boards:
    if board["name"] == "To Do":
        todo_board_id = board["id"]
        break

if todo_board_id is None:
    raise Exception("could not find todo board")

todo_lists = []
for trello_list in get(f"/1/boards/{todo_board_id}/lists"):
    cards = get(f"/1/lists/{trello_list['id']}/cards")

    todo_lists.append({
        "metadata": trello_list,
        "cards": cards,
    })

print(json.dumps(todo_lists))
