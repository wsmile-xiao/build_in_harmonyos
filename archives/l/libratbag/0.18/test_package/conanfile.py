#!/usr/bin/env python3
"""Conan test_package for libratbag 0.18 — consumer-side check of liblur.

Compiles test_lur.c against the *installed* libratbag package and runs it on the
OHOS aarch64 target.  Nothing here needs a Logitech Unifying Receiver: the CI
machine has no /dev/hidraw node, so the test only exercises the pure
classification helper and the documented error paths (see test_lur.c).

Three OHOS specifics are handled the way the rest of the archive does it:
  * libratbag's public dependency glib is packaged together with its
    ``proxy-libintl`` subproject and does not declare ``intl`` as a system lib,
    so ``-lintl`` is added by hand;
  * the OHOS musl loader does not reliably honour LD_LIBRARY_PATH for the conan
    cache, so DT_RPATH entries are baked into the test binary with
    ``--disable-new-dtags``;
  * json-glib/1.10.6 ships ``libjson-glib-1.0.so.0`` as a symlink onto a file
    with a stale ``.codesign`` section that the OHOS kernel refuses to map, so
    a re-signed copy is staged into the test build directory (see
    ``_stage_json_glib_soname``).
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building

TEST_PROGRAM = "test_lur"


class LibratbagTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _collect(self):
        """Include dirs / lib dirs / libs / system libs of every host dep."""
        incs, libdirs, libs, syslibs = [], [], [], []
        for dependency in self.dependencies.host.values():
            agg = dependency.cpp_info.aggregated_components()
            base = dependency.package_folder or ""
            for path in agg.includedirs:
                if not os.path.isabs(path):
                    path = os.path.join(base, path)
                if os.path.isdir(path) and path not in incs:
                    incs.append(path)
            for path in agg.libdirs:
                if not os.path.isabs(path):
                    path = os.path.join(base, path)
                if os.path.isdir(path) and path not in libdirs:
                    libdirs.append(path)
            for name in agg.libs:
                if name not in libs:
                    libs.append(name)
            for name in agg.system_libs:
                if name not in syslibs:
                    syslibs.append(name)
        return incs, libdirs, libs, syslibs

    def build(self):
        incs, libdirs, libs, syslibs = self._collect()
        self.output.info(f"includes: {incs}")
        self.output.info(f"libdirs: {libdirs}")
        self.output.info(f"libs: {libs} + system {syslibs}")

        flags = []
        flags += ["-I" + p for p in incs]
        flags += ["-L" + p for p in libdirs]
        flags += ["-l" + l for l in libs]
        flags += ["-l" + l for l in syslibs]
        if self.settings.os == "OHOS":
            # glib's proxy-libintl: g_libintl_* must be linked explicitly.
            flags += ["-lintl"]
            flags += ["-Wl,--disable-new-dtags"]
            flags += ["-Wl,-rpath," + p for p in libdirs]

        cc = os.environ.get("CC", "clang")
        self.run(f'{cc} -std=gnu11 -O1 -Wall -Wextra '
                 f'-o {TEST_PROGRAM} test_lur.c ' + " ".join(flags))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        _, libdirs, _, _ = self._collect()
        runtime_dirs = []
        if self.settings.os == "OHOS":
            staged = self._stage_json_glib_soname()
            if staged:
                runtime_dirs.append(staged)
        ldpath = os.pathsep.join(runtime_dirs + libdirs)
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        self.run(
            f'{bash} -c \'export LD_LIBRARY_PATH="{ldpath}'
            f'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; '
            f'"./{TEST_PROGRAM}"\'',
            env="conanrun")

    def _stage_json_glib_soname(self):
        """Stage a re-signed ``libjson-glib-1.0.so.0`` for the OHOS loader.

        json-glib/1.10.6 ships the soname as a symlink onto a versioned file
        that still carries a ``.codesign`` section produced by an older
        toolchain; the OHOS kernel refuses to map it and the musl loader
        reports the refusal as
            ``Error loading shared library libjson-glib-1.0.so.0: (needed by
            ./test_lur)``
        with an **empty** strerror (E073 家族：库“存在但载不进”)。The conan
        cache stays read-only: the real file is copied into the test build
        directory, the stale signature is dropped and re-created with
        ``binary-sign-tool``; the caller prepends that directory to
        LD_LIBRARY_PATH.  Same shape as ``archives/g/gxr/0.15.1``.
        """
        dependency = self.dependencies["json-glib"]
        packaged = os.path.join(dependency.package_folder, "lib",
                                "libjson-glib-1.0.so.0")
        if not os.path.lexists(packaged):
            return None
        source = os.path.realpath(packaged)
        root = os.path.realpath(dependency.package_folder)
        if not os.path.isfile(source) \
                or os.path.commonpath((source, root)) != root:
            raise ConanException(f"Unsafe json-glib soname: {packaged}")

        runtime_dir = tempfile.mkdtemp(
            prefix="libratbag-ohos-runtime-", dir=self.build_folder)
        staged = os.path.join(runtime_dir, "libjson-glib-1.0.so.0")
        shutil.copyfile(source, staged)
        os.chmod(staged, 0o755)

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(
                    f"Required OHOS signing tool not found: {tool}")
        self.run(f'"{objcopy}" --remove-section .codesign "{staged}"')
        self.run(f'"{signer}" sign -inFile "{staged}" -outFile "{staged}" '
                 f'-selfSign 1')
        self.output.info(f"staged re-signed json-glib soname: {staged}")
        return runtime_dir
