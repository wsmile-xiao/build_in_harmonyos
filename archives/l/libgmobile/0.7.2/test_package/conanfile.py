#!/usr/bin/env python3
"""Conan test_package for libgmobile 0.7.2 — consumer-side runtime check.

Compiles test.c against the *installed* libgmobile and runs it on the OHOS
aarch64 target.

Three OHOS specifics are handled here:
  * glib is packaged together with its ``proxy-libintl`` subproject, and the
    glib recipe does not declare ``intl`` as a system lib, so the explicit
    ``-lintl`` is added by hand (same reason json-glib's recipe rewrites its
    generated .pc files).
  * the OHOS musl loader resolves neither DT_RUNPATH reliably nor
    LD_LIBRARY_PATH for the conan cache, so DT_RPATH entries are baked into
    the test binary with ``--disable-new-dtags``.  ``/system/bin/sh`` (mksh)
    cannot exec an ELF, hence the bash wrapper.
  * json-glib's ``libjson-glib-1.0.so.0`` is a **symlink** onto a versioned
    file that still carries a stale ``.codesign`` section; the OHOS kernel
    refuses to map it, and the musl loader reports that as
        ``Error loading shared library libjson-glib-1.0.so.0: (needed by ...)``
    with an **empty** strerror.  A materialised + re-signed copy is staged
    into the test build dir and prepended to ``LD_LIBRARY_PATH`` — see
    ``_stage_resigned_sonames``.  (The main recipe stages the same thing for
    its own *build-time* glib tools, but that copy lives in the recipe's build
    folder and is not on the test_package's runtime search path, which is why
    this has to be repeated here — proven shape: libratbag/0.18.)
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building

HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")


class LibgmobileTestConan(ConanFile):
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
        # glib's proxy-libintl: g_libintl_* must be linked explicitly.
        if self.settings.os == "OHOS":
            flags += ["-lintl"]
            flags += ["-Wl,--disable-new-dtags"]
            flags += ["-Wl,-rpath," + p for p in libdirs]

        cc = os.environ.get("CC", "clang")
        self.run(f'{cc} -std=gnu11 -O1 -Wall -o test_libgmobile test.c '
                 + " ".join(flags))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        _, libdirs, _, _ = self._collect()
        runtime_dirs = []
        if self.settings.os == "OHOS":
            staged = self._stage_resigned_sonames()
            if staged:
                runtime_dirs.append(staged)
        ldpath = os.pathsep.join(runtime_dirs + libdirs)
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or "/data/service/hnp/bin/bash"
        self.run(
            f'{bash} -c \'export LD_LIBRARY_PATH="{ldpath}'
            f'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; ./test_libgmobile\'',
            env="conanrun")

    def _dependency_libdirs(self):
        """Existing ``lib`` directories of every host dependency, deduplicated."""
        libdirs = []
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir) and libdir not in libdirs:
                    libdirs.append(libdir)
        return libdirs

    def _stage_resigned_sonames(self):
        """Materialise + re-sign symlinked dependency SONAMEs for the OHOS loader.

        json-glib ships ``lib/libjson-glib-1.0.so.0`` as a symlink onto a
        versioned file that carries a stale ``.codesign`` section; the OHOS
        kernel refuses to mmap it and the musl loader surfaces that as
        ``Error loading shared library libjson-glib-1.0.so.0: (needed by ...)``
        with an **empty** strerror (库“存在但载不进”，区别于真缺失时的
        ``No such file or directory``).

        Materialising alone is NOT enough — the same PR's A/B on 2026-09-27
        showed libratbag/0.18 going FAIL with a plain copy and PASS once the
        copy was re-signed.  The conan cache stays read-only: the real file is
        copied into the test build dir, the stale signature dropped with
        ``llvm-objcopy`` and re-created with ``binary-sign-tool -selfSign 1``.
        The caller prepends that directory to ``LD_LIBRARY_PATH``.
        """
        staged = os.path.join(self.build_folder, "conan-staged-soname-libs")
        materialised = []
        for libdir in self._dependency_libdirs():
            for name in sorted(os.listdir(libdir)):
                if not name.endswith(".so") and ".so." not in name:
                    continue
                source = os.path.join(libdir, name)
                if not os.path.islink(source):
                    continue
                target = os.path.join(staged, name)
                if os.path.exists(target):
                    continue
                real = os.path.realpath(source)
                if not os.path.isfile(real):
                    continue
                os.makedirs(staged, exist_ok=True)
                shutil.copy2(real, target)  # copy2 follows the link → payload
                os.chmod(target, 0o755)
                self._resign(target)
                materialised.append(name)
        if not materialised:
            return None
        self.output.info(
            "E073: materialised + re-signed %d symlinked SONAMEs into %s (%s)"
            % (len(materialised), staged, ", ".join(materialised)))
        return staged

    def _resign(self, binary):
        for tool in (OBJCOPY, SIGN_TOOL):
            if not os.path.isfile(tool):
                raise ConanException(
                    f"OHOS signing tool not found: {tool}")
        self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                 f"{shlex.quote(binary)}")
        self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                             "-outFile", binary, "-selfSign", "1"]))
