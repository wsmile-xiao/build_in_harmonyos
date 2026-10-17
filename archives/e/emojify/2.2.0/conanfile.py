#!/usr/bin/env python3
"""Conan recipe for emojify 2.2.0 — pure bash shell script (no compilation).

emojify substitutes emoji aliases like :sparkling_heart: with raw emoji
characters. It is a single bash script with no build system and no
dependencies (only bash 4+ builtins + cat/tr).

Adaptation for HarmonyOS PC (aarch64):
  - The upstream shebang `#!/usr/bin/env bash` is patched at package time to
    `#!/data/service/hnp/bin/bash` so the script runs under OHOS's bash 5.3.
  - No compilation, no ELF binary, hence no ELF signing needed.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get,
    copy,
    apply_conandata_patches,
    export_conandata_patches,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class EmojifyConan(ConanFile):
    name = "emojify"
    version = "2.2.0"
    description = "Emoji on the command line — substitutes emoji aliases like :sparkling_heart: to emoji characters"
    license = "MIT"
    homepage = "https://github.com/mrowa44/emojify"
    url = ""
    package_type = "application"

    # No options (shared/fpic don't apply to a shell script).
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # The codeload URL ends in "2.2.0" (no extension), so Conan cannot
        # deduce the archive type and would treat it as a zip. Provide an
        # explicit filename so the .tar.gz extension is recognized.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="emojify-2.2.0.tar.gz")

    def build(self):
        # No build system — only apply patches (none for this version).
        apply_conandata_patches(self)

    def package(self):
        # Copy the emojify script into bin/.
        copy(self, "emojify", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        # Patch the shebang so it points to OHOS bash (bash 5.3 at
        # /data/service/hnp/bin/bash; also present on the build machine).
        bin_path = os.path.join(self.package_folder, "bin", "emojify")
        if os.path.exists(bin_path):
            replace_in_file(self, bin_path,
                            "#!/usr/bin/env bash",
                            "#!/data/service/hnp/bin/bash")
            os.chmod(bin_path, 0o755)

        # Copy the license into licenses/ (and a copy under share/emojify/).
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "emojify"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
