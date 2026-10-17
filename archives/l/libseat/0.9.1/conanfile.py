#!/usr/bin/env python3
"""Conan recipe for libseat 0.9.1 (Meson, library component of seatd monorepo)."""

import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibseatConan(ConanFile):
    name = "libseat"
    version = "0.9.1"
    description = "Minimal universal seat management library"
    license = "MIT"
    homepage = "https://git.sr.ht/~kennylevinsen/seatd"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "builtin": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "builtin": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os == "OHOS":
            self.options.shared = False
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _inject_ohos_archiver(self):
        """Add SDK binutils when the OHOS profile only declares clang."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        compiler_dir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or (
            os.path.join(compiler_dir, "llvm-ar") if compiler_dir else ""
        )
        ranlib = executables.get("ranlib") or (
            os.path.join(compiler_dir, "llvm-ranlib") if compiler_dir else ""
        )
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini"
        )
        if not (ar and os.path.isfile(ar) and os.path.isfile(native_file)):
            return

        with open(native_file, encoding="utf-8") as stream:
            content = stream.read()
        if "\nar =" in content or "[binaries]\n" not in content:
            return

        additions = "ar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib and os.path.isfile(ranlib):
            additions += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
        content = content.replace("[binaries]\n", "[binaries]\n" + additions, 1)
        with open(native_file, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)

    def generate(self):
        tc = MesonToolchain(self)
        # Library-only build: no seatd daemon binary, no logind/systemd
        # auto-detection, no man pages, no example programs.
        tc.project_options["server"] = "disabled"
        tc.project_options["libseat-seatd"] = "enabled"
        tc.project_options["libseat-builtin"] = (
            "enabled" if bool(self.options.builtin) else "disabled"
        )
        tc.project_options["libseat-logind"] = "disabled"
        tc.project_options["man-pages"] = "disabled"
        tc.project_options["examples"] = "disabled"

        # OHOS sys/socket.h expands CMSG_NXTHDR with a signedness warning.
        # The warning originates in the SDK header and upstream enables -Werror.
        if self.settings.os == "OHOS":
            tc.project_options["werror"] = "false"
        tc.generate()

        if self.settings.os == "OHOS":
            self._inject_ohos_archiver()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

        # Upstream tests: linked_list and connection are deterministic.
        # poller blocks indefinitely waiting for event dispatch and is
        # excluded from the build-tree run (see test_package/MANIFEST.yml).
        if not self.conf.get(
            "tools.build:skip_test", default=False, check_type=bool
        ):
            self.run(
                'meson test -v --print-errorlogs --no-rebuild -C "{}" '
                "linked_list connection".format(self.build_folder)
            )

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["seat"]
        self.cpp_info.set_property("cmake_file_name", "libseat")
        self.cpp_info.set_property("cmake_target_name", "libseat::libseat")
        self.cpp_info.set_property("pkg_config_name", "libseat")