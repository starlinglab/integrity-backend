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

class OrganizationConfig:
    def __init__(self, config_file):
        """Loads organization configuration from file.

        Args:
            config_file: string with path to JSON file with configuration

        Raises:
            Exception if configuration loading fails
        """
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
            json_config = json.loads(f.read())
            for org in json_config["organizations"]:
                self.config[org["id"]] = org
        # Use print because this will likely happen before logging is configured
        print(f"Loaded configuration for organizations: {self.all_orgs()}")


# Load Organization-specific configuration from file
ORGANIZATION_CONFIG = OrganizationConfig(os.environ.get("ORG_CONFIG_JSON"))


def creative_work(organization_id):
    org_config = ORGANIZATION_CONFIG.get(organization_id)
    if org_config:
        return org_config.get("creative_work_author", [])
    else:
        return []
