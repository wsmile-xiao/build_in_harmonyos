#!/usr/bin/env python3
"""Conan recipe for Chipmunk2D 7.0.3 — 2D rigid-body physics library.

Chipmunk2D is a self-contained C99 physics engine: spatial index, rigid
bodies, joints and collision arbiters, with an optional block-based
iteration API (`cpSpaceEachBody_b` and friends).  The build is plain
CMake with **no external dependencies** — the only library the sources
touch besides libc is libm, which upstream's own CMake lists on the
shared target and which is part of OHOS's musl libc.

Upstream option matrix, as arranged here:

- `BUILD_DEMOS`/`INSTALL_DEMOS` are forced OFF: the demo suite requires
  OpenGL + GLFW, neither of which exists on this platform.
- `shared=False` ships the static archive only (`BUILD_STATIC=ON` with
  `INSTALL_STATIC=ON`, `BUILD_SHARED=OFF`); `shared=True` ships the
  versioned shared library only (`BUILD_SHARED=ON`, static off — the
  upstream CMake force-re-enables BUILD_STATIC whenever INSTALL_STATIC
  is set, so INSTALL_STATIC is what must stay OFF in that mode).

The block API compiles under OHOS's clang (`-fblocks` is force-enabled
by upstream for Clang) without a blocks runtime dependency: the library
only *receives* block pointers from callers and invokes them, it never
creates escaping block literals, so no `_Block_*` symbols are needed.
"""

import hashlib
import os
import ssl
import tarfile
import time
import urllib.request
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches


class ChipmunkConan(ConanFile):
    name = "chipmunk"
    version = "7.0.3"
    description = ("Chipmunk2D: a 2D rigid-body physics library "
                   "(integrated spatial index, joints, collision arbiters)")
    license = "MIT"
    homepage = "https://github.com/slembcke/Chipmunk2D"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"chipmunk is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        """Fetch and unpack the official tag tarball.

        Downloaded explicitly rather than with conan's get()/download()
        helpers: the CA trust store is resolved from conan's own certifi or
        $CONAN_HOME/cacert.pem with a hard failure when neither exists
        (the CI worker has none of the device-side bundle paths), and a
        failing download reports its URL and HTTP status instead of the
        FileNotFoundError that conan's helper raises for a transient TLS
        failure.
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "chipmunk-source.tar.gz")
        # The CI pre-download step rewrites conandata's url into a list of
        # candidates ([mirror, official]); accept either shape and try the
        # candidates in order.
        url = source["url"]
        self._fetch(url if isinstance(url, list) else [url],
                    archive, source["sha256"])
        with tarfile.open(archive, "r:gz") as tar:
            self._extract_flat(tar, Path(self.source_folder))
        archive.unlink()

    def generate(self):
        toolchain = CMakeToolchain(self)
        shared = "ON" if self.options.shared else "OFF"
        static = "OFF" if self.options.shared else "ON"
        toolchain.variables["BUILD_SHARED"] = shared
        toolchain.variables["BUILD_STATIC"] = static
        # INSTALL_STATIC=ON would make upstream force BUILD_STATIC back on
        # (`if(BUILD_DEMOS OR INSTALL_STATIC) set(BUILD_STATIC ON FORCE)`),
        # so the shared mode must keep INSTALL_STATIC off as well.
        toolchain.variables["INSTALL_STATIC"] = static
        # The demo suite needs OpenGL + GLFW; neither exists on OHOS.
        toolchain.variables["BUILD_DEMOS"] = "OFF"
        toolchain.variables["INSTALL_DEMOS"] = "OFF"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        # Explicitly neutralize LD_LIBRARY_PATH: some CI workers carry an
        # ambient LD whose /usr/local/lib holds an incompatible
        # libxml2.so.16, and the SDK's lld (which links libxml2 for
        # itself) then fails every link with "Error relocating ...:
        # xml…: symbol not found" (CI-021 build #48068).  An explicit
        # empty value shields the compiler chain on every worker.
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "chipmunk")
        self.cpp_info.set_property("cmake_target_name", "chipmunk::chipmunk")
        self.cpp_info.set_property("pkg_config_name", "chipmunk")
        self.cpp_info.libs = ["chipmunk"]
        # Upstream links `m` on the shared target; static consumers need it
        # on their own link line (sin/cos/fmod/sqrt across the engine).
        self.cpp_info.system_libs = ["m"]

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
        """Download the first candidate URL that verifies against sha256.

        `url` is one URL or a candidate list (the CI pre-download step
        prepends mirrors); every candidate gets the full attempt budget.
        """
        urls = url if isinstance(url, list) else [url]
        last = None
        for candidate in urls:
            try:
                self._fetch_one(candidate, destination, sha256, attempts)
                return
            except Exception as error:  # noqa: BLE001 - try next candidate
                last = error
                self.output.info(f"candidate {candidate} failed: {error}")
        raise ConanException(f"could not download {urls}: {last}")

    def _fetch_one(self, url, destination, sha256, attempts=3):
        destination = Path(destination)
        if url.startswith("file:"):
            from urllib.parse import urlparse
            source = Path(urlparse(url).path)
            data = source.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest != sha256:
                raise ConanException(
                    f"sha256 mismatch for {url}: expected {sha256}, got {digest}")
            destination.write_bytes(data)
            return
        last = None
        for attempt in range(1, attempts + 1):
            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "conan-recipe/1.0"})
                with urllib.request.urlopen(
                        request, timeout=60,
                        context=ssl.create_default_context(
                            cafile=self._ca_bundle())) as response:
                    data = response.read()
                digest = hashlib.sha256(data).hexdigest()
                if digest != sha256:
                    raise ConanException(
                        f"sha256 mismatch for {url}: expected {sha256}, "
                        f"got {digest}")
                staging = destination.with_name(destination.name + ".part")
                staging.write_bytes(data)
                os.replace(staging, destination)
                return
            except Exception as error:  # noqa: BLE001 - retried, then raised
                last = error
                self.output.info(
                    f"download attempt {attempt}/{attempts} failed: {error}")
                time.sleep(2 * attempt)
        raise ConanException(f"could not download {url}: {last}")


    def _extract_flat(self, tar, destination):
        """Extract a tarball that has a single top-level directory.

        The GitHub tag tarball unpacks to `Chipmunk2D-Chipmunk-7.0.3/`;
        the recipe expects the tree directly in the source folder, so the
        top-level component is stripped the same way `get()` would.
        """
        members = tar.getmembers()
        roots = {member.name.split("/", 1)[0] for member in members}
        strip = 0 if len(roots) > 1 else len(roots.pop()) + 1
        for member in members:
            name = member.name[strip:] if strip else member.name
            if not name or name.endswith("/"):
                continue
            target = Path(destination, name)
            if member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, \
                        open(target, "wb") as sink:
                    sink.write(source.read())
            elif member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                self.output.info(f"skipping non-regular member {member.name}")
