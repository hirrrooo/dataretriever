"""
File: clienthandler.py

Handles one monitoring client's authentication and status reports.
"""

import logging
from threading import Thread
from time import monotonic, strftime

from auth import verify_client
from common import receive_message, send_message


def check_report(report):
    if report.get("type") != "report" or "services" not in report:
        raise ValueError("Expected a monitoring report.")


def add_event(record, name, message):
    record["history"].append(strftime("%H:%M:%S") + " " + message)
    record["history"] = record["history"][-20:]
    logging.info("%s: %s", name, message)


def find_warnings(report, config):
    warnings = []
    if report["cpu"] >= config["cpu_warning"]:
        warnings.append("High CPU usage")
    if report["memory"] >= config["memory_warning"]:
        warnings.append("High memory usage")
    for service, state in report["services"].items():
        if state != "active":
            warnings.append(service + ": " + state)
    return warnings


def save_report(hosts, name, address, report, config):
    if name not in hosts:
        hosts[name] = {"online": False, "report": None,
                       "history": [], "warnings": []}
    record = hosts[name]
    previous = record["report"]

    if not record["online"]:
        add_event(record, name, "ONLINE")

    if previous is not None:
        for service, state in report["services"].items():
            old_state = previous["services"].get(service, "unmonitored")
            if state != old_state:
                message = service + ": " + old_state + " -> " + state
                add_event(record, name, message)
        for service in previous["services"]:
            if service not in report["services"]:
                add_event(record, name, service + ": monitoring removed")

    warnings = find_warnings(report, config)
    if warnings != record["warnings"]:
        if warnings:
            add_event(record, name, "; ".join(warnings))
        else:
            add_event(record, name, "Warnings cleared")

    record["online"] = True
    record["address"] = address
    record["report"] = report
    record["warnings"] = warnings
    record["last_seen"] = monotonic()
    record["last_report"] = strftime("%H:%M:%S")


class ClientHandler(Thread):
    """One thread handles one connected monitoring client."""

    def __init__(self, client, address, config, hosts, connections, lock):
        # Handler threads end when the server program exits.
        Thread.__init__(self, daemon=True)
        self.client = client
        self.address = address
        self.config = config
        self.hosts = hosts
        self.connections = connections
        self.lock = lock
        self.client_id = None

    def authenticate(self, reader):
        message = receive_message(reader)
        name = message.get("server_id")
        credential = message.get("credential")

        if message.get("type") != "authentication" or not name or not credential:
            return False
        if not verify_client(name, credential, self.config["client_file"]):
            return False

        # The lock protects data shared by the client threads and server commands.
        with self.lock:
            if name in self.connections:
                return False
            self.connections[name] = self.client
            self.client_id = name
        return True

    def run(self):
        try:
            self.client.settimeout(10)
            with self.client.makefile("rb") as reader:
                if not self.authenticate(reader):
                    send_message(self.client, {"type": "error",
                                 "message": "Invalid login or identifier already connected."})
                    return

                send_message(self.client, {"type": "auth_ok"})
                # No report before this timeout means the client is offline.
                self.client.settimeout(self.config["offline_timeout"])
                while True:
                    report = receive_message(reader)
                    check_report(report)
                    with self.lock:
                        save_report(self.hosts, self.client_id, self.address[0],
                                    report, self.config)
                    send_message(self.client, {"type": "report_ok"})
        except (OSError, ValueError, ConnectionError) as error:
            logging.info("Connection from %s closed: %s", self.address[0], error)
        finally:
            with self.lock:
                if self.client_id is not None:
                    del self.connections[self.client_id]
                    if self.client_id in self.hosts:
                        record = self.hosts[self.client_id]
                        record["online"] = False
                        add_event(record, self.client_id, "OFFLINE")
            self.client.close()
