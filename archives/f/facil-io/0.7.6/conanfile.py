#!/usr/bin/env python3
"""Conan recipe — facil.io 0.7.6

facil.io: C web application framework (HTTP/WebSocket server, fiobj
dynamic objects, evented networking). CMake builds one static lib
(target "facil.io", output libfacil.io.a, no install rules — headers
and library are packaged manually).
License: MIT.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class FacilIoConan(ConanFile):
    name = "facil-io"
    version = "0.7.6"
    description = "facil.io - C web application framework with HTTP/WebSocket server and fiobj dynamic objects"
    license = "MIT"
    homepage = "https://github.com/boazsegev/facil.io"
    url = ""  # CI fills this

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        # multi-URL fallback: mirrors injected by the W3 pre-download flow may
        # be unreachable; codeload serves the identical archive (same sha256)
        urls = self.conan_data["sources"].get("url")
        sha = self.conan_data["sources"]["sha256"]
        candidates = list(urls) if isinstance(urls, list) else [urls]
        candidates.append(
            "https://codeload.github.com/boazsegev/facil.io/tar.gz/refs/tags/0.7.6")
        last_err = None
        for u in candidates:
            try:
                fname = "facil.io-0.7.6.tar.gz" if "codeload" in u else None
                if fname:
                    get(self, u, sha256=sha, strip_root=True, filename=fname)
                else:
                    get(self, u, sha256=sha, strip_root=True)
                return
            except Exception as e:
                self.output.info(f"source download failed from {u}: {e}")
                last_err = e
        raise last_err

    def generate(self):
        tc = CMakeToolchain(self)
        # upstream CMakeLists requires cmake 2.4-era policies; CMake >= 4
        # refuses without this opt-out
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # upstream ships no install rules: package the static lib (renamed,
        # the dot in libfacil.io.a breaks -l) and the header tree as-is
        pkg_lib = os.path.join(self.package_folder, "lib")
        os.makedirs(pkg_lib, exist_ok=True)
        copied = 0
        for root, _dirs, files in os.walk(self.build_folder):
            if "test" in root.lower() or "example" in root.lower():
                continue
            for fn in files:
                if fn.startswith("libfacil.io") and (fn.endswith(".a") or fn.endswith(".so")):
                    ext = ".a" if fn.endswith(".a") else ".so"
                    shutil.copy2(os.path.join(root, fn),
                                 os.path.join(pkg_lib, "libfacil" + ext))
                    copied += 1
        if copied == 0:
            raise ConanInvalidConfiguration("libfacil library not found after build")

        inc = os.path.join(self.package_folder, "include")
        os.makedirs(inc, exist_ok=True)
        n = 0
        for root, _dirs, files in os.walk(os.path.join(self.source_folder, "lib")):
            for fn in files:
                if fn.endswith(".h"):
                    rel = os.path.relpath(os.path.join(root, fn),
                                          os.path.join(self.source_folder, "lib"))
                    dst = os.path.join(inc, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(os.path.join(root, fn), dst)
                    n += 1
        if n == 0:
            raise ConanInvalidConfiguration("no headers found under lib/")

    def package_info(self):
        self.cpp_info.libs = ["facil"]
        self.cpp_info.includedirs = [
            "include", "include/facil", "include/facil/tls",
            "include/facil/fiobj", "include/facil/cli",
            "include/facil/http", "include/facil/http/parsers",
        ]
        self.cpp_info.system_libs = ["pthread", "m"]
