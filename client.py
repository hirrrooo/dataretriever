"""
File: client.py

Connects to DataRetriever Server, authenticates, and sends Linux monitoring reports.
Retries the connection when the server is unavailable.
"""

import os
import subprocess
from getpass import getpass
from pathlib import Path
from socket import AF_INET, SOCK_STREAM, socket
from time import monotonic, sleep

import psutil

from auth import BASE_SHIFT, encrypt
from common import load_config, receive_message, send_message, valid_name


CONFIG_FILE = Path(__file__).with_name("client_config.json")
RETRY_DELAY = 5


def check_services(services):
    results = {}
    for service in services:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True, text=True, timeout=3)
            state = result.stdout.strip() or "unknown"
        except (OSError, subprocess.TimeoutExpired):
            state = "unknown"
        results[service] = state
    return results


def collect_report(services, previous_network, previous_time):
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    network = psutil.net_io_counters()
    now = monotonic()
    elapsed = now - previous_time

    # Network counters are totals, so use the change between samples for a rate.
    received = max(0, network.bytes_recv - previous_network.bytes_recv)
    sent = max(0, network.bytes_sent - previous_network.bytes_sent)
    report = {
        "type": "report",
        "cpu": cpu,
        "memory": memory,
        "rx_kbps": round(received / elapsed / 1024, 2),
        "tx_kbps": round(sent / elapsed / 1024, 2),
        "services": check_services(services),
    }
    return report, network, now


def authenticate(server, reader, server_id, credential):
    message = {"type": "authentication", "server_id": server_id,
               "credential": credential}
    send_message(server, message)
    reply = receive_message(reader)
    return reply.get("type") == "auth_ok"


def run_client(config, credential):
    address = (config["server_host"], config["port"])
    while True:
        server = socket(AF_INET, SOCK_STREAM)
        try:
            server.settimeout(10)
            server.connect(address)
            with server.makefile("rb") as reader:
                if not authenticate(server, reader, config["server_id"], credential):
                    print("Login rejected. Check the identifier and key.")
                    print("Make sure another client is not using this identifier.")
                    return

                print("Connected as", config["server_id"])
                previous_network = psutil.net_io_counters()
                previous_time = monotonic()
                while True:
                    report, previous_network, previous_time = collect_report(
                        config["services"], previous_network, previous_time)
                    send_message(server, report)
                    reply = receive_message(reader)
                    if reply.get("type") != "report_ok":
                        raise ConnectionError("Server rejected the report.")
                    sleep(config["interval"])
        except (OSError, ValueError, ConnectionError) as error:
            print("Connection problem:", error)
        finally:
            server.close()

        print(f"Retrying in {RETRY_DELAY} seconds...")
        sleep(RETRY_DELAY)


def main():
    try:
        config = load_config(CONFIG_FILE)
        config["server_id"] = os.getenv("DATRETRIEVER_ID", config["server_id"])
        if not valid_name(config["server_id"]):
            raise ValueError("Set a valid server identifier.")

        auth_key = os.getenv("DATRETRIEVER_KEY")
        if auth_key is None:
            auth_key = getpass("Authentication Key: ")
        if not auth_key:
            raise ValueError("Authentication key cannot be empty.")
        credential = encrypt(auth_key, BASE_SHIFT)
        run_client(config, credential)
    except (KeyboardInterrupt, EOFError):
        print("\nClient stopped.")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("Client error:", error)


if __name__ == "__main__":
    main()
