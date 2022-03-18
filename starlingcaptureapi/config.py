"""Configuration variables."""

import json
import os
import dotenv

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
        self.collections = {}
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

    def get_collection(self, org_id, collection_id):
        """Returns the configuration for a collection in an org."""
        return self.collections.get(org_id, {}).get(collection_id)

    def _load_config_from_file(self, config_file):
        with open(config_file, "r") as f:
            self.json_config = json.loads(f.read())
        self._index_json_config()

        # Use print because this will likely happen before logging is configured
        print(f"Loaded configuration for organizations: {list(self.all_orgs())}")

    def _index_json_config(self):
        # Index by organization, collection and action id/name for ease of access
        for org in self.json_config["organizations"]:
            self.config[org["id"]] = org
            self.collections[org["id"]] = {}
            for coll_conf in org.get("collections", []):
                self.collections[org["id"]][coll_conf["id"]] = {
                    "conf": coll_conf,
                    "actions": {
                        action["name"]: action
                        for action in coll_conf.get("actions", [])
                    },
                }


# Load Organization-specific configuration from file
ORGANIZATION_CONFIG = OrganizationConfig(os.environ.get("ORG_CONFIG_JSON"))


def creative_work(organization_id, collection_id, action_name):
    coll_config = ORGANIZATION_CONFIG.get_collection(organization_id, collection_id)
    if coll_config == None:
        return []

    return (
        coll_config.get("actions", {})
        .get(action_name, {})
        .get("params", {})
        .get("creative_work_author", [])
    )
