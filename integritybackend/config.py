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
NUMBERS_API_URL = os.environ.get("NUMBERS_API_URL")

AUTHSIGN_URL = os.environ.get("AUTHSIGN_URL")
AUTHSIGN_TOKEN = os.environ.get("AUTHSIGN_TOKEN","")

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
        """Gets configuration dictionary for an org."""
        if org_id in self.config:
            return self.config.get(org_id)
        else:
            raise Exception(f"No organization with ID {org_id}")

    def get_org(self, org_id):
        """Gets configuration dictionary for an org."""
        org_config = next(
            (
                c
                for c in self.json_config.get("organizations")
                if c.get("id") == org_id
            ),
            None,
        )        
        if org_config == None:
            raise Exception(f"No organization with ID {org_id}")            
        else:
            return org_config           

    def get_collections(self, org_id):
        """Gets collection array for an org id."""
        org_dict = self.get_org(org_id)
        if "collections" in org_dict:
            return org_dict.get("collections")
        else:
            return []

    def get_collection(self, org_id, collection_id):
        """Gets specific collection for an org."""
        org_collections = self.get_collections(org_id)
        collection_config = next(
            (
                c
                for c in org_collections
                if c.get("id") == collection_id
            ),
            None,
        )
        if collection_config is None:
            raise Exception(f"No collection in {org_id} with ID {collection_id}")
        return collection_config

    def get_actions(self, org_id, collection_id):
        """Gets action array for a collection."""
        collection_conf = self.get_collection(org_id, collection_id)
        org_dict = self.get(org_id)
        if "actions" in collection_conf:
            return collection_conf.get("actions")
        else:
            return []

    def get_action(self, org_id, collection_id, action_name):
        """Gets specific action for a collection."""
        collection_conf = self.get_actions(org_id, collection_id)
        action = next(
            (c for c in collection_conf if c.get("name") == action_name), None
        )
        if action is None:
            raise Exception(
                f"No action in {org_id}/{collection_id} with action {action_name}"
            )
        return action

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
