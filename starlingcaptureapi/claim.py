import copy
import geocoder
import json
import logging
import os

from .exif import Exif

_logger = logging.getLogger(__name__)


def _load_template(filename):
    """Loads a claim template JSON file.

    Args:
        filename: basename of file to load, relative to the claims template directory

    Return:
        a dictionary with the loaded claim template
    """
    full_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), f"c2pa_claims/{filename}"
    )
    with open(full_path, "r") as claim_file:
        template = json.load(claim_file)
        _logger.info("Successfully loaded claim template: %s", filename)
        return template


# At code load time, read our claim JSON template files.
CREATE_CLAIM_TEMPLATE = _load_template("claim_create.json")
UPDATE_CLAIM_TEMPLATE = _load_template("claim_update.json")
STORE_CLAIM_TEMPLATE = _load_template("claim_store.json")


class Claim:
    """Generates the claim JSON."""

    def generate_create(self, jwt_payload, meta):
        """Generates a claim for the 'create' action.

        Args:
            jwt_payload: a dictionary with the data we got from the request's JWT payload
            meta: dictionary with the 'meta' section of the request

        Returns:
            a dictionary containing the 'create' claim data
        """
        # TODO: make cleaner. Better error handling for all missing keys.
        claim = copy.deepcopy(CREATE_CLAIM_TEMPLATE)

        assertions = self.assertions_by_label(claim)

        creative_work = assertions["stds.schema-org.CreativeWork"]
        creative_work["data"]["author"][0]["identifier"] = jwt_payload["author"][
            "identifier"
        ]
        creative_work["data"]["author"][0]["name"] = jwt_payload["author"]["name"]

        if meta:
            _logger.info("Processing metadata: %s", meta)
            (lat, lon) = self._get_meta_lat_lon(meta)
            if lat is not None and lon is not None:
                geo_json = self._reverse_geocode(lat, lon)
                photo_meta = assertions["stds.iptc.photo-metadata"]
                photo_meta["data"]["dc:creator"] = [jwt_payload["author"]["name"]]
                photo_meta["data"]["dc:rights"] = jwt_payload["copyright"]

                # Insert LocationCreated.
                if "raw" in geo_json and "address" in geo_json["raw"]:
                    photo_meta["data"]["Iptc4xmpExt:LocationCreated"] = {}
                if "country_code" in geo_json["raw"]["address"]:
                    photo_meta["data"]["Iptc4xmpExt:LocationCreated"]["Iptc4xmpExt:CountryCode"] = geo_json["raw"]["address"]["country_code"]
                if "country" in geo_json["raw"]["address"]:
                    photo_meta["data"]["Iptc4xmpExt:LocationCreated"]["Iptc4xmpExt:CountryName"] = geo_json["raw"]["address"]["country"]
                if "state" in geo_json["raw"]["address"]:
                    photo_meta["data"]["Iptc4xmpExt:LocationCreated"]["Iptc4xmpExt:ProviceState"] = geo_json["raw"]["address"]["state"]
                if "town" in geo_json["raw"]["address"]:
                    photo_meta["data"]["Iptc4xmpExt:LocationCreated"]["Iptc4xmpExt:City"] = geo_json["raw"]["address"]["town"]

                exif = assertions["stds.exif"]
                (exif_lat, exif_lat_ref) = Exif().convert_latitude(lat)
                (exif_lon, exif_lon_ref) = Exif().convert_longitude(lon)
                exif["data"]["exif:GPSLatitude"] = exif_lat
                exif["data"]["exif:GPSLatitudeRef"] = exif_lat_ref
                exif["data"]["exif:GPSLongitude"] = exif_lon
                exif["data"]["exif:GPSLongitudeRef"] = exif_lon_ref
                exif["data"]["exif:GPSTimeStamp"] = self._get_exif_timestamp(meta)

        return claim

    def generate_update(self):
        """Generates a claim for the 'update' action.

        Returns:
            a dictionary containing the 'update' claim data
        """
        claim = copy.deepcopy(UPDATE_CLAIM_TEMPLATE)
        return claim

    def generate_store(self, ipfs_cid):
        """Generates a claim for the 'store' action.

        Args:
            ipfs_cid: the IPFS CID for the asset

        Returns:
            a dictionary containing the 'store' claim data
        """
        claim = copy.deepcopy(STORE_CLAIM_TEMPLATE)
        # Replace claim values.
        for assertion in claim["assertions"]:
            if assertion["label"] == "org.starlinglab.storage.ipfs":
                assertion["data"]["starling:Provider"] = "Web3.Storage"
                assertion["data"]["starling:IpfsCid"] = ipfs_cid
                # TODO
                assertion["data"]["starling:AssetStoredTimestamp"] = ""
                continue

        return claim

    def assertions_by_label(self, claim_dict):
        """Helper to index existing assertions in a Claim by their label.

        Args:
            claim_dict: a Python dictionary containing claim data

        Returns:
            a dictionary mapping label string to an assertion dictionary
        """
        assertions_by_label = {}
        for assertion in claim_dict["assertions"]:
            assertions_by_label[assertion["label"]] = assertion
        return assertions_by_label

    def _reverse_geocode(self, lat, lon):
        """Retrieves reverse geocoding informatioon for the given latitude and longitude.

        Args:
            lat, long: latitude and longitude to reverse geocode, as floats

        Returns:
            geolocation JSON

        """
        # We shouldn't send more than 1 request per second. TODO: Add some kind of throttling and/or caching.
        response = geocoder.osm([lat, lon], method="reverse")
        # TODO: add error handling
        return response.json

    def _get_meta_lat_lon(self, meta):
        """Extracts latitude and longitude from metadata JSON dict.

        Args:
            meta: dictionary with the 'meta' section of the request

        Return:
            (lat, lon) from the 'meta' data, returned as a pair
        """
        if "information" not in meta:
            return None
        lat = lon = None
        for info in meta["information"]:
            if info["name"] == "Last Known GPS Latitude":
                lat = float(info["value"])
                continue
            if info["name"] == "Last Known GPS Longitude":
                lon = float(info["value"])
                continue
        return (lat, lon)

    def _get_exif_timestamp(self, meta):
        """Returns an EXIF-formatted version of the timestamp.

        Args:
            meta: dictionary with the 'meta' secion of the request

        Return:
            string with the exif-formatted timestamp, or None
        """
        if "information" not in meta:
            return None
        for info in meta["information"]:
            if info["name"] == "Last Known GPS Timestamp":
                return Exif().convert_timestamp(info["value"])
