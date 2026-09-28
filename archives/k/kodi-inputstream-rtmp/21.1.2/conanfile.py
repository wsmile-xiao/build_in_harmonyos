#!/usr/bin/env python3
"""Conan recipe for kodi-inputstream-rtmp 21.1.2 — Kodi RTMP input stream add-on.

Upstream: https://github.com/xbmc/inputstream.rtmp (tag 21.1.2-Omega,
release commit fb2745b7768c9babd922dbaf0d811968814306b9).

inputstream.rtmp is a Kodi binary add-on that implements RTMP input streams.
The product is a single shared module (upstream name inputstream.rtmp.so,
packaged here with the standard lib prefix as libinputstream.rtmp.so) built
from src/RTMPStream.cpp + src/timer/Timer.cpp, linking librtmp (static, with
OpenSSL + zlib) and using the Kodi C++ add-on headers.

The upstream CMakeLists.txt requires the Kodi build system:
find_package(Kodi REQUIRED) provides build_addon() and KODI_INCLUDE_DIR, and
the in-tree FindRTMP.cmake resolves librtmp through pkg-config. The ohpcd
registry has no Kodi build system, so this recipe:

- ships its own CMake entry point under recipe-cmake/ (build_script_folder),
  building the unmodified upstream sources against the Conan CMakeDeps
  targets (kodi-platform recipe-cmake precedent);
- vendors the kodi-dev-kit headers it needs under
  kodi-dev-kit/kodi (verbatim kodi/ subtree from xbmc 21.3-Omega,
  sha256 a60afcb556e4a00cb19fc35b7e77758107c9a8096c6ce9b66af5f92396be31aa,
  xbmc/addons/kodi-dev-kit/include/kodi; the include/ path segment is
  normalized away to keep the vendored tree trackable — the repo .gitignore
  excludes archives/**/include/). API compatibility verified against
  the add-on source: all overridden virtuals (Open/Close/GetCapabilities/
  ReadStream/PosTime/GetTime/GetTotalTime) and CAddonBase::CreateInstance
  signatures match the 21.3-Omega headers, whose inputstream instance API
  version (ADDON_INSTANCE_VERSION_INPUTSTREAM) is 3.3.0. BUILD_KODI_ADDON is
  intentionally NOT defined (it is only consulted by kodi/versions.h to trim
  the reported-API-version switch; leaving it undefined keeps all version
  branches compiled in, which test_package exercises).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class KodiInputstreamRtmpConan(ConanFile):
    name = "kodi-inputstream-rtmp"
    version = "21.1.2"
    description = "Kodi input stream add-on for RTMP/RTMPS/RTMPE protocols (inputstream.rtmp)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/xbmc/inputstream.rtmp"
    url = "https://github.com/xbmc/inputstream.rtmp"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # The add-on is a dlopen() module for the Kodi host; a static archive has
    # no consumer, so shared is the default.
    default_options = {"shared": True, "fPIC": True}

    generators = "CMakeDeps"
    exports_sources = "recipe-cmake/*", "kodi-dev-kit/*"

    def requirements(self):
        # Published on the ohpcd registry (probed 2026-09-22, same probe as
        # CI L0i). zlib is deliberately NOT a direct requirement: the conan
        # zlib/1.3.1 package is a static non-PIC archive (system same-name
        # library, R26) which cannot be linked into a shared module; the
        # add-on links the OHOS system libz.so instead (see recipe-cmake/
        # CMakeLists.txt). librtmp keeps zlib in the conan graph transitively.
        self.requires("librtmp/2.4_git20190330")
        self.requires("openssl/3.5.6")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # exports_sources are merged into the source folder BEFORE source()
        # runs, so the tarball extraction would clobber same-named files.
        # recipe-cmake/ and kodi-dev-kit/ are subfolders the tarball does not
        # contain; re-copy them from the recipe folder after extraction
        # (kodi-platform precedent).
        copy(self, "*", src=os.path.join(self.recipe_folder, "recipe-cmake"),
             dst=os.path.join(self.source_folder, "recipe-cmake"))
        copy(self, "*", src=os.path.join(self.recipe_folder, "kodi-dev-kit"),
             dst=os.path.join(self.source_folder, "kodi-dev-kit"))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Upstream code #includes <librtmp/rtmp.h> / <librtmp/log.h>, but the
        # librtmp package declares include/librtmp as its include dir (its own
        # headers resolve each other by plain names), so consumers need the
        # parent directory to use the upstream-style namespaced includes.
        rtmp = self.dependencies["librtmp"]
        rtmp_include_dir = os.path.join(rtmp.package_folder, rtmp.cpp_info.includedirs[0])
        tc.variables["RTMP_INCLUDE_PARENT"] = os.path.dirname(rtmp_include_dir)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="recipe-cmake")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["inputstream.rtmp"]
        # No public headers are installed (the add-on module exposes only its
        # ADDONCREATOR C entry points; Kodi add-on headers are vendored by the
        # consumer recipe when needed) — drop the default include dir so the
        # CMakeDeps target carries no non-existent path.
        self.cpp_info.includedirs = []
        # Self-contained module: librtmp and OpenSSL are PIC static archives
        # baked into the .so at build time; its remaining undefined symbols
        # (zlib) resolve against the OHOS system libz.so.1 at runtime.
        # Consumers need no extra link requirements.
        self.cpp_info.requires = []
