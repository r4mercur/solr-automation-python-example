import base64
import getpass
import hashlib
import json
import os
import time
from typing import cast, Protocol

import pyfiglet
import requests
from dotenv import load_dotenv
from kazoo.client import KazooClient
from requests.auth import HTTPBasicAuth


class SupportsWrite(Protocol):
    def write(self, s: str) -> object:
        ...


def main() -> None:
    load_dotenv()
    zk_host = os.getenv('ZK_HOST', 'zoo:2181')

    print_ascii_title()

    print(f'This script will update the security.json file with the hashed password for Solr security.')

    auth_method = input('Choose authentication method (1: basic, 2: cert): ')

    if auth_method == '1' or auth_method == 'basic':
        # Dialog for user to input the password which will be used in security.json & for solr security
        print('Prompting for password...')
        password = getpass.getpass(prompt='Enter the password for Solr security: ')

        # Hash the password
        hashed_password = hash_password(password)

        # Update security.json with the hashed password
        security_json_path = os.path.join(os.path.dirname(__file__), '../json/security.json')
        with open(security_json_path, 'r', encoding='utf-8') as security_file:
            security = json.load(security_file)
            security['authentication']['credentials']['solr'] = hashed_password
    
    elif auth_method == '2' or auth_method == 'cert':
        cert_path = input('Enter the path to the certificate file: ')
        security_json_path = os.path.join(os.path.dirname(__file__), '../json/security.json')
        with open(security_json_path, 'r', encoding='utf-8') as security_file:
            security = json.load(security_file)
            security['authentication']['class'] = "solr.CertAuthPlugin"
            security['authentication']['trustedCertificates'] = cert_path
    
    else:
        print('Invalid choice. Exiting...')
        return


    # Write the updated security.json
    write_to_file(security_json_path, security)


    # Upload security.json to ZooKeeper
    upload_security_to_zookeeper(zk_host, security_json_path)
    verify_upload_to_zk(zk_host)

    # Restart all Solr nodes
    restart_all_nodes(zk_host)

    # Test Solr authentication
    time.sleep(5)
    solr_url = os.getenv('SOLR_URL')
    solr_auth(solr_url, username='solr', password=password)

def security_main_for_test(password: str) -> None:
    load_dotenv()
    zk_host = os.getenv('ZK_HOST', 'zoo:2181')

    security_json_path = os.path.join(os.path.dirname(__file__), '../json/security.json')
    with open(security_json_path, 'r', encoding='utf-8') as security_file:
        security = json.load(security_file)
        security['authentication']['credentials']['solr'] = hash_password(password)

    # Write the updated security.json
    write_to_file(security_json_path, security)

    # Upload security.json to ZooKeeper
    upload_security_to_zookeeper(zk_host, security_json_path)
    verify_upload_to_zk(zk_host)

    # Restart all Solr nodes
    restart_all_nodes(zk_host)


def write_to_file(security_json_path: str, security: str) -> None:
    with open(security_json_path, 'w', encoding='utf-8') as security_file:
        json.dump(security, cast(SupportsWrite, security_file), indent=4)

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    salt_base64 = base64.b64encode(salt).decode('utf-8')
    salted_password = salt + password.encode('utf-8')

    hash1 = hashlib.sha256(salted_password).digest()
    hash2 = hashlib.sha256(hash1).digest()

    hash_base64 = base64.b64encode(hash2).decode('utf-8')

    return f"{hash_base64} {salt_base64}"

def upload_security_to_zookeeper(zk_host: str, security_json_path: str) -> None:
    print(f"Uploading security.json to ZooKeeper at {zk_host}...")
    zk = KazooClient(hosts=zk_host)
    zk.start()

    print(f"Connecting to ZooKeeper at {zk_host}...")

    with open(security_json_path, 'r', encoding='utf-8') as security_file:
        data = json.load(security_file)

    security = json.dumps(data).encode('utf-8')

    zk_file = "/security.json"
    if zk.exists(zk_file):
        print(f"{zk_file} already exists. Updating...")
        zk.set(zk_file, security)
    else:
        print(f"{zk_file} does not exist. Creating...")
        zk.create(zk_file, security)

    print("Successfully uploaded security.json to ZooKeeper.")
    zk.stop()

def verify_upload_to_zk(zk_host: str) -> None:
    zk = KazooClient(hosts=zk_host)
    zk.start()

    zk_file = "/security.json"
    if zk.exists(zk_file):
        print(f"{zk_file} exists.")
    else:
        print(f"{zk_file} does not exist.")

    zk.stop()

def restart_all_nodes(zk_host: str) -> None:
    zk = KazooClient(hosts=zk_host)
    zk.start()

    print(f"Connecting to ZooKeeper at {zk_host}...")
    zk.ensure_path("/restart")
    zk.set("/restart", b"1")

    print("Restart signal sent. Waiting for nodes to restart...")
    time.sleep(5)

    zk.stop()
    print("All Solr nodes have been restarted.")

def solr_auth(solr_url: str, username: str = "solr", password: str = "") -> None:
    print(f'Testing Solr authentication with {solr_url}...')

    if password == "":
        return print("Password is empty.")

    try:
        response = requests.get(f'{solr_url}/admin/authentication', auth=HTTPBasicAuth(username, password))
        if response.status_code == 200:
            print('Authentication successful.')
            print(f'Solr response: {response.json()}')
        elif response.status_code == 401:
            print('Authentication failed. Invalid credentials.')
        else:
            print(f'Authentication failed: {response.text}')
    except Exception as e:
        print(f'Failed to authenticate: {e}')

def print_ascii_title() -> None:
    art = pyfiglet.figlet_format("SOLR SECURITY")

    art_lines = [line for line in art.split("\n") if line.strip()]
    max_width = max(len(line) for line in art_lines)

    print("#" * (max_width + 4))
    for line in art_lines:
        print(f"# {line.ljust(max_width)} #")
    print("#" * (max_width + 4))

if __name__ == '__main__':
    main()
