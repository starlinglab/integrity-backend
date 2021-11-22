"""Configuration variables."""

import os
import dotenv

# Loads env variables from local .env, if it is present.
dotenv.load_dotenv()

JWT_SECRET = os.environ.get("JWT_SECRET")
