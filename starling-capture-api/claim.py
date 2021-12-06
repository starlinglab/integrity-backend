import json
import os

class Claim:
    """Generates the claim JSON."""

    def generate_create(self, jwt_payload):
        """Generates a claim for the 'create' action.

        Args:
            jwt_payload: a dictionary with the data we got from the request's JWT payload

        Returns:
            a dictionary containing the 'create' claim data
        """
        claim_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "c2pa_claims/claim_create.json"
        )
        with open(claim_file_path, "r") as claim_file:
            claim = json.load(claim_file)

            # Replace claim values with Starling Lab defaults.
            claim['vendor'] = "starlinglab"
            claim['recorder'] = "Starling Capture"

            # Replace claim values with values from JWT payload.
            for assertion in claim['assertions']:
                if assertion['label'] == "stds.schema-org.CreativeWork":
                    assertion['data']['author'][0]['identifier'] = jwt_payload['author']['identifier']
                    assertion['data']['author'][0]['name'] = jwt_payload['author']['name']
                    break
                if assertion['label'] == "stds.iptc.photo-metadata":
                    assertion['data']['dc:creator'] = [jwt_payload['author']['name']]
                    assertion['data']['dc:rights'] = jwt_payload['copyright']
                    break

            # Replace claim values with values from HTTP POST.
            # TODO

        return claim

    def generate_update(self):
        """Generates a claim for the 'update' action.

        Returns:
            a dictionary containing the 'update' claim data
        """
        claim_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "c2pa_claims/claim_update.json"
        )
        with open(claim_file_path, "r") as claim_file:
            claim = json.load(claim_file)
        return claim

    def generate_store(self, ipfs_cid):
        """Generates a claim for the 'store' action.

        Args:
            ipfs_cid: the IPFS CID for the asset

        Returns:
            a dictionary containing the 'store' claim data
        """
        claim_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "c2pa_claims/claim_store.json"
        )
        with open(claim_file_path, "r") as claim_file:
            claim = json.load(claim_file)

            # Replace claim values.
            for assertion in claim['assertions']:
                if assertion['label'] == "org.starlinglab.storage.ipfs":
                    assertion['data']['starling:Provider'] = "Web3.Storage"
                    assertion['data']['starling:IpfsCid'] = ipfs_cid
                    # TODO
                    assertion['data']['starling:AssetStoredTimestamp'] = ""
                    break

        return claim