#!/usr/local/autopkg/python
#
# Copyright 2025 James Smith
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""See docstring for TeradataProductURLFinder class"""

from __future__ import absolute_import

import json
import re
from html.parser import HTMLParser
from urllib.parse import urlencode

from autopkglib import ProcessorError, URLGetter

__all__ = ["TeradataProductURLFinder"]


class TerradataVersionInfo(HTMLParser):
    def __init__(self):
        super().__init__()
        self.versions = []
        self.current_data = None

    def handle_starttag(self, tag, attrs):
        # Check for div tags with class "version" or "date"
        if tag == "div":
            for attr, value in attrs:
                if attr == "class" and value == "version":
                    self.current_data = "version"
                elif attr == "class" and value == "date":
                    self.current_data = "date"

    def handle_data(self, data):
        # Capture the version or date data
        if self.current_data == "version":
            self.versions.append({"version": data.strip()})
            self.current_data = None
        elif self.current_data == "date":
            if self.versions:
                self.versions[-1]["date"] = data.strip()
            self.current_data = None


class FilteredDownloadLinkExtractor(HTMLParser):
    def __init__(self, app_info, arch):
        super().__init__()
        self.product = app_info.get("name", None)
        self.search_pattern = app_info.get("search_pattern", None)
        self.use_vantage_pattern = app_info.get("use_vantage_pattern", False)
        self.arch = arch
        self.current_span_text = None
        self.filtered_link = []
        self.current_link = None
        self.capture_text = False
        self.link_text = ""

    def handle_starttag(self, tag, attrs):
        # Check if the tag is an anchor tag
        if tag == "a":
            # Convert attributes to a dictionary for easier access
            attrs_dict = dict(attrs)
            # Store the href attribute if it exists
            self.current_link = attrs_dict.get("href", None)
        elif tag == "span":
            if self.use_vantage_pattern:
                # Vantage pattern: capture text for link matching
                self.capture_text = True
                self.link_text = ""
            else:
                # Original Teradata pattern: prepare to capture the text inside the <span> tag
                self.current_span_text = ""

    def handle_data(self, data):
        if self.use_vantage_pattern and self.capture_text:
            # Vantage pattern: accumulate link text
            self.link_text += data.strip()
        elif self.current_span_text is not None:
            # Original pattern: capture the text inside the <span> tag
            self.current_span_text += data

    def handle_endtag(self, tag):
        if tag == "span":
            if self.use_vantage_pattern:
                self.capture_text = False
            elif self.current_span_text:
                # Original Teradata pattern logic
                if self.search_pattern:
                    if re.search(self.search_pattern, self.current_span_text):
                        self.filtered_link = self.current_link
                elif (
                    self.product == self.current_span_text.split("__")[0]
                    and self.arch in self.current_span_text.split("mac_")[-1]
                ):
                    # Store the current link if it matches
                    self.filtered_link = self.current_link
                # Reset the span text and current link
                self.current_span_text = None
                self.current_link = None
        elif tag == "a" and self.use_vantage_pattern and self.current_link:
            # Vantage pattern: check link text for architecture match
            text = self.link_text.lower().replace(" ", "")
            if self.arch == "aarch64" and "macosm1pkg" in text:
                self.filtered_link = self.current_link
            elif self.arch == "x86" and "macosintelpkg" in text:
                self.filtered_link = self.current_link
            self.current_link = None
            self.link_text = ""


class TeradataProductURLFinder(URLGetter):
    """Downloads Teradata Studio from Teradata's website."""

    description = __doc__
    input_variables = {
        "teradata_username": {
            "required": True,
            "description": ("Username Teradata Account"),
        },
        "teradata_password": {
            "required": True,
            "description": ("Password Teradata Account"),
        },
        "app": {
            "required": True,
            "description": ("App identifier (teradata_studio, teradata_studio_express, teradata_tools_utilities, teradata_vantage_editor)"),
        },
        "architecture": {
            "required": False,
            "description": ("Architecture (aarch64 or x86)"),
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the requested Teradata product",
        },
        "version": {
            "description": "Version",
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_info = {
            "teradata_studio": {
                "nid": 183396,
                "os": 10872,
                "url": "https://downloads.teradata.com/download/tools/teradata-studio",
                "name": "TeradataStudio",
                "valid_archs": ["aarch64", "x86"],
            },
            "teradata_studio_express": {
                "nid": 7557,
                "os": 10872,
                "url": "https://downloads.teradata.com/download/tools/teradata-studio-express",
                "name": "TeradataStudioExpress",
                "valid_archs": ["aarch64", "x86"],
            },
            "teradata_tools_utilities": {
                "nid": 201214,
                "os": 1541,
                "url": "https://downloads.teradata.com/download/tools/teradata-tools-and-utilities-mac-osx-installation-package",
                "name": "TTU",
                "search_pattern": "^TTU\s\d+\.\d+\.\d+\.\d+\smacOS\sBase$",
            },
            "teradata_vantage_editor": {
                "nid": 202573,
                "os": 10872,
                "url": "https://downloads.teradata.com/download/tools/vantage-editor-desktop",
                "name": "Vantage Editor",
                "valid_archs": ["aarch64", "x86"],
                "use_vantage_pattern": True,
            },
        }

    def get_product_version(self, app):
        """Returns the product version."""
        url = self.app_info[app]["url"]
        downloads_page = self.download(url, text=True)

        # Try Vantage pattern first (more specific)
        if self.app_info[app].get("use_vantage_pattern", False):
            # Check for single version div first
            match = re.search(r'<div id="single_version">([^<]+)</div>', downloads_page)

            # Fallback to select option pattern
            if not match:
                match = re.search(r'<select[^>]*id="edit-version"[^>]*>.*?<option value="([^"]+)"', downloads_page, re.DOTALL)

            if match:
                version = match.group(1).strip()
                self.output(f"Found version: {version}")
                return version
            else:
                self.output("Version not found, using default.")
                return "1.0"
        else:
            # Use original Teradata pattern
            parser = TerradataVersionInfo()
            parser.feed(downloads_page)

            if parser.versions:
                version = parser.versions[0]["version"]
                return version
            else:
                self.output("Version not found.")
                return None

    def get_download_url(self, username, password, app, architecture):
        LOGIN_URL = "https://downloads.teradata.com/user/login?destination="
        login_data = {"name": username, "pass": password, "form_id": "user_login_form"}

        # Login POST request using curl
        curl_cmd = self.prepare_curl_cmd()
        curl_cmd.extend(["-X", "POST"])
        curl_cmd.extend(["-H", "Content-Type: application/x-www-form-urlencoded"])
        curl_cmd.extend(["-c", "/tmp/teradata_cookies.txt"])  # Save cookies
        for key, value in login_data.items():
            curl_cmd.extend(["-d", f"{key}={value}"])
        curl_cmd.append(LOGIN_URL)
        self.download_with_curl(curl_cmd, text=True)

        # Get downloads packages filter
        filter_data = {
            "os": self.app_info[app]["os"],
            "version": self.env["version"],
            "nid": self.app_info[app]["nid"],
            "check_full_user_req": 0,
            "check_user_details": "false",
        }

        curl_cmd = self.prepare_curl_cmd()
        curl_cmd.extend(["-X", "POST"])
        curl_cmd.extend(["-b", "/tmp/teradata_cookies.txt"])  # Use cookies
        for key, value in filter_data.items():
            curl_cmd.extend(["-d", f"{key}={value}"])
        curl_cmd.append("https://downloads.teradata.com/downloads-packages/filter")

        response_content = self.download_with_curl(curl_cmd, text=True)
        download_data = json.loads(response_content)

        parser = FilteredDownloadLinkExtractor(self.app_info[app], architecture)
        parser.feed(download_data[0]["downloads_html"])
        product_link = parser.filtered_link
        if not product_link:
            raise ProcessorError(
                f"Download link not found for {self.app_info[app]['name']}. Please check your credentials or the product name."
            )

        # Check if this is a Vantage app that needs form token handling
        if self.app_info[app].get("use_vantage_pattern", False):
            # Get the license form page to extract form tokens
            curl_cmd = self.prepare_curl_cmd()
            curl_cmd.extend(["-b", "/tmp/teradata_cookies.txt"])  # Use cookies
            curl_cmd.append(product_link)
            form_page_content = self.download_with_curl(curl_cmd, text=True)

            # Extract form tokens
            form_build_id = re.search(r'name="form_build_id" value="([^"]+)"', form_page_content)
            form_token = re.search(r'name="form_token" value="([^"]+)"', form_page_content)

            if not form_build_id or not form_token:
                raise ProcessorError("Unable to parse license form tokens.")

            # Prepare license acceptance data
            final_data = {
                "op": "I Agree",
                "form_id": "license_popup_form",
                "form_build_id": form_build_id.group(1),
                "form_token": form_token.group(1),
            }
        else:
            # Original Teradata pattern
            final_data = {
                "downloadnid": self.app_info[app]["nid"],
                "form_id": "license_popup_form",
            }

        # Final POST to get download URL with headers
        curl_cmd = self.prepare_curl_cmd()
        curl_cmd.extend(["-X", "POST"])
        curl_cmd.extend(["-H", "Content-Type: application/x-www-form-urlencoded"])
        # curl_cmd.extend(["-b", "/tmp/teradata_cookies.txt"]) # Don't use cookies as this will result in error
        curl_cmd.extend(["-D", "-"])  # Include headers in output
        # curl_cmd.extend(["--max-redirs", "0"])  # We follow redirects to capture the final URL
        for key, value in final_data.items():
            curl_cmd.extend(["-d", f"{key}={value}"])
        curl_cmd.append(product_link)

        try:
            response_with_headers = self.download_with_curl(curl_cmd, text=True)
        except ProcessorError as e:
            # Curl returns error code for 3xx redirects when max-redirs=0
            # This is expected behavior - we need to extract the Location header
            if "302" in str(e) or "301" in str(e):
                # Try to extract headers from the error output
                error_str = str(e)
                if "Location:" in error_str:
                    # Extract location from error message
                    location_match = re.search(r'Location:\s*([^\r\n]+)', error_str)
                    if location_match:
                        download_url = location_match.group(1).strip()

                        # Validate CloudFront URL for Vantage apps
                        if self.app_info[app].get("use_vantage_pattern", False):
                            if ".cloudfront.net" not in download_url:
                                raise ProcessorError("Unexpected download URL. Not a CloudFront link.")

                        self.output(f"Selected download link: {download_url}")
                        return download_url
            raise e

        # Parse headers from response (fallback)
        headers = self.parse_headers(response_with_headers.split('\r\n\r\n')[0])
        self.output(f"Response headers: {headers}", 2)
        download_url = headers.get("location") or headers.get("http_redirected")

        if not download_url:
            raise ProcessorError("Could not extract download URL from response headers")

        # Validate CloudFront URL for Vantage apps
        if self.app_info[app].get("use_vantage_pattern", False):
            if ".cloudfront.net" not in download_url:
                raise ProcessorError("Unexpected download URL. Not a CloudFront link.")

        self.output(f"Selected download link: {download_url}")
        return download_url

    def main(self):
        username = self.env.get("teradata_username", None)
        password = self.env.get("teradata_password", None)

        if username is None or password is None:
            raise ProcessorError(
                "Username and password are required. Please provide them in the environment variables."
            )
        architecture = self.env.get("architecture", None)
        app = self.env.get("app", None)

        if app not in self.app_info:
            raise ProcessorError(
                f"Invalid app name: {app}. Valid options are: {list(self.app_info.keys())}"
            )

        valid_archs = self.app_info[app].get("valid_archs", None)
        if valid_archs is not None and architecture not in valid_archs:
            raise ProcessorError(
                f"Invalid architecture: {architecture}. Valid options are: {self.app_info[app]['valid_archs']}"
            )

        self.env["version"] = self.get_product_version(app)
        self.env["url"] = self.get_download_url(username, password, app, architecture)
        self.output(f"Found URL: {self.env['url']}")
        self.output(f"Found VERSION: {self.env['version']}")


if __name__ == "__main__":
    PROCESSOR = TeradataProductURLFinder()
    PROCESSOR.execute_shell()
