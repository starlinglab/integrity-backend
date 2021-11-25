
class Claim:
    """Generates the claim JSON."""

    def generate(self, jwt_payload):
        """Generates a claim.

        TODO: Add as inputs the JSON sections from the request
        TODO: Add logic to generate the claim that we want

        Args:
            jwt_payload: a dictionary with the data we got from the request's JWT payload
                         this is at the moment only here as an example, we'll want something
                         different for the final version

        Returns:
            a dictionary containing the necessary claim data
        """
        return {
            "vendor": "Starling",
            "recorder": "Starling Capture Api",
            "assertions": [
                {
                    "label": "starling.assertion",
                    "data": {"jwt_payload": jwt_payload},
                }
            ],
        }

