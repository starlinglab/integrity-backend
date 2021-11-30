"""Configuration variables."""

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