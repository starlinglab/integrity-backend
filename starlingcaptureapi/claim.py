from datetime import datetime, timezone
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

# Hardcode CreativeWork author for SCMP.
CREATIVE_WORK_AUTHOR = [
    {
        "@type": "Organization",
        "credential": [],
        "identifier": "https://scmp.com",
        "name": "South China Morning Post",
    },
    {
        "@id": "https://twitter.com/SCMPNews",
        "@type": "Organization",
        "identifier": "https://scmp.com",
        "name": "SCMPNews",
    },
]


class Claim:
    """Generates the claim JSON."""

    def generate_create(self, jwt_payload, data):
        """Generates a claim for the 'create' action.

        Args:
            jwt_payload: a dictionary with the data we got from the request's JWT payload
            data: dictionary with the 'meta' and 'signature' sections of the request
                  'meta' is required

        Returns:
            a dictionary containing the 'create' claim data
        """
        meta = data.get("meta")
        signature = data.get("signature")

        if meta is None:
            raise ValueError("Meta must be present, but got None!")

        claim = copy.deepcopy(CREATE_CLAIM_TEMPLATE)
        claim["recorder"] = "Starling Capture by Numbers Protocol"

        assertion_templates = self.assertions_by_label(claim)
        assertions = []

        author_data = self._make_author_data(jwt_payload)
        if author_data is not None:
            creative_work = assertion_templates["stds.schema-org.CreativeWork"]
            creative_work["data"] = author_data
            assertions.append(creative_work)

        photo_meta_data = self._make_photo_meta_data(jwt_payload, meta)
        if photo_meta_data is not None:
            photo_meta = assertion_templates["stds.iptc.photo-metadata"]
            photo_meta["data"] = photo_meta_data
            assertions.append(photo_meta)

        exif_data = self._make_exif_data(meta)
        if exif_data is not None:
            exif = assertion_templates["stds.exif"]
            exif["data"] = exif_data
            assertions.append(exif)

        signature_data = self._make_signature_data(signature, meta)
        if signature_data is not None:
            signature = assertion_templates["org.starlinglab.integrity"]
            signature["data"] = signature_data
            assertions.append(signature)

        timestamp = self._get_value_from_meta(meta, "Timestamp")
        if timestamp is not None:
            c2pa_actions = assertion_templates["c2pa.actions"]
            c2pa_actions["data"]["actions"][0]["when"] = timestamp
            assertions.append(c2pa_actions)

        claim["assertions"] = assertions

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
        claim["recorder"] = "Starling Integrity"

        timestamp = datetime.now(timezone.utc).isoformat()

        assertion_templates = self.assertions_by_label(claim)
        assertions = []

        creative_work = assertion_templates["stds.schema-org.CreativeWork"]
        creative_work["data"] = {"author": CREATIVE_WORK_AUTHOR}
        assertions.append(creative_work)

        c2pa_actions = assertion_templates["c2pa.actions"]
        c2pa_actions["data"]["actions"][0]["when"] = timestamp
        assertions.append(c2pa_actions)

        claim["assertions"] = assertions

        return claim

    def generate_store(self, ipfs_cid):
        """Generates a claim for the 'store' action.

        Args:
            ipfs_cid: the IPFS CID for the asset

        Returns:
            a dictionary containing the 'store' claim data
        """
        claim = copy.deepcopy(STORE_CLAIM_TEMPLATE)
        claim["recorder"] = "Starling Integrity"

        timestamp = datetime.now(timezone.utc).isoformat()

        assertion_templates = self.assertions_by_label(claim)
        assertions = []

        creative_work = assertion_templates["stds.schema-org.CreativeWork"]
        creative_work["data"] = {"author": CREATIVE_WORK_AUTHOR}
        assertions.append(creative_work)

        c2pa_actions = assertion_templates["c2pa.actions"]
        c2pa_actions["data"]["actions"][0]["when"] = timestamp
        assertions.append(c2pa_actions)

        ipfs_storage = assertion_templates["org.starlinglab.storage.ipfs"]
        ipfs_storage["data"]["starling:provider"] = "Web3.Storage"
        ipfs_storage["data"]["starling:ipfsCID"] = ipfs_cid
        ipfs_storage["data"]["starling:assetStoredTimestamp"] = timestamp
        assertions.append(ipfs_storage)

        claim["assertions"] = assertions

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

    def _make_photo_meta_data(self, jwt_payload, meta):
        (lat, lon) = self._get_meta_lat_lon(meta)
        photo_meta_data = {
            "dc:creator": [jwt_payload.get("author", {}).get("name")],
            "dc:rights": jwt_payload.get("copyright"),
            "Iptc4xmpExt:LocationCreated": self._get_location_created(lat, lon),
        }

        photo_meta_data = self._remove_keys_with_no_values(photo_meta_data)

        if not photo_meta_data.keys():
            return None

        return photo_meta_data

    def _get_meta_lat_lon(self, meta):
        """Extracts latitude and longitude from metadata JSON dict.

        Args:
            meta: dictionary with the 'meta' section of the request

        Return:
            (lat, lon) from the 'meta' data, returned as a pair
        """
        lat = self._get_value_from_meta(
            meta, "Current GPS Latitude"
        ) or self._get_value_from_meta(meta, "Last Known GPS Latitude")

        lon = self._get_value_from_meta(
            meta, "Current GPS Longitude"
        ) or self._get_value_from_meta(meta, "Last Known GPS Longitude")

        if lat is None or lon is None:
            _logger.warning("Could not find lat or lon in 'meta'")
            return (None, None)

        return (float(lat), float(lon))

    def _get_exif_timestamp(self, meta):
        """Returns an EXIF-formatted version of the timestamp.

        Args:
            meta: dictionary with the 'meta' secion of the request

        Return:
            string with the exif-formatted timestamp, or None
        """
        timestamp = self._get_value_from_meta(
            meta, "Current GPS Timestamp"
        ) or self._get_value_from_meta(meta, "Last Known GPS Timestamp")

        if timestamp is None:
            return None

        return Exif().convert_timestamp(timestamp)

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

        return self._remove_keys_with_no_values(location_created)

    def _make_exif_data(self, meta):
        """Returns the data fields for the stds.exif section of the claim

        Args:
            meta: metadata dictionary from the incoming request

        Returns:
            dictionary to use as the value of the stds.exif field
            might be empty, if no input data is provided
        """
        (lat, lon) = self._get_meta_lat_lon(meta)

        exif_data = {}

        (exif_lat, exif_lat_ref) = Exif().convert_latitude(lat)
        (exif_lon, exif_lon_ref) = Exif().convert_longitude(lon)
        exif_data["exif:GPSLatitude"] = exif_lat
        exif_data["exif:GPSLatitudeRef"] = exif_lat_ref
        exif_data["exif:GPSLongitude"] = exif_lon
        exif_data["exif:GPSLongitudeRef"] = exif_lon_ref
        exif_data["exif:GPSTimeStamp"] = self._get_exif_timestamp(meta)

        exif_data = self._remove_keys_with_no_values(exif_data)
        if not exif_data.keys():
            return None

        return exif_data

    def _make_author_data(self, jwt_payload):
        author = []
        jwt_author = jwt_payload.get("author", {})
        if jwt_author:
            author.append(
                {
                    "@type": jwt_author.get("type"),
                    "credential": [],
                    "identifier": jwt_author.get("identifier"),
                    "name": jwt_author.get("name"),
                }
            )

        jwt_twitter = jwt_payload.get("twitter", {})
        if jwt_twitter:
            if (twitter_name := jwt_twitter.get("name")) is not None:
                twitter_id = f"https://twitter.com/{twitter_name}"
            else:
                twitter_id = None
            author.append(
                {
                    "@id": twitter_id,
                    "@type": jwt_twitter.get("type"),
                    "identifier": jwt_twitter.get("identifier"),
                    "name": jwt_twitter.get("name"),
                }
            )

        if not author:
            _logger.warning(
                "Couldn't extract author nor Twitter data from JWT %s", jwt_payload
            )
            return None

        return {"author": author}

    def _make_signature_data(self, signatures, meta):
        if signatures is None:
            return None

        proof = meta.get("proof", {})
        timestamp = self._get_value_from_meta(meta, "Timestamp")

        signature_list = []
        for signature in signatures:
            signature_list.append(
                {
                    "starling:provider": signature.get("provider"),
                    "starling:algorithm": f"numbers-{signature.get('provider')}",
                    "starling:publicKey": signature.get("publicKey"),
                    "starling:signature": signature.get("signature"),
                    "starling:authenticatedMessage": signature.get("proofHash"),
                    "starling:authenticatedMessageDescription": "Internal identifier of the authenticated bundle",
                    "starling:authenticatedMessagePublic": {
                        "starling:assetHash": proof.get("hash"),
                        "starling:assetMimeType": proof.get("mimeType"),
                        "starling:assetCreatedTimestamp": timestamp,
                    },
                }
            )
        return {
            "starling:identifier": proof.get("hash"),
            "starling:signatures": signature_list,
        }

    def _remove_keys_with_no_values(self, dictionary):
        return {k: v for k, v in dictionary.items() if v}

    def _get_value_from_meta(self, meta, name):
        """Gets the value for a given 'name' in meta['information'].

        Args:
            meta: dict with the 'meta' section of the request
            name: string with the name of the value we are looking for

        Returns:
            the value corresponding to the given name, or None if not found
        """
        if (information := meta.get("information")) is None:
            return None

        for item in information:
            if item.get("name") == name:
                return item.get("value")

        return None
