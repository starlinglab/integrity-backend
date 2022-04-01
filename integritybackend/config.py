"""Configuration variables."""

import copy
import dotenv
import json
import os

# Loads env variables from local .env, if it is present.
dotenv.load_dotenv()

# Secret for encoding/decoding JWT tokens.
JWT_SECRET = os.environ.get("JWT_SECRET")

# Full path to claim_tool binary. Must be already configured.
CLAIM_TOOL_PATH = os.environ.get("CLAIM_TOOL_PATH")

# Full path to IPFS client binary. Must be already configured.
IPFS_CLIENT_PATH = os.environ.get("IPFS_CLIENT_PATH")

# Local directory for storing internal assets. Must exist and be readable by the server.
INTERNAL_ASSET_STORE = os.environ.get("INTERNAL_ASSET_STORE")

# Local directory for synchronizing with a remote file system. Must exist and be readable by the server.
SHARED_FILE_SYSTEM = os.environ.get("SHARED_FILE_SYSTEM")

# Local file containing a dictionary with custom assertions mapped to asset name.
CUSTOM_ASSERTIONS_DICTIONARY = os.environ.get("CUSTOM_ASSERTIONS_DICTIONARY")

# API token for the web3.storage service
WEB3_STORAGE_API_TOKEN = os.environ.get("WEB3_STORAGE_API_TOKEN")

# Full path to Opentimestamps client. Must be already configured.
OTS_CLIENT_PATH = os.environ.get("OTS_CLIENT_PATH")

# Address of ISCN registration HTTP server to use
ISCN_SERVER = os.environ.get("ISCN_SERVER")

NUMBERS_API_KEY = os.environ.get("NUMBERS_API_KEY")

KEY_STORE = os.environ.get("KEY_STORE")


class OrganizationConfig:
    def __init__(self, config_file):
        """Loads organization configuration from file.

        Args:
            config_file: string with path to JSON file with configuration

        Raises:
            Exception if configuration loading fails
        """
        self.json_config = {}
        self.config = {}
        try:
            # Disable loading of configuration from file in the test environment.
            if os.environ.get("RUN_ENV") != "test":
                self._load_config_from_file(config_file)
        except Exception as err:
            # Use print because this will likely happen before logging is configured
            print(f"Couldn't load organization configuration from: {config_file}")
            raise err

    def all_orgs(self):
        return self.config.keys()

    def get(self, org_id):
        """Gets configuration dictionary for an org id."""
        return self.config.get(org_id)

    def _load_config_from_file(self, config_file):
        with open(config_file, "r") as f:
            self.json_config = json.loads(f.read())
        self._index_json_config()

        # Use print because this will likely happen before logging is configured
        print(f"Loaded configuration for organizations: {list(self.all_orgs())}")

    def _index_json_config(self):
        # Index by organization, collection and action id/name for ease of access
        for org in self.json_config["organizations"]:
            indexed_config = copy.deepcopy(org)
            indexed_config["collections"] = {}
            for coll_conf in org.get("collections", []):
                actions_index = {
                    action["name"]: action for action in coll_conf.get("actions", [])
                }
                indexed_config["collections"][coll_conf["id"]] = {
                    "conf": coll_conf,
                    "actions": actions_index,
                }
            self.config[org["id"]] = indexed_config


# Load Organization-specific configuration from file
ORGANIZATION_CONFIG = OrganizationConfig(os.environ.get("ORG_CONFIG_JSON"))


def get_param(org_config, collection_id, action_name, param_name):
    return (
        org_config.get("collections", {})
        .get(collection_id, {})
        .get("actions", {})
        .get(action_name, {})
        .get("params", {})
        .get(param_name)
    )