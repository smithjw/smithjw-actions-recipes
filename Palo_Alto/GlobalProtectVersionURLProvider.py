#!/usr/local/autopkg/python
#
# Copyright 2024 James Smith based on work by Allister Banks, & Hannes Juutilainen
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

from __future__ import absolute_import

import xml.etree.ElementTree as ET

from autopkglib import Processor, ProcessorError, URLGetter

__all__ = ["GlobalProtectVersionURLProvider"]

FEED_URL = "https://pan-gp-client.s3.amazonaws.com"


class GlobalProtectVersionURLProvider(URLGetter):
    """Provides the version and download URL for the Palo Alto Global Protect Client"""

    input_variables = {}
    output_variables = {
        "version": {"required": False, "description": f"Default is {FEED_URL}"},
    }
    description = __doc__

    def get_version(self, FEED_URL):
        """Parse the Palo Alto S3 Bucket where GlobalProtect installers are hosted for the latest or defined version"""
        try:
            xml = self.download(FEED_URL)
        except Exception as e:
            raise ProcessorError("Can't download %s: %s" % (FEED_URL, e))

        root = ET.fromstring(xml)
        latest = root.find("latest")
        for vers in root.iter("latest"):
            version = vers.find("pkg").text
        return version

    def main(self):
        self.env["version"] = self.get_version(FEED_URL)
        self.output("Found Version Number %s" % self.env["version"])


if __name__ == "__main__":
    processor = GlobalProtectVersionURLProvider()
    processor.execute_shell()
