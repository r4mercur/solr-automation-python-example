import base64
import getpass
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import cast, Protocol

import requests
from kazoo.client import KazooClient
from requests.auth import HTTPBasicAuth

from solr.util import (
    HTTP_TIMEOUT,
    JSON_DIR,
    load_json,
    print_ascii_title,
    require_env,
    setup_logging,
)

logger = logging.getLogger(__name__)

SECURITY_JSON_PATH = JSON_DIR / "security.json"


class SupportsWrite(Protocol):
    def write(self, s: str) -> object: ...


def security_main_for_test(password: str) -> None:
    (zk_host,) = require_env("ZK_HOST")

    security = load_json("security.json")
    security["authentication"]["credentials"]["solr"] = hash_password(password)

    # Write the updated security.json
    write_to_file(SECURITY_JSON_PATH, security)

    # Upload security.json to ZooKeeper
    upload_security_to_zookeeper(zk_host, SECURITY_JSON_PATH)
    verify_upload_to_zk(zk_host)

    # Restart all Solr nodes
    restart_all_nodes(zk_host)


def write_to_file(security_json_path: Path, security: dict) -> None:
    with open(security_json_path, "w", encoding="utf-8") as security_file:
        json.dump(security, cast(SupportsWrite, security_file), indent=4)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    salt_base64 = base64.b64encode(salt).decode("utf-8")
    salted_password = salt + password.encode("utf-8")

    hash1 = hashlib.sha256(salted_password).digest()
    hash2 = hashlib.sha256(hash1).digest()

    hash_base64 = base64.b64encode(hash2).decode("utf-8")

    return f"{hash_base64} {salt_base64}"


def upload_security_to_zookeeper(zk_host: str, security_json_path: Path) -> None:
    logger.info("Uploading security.json to ZooKeeper at %s...", zk_host)
    zk = KazooClient(hosts=zk_host)
    zk.start()

    with open(security_json_path, "r", encoding="utf-8") as security_file:
        data = json.load(security_file)

    security = json.dumps(data).encode("utf-8")

    zk_file = "/security.json"
    if zk.exists(zk_file):
        logger.info("%s already exists. Updating...", zk_file)
        zk.set(zk_file, security)
    else:
        logger.info("%s does not exist. Creating...", zk_file)
        zk.create(zk_file, security)

    logger.info("Successfully uploaded security.json to ZooKeeper.")
    zk.stop()


def verify_upload_to_zk(zk_host: str) -> None:
    zk = KazooClient(hosts=zk_host)
    zk.start()

    zk_file = "/security.json"
    if zk.exists(zk_file):
        logger.info("%s exists.", zk_file)
    else:
        logger.error("%s does not exist.", zk_file)

    zk.stop()


def restart_all_nodes(zk_host: str) -> None:
    zk = KazooClient(hosts=zk_host)
    zk.start()

    logger.info("Connecting to ZooKeeper at %s...", zk_host)
    zk.ensure_path("/restart")
    zk.set("/restart", b"1")

    logger.info("Restart signal sent. Waiting for nodes to restart...")
    time.sleep(5)

    zk.stop()
    logger.info("All Solr nodes have been restarted.")


def solr_auth(solr_url: str, username: str = "solr", password: str = "") -> None:
    logger.info("Testing Solr authentication with %s...", solr_url)

    if password == "":
        logger.warning("Password is empty.")
        return

    try:
        response = requests.get(
            f"{solr_url}/admin/authentication",
            auth=HTTPBasicAuth(username, password),
            timeout=HTTP_TIMEOUT,
        )
        if response.status_code == 200:
            logger.info("Authentication successful.")
            logger.info("Solr response: %s", response.json())
        elif response.status_code == 401:
            logger.error("Authentication failed. Invalid credentials.")
        else:
            logger.error("Authentication failed: %s", response.text)
    except requests.RequestException as e:
        logger.error("Failed to authenticate: %s", e)


def main() -> None:
    setup_logging()
    zk_host, solr_url = require_env("ZK_HOST", "SOLR_URL")

    print_ascii_title("SOLR SECURITY")

    print(
        "This script will update the security.json file with the hashed password for Solr security."
    )

    auth_method = input("Choose authentication method (1: basic, 2: cert): ")
    password = None
    security = load_json("security.json")

    if auth_method == "1" or auth_method == "basic":
        # Dialog for user to input the password which will be used in security.json & for solr security
        password = getpass.getpass(prompt="Enter the password for Solr security: ")
        security["authentication"]["credentials"]["solr"] = hash_password(password)

    elif auth_method == "2" or auth_method == "cert":
        cert_path = input("Enter the path to the certificate file: ")
        security["authentication"]["class"] = "solr.CertAuthPlugin"
        security["authentication"]["trustedCertificates"] = cert_path

    else:
        print("Invalid choice. Exiting...")
        return

    # Write the updated security.json
    write_to_file(SECURITY_JSON_PATH, security)

    # Upload security.json to ZooKeeper
    upload_security_to_zookeeper(zk_host, SECURITY_JSON_PATH)
    verify_upload_to_zk(zk_host)

    # Restart all Solr nodes
    restart_all_nodes(zk_host)

    # Test Solr authentication (only possible with basic auth)
    if password:
        time.sleep(5)
        solr_auth(solr_url, username="solr", password=password)


if __name__ == "__main__":
    main()
