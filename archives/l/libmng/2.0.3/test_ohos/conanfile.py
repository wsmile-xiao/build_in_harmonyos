#!/usr/bin/env python3
# HarmonyOS-specific test runner — libmng/2.0.3
#
# Runs test_ohos.sh against the FINAL Conan package on OpenHarmony PC.
# libmng is static-only on OHOS: the registry zlib/1.3.1 package only
# ships a non-PIC static libz.a which cannot be linked into a shared
# libmng (see conanfile.py validate()). This validates the STATIC
# delivery, independent of test_package (library API): the package
# ships a valid AArch64 libmng.a, and a consumer binary links the real
# libmng.a plus the Conan dependencies (static libz.a — zlib must NOT
# leak in as a host libz.so NEEDED), without libturbojpeg false
# dependencies, RPATH entries or host paths, and really decodes the
# upstream fixture on the OHOS loader.
import base64
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv


class TestOHOS(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        # conan 2.x: tested_reference_str is the injected reference when
        # running `conan test <path> libmng/2.0.3`.
        self.requires(self.tested_reference_str)
        # static libmng.a does not embed its dependencies: the consumer
        # compiled by test_ohos.sh must link the real Conan zlib/jpeg/
        # lcms2 packages itself (never the host system libz.so).
        self.requires("zlib/1.3.1")
        self.requires("libjpeg-turbo/3.0.4")
        self.requires("lcms2/2.19")

    def generate(self):
        VirtualRunEnv(self).generate()  # conanrun env for loader paths

    def build(self):
        pass  # pure post-package verification, nothing to compile

    def test(self):
        if str(self.settings.os) != "OHOS":
            raise ConanException("test_ohos must run on the OHOS profile")
        tested = self.tested_reference_str
        pkg = self.dependencies[tested.split("#")[0]]
        pkg_root = Path(pkg.package_folder).resolve(strict=True)
        readelf = os.environ.get("OHOS_READELF", "readelf")
        script = str(Path(self.recipe_folder, "test_ohos.sh"))
        # Stage link/run-time deps into a private temp dir (never the
        # recipe folder or the package folder), and remove it on any exit
        # path — success, failure or exception — so no test output is
        # left behind.
        runtime_root = Path(tempfile.mkdtemp(prefix="libmng-test-ohos-runtime."))
        try:
            self._prepare_ohos_runtime(str(runtime_root), pkg_root)

            fixture_b64 = (
                Path(self.recipe_folder).parent
                / "test_package"
                / "fixtures"
                / "linux.mng.b64"
            )
            fixture = runtime_root / "linux.mng"
            raw = base64.b64decode(fixture_b64.read_bytes())
            expected_sha256 = (
                "59f1941cb335978a1c9e56c2845638f5"
                "dc2d6a9d87c59f89614683b1bff70553"
            )
            actual_sha256 = hashlib.sha256(raw).hexdigest()
            if actual_sha256 != expected_sha256:
                raise ConanException(
                    f"fixture SHA256 mismatch: "
                    f"{actual_sha256} != {expected_sha256}"
                )
            fixture.write_bytes(raw)
            self.output.info(
                f"OHOS fixture: {fixture} sha256={actual_sha256}")

            # LD_LIBRARY_PATH: staged dependency .so (OHOS loader);
            # CPATH: staged dependency headers (consumer compile);
            # LIBMNG_DEPS_DIR: staged .a/.so (consumer -L link line).
            # All three point at the private staging dir — no conan
            # cache paths and no host system libs are involved.
            self.run(
                f'LD_LIBRARY_PATH="{runtime_root}" '
                f'CPATH="{runtime_root}" '
                f'LIBMNG_DEPS_DIR="{runtime_root}" '
                f'LIBMNG_FIXTURE="{fixture}" '
                f'CC="{os.environ.get("OHOS_CC", "clang")}" '
                f'"bash" "{script}" "{pkg_root}" "{readelf}"',
                env="conanrun",
            )
        finally:
            shutil.rmtree(runtime_root, ignore_errors=True)

    def _prepare_ohos_runtime(self, runtime_root, pkg_root):
        # Stage every dependency library AND its public headers into one
        # flat directory: .so files are copied under every name of their
        # symlink chain (so both the linker's -l<name> and the loader's
        # SONAME search resolve, without creating HMDFS-unsafe symlinks),
        # .a archives (the Conan static libz.a) and headers serve the H5
        # consumer compile/link — the consumer never falls back to the
        # host system libz.so.
        root = Path(runtime_root)
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        for _, dep in self.dependencies.items():
            if getattr(dep, "build", False) or getattr(dep, "test", False):
                continue
            if not dep.package_folder or dep.package_folder == str(pkg_root):
                continue
            dep_root = Path(dep.package_folder).resolve(strict=True)
            for libdir in dep.cpp_info.libdirs:
                source_dir = Path(libdir)
                if not source_dir.is_absolute():
                    source_dir = Path(dep.package_folder, libdir)
                if not source_dir.is_dir():
                    continue
                for entry in sorted(source_dir.iterdir(), key=lambda i: i.name):
                    if not (entry.name.endswith(".a")
                            or entry.name.endswith(".so")
                            or ".so." in entry.name):
                        continue
                    try:
                        source = entry.resolve(strict=True)
                    except OSError:
                        continue  # broken symlink
                    if not source.is_file():
                        continue
                    shutil.copy2(source, root / entry.name)
            for incdir in dep.cpp_info.includedirs:
                inc_dir = Path(incdir)
                if not inc_dir.is_absolute():
                    inc_dir = Path(dep.package_folder, incdir)
                if not inc_dir.is_dir():
                    continue
                for entry in sorted(inc_dir.iterdir(), key=lambda i: i.name):
                    if entry.is_file():
                        shutil.copy2(entry, root / entry.name)
