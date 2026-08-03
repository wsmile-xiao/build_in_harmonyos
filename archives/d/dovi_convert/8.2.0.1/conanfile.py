#!/usr/bin/env python3
"""Conan recipe — dovi_convert 8.2.0 — single-file Python CLI tool.

dovi_convert automates conversion of Dolby Vision Profile 7 MKV files
(UHD Blu-ray) into Profile 8.1 for universal playback compatibility.
The upstream is a single self-contained Python 3 script (dovi_convert.py)
with no build system and no test suite.

Runtime external tools (invoked via subprocess): ffmpeg, dovi_tool,
mkvmerge, mkvextract, mediainfo. These are not Conan requires — the
script auto-detects them at runtime and offers to install them via the
host package manager. On HarmonyOS PC the user installs them separately.

Source: https://github.com/cryptochrome/dovi_convert/releases/tag/v8.2.0
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class DoviConvertConan(ConanFile):
    name = "dovi_convert"
    version = "8.2.0.1"
    description = "Dolby Vision Profile 7 -> 8.1 converter (single-file Python CLI)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/cryptochrome/dovi_convert"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dovi_convert supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        get(self, **sources, strip_root=True)

    def build(self):
        # No build step for a pure-Python single-script tool.
        # Fix shebang for OHOS: upstream uses #!/usr/bin/env python3,
        # which works on OHOS (python3 in PATH). No patch needed.
        src = self.source_folder
        script = os.path.join(src, "dovi_convert.py")
        # Ensure executable bit is set after copy
        st = os.stat(script)
        os.chmod(script, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def package(self):
        # Install the script as bin/dovi_convert (no .py extension, per upstream install docs)
        copy(self, "dovi_convert.py", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Rename to dovi_convert (the canonical command name)
        old = os.path.join(self.package_folder, "bin", "dovi_convert.py")
        new = os.path.join(self.package_folder, "bin", "dovi_convert")
        if os.path.exists(old):
            shutil.move(old, new)
            st = os.stat(new)
            os.chmod(new, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        # License
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # CLI application, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
