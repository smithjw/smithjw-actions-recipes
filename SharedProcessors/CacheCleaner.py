#!/usr/local/autopkg/python
#
# Copyright 2024 James Smith @smithjw
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
"""See docstring for CacheCleaner class"""

from fnmatch import fnmatch
from pathlib import Path

from autopkglib import Processor, ProcessorError

__all__ = ["CacheCleaner"]


def get_size(folder: str):
    try:
        dir_size = sum(p.stat().st_size for p in Path(folder).rglob("*"))
    except FileNotFoundError:
        error = (
            "Either the permissions for the given RECIPE_CACHE_DIR are incorect"
            "or we're looking at the incorrect directory."
        )
        raise ProcessorError(error) from None

    for unit in ("B", "K", "M", "G", "T"):  # noqa: B007
        if dir_size < 1024:
            break
        dir_size /= 1024
    readable_size = f"{dir_size:.1f}{unit}"

    return readable_size


def convert_bool(value):
    if isinstance(value, str):
        value = value.lower()

    match value:
        case bool():
            return value
        case None:
            return None
        case "y" | "yes" | "t" | "true" | "on" | "1":
            return True
        case "n" | "no" | "f" | "false" | "off" | "0":
            return False
        case _:
            raise ValueError(f"Invalid input: {value}")


class CacheCleaner(Processor):
    """This processor is designed to be run in the context of CI/CD builds where the only
    remaining files we want within the cache folder of a given recipe, are receipt plists
    or info.json files from the URLDownloaderPython Processor"""

    input_variables = {
        "RECIPE_CACHE_DIR": {"required": False, "description": ("RECIPE_CACHE_DIR.")},
        "pkg_uploaded": {"required": False, "description": ("pkg_uploaded.")},
        "file_retention_patterns": {
            "description": "Pattern(s) to identify all files we're retaining",
            "default": ["*.plist", "*.info.json"],
            "required": False,
        },
        "cache_cleaner_dry_run": {
            "description": "Determines if the Processor will attempt to remove items within the cache folder not matching the patterns",
            "default": False,
            "required": False,
        },
    }

    output_variables = {
        "removed_files": {
            "description": "List of all the files removed with this processor"
        },
        "folder_size_pre": {
            "description": "Size of the folder before running CacheCleaner"
        },
        "folder_size_post": {
            "description": "Size of the folder after running CacheCleaner"
        },
    }

    description = __doc__

    def validate_recipe_cache_dir(self, recipe_cache_dir: str) -> Path:
        try:
            cache_dir = recipe_cache_dir.strip()
            if not cache_dir:
                raise ProcessorError("RECIPE_CACHE_DIR wasn't set correctly") from None
        except AttributeError:
            raise ProcessorError("RECIPE_CACHE_DIR was set to None") from None

        try:
            cache_dir = Path(cache_dir).resolve()

            if cache_dir == Path(cache_dir.anchor):
                raise ProcessorError(
                    "RECIPE_CACHE_DIR is set to the file system root!"
                ) from None

        except TypeError:
            raise ProcessorError("RECIPE_CACHE_DIR not found") from None

        return cache_dir

    def validate_file_retention_patterns(self, file_retention_patterns) -> list:
        patterns = (
            file_retention_patterns
            if isinstance(file_retention_patterns, list)
            else [file_retention_patterns]
        )

        return patterns

    def main(self):
        # Inputs
        self.recipe_cache_dir = self.validate_recipe_cache_dir(
            self.env.get("RECIPE_CACHE_DIR", None)
        )
        self.file_retention_patterns = self.validate_file_retention_patterns(
            self.env.get("file_retention_patterns")
        )
        self.pkg_uploaded = convert_bool(self.env.get("pkg_uploaded"))

        self.dry_run = convert_bool(self.env.get("cache_cleaner_dry_run"))

        if self.pkg_uploaded is False:
            # If no package was uploaded, exit as we don't want to clean the cache folder
            # This is different to pkg_uploaded being None as that indicates the value was never set
            self.output(f"Package Uploaded: {self.pkg_uploaded}")
            self.output("Exiting as no package was uploaded in prior steps")
            return

        self.output(f"RECIPE_CACHE_DIR: {self.recipe_cache_dir}")
        self.output(f"File retention patterns: {self.file_retention_patterns}")
        self.output(f"Dry Run: {self.dry_run}")

        self.folder_size = get_size(self.recipe_cache_dir)
        self.env["folder_size_pre"] = self.folder_size
        self.output(f"Folder size before CacheCleaner: {self.folder_size}")

        self.files_to_remove = [
            item
            for item in self.recipe_cache_dir.rglob("*")
            if not any(
                fnmatch(item, pattern) for pattern in self.file_retention_patterns
            )
            and (not item.is_dir() or len(list(item.iterdir())) == 0)
        ]

        self.removed_files = []

        for item in self.files_to_remove:
            # match item:
            #     case Path.is_dir():
            #         self.output(f"Removing directory: {item}")
            #         item.rmdir()
            #     case Path.is_file():
            #         self.output(f"Removing file: {item}")
            #         item.unlink(missing_ok=True)

            if self.dry_run:
                self.removed_files.append(str(item))
                continue

            if item.is_dir():
                self.output(f"Removing directory: {item}")
                item.rmdir()

            if item.is_file():
                self.output(f"Removing file: {item}")
                item.unlink(missing_ok=True)

            if item.exists():
                self.output(f"Could not remove {item}")
            else:
                self.removed_files.append(str(item))

        self.folder_size = get_size(self.recipe_cache_dir)
        self.env["folder_size_post"] = self.folder_size
        self.output(f"Folder size after CacheCleaner: {self.folder_size}")

        self.output(f"Items removed: {self.removed_files}")
        self.env["removed_files"] = self.removed_files


if __name__ == "__main__":
    PROCESSOR = CacheCleaner()
    PROCESSOR.execute_shell()
