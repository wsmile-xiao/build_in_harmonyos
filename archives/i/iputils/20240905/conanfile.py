#!/usr/bin/env python3
"""Conan recipe for iputils 20240905 on HarmonyOS."""

import os
import shlex

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class IputilsConan(ConanFile):
    name = "iputils"
    version = "20240905"
    package_type = "application"
    description = "Linux network diagnostic utilities including ping and tracepath"
    license = "GPL-2.0-or-later"
    homepage = "https://iputils.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options.update({
            "BUILD_ARPING": True,
            "BUILD_CLOCKDIFF": True,
            "BUILD_PING": True,
            "BUILD_TRACEPATH": True,
            "BUILD_MANS": False,
            "BUILD_HTML_MANS": False,
            "NO_SETCAP_OR_SUID": True,
            "INSTALL_SYSTEMD_UNITS": False,
            "USE_CAP": False,
            "USE_GETTEXT": False,
            "USE_IDN": False,
            "SKIP_TESTS": False,
        })
        tc.generate()
        # The OHOS profile only registers c/cpp compiler executables, so
        # MesonToolchain cannot emit ar/ranlib into the native file and meson
        # fails to probe the archiver by bare name. Derive the full paths from
        # the C compiler directory and inject them into conan_meson_native.ini.
        _compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        _ar = _compilers.get("ar")
        _ranlib = _compilers.get("ranlib")
        _cc = _compilers.get("c") or ""
        _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
        if not _ar and _bindir:
            _ar_candidate = os.path.join(_bindir, "llvm-ar")
            if os.path.isfile(_ar_candidate):
                _ar = _ar_candidate
                _ranlib_candidate = os.path.join(_bindir, "llvm-ranlib")
                if os.path.isfile(_ranlib_candidate):
                    _ranlib = _ranlib_candidate
        _native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and os.path.isfile(_native_file):
            with open(_native_file, encoding="utf-8") as _handle:
                _content = _handle.read()
            if "\nar =" not in _content and "[binaries]" in _content:
                _insert = "[binaries]\nar = '%s'\n" % _ar
                if _ranlib:
                    _insert += "ranlib = '%s'\n" % _ranlib
                _content = _content.replace("[binaries]\n", _insert, 1)
                with open(_native_file, "w", encoding="utf-8") as _handle:
                    _handle.write(_content)
    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream meson test suite when the build host can run it.

        The OpenDesk pipeline executes conan create natively on the
        HarmonyOS device, so meson test runs the real suite there (19
        tests: ping -c1 localhost/127.0.0.1, option-failure cases, and
        -V smoke tests for arping/tracepath/clockdiff).  On a
        cross-compiling worker (build machine != target) meson has no
        exe_wrapper and would silently no-op, so skip with a log line.
        """
        if str(self.settings_build.os) != str(self.settings.os):
            self.output.info(
                "upstream meson tests skipped: cross build ({} -> {})".format(
                    self.settings_build.os, self.settings.os
                )
            )
            return
        self.run(
            "meson test -C {} --print-errorlogs".format(
                shlex.quote(self.build_folder)
            ),
            env="conanbuild",
        )

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
