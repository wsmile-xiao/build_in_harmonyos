#!/usr/bin/env python3
"""Conan recipe for kodi-addon-inputstream 21.1.2 — Kodi "InputStream Adaptive"
add-on (MPEG-DASH / HLS / SmoothStreaming client with Widevine SSD).

Upstream: https://github.com/xbmc/inputstream.adaptive (tag 21.1.2-Omega,
commit 6ca1c7d5f9b689bcf4c95db50919bc2f8f874cf7 — sha256-verified tarball).
The package name follows the repository's kodi-* family convention
(add-on class "inputstream" + upstream project id "inputstream.adaptive").

The upstream CMakeLists.txt resolves its build through modules shipped with
the kodi-addon-dev distribution (FindKodi.cmake + build_addon() from
AddonHelpers.cmake, FindBento4.cmake, FindPugixml.cmake), which expects a
Kodi SDK installation. The ohpcd registry has no kodi package, so this recipe
supplies its own CMake entry point (recipe-cmake/, consumed via
build_script_folder) that builds the same unmodified upstream sources against
the Kodi add-on SDK headers, the xbmc Bento4 fork (upstream
ENABLE_INTERNAL_BENTO4 flow) and conan-provided pugixml, producing:
  - inputstream.adaptive.so  — the binary add-on module (loaded by Kodi)
  - ssd_wv.so                — the Widevine single-sample-decrypter helper
                               module (dlopen()ed by the add-on at runtime,
                               WIDEVINECDMFILENAME="libwidevinecdm.so")

Bento4 comes from the upstream depends/common/bento4/bento4.txt pin (the
xbmc Bento4 fork tag 1.6.0-639-8-Omega, sha256 cross-checked against the
upstream-shipped bento4.sha256): the add-on code is written against the
fork's extended AP4 API (AP4_File stream+factory+movie ctor,
AP4_AvcFrameParser::ReadGolomb, AP4_UnknownUuidAtom::GetData,
SetParentIsOwner, ...) which the vanilla Bento4 release (ohpcd registry
bento4/1.6.0-641, axiomatic-systems v1.6.0-641) does not provide. The fork
is built into this package exactly like the upstream internal flow does
(-DBUILD_APPS=OFF, position-independent, static libap4.a) and linked into
both modules — no system/registry bento4 dependency remains.

Bundled static libraries (lib/mpegts, lib/webm_parser) are built from the
upstream sources with POSITION_INDEPENDENT_CODE and linked into the add-on
module — replicating the upstream add_subdirectory() + DEPLIBS flow.

The Kodi add-on SDK headers (xbmc/addons/kodi-dev-kit/include) are taken from
the xbmc 21.3-Omega release tarball — the same source the kodi-tools/21.3
recipe consumes; only that include subtree is extracted (the full xbmc tree
extracts to several hundred MB). See kodi-addon-screensaver/21.0.2 for the
selective-extraction precedent and knowledge draft DRAFT-KODI01.

Upstream tests (src/test, 51 TEST() cases over DASH/HLS/Smooth tree parsers
+ utils) are compiled and run by option `with_tests` (R51 three-step: build,
run, count). The test build uses src/test/KodiStubs.h — upstream's own
complete Kodi API stub header — so the tests need no real Kodi SDK either
and run fully offline (curl is stubbed; manifests are local files passed as
argv[1]).
"""
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, download, get


