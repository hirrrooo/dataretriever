# Presentation Link
https://docs.google.com/presentation/d/19N303Ks66K6YznR4bNgNWIeGL-LtePFBZrAZVFF6feY/edit?usp=sharing

# DataRetriever

A lightweight client/server tool for monitoring Linux system metrics (CPU, memory, network, and systemd services) over TCP sockets.

## Requirements

- Python 3.9+
- Linux with `systemd` (required only if monitoring services via `systemctl`)

## Setup

Create a virtual environment and install the dependencies:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

### 1. Register a Client
Register a client identifier and authentication key:

```sh
python3 auth.py
```
Select **1. Register Monitoring Client** and follow the prompts. You can also register clients directly from the server CLI using the `register` command.

### 2. Configuration
Adjust settings in the JSON configuration files as needed:
- **`server_config.json`**: Set `listen_host`, `port`, alert thresholds, and registration file path.
- **`client_config.json`**: Set `server_host`, `port`, `server_id` (matching your registered ID), report `interval`, and `services` to monitor.

### 3. Start the Server
```sh
python3 server.py
```

Available interactive commands:
- `list` — Display an overview of all known clients and their statuses.
- `status <id>` — View detailed metrics and service states for a client.
- `history <id>` — View recent event history for a client.
- `register` — Register a new client interactively.
- `help` — Show available commands.
- `quit` — Stop the server.

### 4. Start the Client
```sh
python3 client.py
```
Enter the authentication key when prompted (or supply it non-interactively via the `DATRETRIEVER_KEY` environment variable).
