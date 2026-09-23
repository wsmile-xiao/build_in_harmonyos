#!/usr/bin/env python3
"""Conan recipe for ZArchive 0.1.2 — zstd-compressed file archive library.

ZArchive provides `ZArchiveWriter` / `ZArchiveReader`: a container format
that stores many files in one zstd-compressed archive with a name table and
a file tree, plus random access into individual files (`ReadFromFile`).
The package ships both the static/shared library and the `zarchive`
command-line tool (pack a directory / extract an archive).

Build system: CMake (>= 3.15), `target_compile_features(zarchive PUBLIC
cxx_std_20)`.

Dependency: zstd, found through upstream's own `cmake/Findzstd.cmake`
(`find_package(zstd CONFIG QUIET)`, then pkg-config as a fallback).  The
device has no pkg-config, so the CONFIG path must succeed — that is what
two things below arrange: Conan's zstd package exports `zstd::libzstd`
(not the `zstd::zstd` / `zstd::libzstd_{static,shared}` names upstream's
find module normalises from), hence patch 0001; and the CMakeDeps config
files live in the generators folder, which the OHOS cross-mode find root
has to include or `find_package` never sees them.

Upstream ships no test suite (no tests/ or *test* sources, no CTest
registration), so the consumer test in test_package/ carries the real
verification: a full pack -> read -> extract round trip through both the
library API and the installed CLI.
"""

import hashlib
import os
import shlex
import ssl
import tarfile
import time
import urllib.request
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches


class ZarchiveConan(ConanFile):
    name = "zarchive"
    version = "0.1.2"
    description = ("Library for creating and reading zstd-compressed file "
                   "archives, with random access into archived files")
    license = "MIT"
    homepage = "https://github.com/Exzap/ZArchive"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zstd/1.5.7.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"zarchive is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        """Fetch and unpack the official tag tarball.

        Downloaded explicitly rather than with conan's get()/download()
        helpers: the CA trust store is resolved from conan's own certifi or
        $CONAN_HOME/cacert.pem with a hard failure when neither exists
        (AGENTS.md §1.2, the CI worker has none of the device-side bundle
        paths), and a failing download reports its URL and HTTP status
        instead of the FileNotFoundError that conan's helper raises for a
        transient TLS failure.
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "zarchive-source.tar.gz")
        self._fetch(source["url"], archive, source["sha256"])
        with tarfile.open(archive, "r:gz") as tar:
            self._extract_flat(tar, Path(self.source_folder))
        archive.unlink()

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.shared else "OFF")
        # Upstream asks for C++20 on the zarchive target itself; keep the
        # profile's cppstd as the project-wide default and let the target
        # feature raise it for that target (CMake takes the maximum).
        # OHOS conan_toolchain runs in cross mode with MODE_PACKAGE=ONLY,
        # so find_package(zstd CONFIG) only looks inside CMAKE_FIND_ROOT_PATH
        # — the CMakeDeps config files must be reachable from there or
        # upstream's Findzstd.cmake silently falls through to its
        # pkg-config branch, which cannot work on this device.
        toolchain.variables["CMAKE_FIND_ROOT_PATH"] = [self.generators_folder]
        toolchain.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        toolchain.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "zarchive")
        self.cpp_info.set_property("cmake_target_name", "ZArchive::zarchive")
        self.cpp_info.set_property("pkg_config_name", "zarchive")
        self.cpp_info.libs = ["zarchive"]
        self.cpp_info.requires = ["zstd::zstd"]

    # ── download helpers ────────────────────────────────────────────────

    def _ca_bundle(self):
        candidates = []
        try:
            import certifi
            candidates.append(certifi.where())
        except ImportError:
            pass
        conan_home = os.getenv("CONAN_HOME") or os.path.join(
            os.path.expanduser("~"), ".conan2")
        candidates.append(os.path.join(conan_home, "cacert.pem"))
        candidates.append(os.getenv("SSL_CERT_FILE") or "")
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanException(
            "no CA bundle found for the source download: looked for certifi's "
            "cacert, $CONAN_HOME/cacert.pem and $SSL_CERT_FILE"
        )

    def _fetch(self, url, destination, sha256, attempts=3):
        destination = Path(destination)
        staging = destination.with_name(destination.name + ".part")
        if url.startswith("file:"):
            from urllib.parse import urlparse
            from urllib.request import url2pathname
            import shutil
            shutil.copyfile(url2pathname(urlparse(url).path), staging)
        else:
            context = ssl.create_default_context(cafile=self._ca_bundle())
            last = None
            for attempt in range(1, attempts + 1):
                try:
                    request = urllib.request.Request(
                        url, headers={"User-Agent": "conan"})
                    with urllib.request.urlopen(request, timeout=120,
                                                context=context) as response:
                        payload = response.read()
                        status = response.status
                    staging.write_bytes(payload)
                    self.output.info(
                        f"downloaded {len(payload)} bytes (HTTP {status}) "
                        f"from {url}")
                    break
                except Exception as error:  # noqa: BLE001 - reported verbatim
                    last = error
                    self.output.warning(
                        f"download attempt {attempt}/{attempts} failed for "
                        f"{url}: {type(error).__name__}: {error}")
                    if staging.exists():
                        staging.unlink()
                    if attempt < attempts:
                        time.sleep(5)
            else:
                raise ConanException(f"could not download {url}: {last}")

        digest = hashlib.sha256(staging.read_bytes()).hexdigest()
        if digest != sha256:
            staging.unlink()
            raise ConanException(
                f"sha256 mismatch for {url}: expected {sha256}, got {digest}")
        os.replace(staging, destination)

    @staticmethod
    def _extract_flat(tar, destination):
        """Extract a GitHub tag tarball, dropping its single root folder."""
        members = tar.getmembers()
        roots = {m.name.split("/")[0] for m in members if m.name}
        if len(roots) != 1:
            raise ConanException(
                f"expected a single root directory in the archive, got {roots}")
        root = roots.pop() + "/"
        for member in members:
            if not member.name.startswith(root):
                continue
            member.name = member.name[len(root):]
            if member.name:
                tar.extract(member, destination)
