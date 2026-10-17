#!/usr/bin/env python3
"""Conan recipe for kodi-pvr-iptvsimple 21.11.0 — Kodi "IPTV Simple" PVR client.

Upstream: https://github.com/kodi-pvr/pvr.iptvsimple (tag 21.11.0-Omega,
release commit fe95755432cd16acfdadac2926780bac088179ac).

pvr.iptvsimple is a Kodi binary add-on implementing an IPTV PVR backend
(M3U playlists, EPG, channels/groups/providers). The product is a single
shared module (upstream name pvr.iptvsimple.so, declared in the add-on's
addon.xml) built from the upstream src/ tree, linking the static Conan
pugixml and lzma archives plus the OHOS system libz, and using the Kodi C++
add-on headers.

The upstream CMakeLists.txt requires the Kodi build system
(find_package(Kodi REQUIRED) provides build_addon()/addon_version() and
KODI_INCLUDE_DIR; the in-tree Findpugixml/Findlzma modules go through
pkg-config). The ohpcd registry has no Kodi build system, so this recipe:

- ships its own CMake entry point under recipe-cmake/ (build_script_folder),
  building the unmodified upstream sources against the Conan CMakeDeps
  targets (kodi-inputstream-rtmp / kodi-addon-screensaver precedents);
- vendors the kodi-dev-kit headers it needs under kodi-dev-kit/kodi
  (verbatim kodi/ subtree from xbmc 21.3-Omega, sha256
  a60afcb556e4a00cb19fc35b7e77758107c9a8096c6ce9b66af5f92396be31aa,
  xbmc/addons/kodi-dev-kit/include/kodi; the include/ path segment is
  normalized away to keep the vendored tree trackable — the repo .gitignore
  excludes archives/**/include/). PVR instance API compatibility verified
  against the add-on source: ADDON_INSTANCE_VERSION_PVR is 8.3.0 (min 8.2.0)
  in these headers, matching the Omega (21.x) PVR API the 21.11.0 add-on is
  written against, and every CInstancePVRClient override resolves.
  BUILD_KODI_ADDON is intentionally NOT defined (it is only consulted by
  kodi/versions.h to trim the reported-API-version switch; leaving it
  undefined keeps all version branches compiled in, which test_package
  exercises).

zlib is deliberately NOT a Conan requirement: the conan zlib/1.3.1 package is
a static non-PIC archive (system same-name library, R26) which cannot be
linked into a shared module; the add-on links the OHOS system libz.so
instead (see recipe-cmake/CMakeLists.txt).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class KodiPvrIptvsimpleConan(ConanFile):
    name = "kodi-pvr-iptvsimple"
    version = "21.11.0"
    description = "Kodi IPTV Simple PVR client add-on (pvr.iptvsimple)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/kodi-pvr/pvr.iptvsimple"
    url = "https://github.com/kodi-pvr/pvr.iptvsimple"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # The add-on is a dlopen() module for the Kodi host; a static archive has
    # no consumer, so shared is the default.
    default_options = {"shared": True, "fPIC": True}

    generators = "CMakeDeps"

    def export_sources(self):
        # Own CMake entry point (replicates the kodi-addon-dev build_addon()
        # semantics) and the vendored Kodi add-on SDK headers; both are merged
        # into the source folder before source() runs (method form keeps the
        # recipe-cmake/ and kodi-dev-kit/ path segments).
        copy(self, "recipe-cmake/*", src=self.recipe_folder,
             dst=self.export_folder)
        copy(self, "kodi-dev-kit/*", src=self.recipe_folder,
             dst=self.export_folder)

    def requirements(self):
        # W0 checked (conan download --only-recipe against the ohpcd remote):
        # both dependencies are published on the registry.
        # pugixml: upstream pins 1.14 (depends/common/pugixml/pugixml.txt);
        # the registry carries 1.15-r0 (same 1.x series, DOM API used by the
        # add-on is source-compatible). Deviation documented in notes.md.
        self.requires("pugixml/1.15-r0")
        # lzma (XZ Utils): upstream pins xz-utils 5.4.3
        # (depends/common/xz-utils/xz-utils.txt); the registry carries
        # lzma/5.6.2 (same liblzma API, static PIC archive).
        self.requires("lzma/5.6.2")

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
        # Standard upstream-patch hook: conandata.yml patches is {} (upstream
        # sources are consumed unmodified), so this is a no-op today — but it
        # keeps the recipe canonical for any future patch.
        apply_conandata_patches(self)
        # export_sources are merged into the source folder BEFORE source()
        # runs, so the tarball extraction would clobber same-named files.
        # recipe-cmake/ and kodi-dev-kit/ are subfolders the tarball does not
        # contain; re-copy them from the recipe folder after extraction
        # (kodi-inputstream-rtmp precedent).
        copy(self, "*", src=os.path.join(self.recipe_folder, "recipe-cmake"),
             dst=os.path.join(self.source_folder, "recipe-cmake"))
        copy(self, "*", src=os.path.join(self.recipe_folder, "kodi-dev-kit"),
             dst=os.path.join(self.source_folder, "kodi-dev-kit"))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["ADDON_SRC_DIR"] = self.source_folder
        tc.variables["KODI_DEV_KIT_INCLUDE"] = os.path.join(
            self.source_folder, "kodi-dev-kit")
        # Version string from the upstream addon.xml.in (addon_version()).
        tc.variables["IPTV_VERSION"] = self.version
        # Do not embed any DT_RUNPATH. CMake otherwise records the build-tree
        # directories of the linked Conan archives and then rewrites the ELF
        # during "cmake --install" (zeroing the RUNPATH string in place); the
        # OHOS loader rejects a module whose file no longer matches the
        # integrity value recorded at link time ("Error loading shared library
        # ...: Permission denied" from dlopen). The module needs no rpath (its
        # only dynamic dependencies are the system libz.so and libc++), so the
        # rpath is skipped entirely and the installed file stays byte-identical
        # to the linker output.
        tc.variables["CMAKE_SKIP_RPATH"] = True
        # E092: CMake has no HarmonyOS platform module, use Linux
        # (kodi-platform/20250416 precedent).
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
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
        # The product is a Kodi-host-loaded module (pvr.iptvsimple.so, declared
        # in the add-on's addon.xml). Nothing links against it — consumers
        # deploy the module into the Kodi add-on tree. The module directory is
        # exposed so tooling can locate it.
        self.cpp_info.libdirs = ["lib"]
        # No public headers are installed (the module exposes only its
        # ADDONCREATOR C entry points; Kodi add-on headers are vendored by the
        # consumer recipe when needed) — drop the default include dir.
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "kodi-pvr-iptvsimple")
        self.cpp_info.set_property("cmake_target_name",
                                   "kodi-pvr-iptvsimple::kodi-pvr-iptvsimple")
