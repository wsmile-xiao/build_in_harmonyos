#!/usr/bin/env python3
# HarmonyOS-specific test runner — msdfgen/1.13
#
# Runs test_ohos.sh against the FINAL Conan package on OpenHarmony PC.
# Independent of test_package (library API): this validates OHOS delivery
# — ELF64 Little-Endian AArch64, versioned SONAME, NEEDED closure,
# .codesign sections, absence of host paths, and real CLI MSDF generation
# with structural checks on the output (dimensions, hex token domain,
# inside/outside pixel relation). No fonts or images are involved: the
# CLI input is the auditable -defineshape text vector.
import os
import shutil
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv


class TestOHOSShared(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        tested = getattr(self, "tested_reference", None)
        if tested is None:
            # conan test <path> <ref> injects the reference; when it is not
            # available during graph computation (older conan 2.x), the
            # recipe's declared fallback below is used.
            tested = "msdfgen/1.13"
        self.requires(tested)
        # runtime deps of the shipped CLI (its NEEDED entries)
        self.requires("freetype/2.14.3")
        self.requires("libpng/1.6.58.2")
        self.requires("tinyxml2/11.0.0")

    def generate(self):
        VirtualRunEnv(self).generate()  # conanrun env for CLI launch

    def build(self):
        pass  # pure post-package verification, nothing to compile

    def test(self):
        if str(self.settings.os) != "OHOS":
            raise ConanException("test_ohos must run on the OHOS profile")
        tested = getattr(self, "tested_reference", None) or "msdfgen/1.13"
        pkg = self.dependencies[tested.split("#")[0]]
        pkg_root = Path(pkg.package_folder).resolve(strict=True)
        readelf = os.environ.get("OHOS_READELF", "readelf")
        script = str(Path(self.recipe_folder, "test_ohos.sh"))
        # Stage runtime deps into a private temp dir (never the recipe
        # folder or the package folder), and remove it on any exit path —
        # success, failure or exception — so no test output is left behind.
        runtime_root = Path(tempfile.mkdtemp(prefix="msdfgen-test-ohos-runtime."))
        try:
            self._prepare_ohos_runtime(str(runtime_root), pkg_root)
            pkg_lib = str(Path(pkg_root, "lib"))
            self.run(
                f'LD_LIBRARY_PATH="{runtime_root}:{pkg_lib}" '
                f'"bash" "{script}" "{pkg_root}" "{readelf}"',
                env="conanrun",
            )
        finally:
            shutil.rmtree(runtime_root, ignore_errors=True)

    def _prepare_ohos_runtime(self, runtime_root, pkg_root):
        # Stage every runtime dependency .so into one flat directory so the
        # CLI's NEEDED closure resolves on the OHOS dynamic loader.
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
                    if not (entry.name.endswith(".so") or ".so." in entry.name):
                        continue
                    source = entry.resolve(strict=True)
                    if source.is_symlink() or not source.is_file():
                        continue  # skip broken/alias symlinks
                    shutil.copy2(source, root / entry.name)
