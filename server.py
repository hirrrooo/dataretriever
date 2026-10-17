"""
File: server.py

Accepts monitoring clients and displays their latest reports.
Each connection is passed to a ClientHandler thread.
"""

import logging
from pathlib import Path
from socket import AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, socket
from threading import Lock, Thread
from time import monotonic

from auth import register_client
from clienthandler import ClientHandler
from common import config_path, load_config


CONFIG_FILE = Path(__file__).with_name("server_config.json")
COMMANDS = "Commands: register, list, status <name>, history <name>, help, quit"


def accept_clients(server, config, hosts, connections, lock):
    while True:
        try:
            client, address = server.accept()
        except OSError:
            return
        handler = ClientHandler(client, address, config, hosts, connections, lock)
        handler.start()


def show_list(hosts):
    print(f"{'HOST':<20} {'STATUS':<9} {'CPU':>7} {'RAM':>7} {'RX KiB/s':>10} {'TX KiB/s':>10}")
    if not hosts:
        print("No reports received yet.")

    for name in sorted(hosts):
        record = hosts[name]
        if not record["online"]:
            print(f"{name:<20} {'OFFLINE':<9} {'--':>7} {'--':>7} {'--':>10} {'--':>10}")
            continue

        report = record["report"]
        status = "WARNING" if record["warnings"] else "ONLINE"
        cpu = f"{report['cpu']:.1f}%"
        memory = f"{report['memory']:.1f}%"
        print(f"{name:<20} {status:<9} {cpu:>7} {memory:>7} "
              f"{report['rx_kbps']:>10.2f} {report['tx_kbps']:>10.2f}")


def show_status(name, record):
    report = record["report"]
    age = int(monotonic() - record["last_seen"])
    print("Host:", name)
    print("Address:", record["address"])
    print("Status:", "ONLINE" if record["online"] else "OFFLINE")
    print(f"Last report: {record['last_report']} ({age} seconds ago)")
    if not record["online"]:
        print("These values are from the last received report.")
    print()
    print(f"CPU: {report['cpu']:.1f}%   Memory: {report['memory']:.1f}%")
    print(f"Network RX: {report['rx_kbps']:.2f} KiB/s")
    print(f"Network TX: {report['tx_kbps']:.2f} KiB/s")
    print()
    print("Services:")
    for service, state in report["services"].items():
        print(" ", service, state.upper())
    for warning in record["warnings"]:
        print("Warning:", warning)


def command_loop(hosts, lock, client_file):
    print(COMMANDS)
    while True:
        parts = input("monitor> ").strip().split(maxsplit=1)
        if not parts:
            continue
        command = parts[0].lower()

        if command == "quit":
            return
        if command == "help":
            print(COMMANDS)
        elif command == "register" and len(parts) == 1:
            try:
                register_client(client_file)
            except OSError as error:
                print("Registration file error:", error)
        else:
            with lock:
                if command == "list" and len(parts) == 1:
                    show_list(hosts)
                elif command in ("status", "history") and len(parts) == 2:
                    name = parts[1]
                    if name not in hosts:
                        print("No reports for that identifier.")
                    elif command == "status":
                        show_status(name, hosts[name])
                    else:
                        for event in hosts[name]["history"]:
                            print(event)
                else:
                    print("Unknown command. Enter help for the command list.")


def main():
    server = socket(AF_INET, SOCK_STREAM)
    try:
        config = load_config(CONFIG_FILE)
        config["client_file"] = config_path(CONFIG_FILE, config["client_file"])

        logging.basicConfig(filename=config_path(CONFIG_FILE, "events.log"),
                            level=logging.INFO, format="%(asctime)s %(message)s")
        hosts = {}
        connections = {}
        lock = Lock()
        address = (config["listen_host"], config["port"])
        server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        server.bind(address)
        server.listen(5)
        print("DataRetriever listening on", address)

        # Accept connections in the background so the main thread can read commands.
        listener = Thread(target=accept_clients,
                          args=(server, config, hosts, connections, lock), daemon=True)
        listener.start()
        command_loop(hosts, lock, config["client_file"])
    except (KeyboardInterrupt, EOFError):
        print()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("Server error:", error)
    finally:
        server.close()
        print("Server stopped.")


if __name__ == "__main__":
    main()
