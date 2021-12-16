"""Helper to import code under test into tests."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from starlingcaptureapi import claim
from starlingcaptureapi import exif
from starlingcaptureapi import geocoder
