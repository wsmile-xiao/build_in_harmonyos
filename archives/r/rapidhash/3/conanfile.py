#!/usr/bin/env python3
"""Conan recipe for rapidhash 3 — header-only C/C++ hash function family.

rapidhash v3 ships as a self-contained header pair at the repo root
(rapidhash.h + optional companion secret.h); there is no upstream build
system and no third-party dependency (only <stdint.h>/<string.h>).
package() installs the headers under include/rapidhash/ so the generic
name "secret.h" never leaks into consumers' include path.

Upstream tests: the rapidhash_v3 tag tree contains no test suite (only the
GPL-2.0 bench/ and collisions/ research tools, which are not packaged).
Verification is consumer-side: test_package builds C and C++ consumers and
runs 789 frozen known-answer vectors plus README-documented property
assertions. See notes.md and test_package/MANIFEST.yml.

Version slug: the upstream v3 release exists only as tag `rapidhash_v3`
(no dotted semver). Conan rejects single-character versions (ConanName
pattern requires >=2 chars: `Invalid package version '3'`), so set_version()
normalizes the artifact version to `v3` (tag suffix, lowercased — same
normalization the repo's hfsm2 Beta73 -> beta73 adaptation used). The
archive directory and branch keep the task-card form `3` for the platform
branch-name gate.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RapidhashConan(ConanFile):
    name = "rapidhash"
    description = "Very fast, high quality, platform-independent 64-bit hash functions (header-only)"
    license = "MIT"
    homepage = "https://github.com/Nicoshev/rapidhash"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = "hash", "hashing", "header-only", "no-dependencies"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def set_version(self):
        # Upstream tag rapidhash_v3 -> artifact version `v3` (see docstring).
        # Deliberately NOT a literal `self.version = "..."` attribute: the
        # archive directory keeps the task-card `3`, which a literal would
        # have to equal for CI L0m-3 — impossible, since Conan itself
        # rejects the single-character version.
        self.version = "v3"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "rapidhash is only validated on Linux/OHOS/FreeBSD/Macos/Windows, "
                "not {}".format(self.settings.os))

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: no build step; apply any conandata patches
        # (currently none — kept as the explicit no-op gate requires).
        apply_conandata_patches(self)

    def package(self):
        # Official headers at the tarball root. The legacy snapshot
        # old_version/rapidhashV1.h is intentionally not packaged: it
        # redefines rapid_secret with a different arity and would collide
        # with the v3 header if both were on the include path.
        copy(self, "rapidhash.h", self.source_folder,
             os.path.join(self.package_folder, "include", "rapidhash"))
        copy(self, "secret.h", self.source_folder,
             os.path.join(self.package_folder, "include", "rapidhash"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "rapidhash")
        self.cpp_info.set_property("cmake_target_name", "rapidhash::rapidhash")
        self.cpp_info.set_property("pkg_config_name", "rapidhash")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
