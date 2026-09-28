#!/usr/bin/env python3
"""Conan recipe for wtype 0.4 — a Wayland virtual-keyboard command-line tool."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


SCANNER_WAYLAND_VERSION = "1.24.0"


class WtypeConan(ConanFile):
    name = "wtype"
    version = "0.4"
    description = "Command-line tool for sending virtual-keyboard input through Wayland"
    license = "MIT"
    homepage = "https://github.com/atx/wtype"
    url = "https://github.com/atx/wtype"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # Keep runtime dependencies available on OHOS without loading Conan-cache
    # shared objects when the packaged executable is launched.
    default_options = {
        "wayland/*:shared": False,
        "libxkbcommon/*:shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("wayland/1.24.0")
        self.requires("libxkbcommon/1.8.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["scanner_sources"],
            strip_root=True,
            destination="wayland-scanner-src",
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        dep_pc_paths = []
        for dep in self.dependencies.values():
            for subdir in ("lib/pkgconfig", "share/pkgconfig"):
                pc_dir = os.path.join(dep.package_folder, subdir)
                if os.path.isdir(pc_dir):
                    dep_pc_paths.append(pc_dir)
        tc.pkg_config_path = os.pathsep.join(
            [path for path in [tc.pkg_config_path, *dep_pc_paths] if path]
        )
        tc.generate()

        # Meson does not consistently discover llvm-ar in the OHOS environment.
        ar_path = shutil.which("ar") or "/data/service/hnp/bin/ar"
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as f:
                content = f.read()
            if "ar =" not in content:
                content = content.replace(
                    "[binaries]\nc =",
                    f"[binaries]\nar = '{ar_path}'\nc =",
                    1,
                )
            with open(native_file, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)

        # The static scanner is generated into generators_folder before Meson
        # configure; make that directory visible to find_program().
        env = Environment()
        env.prepend_path("PATH", self.generators_folder)
        env.vars(self).save_script("conanbuild_env")

    def _find_expat_static(self):
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a",
        ]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat":
                candidates.append(os.path.join(dep.package_folder, "lib", "libexpat.a"))
        for candidate in candidates:
            if os.path.isfile(candidate):
                self.output.info(f"wtype: static expat -> {candidate}")
                return candidate
        raise ConanException(
            "wtype needs a static libexpat.a to build the native wayland-scanner; "
            f"tried: {candidates}"
        )

    def _find_expat_include(self):
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/include",
        ]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat":
                candidates.append(os.path.join(dep.package_folder, "include"))
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "expat.h")):
                return candidate
        return None

    def _build_static_scanner(self):
        scanner_src = os.path.join(self.source_folder, "wayland-scanner-src")

        config_h = os.path.join(scanner_src, "config.h")
        with open(config_h, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                '#define HAVE_EXPAT 1\n'
                '#define PACKAGE "wayland"\n'
                f'#define VERSION "{SCANNER_WAYLAND_VERSION}"\n'
            )

        version_template = os.path.join(scanner_src, "src", "wayland-version.h.in")
        version_header = os.path.join(scanner_src, "src", "wayland-version.h")
        with open(version_template, encoding="utf-8") as f:
            content = f.read()
        major, minor, micro = SCANNER_WAYLAND_VERSION.split(".")
        for key, value in (
            ("@WAYLAND_VERSION@", SCANNER_WAYLAND_VERSION),
            ("@WAYLAND_VERSION_MAJOR@", major),
            ("@WAYLAND_VERSION_MINOR@", minor),
            ("@WAYLAND_VERSION_MICRO@", micro),
        ):
            content = content.replace(key, value)
        with open(version_header, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        dtd_header = os.path.join(scanner_src, "src", "wayland.dtd.h")
        self.run(
            f"python3 {scanner_src}/src/embed.py "
            f"{scanner_src}/protocol/wayland.dtd wayland_dtd > {dtd_header}",
            env="conanbuild",
        )

        scanner_bin = os.path.join(self.generators_folder, "wayland-scanner")
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        expat_include = self._find_expat_include()
        expat_library = self._find_expat_static()
        include_flag = f"-I{expat_include} " if expat_include else ""
        self.run(
            f"{cc} -o {scanner_bin} "
            f"-include {config_h} "
            f"-I{scanner_src} -I{scanner_src}/src -I{scanner_src}/protocol "
            f"{scanner_src}/src/scanner.c {scanner_src}/src/wayland-util.c "
            f"{include_flag}{expat_library} -lm -lpthread -static",
            env="conanbuild",
        )
        self.output.info("wtype: built static wayland-scanner")

    def build(self):
        self._build_static_scanner()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

        # The v0.4 source archive contains no upstream test suite or Meson test
        # targets. Run the upstream test command so this absence is explicit.
        self.run("meson test", env="conanbuild")

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
