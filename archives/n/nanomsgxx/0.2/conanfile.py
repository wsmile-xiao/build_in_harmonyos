#!/usr/bin/env python3
"""Conan recipe — nanomsgxx 0.2 (waf build).

nanomsgxx is a C++11 wrapper for nanomsg, built with the waf build system.
The upstream 0.2 tag ships a Python-2-era waf 1.7.11 (won't run under Python
3), so we pull the py3-compatible waf 2.0.22 — the exact same upstream master
waf the Homebrew formula uses (commit 4426567809, sha256-identical), verified
for version before use.

Patches applied via conandata.yml (in build()):
  0001-nnxx-wscript-py3.patch     : print(cmd) → print(cmd) in src/nnxx/wscript
  0002-tests-wscript-newer-waf.patch : f.path_from(waf.path) — upstream
                commit 08c6d88 "waf 1.9.x support" (PR#13); without it waf 2.x
                fails to resolve the tests targets ("source not found").

Library type (libnnxx shared/static + headers) → no commands.json (R38).
"""
import os
import re
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, download, rmdir)

# waf 2.0.22 bootstrap script (py3-compatible, Homebrew-identical)
WAF_VERSION = "2.0.22"


class NanomsgxxConan(ConanFile):
    name = "nanomsgxx"
    version = "0.2"
    description = "nanomsgxx — simple C++11 binding for the nanomsg library"
    license = "MIT"
    homepage = "https://github.com/achille-roussel/nanomsgxx"
    url = "https://github.com/achille-roussel/nanomsgxx"
    topics = ("nanomsg", "nanomsgxx", "scalable", "messaging", "cxx11")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    requires = "nanomsg/1.2"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nanomsgxx/0.2 supports Linux/OHOS only, got {self.settings.os}")
        if not self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Fetch the py3-compatible waf 2.0.22 into the source root.
        # Same source the Homebrew nanomsgxx.rb formula ships.
        waf_meta = self.conan_data["waf"]
        waf_src = os.path.join(self.source_folder, "waf")
        download(self, waf_meta["url"][0], waf_src,
                 sha256=waf_meta["sha256"])  # sha256 必须以关键字传入
        data = open(waf_src, "rb").read()
        m = re.search(rb'VERSION="([0-9.]+)"', data)
        ver = m.group(1).decode() if m else ""
        if ver != WAF_VERSION:
            raise ConanException(
                f"Unexpected waf version {ver!r} (expected {WAF_VERSION}); "
                "waf 2.x is required for Python-3 compatibility.")
        os.chmod(waf_src, 0o755)

    def generate(self):
        # Expose the profile toolchain PATH etc. from [buildenv]
        VirtualBuildEnv(self).generate()

    def _build_env(self):
        """Expose the profile toolchain (CC/CXX/AR/RANLIB) + nanomsg dep paths
        to the waf build scripts.  waf's check_cxx(lib='nanomsg') needs to be
        able to find clang and the nanomsg headers/libs."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = compilers.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "llvm-ar")
        ranlib = compilers.get("ranlib") or (os.path.join(bindir, "llvm-ranlib") if bindir else "llvm-ranlib")
        env.define("AR", ar)
        env.define("RANLIB", ranlib)
        nanomsg = self.dependencies["nanomsg"].cpp_info
        env.append("CFLAGS", f"-I'{nanomsg.includedir}'")
        env.append("CXXFLAGS", f"-I'{nanomsg.includedir}' -std=c++11")
        env.append("LINKFLAGS", f"-L'{nanomsg.libdir}'")
        return env

    def _waf(self, command, *args):
        joined = " ".join(args)
        # Use the interpreter running this recipe (avoids PATH assumptions).
        self.run(f'"{sys.executable}" waf {command} {joined}'.strip(),
                 cwd=self.source_folder, env="conanbuild")

    def build(self):
        apply_conandata_patches(self)
        # --nodoc --nopkgconfig: skip docs/null pkg-config template.
        # NOTE: tests are NOT disabled so the waf_unit_test targets build.
        with self._build_env().vars(self).apply():
            self._waf("configure",
                      "--prefix=/", "--libdir=/lib",
                      "--nodoc", "--nopkgconfig")
            self._waf("build")
        # Run the upstream waf_unit_test suite.  Test binaries link against
        # the freshly built libnnxx/libnanomsgext plus the nanomsg dependency,
        # so point LD_LIBRARY_PATH at those build dirs for execution.
        test_env = Environment()
        test_lib_dirs = [
            os.path.join(self.source_folder, "build", "src", "nnxx"),
            os.path.join(self.source_folder, "build", "src", "nanomsg", "ext"),
            self.dependencies["nanomsg"].cpp_info.libdir,
        ]
        test_env.prepend_path("LD_LIBRARY_PATH", test_lib_dirs)
        test_env.vars(self).save_script("nanomsgxx_test_env")
        # waf 2.x runs the unit tests with --alltests (not --run_tests).
        self.run(f'"{sys.executable}" waf --alltests', cwd=self.source_folder,
                 env=["conanbuild", "nanomsgxx_test_env"])

    def package(self):
        self._waf("install", f"--destdir={self.package_folder}")
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["nnxx"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.requires = ["nanomsg::nanomsg"]
        self.cpp_info.set_property("cmake_file_name", "nanomsgxx")
        self.cpp_info.set_property("cmake_target_name", "nanomsgxx::nanomsgxx")
        self.cpp_info.set_property("pkg_config_name", "nnxx")
