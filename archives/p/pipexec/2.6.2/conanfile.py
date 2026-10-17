#!/usr/bin/env python3
"""Conan recipe — pipexec 2.6.2 (autotools, application).

pipexec builds arbitrary process trees whose file descriptors are wired
together, so a shell pipeline can be expressed as a single command:

    pipexec -- [ A /bin/echo Hello World ] [ B /bin/cat ] '{A:1>B:0}'

Build system: GNU autotools (configure.ac + automake Makefile.am/inc +
libtool).  This recipe consumes the upstream **release asset**
``pipexec-2.6.2.tar.xz`` rather than the GitHub tag archive, because only the
release asset ships the generated ``configure`` / ``Makefile.in`` /
``aclocal.m4`` / ``config.h.in`` (``build/create_tar.sh`` runs autotools at
release time).  The CI image has no autoconf/automake, so a tag archive would
force an autoreconf that cannot run there.

HarmonyOS PC adaptation points (all OHOS-only; no effect on Linux):

1. E007 — upstream ``config.guess`` (2018-02-24) / ``config.sub`` know nothing
   about HarmonyOS, so ``configure`` aborts at "checking host system type"
   (``uname -s`` = ``HarmonyOS``).  ``0001-config-guess-sub-ohos.patch`` adds
   the HarmonyOS branch (→ ``aarch64-unknown-linux-ohos``) and the
   ``linux-ohos`` / ``ohos-linux`` triplets.  Patch, never ``--build/--host``
   (E007 forbids the latter: it flips ``cross_compiling=yes`` and skips
   ``AC_RUN_IFELSE`` probes).
2. ``configure.ac`` assigns ``CFLAGS``/``CXXFLAGS`` **unconditionally** at the
   end of the script, discarding the flags Conan injects through
   ``AutotoolsToolchain`` (``--target=aarch64-linux-ohos``, ``--sysroot=...``,
   ``-fPIC``).  ``0002-configure-respect-user-cflags.patch`` turns both
   assignments into appends (``CFLAGS="$CFLAGS ..."``), the same shape used by
   ``archives/l/libnova/0.16`` ("respect user cflags").
3. ``src/Makefile.inc`` invokes ``/bin/sh`` literally to generate
   ``src/app_version.c``, and the generated ``build/version-gen.sh`` shells out
   to ``version.sh`` whose shebang is ``#!/bin/sh``.  Neither ``/bin/sh`` nor a
   ``/bin`` directory exists on HarmonyOS (E165); ``/bin/sh`` is off PATH.
   ``0003-version-gen-portable-shell.patch`` (a) uses ``$(SHELL)``, which
   ``configure`` fills in, and (b) reads ``version.txt`` directly instead of
   re-invoking ``version.sh``.  Both scripts stay POSIX.

``configure``/``make`` are not re-generated: ``build()`` pins the autotools
*source* inputs (``configure.ac``, ``Makefile.am``, ``Makefile.inc``, ``m4/*``)
to the epoch and the *generated* files (``configure``, ``Makefile.in``,
``aclocal.m4`` ...) to now, so ``make`` never tries to run the absent
autoconf/automake (same treatment as ``archives/l/libmodbus/3.2.0``).

Upstream test: ``test/basic_tests.sh`` (4 checks) — actually executed in
``build()`` against the binaries just built; see ``notes.md`` (R51).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Native OHOS build executor: on the device the source tree lives on HMDFS,
# where a file cannot be executed directly even when it carries +x, so the
# generated `configure` script has to be interpreted by a system shell
# (knowledge E232). CONFIG_SHELL alone is not enough — it only governs the
# sub-shells Autoconf starts later, not that first launch.
_OHOS_SHELL = "/system/bin/sh"

# Upstream processes that test/basic_tests.sh invokes through /bin/*.  On
# HarmonyOS there is no traditional /bin (E165); they are remapped to whatever
# absolute path this machine actually provides.
_UPSTREAM_BIN_TOOLS = ("true", "false", "echo", "cat", "grep")

# Extra places to look when PATH does not carry the usual utilities (the OHOS
# buildenv PATH lists only ~/usr/local/bin and the HNP bin dir, so /system/bin
# toybox applets are not guaranteed to be resolvable through shutil.which).
_FALLBACK_BIN_DIRS = ("/system/bin", "/data/service/hnp/bin")

# Fixed mtimes for the autotools timestamp dance.  Three tiers are required
# because aclocal.m4 is both a *prerequisite* of configure/Makefile.in and a
# *product* of configure.ac + m4/*; giving every file the same "now" value left
# aclocal.m4 looking newer than Makefile.in and re-triggered aclocal/automake.
# Distinct past values keep the derived graph strictly increasing and avoid
# same-second ties entirely.
_MTIME_INPUT = 946684800    # 2000-01-01T00:00:00Z  configure.ac, Makefile.am, *.inc, m4/*
_MTIME_DERIVED = 946684900  # 2000-01-01T00:01:40Z  aclocal.m4
_MTIME_FINAL = 946685000    # 2000-01-01T00:03:20Z  configure, Makefile.in, config.h.in, config.guess/sub

# Generated autotools outputs that must end up newer than their inputs.
_AUTOTOOLS_GENERATED = (
    "configure",
    "Makefile.in",
    "config.h.in",
    "config.guess",
    "config.sub",
)

# Autotools sources/inputs (patched in place by export/apply) that must end up
# older than the generated outputs.
_AUTOTOOLS_INPUTS = (
    "configure.ac",
    "Makefile.am",
    "src/Makefile.inc",
    "test/Makefile.inc",
    "m4/libtool.m4",
    "m4/ltoptions.m4",
    "m4/ltsugar.m4",
    "m4/ltversion.m4",
    "m4/lt~obsolete.m4",
)


class PipexecConan(ConanFile):
    name = "pipexec"
    version = "2.6.2"
    description = (
        "Build a tree of processes with connected pipes from a single "
        "command line"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/flonatel/pipexec"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # R32: only Linux and HarmonyOS are supported targets.
    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pipexec {self.version} supports Linux and OHOS only"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream needs nothing beyond libc: configure.ac has no library
        # checks, the sources are strict POSIX (execv/fork/pipe/waitpid/
        # poll) and configure only probes the C compiler.  No Conan dependency
        # to declare, so there is no R36 dependency-publishing blocker.
        pass

    def layout(self):
        # Upstream ships a real automake Makefile.in with VPATH support, so
        # out-of-tree builds work; keep the default conan split.
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R1: nothing beyond what AutotoolsToolchain injects (--prefix, CC,
        # CFLAGS, --target, --sysroot).  Upstream configure accepts no other
        # documented switches relevant here (--enable-debug/--enable-profiling
        # /--enable-coverage default off, --enable-valgrind must stay off).
        #
        # On a native OHOS build host the toolchain shell is pinned to the
        # system shell so Autoconf's later sub-shells (config.status and the
        # helpers it launches) do not fall back to a /bin/sh that the HMDFS
        # sandbox refuses (E232 / E165).
        tc = AutotoolsToolchain(self)
        if str(self.settings_build.os) == "OHOS":
            environment = tc.environment()
            environment.define_path("SHELL", _OHOS_SHELL)
            environment.define_path("CONFIG_SHELL", _OHOS_SHELL)
            tc.generate(env=environment)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._stabilize_autotools_timestamps()
        autotools = Autotools(self)
        if str(self.settings_build.os) == "OHOS":
            # E232: the generated configure script sits on HMDFS and cannot be
            # exec'd directly (Error 126 while executing -> "Permission
            # denied"), and CONFIG_SHELL cannot wrap that first launch.  Hand
            # it to the system shell explicitly, reusing the exact argument
            # list Conan generated (never reconstruct it by hand).
            configure = os.path.join(self.source_folder, "configure")
            if not os.path.isfile(_OHOS_SHELL):
                raise ConanException(f"required OHOS shell missing: {_OHOS_SHELL}")
            environment = Environment()
            environment.define_path("SHELL", _OHOS_SHELL)
            environment.define_path("CONFIG_SHELL", _OHOS_SHELL)
            with environment.vars(self).apply():
                self.run(f'"{_OHOS_SHELL}" "{configure}" {autotools._configure_args}')
        else:
            autotools.configure()
        # -j1: keep the log deterministic and avoid jobserver/fifo quirks on
        # the device (same default as the sibling autotools recipes).
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def package(self):
        Autotools(self).install()
        # `make install` also drops the upstream test helper test/ptest; it is
        # not a runtime file, so keep it out of the package (§7.5).
        ptest = os.path.join(self.package_folder, "bin", "ptest")
        if os.path.isfile(ptest):
            os.remove(ptest)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    # ── helpers ──────────────────────────────────────────────────────────
    def _stabilize_autotools_timestamps(self):
        """Keep generated autotools files strictly newer than their inputs.

        export_sources()/apply_conandata_patches() rewrite configure.ac,
        Makefile.inc and config.guess/sub with a fresh mtime, which makes
        ``make`` believe ``configure`` / ``Makefile.in`` / ``aclocal.m4`` are
        stale and re-run autoconf/automake.  The CI image ships neither, so the
        build would die with ``autoconf: command not found`` (Error 127).
        Assign three increasing past timestamps along the real dependency
        chain: inputs < aclocal.m4 < configure/Makefile.in.
        """
        mtimes = (
            (_AUTOTOOLS_INPUTS, _MTIME_INPUT),
            (("aclocal.m4",), _MTIME_DERIVED),
            (_AUTOTOOLS_GENERATED, _MTIME_FINAL),
        )
        for rels, stamp in mtimes:
            for rel in rels:
                path = os.path.join(self.source_folder, rel)
                if os.path.exists(path):
                    os.utime(path, (stamp, stamp))

    def _find_bash(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            "/data/service/hnp/bin/bash",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def _resolve_tool(self, tool):
        """Absolute path of a core utility, or None.

        Checks PATH first, then the well-known OHOS bin directories.  The
        original /bin/<tool> is only accepted if it really exists, so on
        HarmonyOS (no /bin) the caller re-points it to a real path instead of
        silently keeping a dead one.
        """
        candidates = [shutil.which(tool)]
        candidates += [os.path.join(d, tool) for d in _FALLBACK_BIN_DIRS]
        original = f"/bin/{tool}"
        if os.path.isfile(original):
            candidates.append(original)
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _run_upstream_tests(self):
        """Run upstream test/basic_tests.sh against the freshly built binaries.

        R51: the suite is small and self-contained (4 checks), so it runs for
        real.  The only OHOS adjustment is path resolution — the script spells
        out ``/bin/true`` etc., and HarmonyOS has no traditional /bin (E165) —
        so those tokens are remapped to the absolute paths this machine
        provides.  Nothing is skipped and the exit status is propagated.
        """
        script = os.path.join(self.source_folder, "test", "basic_tests.sh")
        if not os.path.isfile(script):
            raise ConanInvalidConfiguration(
                "upstream test/basic_tests.sh missing from the source archive"
            )
        with open(script, "r", encoding="utf-8") as handle:
            text = handle.read()

        remapped = {}
        unresolved = []
        for tool in _UPSTREAM_BIN_TOOLS:
            original = f"/bin/{tool}"
            resolved = self._resolve_tool(tool)
            if resolved and os.path.realpath(resolved) != os.path.realpath(original):
                text = text.replace(original, resolved)
                remapped[original] = resolved
            elif not resolved:
                unresolved.append(original)

        if unresolved:
            # Fail loudly rather than let the script die with a bare
            # "No such file or directory" and no explanation.
            raise ConanInvalidConfiguration(
                "cannot locate these programs required by upstream "
                "test/basic_tests.sh on this system: " + ", ".join(unresolved)
            )

        ported = os.path.join(self.build_folder, "_ohos_basic_tests.sh")
        with open(ported, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

        if remapped:
            self.output.info(
                "upstream basic_tests.sh: remapped for OHOS (no /bin): "
                + ", ".join(f"{k}->{v}" for k, v in sorted(remapped.items()))
            )
        bash = self._find_bash()
        self.run(f'"{bash}" "{ported}"', cwd=self.build_folder)

        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "executed",
            "framework": "shell",
            "command": "test/basic_tests.sh (via bash, /bin tools remapped on OHOS)",
            "discovered": 4,
            "executed": 4,
            "passed": 4,
            "failed": 0,
            "skipped": 0,
            "reason": "",
        }))
