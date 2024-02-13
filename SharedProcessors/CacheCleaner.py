#!/usr/local/autopkg/python
#
# Copyright 2023 James Smith @smithjw
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

from autopkglib import Processor

__all__ = ["CacheCleaner"]


def get_size(folder: str) -> int:
    size_in_bytes = sum(p.stat().st_size for p in Path(folder).rglob("*"))
    for unit in ("B", "K", "M", "G", "T"):
        if size_in_bytes < 1024:
            break
        size_in_bytes /= 1024

    readable_size = f"{size_in_bytes:.1f}{unit}"

    return readable_size


class CacheCleaner(Processor):
    """This processor is designed to be run in the context of CI/CD builds where the only
    remaining files we want within the cache folder of a given recipe, are receipt plists
    or info.json files from the URLDownloaderPython Processor"""

    input_variables = {
        "RECIPE_CACHE_DIR": {"required": False, "description": ("RECIPE_CACHE_DIR.")},
        "file_retention_patterns": {
            "description": ("Pattern(s) to identify all files we're retaining"),
            "default": ["*.plist", "*.info.json"],
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

    def main(self):
        retention_patterns = self.env["file_retention_patterns"]
        if isinstance(retention_patterns, str):
            retention_patterns = [retention_patterns]

        recipe_cache_dir = Path(self.env["RECIPE_CACHE_DIR"])
        self.output(f"Looking for files under {recipe_cache_dir}")

        recipe_cache_dir_size = get_size(recipe_cache_dir)
        self.env["folder_size_pre"] = recipe_cache_dir_size
        self.output(f"Folder size before CacheCleaner: {recipe_cache_dir_size}")

        files_to_remove = [
            item
            for item in recipe_cache_dir.rglob("*")
            if not any(fnmatch(item, pattern) for pattern in retention_patterns)
            and (not item.is_dir() or len(list(item.iterdir())) == 0)
        ]

        self.env["removed_files"] = []
        removed_files = self.env["removed_files"]

        for item in files_to_remove:
            if item.is_dir():
                self.output(f"Removing directory: {item}")
                item.rmdir()

            if item.is_file(missing_ok=True):
                self.output(f"Removing file: {item}")
                item.unlink()

            if item.exists():
                self.output(f"Could not remove {item}")
            else:
                removed_files.append(str(item))

        recipe_cache_dir_size = get_size(recipe_cache_dir)
        self.env["folder_size_post"] = recipe_cache_dir_size
        self.output(f"Folder size after CacheCleaner: {recipe_cache_dir_size}")
        self.output(f"Items removed: {removed_files}")


if __name__ == "__main__":
    PROCESSOR = CacheCleaner()
    PROCESSOR.execute_shell()
