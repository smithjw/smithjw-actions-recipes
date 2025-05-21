from autopkglib import Processor, ProcessorError
import subprocess
import json

__all__ = ["FindLatestPolyLensURL"]

class FindLatestPolyLensURL(Processor):
    description = "Fetches latest Poly Lens download URL and version using GraphQL API."
    input_variables = {}
    output_variables = {
        "download_url": {
            "description": "URL to the latest Poly Lens .dmg"
        },
        "version": {
            "description": "Version of the latest Poly Lens release"
        }
    }

    def main(self):
        graphql_query = {
            "query": """
            query {
                availableProductSoftwareByPid(pid:"lens-desktop-mac") {
                    name
                    version
                    publishDate
                    productBuild {
                        archiveUrl
                    }
                }
            }
            """
        }

        try:
            result = subprocess.run(
                [
                    "/usr/bin/curl",
                    "--silent",
                    "--location",
                    "--header", "content-type: application/json",
                    "--data-binary", json.dumps(graphql_query),
                    "https://api.silica-prod01.io.lens.poly.com/graphql"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            print("Curl stdout:", result.stdout)
            print("Curl stderr:", result.stderr)

            if not result.stdout.strip():
                raise ProcessorError("Empty response from GraphQL API.")

            response = json.loads(result.stdout)
            data = response["data"]["availableProductSoftwareByPid"]

            archive_url = data["productBuild"]["archiveUrl"]
            version = data["version"]

            if not archive_url:
                raise ProcessorError("archiveUrl not found in response.")

            self.env["download_url"] = archive_url
            full_version = response["data"]["availableProductSoftwareByPid"]["name"].split(" - ")[-1]
            self.env["version"] = full_version
            self.output(f"Found latest download URL: {archive_url}")
            self.output(f"Found version: {version}")

        except subprocess.CalledProcessError as e:
            raise ProcessorError(f"Curl command failed: {e.stderr.strip()}")
        except json.JSONDecodeError as e:
            raise ProcessorError(f"Failed to parse JSON response: {e}")
        except KeyError as e:
            raise ProcessorError(f"Expected key missing in response: {e}")
