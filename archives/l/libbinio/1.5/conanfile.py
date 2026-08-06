#!/usr/bin/env python3
"""Conan recipe — libbinio 1.5 (Autotools).

libbinio is a platform-independent binary I/O stream class library,
used by adplug. No external dependencies (only C++ stdlib).

Platform adaptations:
  - E007/E072: config.guess/config.sub replaced with OHOS-aware versions
  - HMDFS umask 077 -> 022 (config.status creates 700 temp dirs HMDFS can't write)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibbinioConan(ConanFile):
    name = "libbinio"
    version = "1.5"
    description = "Binary I/O stream class library"
    license = "LGPL-2.1"
    homepage = "https://adplug.github.io/libbinio"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # recipe repo

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # libbinio is a pure C++ library with no external deps; static build
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # E007/E072: Update config.guess/config.sub from local automake share
        # (OHOS-aware versions installed via cmd-pkgs automake).
        import shutil, glob
        am_dirs = sorted(
            glob.glob("/storage/Users/currentUser/usr/local/share/automake-*"),
            reverse=True,
        )
        for am_dir in am_dirs:
            cg_src = os.path.join(am_dir, "config.guess")
            cs_src = os.path.join(am_dir, "config.sub")
            if os.path.exists(cg_src) and os.path.exists(cs_src):
                for dest_dir in [src, self.build_folder]:
                    if os.path.isdir(dest_dir):
                        for s, name in [(cg_src, "config.guess"), (cs_src, "config.sub")]:
                            dst = os.path.join(dest_dir, name)
                            if os.path.exists(dst):
                                shutil.copy2(s, dst)
                                os.chmod(dst, 0o755)
                self.output.info(f"Updated config.guess/config.sub from {am_dir}")
                break

        # HMDFS: config.status umask 077 creates 700 temp dirs HMDFS can't write.
        # Patch configure (and config.status if already generated) to use 022.
        for dest_dir in [src, self.build_folder]:
            for cfg_name in ("configure", "config.status"):
                cfg = os.path.join(dest_dir, cfg_name)
                if os.path.exists(cfg):
                    with open(cfg, "r") as f:
                        content = f.read()
                    if "umask 077" in content:
                        content = content.replace("umask 077", "umask 022")
                        with open(cfg, "w") as f:
                            f.write(content)
                        self.output.info(f"Patched {cfg_name}: umask 077 -> 022")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["binio"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libbinio")
        self.cpp_info.set_property("cmake_target_name", "libbinio::libbinio")
