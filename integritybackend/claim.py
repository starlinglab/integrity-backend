from datetime import datetime, timezone

import copy
import json
import os
from decimal import Decimal
from fractions import Fraction
from typing import Optional, Tuple
import base64

from . import config
from .log_helper import LogHelper

_logger = LogHelper.getLogger()


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


class Claim:
    """Generates the claim JSON."""

    def generate_c2pa_starling_capture(self, meta_content):
        """Generates a claim for the 'c2pa-starling-capture' action.

        Args:
            meta_content: dictionary of the content metadata from ZIP

        Returns:
            a dictionary containing the claim data
        """

        claim = copy.deepcopy(CREATE_CLAIM_TEMPLATE)
        claim["recorder"] = "Starling Capture by Numbers Protocol"
        claim["claim_generator"] = "Starling Integrity"

        assertion_templates = self.assertions_by_label(claim)
        assertions = []

        author_data = meta_content.get("author")
        if author_data is not None:
            creative_work = assertion_templates["stds.schema-org.CreativeWork"]
            creative_work["data"] = {"author": [author_data]}
            author_data["credential"] = []
            assertions.append(creative_work)

        author_name = meta_content.get("author", {}).get("name")
        copyright = meta_content.get("copyright")

        geo = meta_content["private"].get("geolocation")

        photo_metadata = self._make_photo_metadata(author_name, copyright, geo)
        if photo_metadata is not None:
            photo_meta = assertion_templates["stds.iptc.photo-metadata"]
            photo_meta["data"] = photo_metadata
            assertions.append(photo_meta)

        if geo is not None:
            if geo["timestamp"] is not None:
                lat, lon, alt = self._get_meta_content_lat_lon_alt(geo)
                exif_data = self._make_c2pa_exif_gps_data(
                    lat,
                    lon,
                    alt,
                    datetime.fromisoformat(geo["timestamp"].replace("Z", "+00:00")),
                )
                if exif_data is not None:
                    exif = assertion_templates["stds.exif"]
                    exif["data"] = exif_data
                    assertions.append(exif)

        proof = self._get_starling_capture_proof(meta_content)
        # Convert from Unix to RFC
        proofTimestamp = (
            datetime.fromtimestamp(proof["timestamp"] / 1000, timezone.utc)
            .replace(tzinfo=None)
            .isoformat(timespec="milliseconds")
            + "Z"
        )

        signature_data = self._make_signature_data_starling_capture(
            meta_content["private"].get("signatures"), proof, proofTimestamp
        )
        if signature_data is not None:
            signature = assertion_templates["org.starlinglab.integrity"]
            signature["data"] = signature_data
            assertions.append(signature)

        if proofTimestamp is not None:
            c2pa_actions = assertion_templates["c2pa.actions"]
            c2pa_actions["data"]["actions"][0]["when"] = proofTimestamp
            assertions.append(c2pa_actions)

        claim["assertions"] = assertions

        return claim

    def generate_c2pa_proofmode(self, meta_content: dict, filename: str):
        """Generates a claim for the 'c2pa-proofmode' action.

        Args:
            meta_content: dictionary of the content metadata of a proofmode input zip
            filename: filename of the JPG file in the proofmode bundle to generate this claim for

        Returns:
            a dictionary containing the claim data
        """
        claim = copy.deepcopy(CREATE_CLAIM_TEMPLATE)
        claim["recorder"] = "ProofMode by Guardian Project and WITNESS"
        claim["claim_generator"] = "Starling Integrity"
        assertion_templates = self.assertions_by_label(claim)
        assertions = []

        author_data = meta_content.get("author")
        if author_data is not None:
            creative_work = assertion_templates["stds.schema-org.CreativeWork"]
            creative_work["data"] = author_data
            author_data["credential"] = []
            assertions.append(creative_work)

        author_name = meta_content.get("author", {}).get("name")
        copyright = meta_content.get("copyright")

        photo_metadata = self._make_photo_metadata(author_name, copyright, None)
        if photo_metadata is not None:
            photo_meta = assertion_templates["stds.iptc.photo-metadata"]
            photo_meta["data"] = photo_metadata
            assertions.append(photo_meta)

        # Find proofmode data for asset
        proofmode_data = (
            meta_content.get("private", {}).get("proofmode", {}).get(filename, {})
        )

        # TODO Make GPS data optional
        gps_lat = Decimal(proofmode_data["proofmodeJSON"]["Location.Latitude"])
        gps_lon = Decimal(proofmode_data["proofmodeJSON"]["Location.Longitude"])
        gps_alt = Decimal(proofmode_data["proofmodeJSON"]["Location.Altitude"])
        gps_time = datetime.utcfromtimestamp(
            int(proofmode_data["proofmodeJSON"]["Location.Time"]) / 1000
        )
        exif_data = self._make_c2pa_exif_gps_data(gps_lat, gps_lon, gps_alt, gps_time)
        if exif_data is not None:
            exif = assertion_templates["stds.exif"]
            exif["data"] = exif_data
            assertions.append(exif)

        pgp_sig = proofmode_data.get("pgpSignature")
        pgp_pubkey = proofmode_data.get("pgpPublicKey")
        sha256hash = proofmode_data.get("sha256hash")
        signature_data = self._make_signature_data_proofmode(
            pgp_sig, pgp_pubkey, sha256hash, filename
        )
        if signature_data is not None:
            signature = assertion_templates["org.starlinglab.integrity"]
            signature["data"] = signature_data
            assertions.append(signature)

        proofmode_time = meta_content.get("dateCreated")
        if proofmode_time is not None:
            c2pa_actions = assertion_templates["c2pa.actions"]
            c2pa_actions["data"]["actions"][0]["when"] = proofmode_time
            assertions.append(c2pa_actions)

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

    def _get_starling_capture_proof(self, meta_content: dict) -> dict:
        """
        Decode the original Starling Capture metadata stored in the meta_content.

        Returns the proof dict.
        """

        return json.loads(
            base64.standard_b64decode(
                meta_content["private"]["b64AuthenticatedMetadata"]
            )
        )["proof"]

    def _make_photo_metadata(self, author_name: str, copyright: str, geolocation: dict):
        photo_metadata = {
            "dc:creator": [author_name],
            "dc:rights": copyright,
            "Iptc4xmpExt:LocationCreated": self._get_location_created(geolocation),
        }

        photo_metadata = self._remove_keys_with_no_values(photo_metadata)

        if not photo_metadata.keys():
            return None

        return photo_metadata

    def _get_meta_content_lat_lon_alt(
        self, geolocation: dict
    ) -> tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """
        Extracts latitude, longitude, altitude from metadata JSON dict.

        Args:
            geolocation: dictionary from content metadata

        Return:
            (lat, lon, alt)

            All are Decimal objects. If any are not available then None is
            returned in their place.
        """

        lat = geolocation.get("latitude")
        lon = geolocation.get("longitude")
        alt = geolocation.get("altitude")

        if lat is None or lon is None:
            _logger.warning("Could not find both of lat/lon in 'meta'")
            return (None, None, None)

        if lat is not None:
            lat = Decimal(lat)
        if lon is not None:
            lon = Decimal(lon)
        if alt is not None:
            alt = Decimal(alt)

        return (lat, lon, alt)

    def _convert_coords_to_c2pa(
        self, lat: Optional[Decimal], lon: Optional[Decimal], alt: Optional[Decimal]
    ) -> tuple[Optional[str], Optional[str], Optional[str], Optional[int]]:
        """
        Converts decimal latitude, longitude, and altitude into valid C2PA (XMP Exif) strings.

        Args:
            lat: latitude as a Decimal or None
            lon: longitude as a Decimal or None
            alt: altitude as a Decimal or None

        Returns:
            Tuple of latitude, longitude, altitude (strings),
            and then the altitude reference integer. Any might be None if the
            relevant argument was None.
        """

        lat_c2pa, lon_c2pa, alt_c2pa, alt_ref = None, None, None, None

        # Latitude and longitude:
        #
        # Need to convert decimal degrees (DD) in to sexagesimal
        # degrees (degrees, minutes, and seconds - DMS notation).
        # However in the case of XMP Exif, seconds aren't used, and are instead
        # represented as decimal points of the minutes. Also, all values are
        # positive, and the direction is appended instead.
        #
        # Example:
        # -77.123456 -> 77,7.40736W

        def latlon_conv(l: Decimal) -> str:
            degs = int(l)
            mins = (60 * abs(l - degs)).normalize()  # Remove trailing zeros
            if int(mins) == mins:
                # It has no decimal places
                # But we want the output to, just in case
                # Example:
                #   Bad:  "5,12S"
                #   Good: "5,12.0S"
                mins = mins.quantize(Decimal("1.0"))
            return f"{abs(degs)},{mins}"

        if lat is not None:
            lat_c2pa = latlon_conv(lat)
            lat_c2pa += "N" if lat >= 0 else "S"
        if lon is not None:
            lon_c2pa = latlon_conv(lon)
            lon_c2pa += "E" if lon >= 0 else "W"

        # Altitude:
        #
        # This is a rational number, stored as a string.
        # For example: "100963/29890"
        #
        # The Exif spec stores altitude as a rational number as well.
        # It specifies the numerator and dominator are unsigned 32-bit integers
        # (long type in C), meaning the max value is: 2^32 - 1 = 4294967295
        #
        # XMP just natively stores rational numbers as text, and doesn't
        # seem to mention a limit. However since it's supposed to be derived
        # from Exif, I will keep the limit. This is likely more correct and
        # will help ensure compatibility across parser implementations.
        #
        # No meaningful precision is lost from using this limit. The maximum
        # amount that could be lost is 1/4294967295. This is roughly 2.3e-10,
        # less than a nanometre.

        if alt is not None:
            numer, denom = (
                Fraction(abs(alt)).limit_denominator(4294967295).as_integer_ratio()
            )
            alt_c2pa = f"{numer}/{denom}"
            if alt < 0:
                # Presumably negative altitude means below sea level
                alt_ref = 1
            else:
                alt_ref = 0

        return lat_c2pa, lon_c2pa, alt_c2pa, alt_ref

    def _convert_datetime_to_c2pa(self, dt: datetime) -> str:
        """
        Converts a datetime object into a valid C2PA (XMP Exif) string.

        Args:
            dt: an datetime.datetime object. If no timezone information is
                included, UTC is assumed.

        Returns:
            string
        """

        # C2PA format is RFC3339, with second precision.
        # Example: 2019-09-22T18:22:57Z

        if dt.tzinfo != timezone.utc and dt.tzinfo is not None:
            # Not UTC
            #
            # Non-UTC times are probably still valid, but convert to UTC just
            # in case to reduce timezone issues by parsers.
            dt = dt.astimezone(timezone.utc)

        # Now UTC
        # .isoformat does "+00:00" which is valid but ugly,
        # so manually add the Z.
        return dt.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"

    def _get_location_created(self, geolocation: dict):
        """Returns the Iptc4xmpExt:LocationCreated section, based on the given lat / lon

        Args:
            geolocation: a dictionary defined by the meta-content schema

        Returns:
            Dictionary to use as the value of the Iptc4xmpExt:LocationCreated field.
            Might be empty if geolocation was empty.
        """

        if geolocation is None or len(geolocation) == 0:
            return {}

        location_created = {}
        location_created["Iptc4xmpExt:CountryCode"] = geolocation.get("countryCode")
        location_created["Iptc4xmpExt:CountryName"] = geolocation.get("countryName")
        location_created["Iptc4xmpExt:ProvinceState"] = geolocation.get("provinceState")
        location_created["Iptc4xmpExt:City"] = geolocation.get("city")

        return self._remove_keys_with_no_values(location_created)

    def _make_c2pa_exif_gps_data(
        self,
        lat: Optional[Decimal],
        lon: Optional[Decimal],
        alt: Optional[Decimal],
        timestamp: Optional[datetime],
    ):
        """
        Convert arguments into valid C2PA (XMP Exif) strings and embed them into
        a stds.exif assertion.


        """

        lat, lon, alt, alt_ref = self._convert_coords_to_c2pa(lat, lon, alt)

        exif_data = {}
        exif_data["exif:GPSVersionID"] = "2.2.0.0"
        exif_data["exif:GPSLatitude"] = lat
        exif_data["exif:GPSLongitude"] = lon
        exif_data["exif:GPSAltitude"] = alt
        exif_data["exif:GPSAltitudeRef"] = alt_ref
        exif_data["exif:GPSTimeStamp"] = (
            timestamp.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
        )

        exif_data = self._remove_keys_with_no_values(exif_data)
        if not exif_data.keys():
            return None

        return exif_data

    def _make_signature_data_starling_capture(self, signatures, proof, timestamp):
        """
        Create signature data.

        Args:
            signatures: signatures dict from meta-content
            proof: proof dict from original Starling Capture metadata
            timestamp: RFC timestamp of asset creation time
        """

        if signatures is None:
            return None

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
                }
            )
        return {
            "starling:identifier": proof.get("hash"),
            "starling:signatures": signature_list,
        }

    def _make_signature_data_proofmode(self, pgp_sig, pgp_pubkey, sha256hash, filename):
        if (
            pgp_sig is None
            or pgp_pubkey is None
            or sha256hash is None
            or filename is None
        ):
            return None

        signature_list = []
        signature_list.append(
            {
                "starling:provider": "pgp",
                "starling:algorithm": "proofmode-pgp",
                "starling:publicKey": pgp_pubkey,
                "starling:signature": pgp_sig,
                "starling:authenticatedMessage": sha256hash,
                "starling:authenticatedMessageDescription": f"File Hash SHA256 of {filename} in ProofMode bundle",
            }
        )
        return {
            "starling:identifier": sha256hash,
            "starling:signatures": signature_list,
        }

    def _remove_keys_with_no_values(self, dictionary):
        ret = {}
        for k, v in dictionary.items():
            if v is None:
                continue
            if hasattr(v, "__len__") and len(v) == 0:
                # Remove empty strings, dicts, lists
                continue

            # Keep truthy values
            # But also falsy values that we like: 0, float(0), False
            ret[k] = v

        return ret

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
