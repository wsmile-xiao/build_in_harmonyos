#!/usr/bin/env python3
"""Conan recipe — lddtree 1.27 (POSIX-shell ELF dependency tree viewer).

Upstream: https://github.com/ncopa/lddtree  (GPL-2.0-only)
Product:  a single command-line tool, `lddtree.sh`, which prints the ELF
dependency tree of one or more executables/libraries. Fork of pax-utils'
lddtree.sh; unlike the bash original it resolves symlinks and falls back to
binutils (objdump + readelf) when pax-utils' scanelf is unavailable.

HarmonyOS PC (aarch64) adaptation:
  * Pure shell — there is no compilation step. The product is installed
    verbatim as bin/lddtree.sh.
  * patches/0001 replaces upstream's external GNU getopt(1) call with an
    equivalent POSIX-shell parser: toybox/busybox in this environment ships
    no getopt and util-linux is not published to the registry, so upstream's
    parser aborts every invocation.
  * patches/0002 adds tools/atf-sh-mini so the real upstream suite
    (tests/lddtree_test, 13 ATF cases) runs under `make check` without
    kyua/atf-sh; the upstream test files are not touched.
  * build() runs the genuine upstream test suite and prints machine readable
    "UPSTREAM-TEST-SUMMARY: ..." / "ASSERTIONS: ..." lines (TEST_QUALITY_SPEC
    layer 1 / R51).
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# make is not part of the CI worker's PATH; the registry bmake package is the
# canonical provider (same approach used by other archives/ recipes).
MAKE_PROVIDER = "bmake/20200710"

# lddtree shells out to an ELF inspection backend. This platform has no
# pax-utils scanelf and no OHOS package publishes one, so binutils' objdump +
# readelf is the only usable backend — a genuine runtime prerequisite.
BINUTILS = "binutils/2.46.0"


class LddtreeConan(ConanFile):
    name = "lddtree"
    version = "1.27"
    description = (
        "lddtree: a POSIX-shell lddtree implementation that prints the "
        "dependency tree of ELF files (binutils backend)."
    )
    license = "GPL-2.0-only"
    homepage = "https://github.com/ncopa/lddtree"
    url = "https://github.com/ncopa/lddtree"

    # CLI tool => "application" (R38).
    package_type = "application"
    # L0p: all four settings declared.
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime dependency: without objdump/readelf (or scanelf) lddtree exits
        # 1 with "needs either scanelf or binutils". Declared here rather than as
        # a tool_require so `conan install lddtree/1.27` yields a working tool;
        # binutils' runenv_info puts its bin/ on PATH.
        self.requires(BINUTILS)

    def build_requirements(self):
        # The upstream suite is driven by `make check`; the CI worker's PATH
        # has no make, so it comes from the registry (R18/R36).
        self.tool_requires(MAKE_PROVIDER)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _tool_dirs(self):
        """bin/ dirs of the dependencies that provide build-time tools.

        Both make (bmake) and the ELF backend (binutils) must be reachable by
        the test suite's subprocesses; Conan's buildenv PATH is not inherited by
        them, so the directories are injected explicitly.
        """
        dirs = []
        for dep in list(self.dependencies.build.values()) + \
                list(self.dependencies.host.values()):
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir):
                dirs.append(bindir)
        return dirs

    def _make_exe(self):
        for bindir in self._tool_dirs():
            if "bmake" not in bindir:
                continue
            for candidate in ("make", "bmake"):
                exe = os.path.join(bindir, candidate)
                if os.path.isfile(exe):
                    return exe
        return "make"

    def _test_env(self):
        env = dict(os.environ)
        # /tmp is read-only on this platform (E002/R10).
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env["TMPDIR"] = tmpdir
        dirs = self._tool_dirs()
        if dirs:
            env["PATH"] = os.pathsep.join(dirs + [env.get("PATH", "")])
        return env

    @staticmethod
    def _backend(env):
        for exe, name in (("scanelf", "scanelf"), ("objdump", "binutils")):
            for d in env["PATH"].split(os.pathsep):
                if d and os.path.isfile(os.path.join(d, exe)):
                    return name
        return "none"

    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)

        env = self._test_env()
        make_exe = self._make_exe()
        backend = self._backend(env)
        self.output.info(f"make: {make_exe}")
        self.output.info(f"elf inspection backend: {backend}")
        if backend == "none":
            raise ConanException(
                "no ELF inspection backend available (need scanelf or "
                "objdump+readelf); PATH={}".format(env["PATH"])
            )

        # No compilation: lddtree.sh is the deliverable. Verify it parses.
        script = os.path.join(self.source_folder, "lddtree.sh")
        if not os.path.isfile(script):
            raise ConanException(f"lddtree.sh missing from sources: {script}")
        syntax = subprocess.run(["sh", "-n", "lddtree.sh"],
                                cwd=self.source_folder, env=env,
                                capture_output=True, text=True, timeout=120)
        if syntax.returncode != 0:
            raise ConanException(f"lddtree.sh failed syntax check: {syntax.stderr}")

        # ── Upstream official test suite (TEST_QUALITY_SPEC layer 1 / R51) ──
        # `make check` drives tools/atf-sh-mini, so the unmodified upstream
        # cases in tests/lddtree_test really execute. The full transcript is
        # echoed back so the CI log carries the required execution traces
        # (L1b/L1c) even when this runs inside conan create.
        #
        # `-r` (no built-in rules) is required for the registry bmake: it ships
        # its sys.mk under share/mk, which bmake does not search by default, so
        # a bare invocation dies with "no system rules (sys.mk)" before reading
        # the Makefile. lddtree's Makefile declares every rule explicitly, and
        # `-r` is also accepted by GNU make, so the flag is portable.
        log = os.path.join(self.build_folder, "upstream-make-check.log")
        cmd = ["sh", "-c",
               f'"{make_exe}" -r check > "{log}" 2>&1; echo $?']
        proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                              capture_output=True, text=True, timeout=1800)
        rc = int((proc.stdout or "1").strip().splitlines()[-1])

        self.output.info(f"command: {make_exe} -r check")
        with open(log, "r", errors="replace") as fh:
            transcript = fh.read()
        for line in transcript.splitlines():
            self.output.info("  " + line)

        summary = self._summary_line(transcript)
        asserts = self._assertions_line(transcript)
        self.output.info(f"UPSTREAM-TEST-SUMMARY: {summary or 'n/a'}")
        self.output.info(f"UPSTREAM-{asserts or 'ASSERTIONS: n/a'}")

        total, passed, failed, skipped = self._numbers(summary)
        if rc != 0 or failed or total == 0 or passed == 0 or skipped:
            raise ConanException(
                "upstream test suite not fully green (make check exit {}): {}. "
                "{} make={} backend={} TMPDIR={} log={}".format(
                    rc, summary or "no summary line", asserts or "n/a",
                    make_exe, backend, env["TMPDIR"], log,
                )
            )

    @staticmethod
    def _summary_line(text):
        for line in reversed(text.splitlines()):
            if " tests, " in line and " passed, " in line:
                return line.strip()
        return ""

    @staticmethod
    def _assertions_line(text):
        for line in reversed(text.splitlines()):
            if line.strip().startswith("ASSERTIONS:"):
                return line.strip()
        return ""

    @staticmethod
    def _numbers(summary):
        """(total, passed, failed, skipped) parsed from the runner summary."""
        try:
            head = summary.split(" tests,")[0].strip()
            rest = summary.split(" tests,")[1]
            total = int(head)
            counts = [int(piece.strip().split()[0])
                      for piece in rest.split(",") if piece.strip()]
            passed, failed, skipped = (counts + [0, 0, 0])[:3]
            return total, passed, failed, skipped
        except (ValueError, IndexError):
            return 0, 0, 0, 0

    def package(self):
        src = self.source_folder
        # Ship the tool under its upstream name (commands.json declares it).
        copy(self, "lddtree.sh", src=src,
             dst=os.path.join(self.package_folder, "bin"))
        os.chmod(os.path.join(self.package_folder, "bin", "lddtree.sh"), 0o755)
        copy(self, "README.md", src=src,
             dst=os.path.join(self.package_folder, "doc"))
        copy(self, "COPYING*", src=src,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
