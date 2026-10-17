"""
File: common.py

Shared configuration and JSON message helpers.
"""

import json
from pathlib import Path


def load_config(filename):
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def config_path(config_file, filename):
    return str(Path(config_file).resolve().parent / filename)


def valid_name(name):
    return isinstance(name, str) and 1 <= len(name) <= 64 and all(c.isalnum() or c in "_.-" for c in name)


def send_message(connection, message):
    connection.sendall((json.dumps(message) + "\n").encode("utf-8"))


def receive_message(reader):
    line = reader.readline()
    if not line:
        raise ConnectionError("Connection closed.")
    return json.loads(line.decode("utf-8"))
