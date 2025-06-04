#!/usr/local/autopkg/python
#
# Copyright 2025 Dharmateja
#
# Licensed under the Apache License, Version 2.0

from __future__ import absolute_import

import re
from html.parser import HTMLParser
import requests

from autopkglib import ProcessorError, URLGetter

__all__ = ["VantageProductURLFinder"]


class TerradataVersionInfo(HTMLParser):
    def __init__(self):
        super().__init__()
        self.versions = []
        self.current_data = None

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            for attr, value in attrs:
                if attr == "class" and value == "version":
                    self.current_data = "version"
                elif attr == "class" and value == "date":
                    self.current_data = "date"

    def handle_data(self, data):
        if self.current_data == "version":
            self.versions.append({"version": data.strip()})
            self.current_data = None
        elif self.current_data == "date":
            if self.versions:
                self.versions[-1]["date"] = data.strip()
            self.current_data = None


class FilteredDownloadLinkExtractor(HTMLParser):
    def __init__(self, arch):
        super().__init__()
        self.arch = arch
        self.filtered_link = None
        self.current_link = None
        self.capture_text = False
        self.link_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "a":
            self.current_link = attrs_dict.get("href", "")
        if tag == "span":
            self.capture_text = True
            self.link_text = ""

    def handle_data(self, data):
        if self.capture_text:
            self.link_text += data.strip()

    def handle_endtag(self, tag):
        if tag == "span":
            self.capture_text = False
        elif tag == "a" and self.current_link:
            text = self.link_text.lower().replace(" ", "")
            if self.arch == "aarch64" and "macosm1pkg" in text:
                self.filtered_link = self.current_link
            elif self.arch == "x86" and "macosintelpkg" in text:
                self.filtered_link = self.current_link
            self.current_link = None
            self.link_text = ""


class VantageProductURLFinder(URLGetter):
    description = __doc__
    input_variables = {
        "teradata_username": {"required": True, "description": "Teradata login username"},
        "teradata_password": {"required": True, "description": "Teradata login password"},
        "app": {"required": True, "description": "App identifier"},
        "architecture": {"required": True, "description": "aarch64 or x86"},
    }
    output_variables = {
        "url": {"description": "Final CloudFront download URL"},
        "version": {"description": "Product version"},
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session()
        self.app_info = {
            "teradata_vantage_editor": {
                "nid": 202573,
                "os": 10872,
                "url": "https://downloads.teradata.com/download/tools/vantage-editor-desktop",
                "name": "Vantage Editor",
                "valid_archs": ["aarch64", "x86"],
            }
        }

    def login(self, username, password):
        login_url = "https://downloads.teradata.com/user/login?destination="
        payload = {
            "name": username,
            "pass": password,
            "form_id": "user_login_form",
        }
        response = self.session.post(
            login_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        cookies = self.session.cookies.get_dict()
        self.output(f"Login response cookies: {cookies}")
        self.output(f"Login response status: {response.status_code}")
        if not any(cookie.startswith("SSESS") for cookie in cookies.keys()):
            raise ProcessorError("Login failed. Session cookie not set. Check credentials or login flow.")

    def get_product_version(self, app):
        url = self.app_info[app]["url"]
        response = self.session.get(url)
        match = re.search(r'<div id="single_version">([^<]+)</div>', response.text)

        #another check as a fall back
        if not match:
            match = re.search(r'<select[^>]*id="edit-version"[^>]*>.*?<option value="([^"]+)"', response.text, re.DOTALL)

        if match:
            version = match.group(1).strip()    
            self.output(f"Found version: {version}")
            return version
        else:
            self.output("Version not found.")
            return "1.0"

    def get_download_url(self, username, password, app, architecture):
        self.login(username, password)

        payload = {
            "os": self.app_info[app]["os"],
            "version": self.env["version"],
            "nid": self.app_info[app]["nid"],
            "check_full_user_req": 0,
            "check_user_details": "false",
        }

        r = self.session.post(
            "https://downloads.teradata.com/downloads-packages/filter",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        downloads_json = r.json()
        self.output(f"Filtered HTML snippet:\n{downloads_json[0]['downloads_html']}")
        parser = FilteredDownloadLinkExtractor(architecture)
        parser.feed(downloads_json[0]["downloads_html"])
        product_link = parser.filtered_link

        if not product_link:
            raise ProcessorError(f"Download link not found for {self.app_info[app]['name']} ({architecture}).")

        form_page = self.session.get(product_link)
        form_build_id = re.search(r'name="form_build_id" value="([^"]+)"', form_page.text)
        form_token = re.search(r'name="form_token" value="([^"]+)"', form_page.text)

        if not form_build_id or not form_token:
            raise ProcessorError("Unable to parse license form tokens.")

        license_post_data = {
            "op": "I Agree",
            "form_id": "license_popup_form",
            "form_build_id": form_build_id.group(1),
            "form_token": form_token.group(1),
        }

        download = self.session.post(
            product_link,
            data=license_post_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        )

        self.output(f"License POST response headers: {download.headers}")

        if "Location" not in download.headers:
            self.output(f"License response content: {download.text}")
            raise ProcessorError("License acceptance failed, no redirect to download URL.")

        location = download.headers["Location"]
        if ".cloudfront.net" not in location:
            raise ProcessorError("Unexpected download URL. Not a CloudFront link.")

        self.output(f"Selected download link: {location}")
        return location

    def main(self):
        username = self.env.get("teradata_username")
        password = self.env.get("teradata_password")
        app = self.env.get("app")
        architecture = self.env.get("architecture")

        if not username or not password:
            raise ProcessorError("Username and password are required.")
        if app not in self.app_info:
            raise ProcessorError(f"Invalid app '{app}'")
        if architecture not in self.app_info[app]["valid_archs"]:
            raise ProcessorError(f"Invalid architecture '{architecture}' for app '{app}'")

        self.env["version"] = self.get_product_version(app)
        self.env["url"] = self.get_download_url(username, password, app, architecture)

        self.output(f"Found URL: {self.env['url']}")
        self.output(f"Found VERSION: {self.env['version']}")


if __name__ == "__main__":
    PROCESSOR = VantageProductURLFinder()
    PROCESSOR.execute_shell()
