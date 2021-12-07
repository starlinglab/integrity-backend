import copy
import json
import logging
import os

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
        print(f"meta: {meta}")

        # Replace claim values with values from JWT payload.
        for assertion in claim["assertions"]:
            if assertion["label"] == "stds.schema-org.CreativeWork":
                assertion["data"]["author"][0]["identifier"] = jwt_payload["author"][
                    "identifier"
                ]
                assertion["data"]["author"][0]["name"] = jwt_payload["author"]["name"]
                continue
            if assertion["label"] == "stds.iptc.photo-metadata":
                assertion["data"]["dc:creator"] = [jwt_payload["author"]["name"]]
                assertion["data"]["dc:rights"] = jwt_payload["copyright"]
                continue

        # Replace claim values with values from HTTP POST.
        # TODO

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
