"""
File: auth.py

DataRetriever registration and authentication.
Provides credential encryption, client registration, and verification
using an Indexed Shift Cipher.
"""

from common import valid_name
from getpass import getpass
from pathlib import Path



CLIENT_FILE = Path(__file__).resolve().parent / "registered_clients.txt"
BASE_SHIFT = 3
FIRST_PRINTABLE = 32
PRINTABLE_COUNT = 95


def encrypt(text, base_shift):
    """Shift each printable ASCII character by base_shift plus its position."""
    encrypted_text = ""
    for position in range(len(text)):
        character = text[position]
        if ord(character) < 32 or ord(character) > 126:
            raise ValueError("Authentication keys may only contain printable ASCII characters.")
        shift = base_shift + position
        character_position = ord(character) - FIRST_PRINTABLE
        shifted_position = (character_position + shift) % PRINTABLE_COUNT
        encrypted_text += chr(shifted_position + FIRST_PRINTABLE)
    return encrypted_text


def load_clients(filename=None):
    """Read identifier:ciphertext entries, including ciphertext containing colons."""
    filename = Path(filename) if filename is not None else CLIENT_FILE
    clients = {}
    if not filename.exists():
        return clients
    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            # Do not strip spaces: they can be part of the encrypted key.
            line = line.rstrip("\n")
            if ":" not in line:
                continue
            server_id, encrypted_key = line.split(":", 1)
            clients[server_id] = encrypted_key
    return clients


def save_client(server_id, encrypted_key, filename=None):
    """Append a client identifier and its encrypted key to the registration file."""
    filename = filename if filename is not None else CLIENT_FILE
    with open(filename, "a", encoding="utf-8") as file:
        file.write(server_id + ":" + encrypted_key + "\n")


def register_client(filename=None):
    """Prompt for a client identifier and authentication key, encrypt it, and save the registration."""
    print("\n--- Register Monitoring Client ---")
    server_id = input("Server Identifier: ").strip()
    if not valid_name(server_id):
        print("Use 1-64 letters, numbers, underscores, dots, or hyphens for the identifier.")
        return
    if server_id in load_clients(filename):
        print(f"A client named '{server_id}' is already registered.")
        return
    auth_key = getpass("Authentication Key: ")
    if auth_key == "":
        print("Authentication key cannot be empty.")
        return
    try:
        encrypted_key = encrypt(auth_key, BASE_SHIFT)
    except ValueError as error:
        print(error)
        return
    save_client(server_id, encrypted_key, filename)
    print(f"Client '{server_id}' registered successfully.")


def verify_client(server_id, encrypted_credential, filename=None):
    """Compare the supplied ciphertext with the registered ciphertext."""
    clients = load_clients(filename)
    if server_id not in clients:
        return False
    stored_credential = clients[server_id]
    return encrypted_credential == stored_credential


def authenticate_client(filename=None):
    """Prompt for client credentials and verify them against the registration file."""
    print("\n--- Authenticate Monitoring Client ---")
    server_id = input("Server Identifier: ").strip()
    auth_key = getpass("Authentication Key: ")
    if auth_key == "":
        print("Authentication key cannot be empty.")
        return
    try:
        encrypted_credential = encrypt(auth_key, BASE_SHIFT)
    except ValueError as error:
        print(error)
        return
    if verify_client(server_id, encrypted_credential, filename):
        print("Authentication successful.")
        print(f"Client '{server_id}' may submit monitoring data.")
    else:
        print("Authentication failed.")


def main():
    """Display an interactive menu for registering and authenticating clients."""
    try:
        while True:
            print()
            print("======================================")
            print("     DataRetriever Authentication")
            print("======================================")
            print("1. Register Monitoring Client")
            print("2. Authenticate Monitoring Client")
            print("3. Exit")
            choice = input("\nSelection: ").strip()
            if choice == "1":
                register_client()
            elif choice == "2":
                authenticate_client()
            elif choice == "3":
                print("Exiting DataRetriever.")
                return
            else:
                print("Invalid selection.")
    except (EOFError, KeyboardInterrupt):
        print("\nAuthentication menu closed.")
    except OSError as error:
        print("Registration file error:", error)


if __name__ == "__main__":
    main()
