import copy
import json
import logging
import os

from .exif import Exif
from .geocoder import Geocoder

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
        claim = copy.deepcopy(CREATE_CLAIM_TEMPLATE)

        assertions = self.assertions_by_label(claim)

        creative_work = assertions["stds.schema-org.CreativeWork"]
        jwt_author = jwt_payload.get("author", {})
        creative_work["data"]["author"][0]["identifier"] = jwt_author.get("identifier")
        creative_work["data"]["author"][0]["name"] = jwt_author.get("name")

        photo_meta = assertions["stds.iptc.photo-metadata"]
        photo_meta["data"]["dc:creator"] = [jwt_author.get("name")]
        photo_meta["data"]["dc:rights"] = jwt_payload.get("copyright")

        if meta is None:
            _logger.warning(
                "No 'meta' found in request. Metadata will be missing from Claim."
            )
        else:
            _logger.info("Processing metadata: %s", meta)
            (lat, lon) = self._get_meta_lat_lon(meta)
            photo_meta["data"][
                "Iptc4xmpExt:LocationCreated"
            ] = self._get_location_created(lat, lon)

            exif = assertions["stds.exif"]
            exif["data"] = self._make_exif_data(lat, lon, meta)

        return claim

    def generate_create_proofmode(self, jwt_payload, meta_proofmode):
        """Generates a claim for the 'create_proofmode' action.

        Args:
            jwt_payload: a dictionary with the data we got from the request's JWT payload
            meta_proofmode: dictionary with the metadata from a proofmode bundle

        Returns:
            a dictionary containing the 'create' claim data
        """
        claim = copy.deepcopy(CREATE_CLAIM_TEMPLATE)

        # TODO: Parse proofmode metadata and create claim.
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
        if lat is None or lon is None:
            _logger.warning("Could not find lat or lon in 'meta'")
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

    def _get_location_created(self, lat, lon):
        """Returns the Iptc4xmpExt:LocationCreated section, based on the given lat / lon

        Args:
            lat, lon: floats (or None), indicating the latitude and longitude to use

        Returns:
            dictionary to use as the value of the Iptc4xmpExt:LocationCreated field
            might be empty if lat or lon was None, or if reverse geocoding did not return an address
        """
        location_created = {}
        if lat is None or lon is None:
            return location_created

        address = Geocoder().reverse_geocode(lat, lon)
        if address is None:
            return location_created

        location_created["Iptc4xmpExt:CountryCode"] = address.get("country_code")
        location_created["Iptc4xmpExt:CountryName"] = address.get("country")
        location_created["Iptc4xmpExt:ProvinceState"] = address.get("state")
        location_created["Iptc4xmpExt:City"] = address.get("city")

        return {k: v for k, v in location_created.items() if v is not None}

    def _make_exif_data(self, lat, lon, meta):
        """Returns the data fields for the stds.exif section of the claim

        Args:
            lat, lon: floats (or None), indicating the latitude and longitude to use
            meta: metadata dictionary from the incoming request

        Returns:
            dictionary to use as the value of the stds.exif field
            might be empty, if no input data is provided
        """
        exif_data = {}

        (exif_lat, exif_lat_ref) = Exif().convert_latitude(lat)
        (exif_lon, exif_lon_ref) = Exif().convert_longitude(lon)
        exif_data["exif:GPSLatitude"] = exif_lat
        exif_data["exif:GPSLatitudeRef"] = exif_lat_ref
        exif_data["exif:GPSLongitude"] = exif_lon
        exif_data["exif:GPSLongitudeRef"] = exif_lon_ref
        exif_data["exif:GPSTimeStamp"] = self._get_exif_timestamp(meta)

        return {k: v for k, v in exif_data.items() if v is not None}
