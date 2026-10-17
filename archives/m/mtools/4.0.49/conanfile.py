#!/usr/bin/env python3
"""Conan recipe — GNU mtools: collection of tools to access MS-DOS disks."""
import os
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class MtoolsConan(ConanFile):
    name = "mtools"
    version = "4.0.49"
    description = "GNU mtools — collection of tools to access MS-DOS disks from Unix"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/mtools/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text('#!/bin/sh\nexit 1\n')
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        tc.generate()

        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        if self.settings.os in ("Linux", "OHOS"):
            env.define("CC", "clang")
            env.define("CXX", "clang++")
        env.vars(self).save_script("hmos_env")

    def build(self):
        for f in os.listdir(self.source_folder):
            if f.endswith(".orig"):
                os.remove(os.path.join(self.source_folder, f))

        # E165: Fix shebang for HarmonyOS (/bin/bash -> /data/service/hnp/bin/bash)
        if self.settings.os in ("Linux", "OHOS"):
            import glob as _glob
            for script in _glob.glob(os.path.join(self.source_folder, "*")):
                try:
                    with open(script, "r") as fh:
                        first_line = fh.readline()
                    if "#!/bin/bash" in first_line:
                        from conan.tools.files import replace_in_file
                        replace_in_file(self, script, "#!/bin/bash", "#!/data/service/hnp/bin/bash")
                    elif "#! /bin/bash" in first_line:
                        from conan.tools.files import replace_in_file
                        replace_in_file(self, script, "#! /bin/bash", "#!/data/service/hnp/bin/bash")
                    elif "#!/bin/sh" in first_line:
                        from conan.tools.files import replace_in_file
                        replace_in_file(self, script, "#!/bin/sh", "#!/system/bin/sh")
                    elif "#! /bin/sh" in first_line:
                        from conan.tools.files import replace_in_file
                        replace_in_file(self, script, "#! /bin/sh", "#!/system/bin/sh")
                except (IOError, OSError, UnicodeDecodeError):
                    pass

        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
