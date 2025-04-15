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
from html.parser import HTMLParser

import requests
from autopkglib import URLGetter

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


class TeradataProductURLFinder(URLGetter):
    """Downloads Teradata Studio from Teradata's website."""

    description = __doc__
    input_variables = {
        "username": {"required": True, "description": ("Username Teradata Account")},
        "password": {"required": True, "description": ("Password Teradata Account")},
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
        self.session = requests.Session()
        self.app_info = {
            "teradata_studio": {
                "nid": 183396,
                "os": 10872,
                "url": "https://downloads.teradata.com/download/tools/teradata-studio",
            }
        }

    def get_product_version(self, app):
        """Returns the product version."""
        url = self.app_info[app]["url"]
        downloads_page = self.session.get(url)

        parser = TerradataVersionInfo()
        parser.feed(downloads_page.text)

        if parser.versions:
            print(f"Version found: {parser.versions[0]['version']}")
            version = parser.versions[0]["version"]
            return version
        else:
            print("Version not found.")
            return None

    def get_download_url(self, username, password, app):
        LOGIN_URL = "https://downloads.teradata.com/user/login?destination="
        payload = {"name": username, "pass": password, "form_id": "user_login_form"}

        self.session.post(
            LOGIN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        uid = (
            self.session.get("https://downloads.teradata.com/user")
            .url.rstrip("/")
            .split("/")[-1]
        )

        payload = {
            "os": self.app_info[app]["os"],
            "version": self.env["version"],
            "nid": self.app_info[app]["nid"],
            "check_full_user_req": 0,
            "uid": uid,
            "check_user_details": "false",
        }
        r = self.session.post(
            "https://downloads.teradata.com/downloads-packages/filter",
            data=payload,
        )

        download_url = json.dumps(r.json())
        print(download_url)
        download = requests.post(
            "https://downloads.teradata.com/download/license?destination=download/files/183396/202783/0/TeradataStudio__win64_x86.17.20.00.04.zip&message=License%2520Agreement&key=0",
            data={
                "downloadnid": self.app_info[app]["nid"],
                "form_id": "license_popup_form",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            allow_redirects=False,
        )

        download_url = download.headers["Location"]

        return download_url

    def main(self):
        username = self.env.get("username", None)
        password = self.env.get("password", None)
        app = self.env.get("app", None)

        self.env["version"] = self.get_product_version(app)
        self.env["url"] = self.get_download_url(username, password, app)
        self.output("Found URL %s" % self.env["url"])
        self.output("Found VERSION %s" % self.env["version"])


if __name__ == "__main__":
    PROCESSOR = TeradataProductURLFinder()
    PROCESSOR.execute_shell()
    # TeradataProductURLFinder()
