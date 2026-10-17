#!/usr/bin/env python3
"""Conan recipe for libLASi 1.1.3 on HarmonyOS PC."""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LasiConan(ConanFile):
    name = "lasi"
    version = "1.1.3"
    description = "Library for PostScript complex text layout"
    license = "LGPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/lasi/"
    url = "https://sourceforge.net/projects/lasi/"
    topics = ("postscript", "pango", "freetype", "text-layout")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def requirements(self):
        # This published OHOS build supplies the three modules required by
        # upstream's pkg-config probe: pangoft2, pango and freetype2.
        self.requires(
            "pango/1.50.14.1.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        # LASi.h exposes both dependency header families in its public API.
        # Declare them directly so all Conan generators propagate the public
        # include closure (including glib-object.h used by pango/pango.h).
        self.requires(
            "glib/2.84.0.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "freetype/2.14.3",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "harfbuzz/14.2.0.1.1.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            filename="libLASi-1.1.3.tar.gz",
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()

        tc = CMakeToolchain(self)
        # CMake 4 on the worker has no Platform/HarmonyOS.cmake. The compiler
        # and dependency graph remain OHOS; this alias only selects CMake's
        # generic Unix platform rules for this platform-neutral C++ source.
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        tc.variables["CMAKE_CXX_STANDARD"] = 17
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        # Never install dependency-cache absolute paths into LASi binaries.
        tc.variables["USE_RPATH"] = False
        tc.generate()

        # fontconfig's generic Unix defaults do not include the HarmonyOS
        # system font directory. Both upstream examples and the consumer
        # test exercise real Unicode shaping, so provide the device font root.
        save(self, self._build_fontconfig_file(), self._fontconfig_xml())

    def build(self):
        self._activate_ohos_fontconfig()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        log_path = os.path.join(self.build_folder, "upstream-ctest.log")
        ctest = shutil.which("ctest") or "ctest"
        command = (
            '"%s" --test-dir "%s" --output-on-failure > "%s" 2>&1'
            % (ctest, self.build_folder, log_path)
        )
        error = None
        try:
            self.run(command, env="conanrun")
        except Exception as exc:
            error = exc

        output = ""
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                output = handle.read()
            self.output.info("Upstream CTest output:\n%s" % output)

        passed = output.count("   Passed")
        result = {
            "status": "passed" if error is None and passed == 3 else "failed",
            "framework": "CTest",
            "command": "ctest --test-dir <build> --output-on-failure",
            "discovered": 3,
            "executed": 3,
            "passed": passed,
            "failed": 3 - passed,
            "skipped": 0,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
        print(marker, flush=True)
        self.output.info(marker)
        if error is not None:
            raise ConanException("upstream CTest failed: %s" % error)
        if passed != 3:
            raise ConanException(
                "upstream CTest evidence mismatch: expected 3 passed, got %d"
                % passed
            )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        save(
            self,
            os.path.join(self.package_folder, "res", "fonts.conf"),
            self._fontconfig_xml(),
        )

    def package_info(self):
        self.cpp_info.libs = ["LASi"]
        # LASi.h publicly includes both Pango and FreeType headers. Use the
        # dependency's aggregate target so CMakeDeps also propagates Pango's
        # public GLib/Harfbuzz/Freetype include closure to consumers.
        self.cpp_info.requires = [
            "pango::pangoft2",
            "pango::pango",
            "glib::glib",
            "freetype::freetype",
            "harfbuzz::harfbuzz",
        ]
        self.cpp_info.set_property("cmake_file_name", "lasi")
        self.cpp_info.set_property("cmake_target_name", "lasi::lasi")
        self.cpp_info.set_property("pkg_config_name", "lasi")
        if bool(self.options.shared):
            self.cpp_info.defines.append("LASi_DLL")
        if str(self.settings.os) == "OHOS":
            self.runenv_info.define_path(
                "FONTCONFIG_FILE",
                os.path.join(self.package_folder, "res", "fonts.conf"),
            )

    def _build_fontconfig_file(self):
        return os.path.join(self.generators_folder, "lasi-fonts.conf")

    def _activate_ohos_fontconfig(self):
        if str(self.settings.os) != "OHOS":
            return
        os.environ["FONTCONFIG_FILE"] = self._build_fontconfig_file()
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            self.build_folder, "fontconfig-cache"
        )
        os.makedirs(tmpdir, exist_ok=True)
        os.environ.setdefault("XDG_CACHE_HOME", tmpdir)

    @staticmethod
    def _fontconfig_xml():
        return (
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
            '<fontconfig>\n'
            '  <dir>/system/fonts</dir>\n'
            '  <dir>/data/fonts</dir>\n'
            '  <dir>~/.fonts</dir>\n'
            '  <cachedir prefix="xdg">fontconfig</cachedir>\n'
            '</fontconfig>\n'
        )