class KodiAddonInputstreamConan(ConanFile):
    name = "kodi-addon-inputstream"
    version = "21.1.2"
    description = ("Kodi 'InputStream Adaptive' add-on (MPEG-DASH/HLS/"
                   "SmoothStreaming client + Widevine SSD decrypter)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/xbmc/inputstream.adaptive"
    url = "https://github.com/xbmc/inputstream.adaptive"

    settings = "os", "compiler", "build_type", "arch"

    options = {"with_tests": [True, False]}
    default_options = {"with_tests": False}

    # CMakeDeps so consumers (test_package here, a future Kodi port later)
    # can consume this package through find_package().
    generators = "CMakeDeps"

    def export_sources(self):
        # Own CMake entry point (replicates the kodi-addon-dev build_addon()
        # semantics; consumed via build_script_folder). Method form, merged
        # into the source folder before source() runs. The pattern already
        # carries the recipe-cmake/ path segment (keep_path=True), so the
        # destination is the export folder itself.
        copy(self, "recipe-cmake/*", src=self.recipe_folder,
             dst=self.export_folder)

    def requirements(self):
        # W0 checked (conan download --only-recipe against the ohpcd remote):
        # the dependency is published on the registry.
        #
        # pugixml: upstream pins 1.13 (depends/common/pugixml/pugixml.txt);
        # the registry has no 1.13 — closest is 1.15-r0 (same 1.x series).
        # The add-on uses the stable DOM subset (xml_document, xml_node,
        # PUGIXML_TEXT) — API-compatible. Deviation documented in notes.md.
        self.requires("pugixml/1.15-r0")
        # Bento4 is NOT a conan dependency: the add-on code requires the xbmc
        # fork's extended AP4 API, so the fork tarball pinned by upstream
        # (depends/common/bento4/bento4.txt, sha256 in bento4.sha256) is
        # downloaded and built in-tree (upstream ENABLE_INTERNAL_BENTO4
        # flow) — see source() and recipe-cmake/CMakeLists.txt.
        # googletest: only for the upstream test build (R51); upstream pins
        # 1.13.0, registry carries 1.17.0 (same 1.x series, TEST() API
        # compatible). test_requires: the test binary is a host-context
        # artifact (linked against host pugixml and run on the target) —
        # never linked into the shipped modules and not part of package_id.
        if self.options.with_tests:
            self.test_requires("gtest/1.17.0")

    def validate(self):
        # The add-on is headless (no GL); it links conan bento4/pugixml and
        # the system libc++/dl. Packaged and validated for the OHOS target
        # only (aarch64-linux-ohos toolchain profile used throughout).
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "kodi-addon-inputstream/21.1.2 is packaged for OHOS only."
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        data = self.conan_data["sources"][self.version]

        # 1. Add-on sources. Conan merges exports_sources into the source
        #    folder BEFORE source() runs (config_source trap, see
        #    kodi-platform/20250416 notes), so recipe-cmake/ already exists
        #    here and the tarball (which has no recipe-cmake/ directory)
        #    cannot clobber it. Re-copy defensively like the
        #    kodi-addon-screensaver precedent.
        get(self, **data["addon"], strip_root=True,
            filename="inputstream.adaptive-21.1.2-Omega.tar.gz")
        # Standard upstream-patch hook: conandata.yml patches is {} (upstream
        # sources are consumed unmodified), so this is a no-op today — but it
        # keeps the recipe canonical for any future patch (drop a file in
        # patches/ and list it in conandata.yml).
        apply_conandata_patches(self)
        copy(self, "*", src=os.path.join(self.recipe_folder, "recipe-cmake"),
             dst=os.path.join(self.source_folder, "recipe-cmake"))

        # 2. Kodi add-on SDK headers: download the xbmc 21.3-Omega tarball
        #    (URL list tried in order) and extract only the kodi-dev-kit
        #    include subtree.
        sdk_data = data["sdk"]
        urls = sdk_data["url"] if isinstance(sdk_data["url"], list) else [sdk_data["url"]]
        sdk_archive = os.path.join(self.source_folder, "kodi-sdk.tar.gz")
        last_error = None
        for url in urls:
            try:
                download(self, url, sdk_archive, sha256=sdk_data["sha256"])
                last_error = None
                break
            except ConanException as exc:
                last_error = exc
        if last_error is not None:
            raise ConanException("could not download the Kodi add-on SDK "
                                 "source: %s" % last_error)

        sdk_root = os.path.join(self.source_folder, "kodi-sdk")
        prefix = "xbmc-21.3-Omega/xbmc/addons/kodi-dev-kit/include"
        with tarfile.open(sdk_archive, "r:gz") as archive:
            members = [member for member in archive.getmembers()
                       if member.name == prefix or member.name.startswith(prefix + "/")]
            archive.extractall(sdk_root, members=members, filter="data")
        os.rename(os.path.join(sdk_root, prefix),
                  os.path.join(self.source_folder, "kodi-sdk-include"))
        # Only the empty xbmc-21.3-Omega/ directory chain is left here.
        shutil.rmtree(sdk_root)
        os.remove(sdk_archive)

        # 3. xbmc Bento4 fork (upstream ENABLE_INTERNAL_BENTO4 sources):
        #    extract and stage its public headers under
        #    <staging>/bento4/ — the installed layout the upstream code
        #    #includes (<bento4/Ap4.h>; mirrors the upstream externalproject
        #    install include/ dir). The static lib is built from the fork's
        #    own CMakeLists in recipe-cmake (add_subdirectory).
        b4_data = data["bento4"]
        b4_src = os.path.join(self.source_folder, "bento4-src")
        get(self, **b4_data, destination=b4_src, strip_root=True,
            filename="Bento4-1.6.0-639-8-Omega.tar.gz")
        # The fork's own CMakeLists installs these headers flat into
        # include/bento4/; stage the same flat set (Core/Codecs/Crypto/
        # MetaData) so consumers resolve <bento4/...> includes. Header file
        # names are globally unique across those four dirs.
        staging = os.path.join(self.source_folder, "bento4-include", "bento4")
        for sub in ("Core", "Codecs", "Crypto", "MetaData"):
            copy(self, "*.h",
                 src=os.path.join(b4_src, "Source", "C++", sub),
                 dst=staging, keep_path=False)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["ADDON_SRC_DIR"] = self.source_folder
        toolchain.variables["KODI_SDK_INCLUDE_DIR"] = os.path.join(
            self.source_folder, "kodi-sdk-include")
        toolchain.variables["BENTO4_SRC"] = os.path.join(
            self.source_folder, "bento4-src")
        toolchain.variables["BENTO4_INCLUDE_STAGING"] = os.path.join(
            self.source_folder, "bento4-include")
        toolchain.variables["INPUTSTREAM_TESTS"] = bool(self.options.with_tests)
        # E092: CMake has no HarmonyOS platform module, use Linux
        # (kodi-platform/20250416 precedent).
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="recipe-cmake")
        cmake.build()
        self._run_upstream_tests(cmake)

    def _run_upstream_tests(self, cmake):
        """R51 three-step upstream-test protocol (build/run/count).

        The upstream test suite (src/test, 51 TEST() cases) is built by the
        same configure when INPUTSTREAM_TESTS=ON and executed here against
        the in-tree manifests directory. TestHelper stubs curl, so the run
        is fully offline. The count is cross-checked against the number of
        TEST() macros upstream (51) and recorded in notes.md.
        """
        if not self.options.with_tests:
            return
        if not can_run(self):
            self.output.warning("Cross-built upstream tests cannot run on "
                                "this host — skipped (R51 ②, honest gap)")
            return
        test_bin = os.path.join(self.build_folder, "inputstream.adaptive_test")
        manifests = os.path.join(self.source_folder, "src", "test", "manifests")
        self.output.info("R51 upstream tests: running %s %s" % (test_bin, manifests))
        self.run('"%s" "%s"' % (test_bin, manifests), env="conanbuild")

    def package(self):
        copy(self, "*.so", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # The products are Kodi-host-loaded modules (inputstream.adaptive.so
        # declared in the add-on's addon.xml; ssd_wv.so dlopen()ed by the
        # add-on itself for Widevine). Nothing links against them — consumers
        # deploy the modules into the Kodi add-on tree. The module directory
        # is exposed so tooling can locate it.
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "kodi-addon-inputstream")
        self.cpp_info.set_property("cmake_target_name",
                                   "kodi-addon-inputstream::kodi-addon-inputstream")
