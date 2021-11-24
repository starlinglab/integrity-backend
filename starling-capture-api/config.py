"""Configuration variables."""

import os
import dotenv

# Loads env variables from local .env, if it is present.
dotenv.load_dotenv()

# Secret for encoding/decoding JWT tokens
JWT_SECRET = os.environ.get("JWT_SECRET")

# Full path to claim_tool binary. Must be already configured.
CLAIM_TOOL_PATH = os.environ.get("CLAIM_TOOL_PATH")

# Root folder for output images. Must exist and be readable by the server.
IMAGES_DIR = os.environ.get("IMAGES_DIR")
