#!/usr/bin/env python3
"""Conan recipe — crossguid 0.2.2 (CMake, GUID_LIBUUID via uuid/2.40.1).

- CMake build: upstream CMakeLists.txt patched to (a) rename target output to
  libcrossguid, (b) consume the conan-managed uuid/2.40.1 through uuid::uuid
  instead of the pkg-config FindLibuuid module, (c) add install rules.
- Upstream test runner (xgtest, XG_TESTS=ON) is built and executed in build().
- TMPDIR/TMP/TEMP are forwarded into source() and buildenv (E002: /tmp may be
  read-only on OHOS PC). No bare $CC/$CXX shell variables (R33).
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CrossguidConan(ConanFile):
    name = "crossguid"
    version = "0.2.2"
    description = "Lightweight cross platform C++ GUID/UUID library"
    license = "MIT"
    homepage = "https://github.com/graeme-hill/crossguid"
    url = ""
    topics = ("guid", "uuid")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("uuid/2.40.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # E002: /tmp may be read-only; forward a writable TMPDIR for get()/extract.
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.base_source_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(_k, _v)
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["XG_TESTS"] = "ON"
        if self.options.fPIC:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream test runner (built via XG_TESTS=ON): run it in place.
        if can_run(self):
            xgtest = os.path.join(self.build_folder, "xgtest")
            if not os.path.isfile(xgtest):
                hits = glob.glob(os.path.join(self.build_folder, "**", "xgtest"),
                                 recursive=True)
                if hits:
                    xgtest = hits[0]
            self.run("{}".format(xgtest), env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["crossguid"]
