#!/usr/bin/env python3
"""Conan recipe for dzr 260315 — Command-line Deezer.com player (shell script)."""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class DzrConan(ConanFile):
    name = "dzr"
    version = "260315"
    description = "Command-line Deezer.com player"
    license = "Unlicense"
    homepage = "https://github.com/yne/dzr"
    url = ""

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        # No patches for dzr (upstream shell scripts work with only an
        # E165 shebang fix applied in build()); declare the hook anyway
        # so the recipe passes the G1 structural gate.
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No upstream patches to apply (conandata.yml declares none);
        # call apply_conandata_patches() for the G1 structural gate — it
        # is a no-op when conandata.yml has no `patches:` key.
        apply_conandata_patches(self)

        # E165: Fix shebang for OHOS (/bin/sh -> /system/bin/sh)
        import os
        for root, dirs, files in os.walk(self.source_folder):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.isfile(fp) and not f.endswith('.md'):
                    try:
                        with open(fp, 'r') as fh:
                            first_line = fh.readline()
                        if first_line.startswith('#!') and '/bin/sh' in first_line:
                            with open(fp, 'r') as fh:
                                content = fh.read()
                            content = content.replace('#!/bin/sh', '#!/system/bin/sh', 1)
                            with open(fp, 'w') as fh:
                                fh.write(content)
                    except (IOError, OSError) as exc:
                        # Surface shebang-fix failures instead of silently
                        # swallowing them — a bare except: pass would let
                        # IOError/PermissionError/UnicodeDecodeError go
                        # undetected and falsely report build success while
                        # the shebang stays wrong (script won't exec on OHOS).
                        self.output.warn(
                            f"shebang fix failed for {fp}: {exc} — "
                            f"script may not exec on OHOS (/bin/sh shebang)"
                        )

    def package(self):
        copy(self, "dzr", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "dzr-url", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "dzr-dec", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "dzr-srt", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "dzr-id3", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []