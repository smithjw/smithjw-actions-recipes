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

import os.path
import re
import subprocess
import tempfile
import time

import xattr
from autopkglib import Processor, ProcessorError

try:
    from autopkglib import BUNDLE_ID
except ImportError:
    BUNDLE_ID = "com.github.autopkg"


__all__ = ["TeradataProductURLFinder"]


class TeradataProductURLFinder(Processor):
    """Downloads a URL to the specified download_dir using curl."""

    description = __doc__
    input_variables = {
        "teradata_username": {
            "description": "Teradata Forum username.",
            "required": True,
        },
        "teradata_password": {
            "description": "Teradata Forum password.",
            "required": True,
        },
        "re_pattern": {
            "description": "Regular expression (Python) to match against page.",
            "required": True,
        },
        "re_flags": {
            "description": (
                "Optional array of strings of Python regular "
                "expression flags. E.g. IGNORECASE."
            ),
            "required": False,
        },
        "url": {
            "required": True,
            "description": "The URL to search.",
        },
        "request_headers": {
            "required": False,
            "description": (
                "Optional dictionary of headers to include with the download request."
            ),
        },
    }
    output_variables = {
        "url": {
            "description": "URL to download",
        }
    }

    def get_url_and_search(self, url, re_pattern, cookiePath, headers=None, flags=None):
        """Get data from url and search for re_pattern"""
        # pylint: disable=no-self-use
        flag_accumulator = 0
        if flags:
            for flag in flags:
                if flag in re.__dict__:
                    flag_accumulator += re.__dict__[flag]

        re_pattern = re.compile(re_pattern, flags=flag_accumulator)

        try:
            cmd = [
                self.env["CURL_PATH"],
                "--location",
                "-b",
                cookiePath,
                "-c",
                cookiePath,
            ]
            if headers:
                for header, value in headers.items():
                    cmd.extend(["--header", "%s: %s" % (header, value)])
            cmd.append(url)
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (content, stderr) = proc.communicate()
            if proc.returncode:
                os.remove(cookiePath)
                raise ProcessorError("Could not retrieve URL %s: %s" % (url, stderr))
        except OSError:
            os.remove(cookiePath)
            raise ProcessorError("Could not retrieve URL: %s" % url)

        match = re_pattern.search(content)

        if not match:
            os.remove(cookiePath)
            raise ProcessorError("No match found on URL: %s" % url)

        # return the last matched group with the dict of named groups
        return (
            match.group(match.lastindex or 0),
            match.groupdict(),
        )

    def getTeradataAuthCookie(self, cookiePath, headers):
        authURL = "https://downloads.teradata.com/user/login"

        dataString = "username={}&password={}&rememberme=forever".format(
            self.env["teradata_username"], self.env["teradata_password"]
        )

        try:
            cmd = [
                self.env["CURL_PATH"],
                "--location",
                "-b",
                cookiePath,
                "-c",
                cookiePath,
                "-d",
                dataString,
            ]
            if headers:
                for header, value in headers.items():
                    cmd.extend(["--header", "%s: %s" % (header, value)])
            cmd.append(authURL)
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (content, stderr) = proc.communicate()
            if proc.returncode:
                os.remove(cookiePath)
                raise ProcessorError(
                    "Could not retrieve URL %s: %s" % (authURL, stderr)
                )
        except OSError:
            os.remove(cookiePath)
            raise ProcessorError(
                "Could not retrieve URL: %s when attempting to get auth cookie"
                % authURL
            )

        # Check returned content doesn't indicate auth failure
        re_pattern = re.compile(r"Incorrect\susername")
        match = re_pattern.search(content)
        if match:
            os.remove(cookiePath)
            raise ProcessorError(
                "Incorrect Ircam Forum authorisation credentials for user {}.".format(
                    self.env["ircam_username"]
                )
            )
        else:
            self.output("Ircam Forum authorisation successful.")

        return

    def main(self):
        # clear any pre-exising summary result
        if "ircam_downloader_summary_result" in self.env:
            del self.env["ircam_downloader_summary_result"]

        output_var_name = self.env["result_output_var_name"]

        headers = self.env.get("request_headers", {})

        flags = self.env.get("re_flags", {})

        temporary_cookie_file = tempfile.NamedTemporaryFile(delete=False)
        cookiePath = temporary_cookie_file.name

        self.getIrcamAuthCookie(cookiePath, headers)

        groupmatch, groupdict = self.get_url_and_search(
            self.env["url"], self.env["re_pattern"], cookiePath, headers, flags
        )

        # favor a named group over a normal group match
        if output_var_name not in groupdict.keys():
            groupdict[output_var_name] = groupmatch

        # Use download_found method to get matched URL.
        self.download_found(groupmatch, cookiePath)

        for key in groupdict.keys():
            self.env[key] = groupdict[key]
            # self.output('Found matching text (%s): %s' % (key, self.env[key], ))
            self.output_variables[key] = {
                "description": "Matched regular expression group"
            }

        os.remove(cookiePath)


if __name__ == "__main__":
    PROCESSOR = IrcamFindAndDownload()
    PROCESSOR.execute_shell()
