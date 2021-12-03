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