#!/usr/bin/env python3
"""Conan recipe for colortest 20110624 — terminal color test scripts.

Pure shell/perl script tool, no compilation needed.  Installs the color
test scripts (colortest, 256colors2.pl, 8colors.sh, 16colors.sh,
colortable16.sh) into bin/.  Runtime requires perl and bash.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ColortestConan(ConanFile):
    name = "colortest"
    version = "20110624"
    description = ("Terminal color test tools: 8/16/256-color display "
                   "charts and scripts")
    license = "MIT AND GPL-3.0-or-later"
    homepage = "https://www.colortest.org/"
    url = "https://www.colortest.org/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.output.info("No compilation needed: pure script tool")

    def _fix_shebang(self, path, interpreter):
        """Rewrite the shebang to a portable /usr/bin/env form.

        OHOS has no /usr/bin/perl nor /bin/bash in the standard location;
        /usr/bin/env resolves via PATH, so the packaged scripts stay
        relocatable across toolchains.
        """
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if content.startswith("#!"):
            first_newline = content.index("\n")
            content = "#!/usr/bin/env " + interpreter + content[first_newline:]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.chmod(path, 0o755)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        # sh scripts: keep the original #!/bin/sh (present on OHOS)
        for f in ("8colors.sh", "16colors.sh"):
            dst = os.path.join(bin_dir, f)
            shutil.copy2(os.path.join(self.source_folder, f), dst)
            os.chmod(dst, 0o755)

        # bash script: rewrite shebang to /usr/bin/env bash
        dst = os.path.join(bin_dir, "colortable16.sh")
        shutil.copy2(os.path.join(self.source_folder, "colortable16.sh"), dst)
        self._fix_shebang(dst, "bash")

        # perl scripts: rewrite shebang to /usr/bin/env perl
        for f in ("colortest", "256colors2.pl"):
            dst = os.path.join(bin_dir, f)
            shutil.copy2(os.path.join(self.source_folder, f), dst)
            self._fix_shebang(dst, "perl")

        # docs
        doc_dir = os.path.join(self.package_folder, "share", "doc", "colortest")
        os.makedirs(doc_dir, exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "README"),
                     os.path.join(doc_dir, "README"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
