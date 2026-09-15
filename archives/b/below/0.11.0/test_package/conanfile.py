#!/usr/bin/env python3
"""Conan consumer test for below 0.11.0 (Rust binary package).

Three layers of verification:

  1. package integrity — the packaged `below` executable exists;
  2. consumer smoke + HarmonyOS traits — test_below.py runs the binary and
     asserts AArch64 / musl loader / OHOS code signature;
  3. dependency functional test — test_deps.c is compiled against the
     dependency packages (libelf/0.8.13.1, zlib/1.3.2; both ship *static*
     libraries only, so no runtime DT_NEEDED entry exists for them) and
     executed, exercising real dependency code paths on HarmonyOS PC:
     zlib compress2/uncompress round-trip and libelf ELF parsing.
"""

import os
import shutil
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class BelowTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"
    exports_sources = "test_below.py", "test_deps.c"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Declared explicitly so their package folders are resolvable from the
        # consumer side: below links these libraries statically, so nothing in
        # the packaged binary proves they work at runtime. Same versions as
        # below's own requirements, so the binaries are shared, not rebuilt.
        self.requires("libelf/0.8.13.1")
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self)

    # ── helpers ──────────────────────────────────────────────────────────

    def _ohos_cc(self):
        """Locate the OHOS C compiler (profile conf first, then known paths)."""
        candidates = []
        try:
            conf = self.conf.get("tools.build:compiler_executables")
            if isinstance(conf, dict):
                candidates.append(conf.get("c"))
        except Exception:  # noqa: BLE001 - conf may be absent on some runners
            pass
        candidates += [
            shutil.which("aarch64-unknown-linux-ohos-clang"),
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/"
            "aarch64-unknown-linux-ohos-clang",
            shutil.which("clang"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _dep(self, name):
        try:
            return self.dependencies[name]
        except Exception:  # noqa: BLE001 - missing dependency in the graph
            return None

    def _compile_dependency_test(self):
        """Compile test_deps.c against libelf + zlib; return its path or None."""
        cc = self._ohos_cc()
        libelf = self._dep("libelf")
        zlib = self._dep("zlib")
        for dep in (libelf, zlib):
            if dep is None:
                continue
            self.output.info(
                "dep %s: package_folder=%s includedirs=%s libdirs=%s libs=%s"
                % (dep.ref.name if dep.ref else "?",
                   dep.package_folder,
                   list(dep.cpp_info.includedirs or []),
                   list(dep.cpp_info.libdirs or []),
                   list(dep.cpp_info.libs or []))
            )
        if cc is None or libelf is None or zlib is None:
            self.output.warning(
                "dependency test skipped: cc=%s libelf=%s zlib=%s"
                % (cc, bool(libelf), bool(zlib))
            )
            return None

        source = os.path.join(self.source_folder, "test_deps.c")
        binary = os.path.join(self.build_folder, "test_deps")
        cmd = " ".join(
            ['"%s"' % cc, '"%s"' % source, "-o", '"%s"' % binary]
            + ['-I"%s"' % os.path.join(libelf.package_folder, inc)
               for inc in (libelf.cpp_info.includedirs or ["include"])]
            + ['-I"%s"' % os.path.join(zlib.package_folder, inc)
               for inc in (zlib.cpp_info.includedirs or ["include"])]
            + ['-L"%s"' % os.path.join(libelf.package_folder, ldir)
               for ldir in (libelf.cpp_info.libdirs or ["lib"])]
            + ['-L"%s"' % os.path.join(zlib.package_folder, ldir)
               for ldir in (zlib.cpp_info.libdirs or ["lib"])]
            + ["-lelf", "-lz"]
        )
        self.output.info(f"compiling dependency test: {cmd}")
        if self.run(cmd, env="conanbuild", ignore_errors=True) != 0:
            raise AssertionError("dependency test failed to compile")
        if not os.path.isfile(binary):
            raise AssertionError(f"dependency test binary missing: {binary}")
        os.chmod(binary, 0o755)
        return binary

    # ── test entry point ─────────────────────────────────────────────────

    def test(self):
        package_folder = self.dependencies["below"].package_folder
        exe = os.path.join(package_folder, "bin", "below")
        if not os.path.isfile(exe):
            raise AssertionError(f"Missing below executable: {exe}")

        if not can_run(self):
            self.output.info("Cross-building: verified package layout only.")
            return

        script = os.path.join(self.source_folder, "test_below.py")
        result = self.run(
            f'PACKAGE_FOLDER="{package_folder}" "{sys.executable}" "{script}"',
            env="conanrun",
            ignore_errors=True,
        )
        if result != 0:
            raise AssertionError(f"below test_package failed with exit code {result}")

        # Dependency functional test (libelf + zlib are static-only deps, so
        # nothing else would prove they work on this platform).
        dep_test = self._compile_dependency_test()
        if dep_test is None:
            self.output.warning("SKIP: dependency functional test not executed")
            return
        result = self.run(f'"{dep_test}"', env="conanrun", ignore_errors=True)
        if result != 0:
            raise AssertionError(
                f"dependency functional test failed with exit code {result}"
            )
