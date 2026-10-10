#!/usr/bin/env python3
"""Conan test_package for memcacheq 0.2.1 - HarmonyOS PC consumer validation.

Two layers, both driven from test():

Layer 1 (runs whenever the target is OHOS) - ohos_abi_check.py inspects the
    packaged artifact instead of executing it: A1-A7 cover ELF64/AArch64, the
    OHOS musl interpreter, .note.ohos.ident, the exact musl+libevent+libdb
    DT_NEEDED set, no host RPATH/RUNPATH, NX/PIE/RELRO/BIND_NOW and the
    absence of glibc symbol versioning.  It is pure Python ELF parsing with
    no external tool, so it also runs on a dev box that cross-compiles the
    package but cannot execute an aarch64-linux-ohos ELF: that host must
    still validate the artifact rather than pass silently.  It is also what
    keeps the CI L1e destructive reverse check meaningful when
    cross-building - move bin/ away and this layer fails.

Layer 2 (can_run only) - test_memcacheq.sh starts the packaged daemon on a
    real HarmonyOS host and drives 15 protocol-level cases (F1-F13b) over
    TCP: version, set/get FIFO queue semantics, queue isolation, length
    handling, stats, stats queue, delete-NOT_FOUND, unknown-command ERROR,
    -h usage and -i license.  Upstream ships no test framework at all (its
    tools/ only has two demo push/pop python scripts), so this is the
    补全 suite declared in MANIFEST.yml.
"""
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run


class MemcacheqTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"memcacheq test supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # run=True: VirtualRunEnv only injects bin/ of run dependencies into
        # PATH, and memcacheq is an application package.
        self.requires(self.tested_reference_str, run=True)
        # The daemon links libevent-2.1.so.7 / libdb-6.2.so from its own
        # dependency packages.  Requiring them here gives the test_package
        # graph nodes with real package_folder values, so the LD_LIBRARY_PATH
        # collection in test() can locate them (transitive nodes of a
        # test_package carry no package_folder in Conan 2).  Version-locked
        # to the recipe's requirements.
        self.requires("libevent/2.1.12")
        self.requires("db/6.2.32")

    def _bindir(self):
        """Absolute bin/ of the tested package (do not rely on PATH alone)."""
        dep = self.dependencies.get("memcacheq")
        if dep is None:
            raise ConanException("memcacheq dependency missing from the graph")
        rel = "bin"
        try:
            if dep.cpp_info.bindirs:
                rel = dep.cpp_info.bindirs[0]
        except Exception:
            rel = "bin"
        cand = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
        self.output.info("memcacheq package_folder=%s bindir=%s"
                         % (dep.package_folder, cand))
        if not os.path.isfile(os.path.join(cand, "memcacheq")):
            raise ConanException(
                f"memcacheq executable not found in the package: {cand}/memcacheq")
        return cand

    def test(self):
        bin_dir = self._bindir()

        # Layer 1: HarmonyOS artifact/ABI checks (host independent).
        if str(self.settings.os) == "OHOS":
            checker = os.path.join(self.recipe_folder, "ohos_abi_check.py")
            binary = os.path.join(bin_dir, "memcacheq")
            self.run(" ".join(shlex.quote(arg) for arg in (
                sys.executable, checker, "--binary", binary)))
        else:
            self.output.info(
                "target os=%s: the A1-A7 artifact layer is OHOS specific and "
                "is skipped; the functional layer below still exercises the "
                "packaged binary" % self.settings.os)

        # Layer 2: on-device daemon + protocol suite.
        if not can_run(self):
            self.output.info(
                "cross-building: an aarch64-linux-ohos ELF cannot execute on "
                "this host, so the test_memcacheq.sh runtime cases are "
                "skipped here and are exercised on the HarmonyOS CI worker; "
                "the artifact/ABI layer above did execute against the "
                "packaged binary")
            return

        script = os.path.join(self.recipe_folder, "test_memcacheq.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        # Guard: CONFIG_SHELL may point at a CI-worker bash that does not
        # exist on a dev box (conanbuildenv hardcodes /data/service/hnp/bin/
        # bash).  Use it only when it really is executable, else /bin/sh
        # (toybox sh runs this POSIX script fine).
        if shell != "/bin/sh" and not os.path.isfile(shell):
            shell = "/bin/sh"
        # OHOS / is largely read-only (erofs): seed a writable TMPDIR in the
        # parent process before exec so the script's scratch files (and the
        # BerkeleyDB environment home) land there.
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP") or "")
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for var in ("TMPDIR", "TMP", "TEMP", "TEMPDIR"):
            os.environ[var] = tmpdir

        # The daemon links its two dependency libraries as shared objects
        # (libevent-2.1.so.7, libdb-6.2.so).  They live in the *dependency
        # packages'* lib/ directories one level below the tested package, so
        # walk the whole host graph (the direct requires of a test_package is
        # only the tested package itself) and collect every libdir into
        # LD_LIBRARY_PATH before starting the daemon -- the OHOS musl loader
        # has no default search entry for package folders, and
        # self.run(env="conanrun") starts from the conanrun env, not from
        # os.environ, so the variable must be prepended on the command
        # line itself to survive.
        lib_paths = []
        try:
            deps = self.dependencies.host.topological_order
        except Exception:
            deps = list(self.dependencies.items())
        for _ref, dep in deps:
            # Some graph nodes (e.g. virtual/test-scope entries) carry no
            # package_folder; skip them rather than crash on os.path.join.
            if not dep.package_folder:
                continue
            try:
                libdirs = list(dep.cpp_info.aggregated_components().libdirs)
            except Exception:
                libdirs = []
            if not libdirs:
                fallback = os.path.join(dep.package_folder, "lib")
                libdirs = [fallback] if os.path.isdir(fallback) else []
            for ld in libdirs:
                if not ld:
                    continue
                if not os.path.isabs(ld):
                    ld = os.path.join(dep.package_folder, ld)
                if os.path.isdir(ld) and ld not in lib_paths:
                    lib_paths.append(ld)
        ld_prefix = ""
        if lib_paths:
            ld_prefix = 'LD_LIBRARY_PATH=%s:$LD_LIBRARY_PATH ' % (
                ":".join(lib_paths))
            self.output.info("run-time LD_LIBRARY_PATH entries: %s"
                             % ", ".join(lib_paths))

        self.run('%s"%s" "%s" "%s"'
                 % (ld_prefix, shell, script, bin_dir), env="conanrun")
