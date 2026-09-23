#!/usr/bin/env python3
"""Conan recipe for liborcus 0.21.0 — spreadsheet file import filter library.

liborcus parses ODS, XLSX, CSV, Gnumeric and related spreadsheet formats.
Build system is autotools with a dist-carried `configure` (GNU Autoconf
2.71), so no autoreconf is needed — the OHOS device has no
automake/autoconf/libtoolize.

Scope of this adaptation (base adaptation, path A): the parser library
(liborcus-parser-0.21) plus the core import-filter library (liborcus-0.21)
with the default ODS/XLSX/XLS-XML/Gnumeric filters. Three upstream
capabilities are disabled, each for a concrete missing-dependency reason
(documented in notes.md and the PR body, never silently skipped):

* `--disable-spreadsheet-model` — needs libixion-0.20 >= 0.20.0; the
  registry has no ixion Conan package (only a pre-conan 0.19.0 archive).
  This also drops the spreadsheet-model test binaries and the src/
  round-trip tests, which all link the model library.
* `--disable-python` — python bindings need a Python dev environment.
* `--without-tools` / `--without-benchmark` — the CLI tools link the
  spreadsheet model (and need boost program_options); benchmarks are not
  part of verification.
* `--without-gnumeric-filter` — the gnumeric filter's configure probe
  (`BOOST_IOSTREAMS`) link-tests `boost::iostreams::file_descriptor`,
  which needs the compiled libboost_iostreams library; no boost package
  in the registry ships it (boost/1.90.0 is headers plus Boost.Test).
  Keeping the default filter set otherwise (ODS/XLSX/XLS-XML).

Dependency wiring: upstream finds its dependencies with
`PKG_CHECK_MODULES([ZLIB], [zlib])` and
`PKG_CHECK_MODULES([MDDS], [mdds-3.0 >= 3.0.0])`, and boost headers with
`--with-boost` / `BOOST_ROOT` (boost.m4). The device has no pkg-config,
so the two `<PREFIX>_CFLAGS`/`<PREFIX>_LIBS` pairs are exported from the
package folders instead; PKG_CHECK_MODULES prefers non-empty variables
over pkg-config by design (same mechanism as libwpd 0.10.3). mdds is
header-only and its own mdds.pc.in carries no `Libs:` line, so MDDS_LIBS
is whitespace-only — semantically empty, matching upstream metadata.
Boost 1.90.0 is header-only for everything this build touches
(BOOST_SYSTEM is header-only since boost 1.70, so boost.m4 only checks
for the header, no link test).

OHOS machinery (device-verified by libwpd 0.10.3 on the same toolchain,
each item re-checked against this tarball first):

* **In-tree build**: the source tree is copied into the build folder
  before configuring. Folders are shallow (`src_folder="."`,
  `build="."`, cyrus-sasl-login precedent): the default deep
  `p/b/<hash>/b/build-release` dir triggers an HMDFS getcwd storm with
  the OHOS system bash (CI #50593), one level up is normal.
* **Shell**: bash verified against this autoconf 2.71 tree (`exec 7<&0`
  rejects toybox `/system/bin/sh`; bash also gives the POSIX word
  splitting automake's recursive make needs). Candidates are gated on a
  live `pwd` probe inside the build dir: `/data/service/hnp/bin/bash`
  is preferred only when its getcwd() works there, otherwise the PATH
  bash wins (DRAFT-6487-classads-configshell-hmdfs-getcwd).
* **umask 077 -> 022** in the generated configure (exactly 2
  occurrences, asserted): its scratch directory is created with
  `umask 077` (mode 2700) and hmdfs decides traversal on the group
  bits, where `chmod` has no effect — the directory becomes
  untraversable and everything inside it fails with EACCES.
* **Script modes restored** after the copy (configure, config.guess,
  config.sub, install-sh, ...).
* **Triplets**: this dist's `config.sub` is dated 2022-01-03. It knows
  `aarch64` but not the `ohos` OS, so an ohos triplet is rejected; the
  `--build=arm-unknown-linux-gnu --host=aarch64-unknown-linux-gnu` pair
  passes through untouched and keeps build != host (cross mode).
* **Compilers from the profile** (`tools.build:compiler_executables`),
  never bare shell variables (R33).

Upstream tests (`make check`, automake TESTS) run unconditionally in
build(): 3 format/dump tests in src/, 22 parser unit tests in
src/parser/, 14 filter unit tests in src/liborcus/ — 39 TESTS in total
with the flags above. The per-directory `# TOTAL:/# PASS:/# FAIL:`
summaries are parsed, aggregated, emitted as the HMBS_UPSTREAM_TEST_RESULT
machine-evidence marker (dual channel: print + self.output.info),
persisted to build_folder/upstream_test_result.json and shipped into the
package res/ directory so test_package can re-emit the identical marker
on every run (conan skips build() on a cached binary). Any failure
closes the build with an exception — exit 0 without the marker never
counts as passed.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# NOTE: shell candidates are resolved inside _resolve_shell(): hnp bash
# first, PATH bash second, zsh strictly as last resort.

# Automake TESTS present in the 0.21.0 tarball that can never run in this
# adaptation (audited from src/Makefile.am, src/spreadsheet/Makefile.am
# and src/python/Makefile.am). Every entry needs --enable-spreadsheet-model
# (libixion-0.20 >= 0.20.0, not published in the registry) and all but the
# python ones additionally need --with-tools; the python ones need
# --enable-python on top. Reported as excluded (not passed) in the
# HMBS_UPSTREAM_TEST_RESULT marker.
EXCLUDED_UPSTREAM_TESTS = [
    # src/ filter round-trip tests (WITH_TOOLS + BUILD_SPREADSHEET_MODEL).
    "orcus-csv-test",
    "orcus-detect-test",
    "orcus-xml-mapped-test",
    "orcus-json-mapped-test",
    "orcus-ods-test",
    "orcus-ods-import-test",
    "orcus-xlsx-test",
    "orcus-xls-xml-test",
    "orcus-gnumeric-test",
    # src/liborcus/ unit tests gated on the gnumeric filter, disabled
    # because the BOOST_IOSTREAMS configure probe needs the compiled
    # libboost_iostreams library (not shipped by any registry boost).
    "gnumeric-cell-context-test",
    "gnumeric-sheet-context-test",
    # src/spreadsheet/ (BUILD_SPREADSHEET_MODEL).
    "auto-filter-test",
    # src/python/ (BUILD_PYTHON + BUILD_SPREADSHEET_MODEL).
    "test_xlsx.py",
    "test_ods.py",
    "test_xls_xml.py",
    "test_gnumeric.py",
]

EXCLUDED_REASON = (
    "Require --enable-spreadsheet-model (libixion-0.20 >= 0.20.0; no ixion "
    "Conan package is published in the registry) and --with-tools / "
    "--enable-python, all disabled in this adaptation; the two "
    "gnumeric-*-context tests additionally require the gnumeric filter, "
    "whose BOOST_IOSTREAMS configure probe needs the compiled "
    "libboost_iostreams library (not shipped by any registry boost). "
    "See notes.md 'Scope' and the PR body 'supplementary notes'."
)


class LiborcusConan(ConanFile):
    name = "liborcus"
    version = "0.21.0"
    description = ("Standalone file import filter library for spreadsheet "
                   "documents (ODS, XLSX, CSV and more)")
    license = "MPL-2.0"
    homepage = "https://gitlab.com/orcus/orcus"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = "spreadsheet", "ods", "xlsx", "csv", "import-filter"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # mdds-3.0 >= 3.0.0 is a hard configure requirement (headers only).
        self.requires("mdds/3.2.1")
        # Boost headers (boost.system is header-only since 1.70, so the
        # configure check is header-only too). Pinned to the exact version
        # mdds already depends on so the graph never wants two boosts.
        self.requires("boost/1.90.0")
        # zlib is a hard requirement of liborcus-parser. Pinned to the
        # version the merged libwpd recipe already validated, so the
        # binary is known to be published.
        self.requires("zlib/1.3.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "liborcus is adapted for Linux and OHOS, not %s"
                % self.settings.os
            )

    def layout(self):
        # Shallow folders (cyrus-sasl-login precedent): the default
        # basic_layout() build dir (p/b/<hash>/b/build-release) triggers
        # an HMDFS getcwd storm with the OHOS system bash
        # (DRAFT-6487-classads-configshell-hmdfs-getcwd: shell-init
        # "cannot access parent directories" -> "working directory cannot
        # be determined"), while one level up (p/b/<hash>/b) is normal.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def generate(self):
        env = Environment()
        for name, value in self._build_environment_items().items():
            env.define(name, value)
        env.vars(self).save_script("conanbuild")

    def build(self):
        apply_conandata_patches(self)
        shell = self._resolve_shell()
        self._stage_source_tree()
        self._relax_umask_in_configure()
        with self._build_environment().vars(self).apply():
            args = " ".join(shlex.quote(a) for a in self._configure_args())
            self._run("%s ./configure %s" % (shlex.quote(shell), args))
            self._run("make -j1")
            self._run_upstream_tests()

    def package(self):
        # Pre-create the DESTDIR subdirs from Python (not via the shell's
        # mkdir -p): with --prefix=/ the default libdir expands to //lib,
        # so DESTDIR paths contain a double slash (log: .../p//lib/...).
        # Creating the normalized dirs first keeps the install working even
        # if one tool in the chain normalizes // differently from another.
        for subdir in ("lib", "include", "lib/pkgconfig"):
            try:
                os.makedirs(os.path.join(self.package_folder, subdir),
                            exist_ok=True)
            except OSError:
                pass
        with self._build_environment().vars(self).apply():
            # Round-5 strategy (rounds 2-4 exhausted and falsified: //lib
            # normalization deployed yet the same chmod ENOENT recurred;
            # round 3 proved src/parser/.libs/*.a exists at 6933404 bytes;
            # round 4 showed plain INSTALL works — dest lib already holds
            # pkgconfig — while only the libtool-wrapped copy fails, so the
            # defect is libtool-specific, not the INSTALL binary, the
            # DESTDIR path, or a missing source artifact). Stop trying to
            # make libtool succeed: attempt the normal install once, then
            # finish deterministically — keep-going install for headers/pc
            # plus a Python byte-copy of the verified .libs archives.
            self._assert_install_artifacts(rebuild=True)
            try:
                self._run_install()
            except ConanException as exc:
                self.output.warning(
                    "normal make install failed (%s); falling back to "
                    "keep-going install + manual lib copy" % exc)
                self._run_keep_going_install()
                self._manual_install_libs()
            # Headers/pc must be present regardless of which install path
            # ran: this round's preflight reached test_package but
            # test_orcus.cpp failed with 'orcus/base64.hpp file not found',
            # so the lib copy alone is not sufficient. Fill any gaps from
            # the staged tree with a verified Python copy.
            self._ensure_headers_and_pkgconfig()
        # Autotools install drops libtool archives next to the real libs;
        # they must not ship (libtool .la files record install prefixes).
        for stale in sorted(Path(self.package_folder, "lib").glob("*.la")):
            try:
                stale.unlink()
            except OSError:
                pass
        for stale in sorted(
                Path(self.package_folder, "lib").glob("*.dylib")):
            try:
                stale.unlink()
            except OSError:
                pass
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # Ship the persisted upstream result so test_package can re-emit
        # the identical HMBS_UPSTREAM_TEST_RESULT marker even when conan
        # skips build() on a cached binary.
        result_path = os.path.join(self.build_folder,
                                   "upstream_test_result.json")
        if os.path.isfile(result_path):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "upstream_test_result.json", self.build_folder,
                 res_dir, keep_path=False)
        else:
            self.output.warning(
                "upstream_test_result.json not found in build folder; "
                "package will lack upstream evidence")

    def _assert_install_artifacts(self, rebuild=False):
        """Verify the static archives `make install` must copy exist.

        Expected libtool outputs for --enable-static --disable-shared:
        src/parser/.libs/liborcus-parser-0.21.a and
        src/liborcus/.libs/liborcus-0.21.a. Every path is logged with its
        size so the next preflight log distinguishes "never built" from
        "copy failed". When rebuild=True a missing artifact triggers one
        `make -j1` retry before failing closed — a doomed install is never
        attempted silently.
        """
        candidates = [
            os.path.join("src", "parser", ".libs",
                         "liborcus-parser-0.21.a"),
            os.path.join("src", "liborcus", ".libs",
                         "liborcus-0.21.a"),
        ]
        missing = []
        for relative in candidates:
            absolute = os.path.join(self.build_folder, relative)
            if os.path.isfile(absolute):
                try:
                    size = os.path.getsize(absolute)
                except OSError:
                    size = -1
                self.output.info("install artifact present: %s (%d bytes)"
                                 % (relative, size))
            else:
                self.output.warning("install artifact MISSING: %s"
                                    % relative)
                missing.append(relative)
        # Also list the directories so a renamed output is visible.
        for directory in (os.path.join("src", "parser", ".libs"),
                          os.path.join("src", "liborcus", ".libs")):
            absolute = os.path.join(self.build_folder, directory)
            try:
                entries = sorted(os.listdir(absolute))
            except OSError as exc:
                self.output.warning("cannot list %s: %s" % (directory, exc))
                continue
            self.output.info("contents of %s: %s"
                             % (directory, " ".join(entries[:40]) or "(empty)"))
        if missing and rebuild:
            self.output.warning(
                "rebuilding before install (%d missing); see list above"
                % len(missing))
            self._run("make -j1")
            still = [r for r in missing
                     if not os.path.isfile(os.path.join(self.build_folder, r))]
            if still:
                raise ConanException(
                    "static archives still missing after rebuild: %s; "
                    "refusing a doomed make install" % ", ".join(still))
        elif missing:
            raise ConanException(
                "static archives missing for make install: %s"
                % ", ".join(missing))

    def _baked_install_program(self):
        """Return the INSTALL program baked into src/parser/Makefile.

        AC_PROG_INSTALL resolves the system `install` at configure time and
        bakes the absolute path into every Makefile. The profile pins tools
        under /data/service/hnp/bin which this worker lacks (see the CC/CXX
        PATH fallback); a baked INSTALL under a missing prefix would make
        every libtool copy fail while leaving only the trailing chmod
        ENOENT visible. Returns (full_line, program_path_or_None).
        """
        makefile = os.path.join(self.build_folder, "src", "parser",
                                "Makefile")
        try:
            with open(makefile, "r", encoding="utf-8",
                      errors="replace") as handle:
                for line in handle:
                    if line.startswith("INSTALL = "):
                        full = line.strip()
                        # Value looks like "/path/install -c" or
                        # "$(SHELL) .../install-sh -c".
                        value = full[len("INSTALL = "):].strip()
                        first = value.split()[0] if value.split() else ""
                        if first.startswith("$"):
                            return full, None
                        return full, first
        except OSError as exc:
            self.output.warning("cannot read src/parser/Makefile: %s" % exc)
        return "", None

    def _run_install(self):
        """Run `make install` with captured output and INSTALL fallback.

        Round-4 strategy (rounds 2-3 exhausted: //lib normalization deployed
        yet the same chmod ENOENT recurred, and round 3 proved the source
        .a exists at 6933404 bytes — so the libtool copy itself fails and
        its message is truncated away by the HMBS summarizer). This runs
        V=1 install captured, re-emits the tail via self.output.info so the
        next summary keeps the real failing line, and — only when the
        Makefile-baked INSTALL program is absent from this worker — retries
        once with the dist install-sh that needs no system install binary.
        """
        baked_line, program = self._baked_install_program()
        self.output.info("baked parser INSTALL: %r" % baked_line)
        try:
            which_install = shutil.which("install")
        except Exception:
            which_install = None
        self.output.info("PATH install: %r" % which_install)
        dest = shlex.quote(self.package_folder)
        base = "make -j1 V=1 install DESTDIR=%s" % dest
        shell, environment = self._prepare_run_environment(base)
        if base.startswith("make") and "SHELL=" not in base:
            base = base + self._make_shell_assignment()
        self.output.info("effective make command: %s" % base)
        proc = subprocess.run(
            [shell, "-c", base + " < /dev/null"], env=environment,
            cwd=self.build_folder, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=3600)
        output = proc.stdout or ""
        tail = output.splitlines()[-40:]
        for line in tail:
            self.output.info("[install] %s" % line)
        if proc.returncode == 0:
            return
        # Failure path: dump the evidence the summary would otherwise cut.
        self._dump_install_evidence()
        if program and not os.path.isfile(program) and which_install is None:
            fallback = os.path.join(self.build_folder, "install-sh")
            if os.path.isfile(fallback):
                retry = ("%s INSTALL=%s" %
                         (base, shlex.quote("%s -c" % fallback)))
                self.output.warning(
                    "baked INSTALL %r missing and no PATH install; "
                    "retrying once with dist install-sh: %s"
                    % (program, retry))
                proc2 = subprocess.run(
                    [shell, "-c", retry + " < /dev/null"], env=environment,
                    cwd=self.build_folder, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    timeout=3600)
                output2 = proc2.stdout or ""
                for line in output2.splitlines()[-40:]:
                    self.output.info("[install-retry] %s" % line)
                if proc2.returncode == 0:
                    return
                self._dump_install_evidence()
                raise ConanException(
                    "make install failed even with dist install-sh "
                    "(rc=%d then rc=%d); see [install] tail above"
                    % (proc.returncode, proc2.returncode))
        raise ConanException(
            "make install failed (rc=%d); see [install] tail above"
            % proc.returncode)

    def _run_keep_going_install(self):
        """Run `make -k install` so non-libtool parts still land.

        With `-k` make continues past the failing libtool
        install-libLTLIBRARIES target and still installs headers,
        pkgconfig files and any other installable artifacts. The return
        code is tolerated (non-zero is expected while the libtool target
        fails); the tail is logged for evidence.
        """
        dest = shlex.quote(self.package_folder)
        base = "make -j1 -k V=1 install DESTDIR=%s" % dest
        shell, environment = self._prepare_run_environment(base)
        if base.startswith("make") and "SHELL=" not in base:
            base = base + self._make_shell_assignment()
        self.output.info("keep-going install command: %s" % base)
        proc = subprocess.run(
            [shell, "-c", base + " < /dev/null"], env=environment,
            cwd=self.build_folder, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=3600)
        output = proc.stdout or ""
        for line in output.splitlines()[-20:]:
            self.output.info("[install-keepgoing] %s" % line)
        self.output.info("keep-going install rc=%d (tolerated)"
                         % proc.returncode)

    def _manual_install_libs(self):
        """Copy the verified .libs archives into the package lib.

        The source bytes are the exact files `make install` would have
        copied (verified present by _assert_install_artifacts, sizes up
        to ~7 MB, never stubs). Both static archives are required; any
        shared objects present (shared=True builds) are copied as well
        with their symlinks preserved. Ends with a hard verification —
        both archives must exist non-empty in the destination.
        """
        dest_lib = os.path.join(self.package_folder, "lib")
        try:
            os.makedirs(dest_lib, exist_ok=True)
        except OSError:
            pass
        pairs = [
            (os.path.join("src", "parser", ".libs",
                          "liborcus-parser-0.21.a"),
             "liborcus-parser-0.21.a"),
            (os.path.join("src", "liborcus", ".libs",
                          "liborcus-0.21.a"),
             "liborcus-0.21.a"),
        ]
        for relative, name in pairs:
            src = os.path.join(self.build_folder, relative)
            dst = os.path.join(dest_lib, name)
            if not os.path.isfile(src):
                raise ConanException(
                    "manual install source missing: %s" % relative)
            shutil.copy2(src, dst)
            try:
                os.chmod(dst, 0o644)
            except OSError as exc:
                self.output.warning(
                    "chmod 644 %s failed (tolerated): %s" % (name, exc))
            try:
                size = os.path.getsize(dst)
            except OSError:
                size = -1
            self.output.info("manual install copied: %s -> %s (%d bytes)"
                             % (relative, name, size))
        # Shared-build companion files, if any (static builds: no-op).
        for directory in (os.path.join("src", "parser", ".libs"),
                          os.path.join("src", "liborcus", ".libs")):
            absolute = os.path.join(self.build_folder, directory)
            try:
                entries = sorted(os.listdir(absolute))
            except OSError:
                continue
            for entry in entries:
                if entry.endswith((".so", ".so.0", ".dylib")) or ".so." in entry:
                    src = os.path.join(absolute, entry)
                    dst = os.path.join(dest_lib, entry)
                    if os.path.islink(src):
                        try:
                            target = os.readlink(src)
                            if os.path.lexists(dst):
                                os.unlink(dst)
                            os.symlink(target, dst)
                            self.output.info(
                                "manual install symlinked: %s -> %s"
                                % (entry, target))
                        except OSError as exc:
                            self.output.warning(
                                "symlink %s failed: %s" % (entry, exc))
                    elif os.path.isfile(src) and not os.path.isfile(dst):
                        shutil.copy2(src, dst)
                        self.output.info(
                            "manual install copied shared: %s" % entry)
        for _, name in pairs:
            dst = os.path.join(dest_lib, name)
            if (not os.path.isfile(dst) or
                    os.path.getsize(dst) == 0):
                raise ConanException(
                    "manual install verification failed for %s" % name)
        try:
            entries = sorted(os.listdir(dest_lib))
        except OSError as exc:
            raise ConanException(
                "cannot list dest lib after manual install: %s" % exc)
        self.output.info("dest lib after manual install: %s"
                         % (" ".join(entries[:40]) or "(empty)"))

    def _ensure_headers_and_pkgconfig(self):
        """Verify headers/pc landed; fill gaps with a Python copy.

        This round's preflight compiled the library but test_package
        failed at `#include <orcus/base64.hpp> file not found`, so the
        archived .a files alone do not make a consumable package. The
        keep-going `make -k install` is supposed to land headers/pc, but
        on the device it can be truncated by the failing libtool target.
        This helper runs on both install paths: it checks the two header
        locations the consumer can use, copies the staged
        `include/orcus` tree into `include/liborcus-0.21/orcus` when the
        versioned dir is missing, and copies any built `*.pc` files into
        `lib/pkgconfig`. Ends with a hard verification — base64.hpp must
        exist non-empty — so a header-less package never reaches
        test_package silently.
        """
        pkg_include_versioned = os.path.join(
            self.package_folder, "include", "liborcus-0.21", "orcus")
        pkg_include_plain = os.path.join(
            self.package_folder, "include", "orcus")
        for probe in (os.path.join(pkg_include_versioned, "base64.hpp"),
                      os.path.join(pkg_include_plain, "base64.hpp")):
            if os.path.isfile(probe):
                try:
                    size = os.path.getsize(probe)
                except OSError:
                    size = -1
                self.output.info("header present: %s (%d bytes)"
                                 % (os.path.relpath(probe,
                                                    self.package_folder),
                                    size))
            else:
                self.output.warning("header MISSING: %s"
                                    % os.path.relpath(probe,
                                                      self.package_folder))
        if not os.path.isfile(os.path.join(pkg_include_versioned,
                                            "base64.hpp")):
            staged = os.path.join(self.build_folder, "include", "orcus")
            if not os.path.isdir(staged):
                staged = os.path.join(self.source_folder, "include", "orcus")
            if os.path.isdir(staged):
                try:
                    os.makedirs(pkg_include_versioned, exist_ok=True)
                except OSError:
                    pass
                copied = 0
                for root, _, files in os.walk(staged):
                    rel = os.path.relpath(root, staged)
                    dest_dir = (pkg_include_versioned if rel == "."
                                else os.path.join(pkg_include_versioned, rel))
                    try:
                        os.makedirs(dest_dir, exist_ok=True)
                    except OSError:
                        pass
                    for name in files:
                        src = os.path.join(root, name)
                        dst = os.path.join(dest_dir, name)
                        try:
                            shutil.copy2(src, dst)
                            copied += 1
                        except OSError as exc:
                            self.output.warning(
                                "header copy %s failed: %s" % (name, exc))
                self.output.info("manual header copy: %d files from %s"
                                 % (copied, staged))
            else:
                self.output.warning(
                    "staged header source missing: %s" % staged)
        dest_pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        try:
            existing_pc = sorted(f for f in os.listdir(dest_pc_dir)
                                 if f.endswith(".pc")) if os.path.isdir(
                dest_pc_dir) else []
        except OSError:
            existing_pc = []
        self.output.info("dest pkgconfig contents: %s"
                         % (" ".join(existing_pc[:20]) or "(empty)"))
        if not existing_pc:
            try:
                os.makedirs(dest_pc_dir, exist_ok=True)
            except OSError:
                pass
            for search_root in (self.build_folder, self.source_folder):
                for root, _, files in os.walk(search_root):
                    for name in files:
                        if not name.endswith(".pc"):
                            continue
                        if "liborcus" not in name and "orcus" not in name:
                            continue
                        src = os.path.join(root, name)
                        dst = os.path.join(dest_pc_dir, name)
                        if os.path.isfile(dst):
                            continue
                        try:
                            shutil.copy2(src, dst)
                            self.output.info(
                                "manual pc copy: %s" % os.path.relpath(
                                    src, search_root))
                        except OSError as exc:
                            self.output.warning(
                                "pc copy %s failed: %s" % (name, exc))
        final_headers = [
            os.path.join(pkg_include_versioned, "base64.hpp"),
            os.path.join(pkg_include_versioned, "csv_parser.hpp"),
            os.path.join(pkg_include_versioned, "json_parser.hpp"),
            os.path.join(pkg_include_versioned, "sax_parser.hpp"),
            os.path.join(pkg_include_versioned, "string_pool.hpp"),
        ]
        missing = [p for p in final_headers
                   if not os.path.isfile(p) or os.path.getsize(p) == 0]
        # Plain include dir is a fallback for the consumer; versioned dir
        # is the contract, so only the versioned dir is hard-gated.
        if missing:
            # Last chance: mirror versioned tree to plain include dir is
            # handled by package_info includedirs; here just report.
            for path in final_headers:
                try:
                    size = os.path.getsize(path) if os.path.isfile(
                        path) else -1
                except OSError:
                    size = -1
                self.output.info("final header %s: %d bytes"
                                 % (os.path.relpath(path,
                                                    self.package_folder),
                                    size))
            raise ConanException(
                "packaged headers missing: %s; refusing a header-less "
                "package" % ", ".join(
                    os.path.relpath(p, self.package_folder)
                    for p in missing))
        self.output.info("packaged headers verified: %d files" %
                         len(final_headers))

    def _dump_install_evidence(self):
        """Emit .la metadata + dest listing after an install failure."""
        la_path = os.path.join(self.build_folder, "src", "parser",
                               "liborcus-parser-0.21.la")
        try:
            with open(la_path, "r", encoding="utf-8",
                      errors="replace") as handle:
                for line in handle.read().splitlines():
                    if line.startswith(("dlname=", "old_library=",
                                        "libdir=", "dependency_libs=")):
                        self.output.info("[install] la %s" % line[:500])
        except OSError as exc:
            self.output.warning("[install] cannot read parser .la: %s" % exc)
        dest_lib = os.path.join(self.package_folder, "lib")
        try:
            entries = sorted(os.listdir(dest_lib))
        except OSError as exc:
            self.output.warning("[install] cannot list dest lib: %s" % exc)
        else:
            self.output.info("[install] dest lib contents: %s"
                             % (" ".join(entries[:40]) or "(empty)"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "liborcus")
        self.cpp_info.set_property("cmake_target_name",
                                   "liborcus::liborcus")
        self.cpp_info.set_property("pkg_config_name", "liborcus-0.21")
        # Static link order matters: liborcus references liborcus-parser,
        # which references zlib. (Same order as upstream liborcus.pc.in.)
        self.cpp_info.libs = ["orcus-0.21", "orcus-parser-0.21"]
        # Upstream installs headers under <includedir>/liborcus-0.21/orcus/
        # (notes.md Scope), so the versioned dir is the primary include
        # root. Keep plain "include" as well: if a keep-going install ever
        # lands headers one level up, the consumer still finds
        # <orcus/base64.hpp> instead of failing closed at test_package
        # compile time (this round's failure).
        self.cpp_info.includedirs = ["include/liborcus-0.21", "include"]
        self.cpp_info.requires = ["mdds::mdds", "zlib::zlib",
                                  "boost::boost"]

    # ── configure arguments ──────────────────────────────────────────

    def _configure_args(self):
        args = []
        if str(self.settings.os) == "OHOS":
            # 2022-01-03 config.sub: `aarch64` is known, `ohos` is not, so
            # an ohos triplet is rejected — a four-part name with the
            # `unknown` vendor passes through untouched. build != host
            # keeps configure in cross mode.
            args.extend(["--build=arm-unknown-linux-gnu",
                         "--host=aarch64-unknown-linux-gnu"])
        args.append("--prefix=/")
        # Normalize libdir/includedir: with prefix=/ autoconf expands
        # libdir to ${exec_prefix}/lib = //lib, so DESTDIR installs use a
        # double slash (.../p//lib/liborcus-parser-0.21.a in this round's
        # log) and the libtool chmod step reports "No such file or
        # directory" on the device filesystem. Pinning single-slash absolute
        # paths keeps DESTDIR + libdir single-slashed (.../p/lib/...).
        args.append("--libdir=/lib")
        args.append("--includedir=/include")
        if self.options.shared:
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend(["--enable-static", "--disable-shared"])
        args.append("--disable-dependency-tracking")
        # Feature scope (see module docstring for the reasons).
        args.extend(["--disable-spreadsheet-model",
                     "--disable-python",
                     "--without-tools",
                     "--without-gnumeric-filter",
                     "--without-benchmark"])
        # Boost headers live in the Conan package, not in a standard
        # prefix; boost.m4 honors --with-boost=DIR (or BOOST_ROOT).
        boost_pkg = self.dependencies["boost"].package_folder
        args.append("--with-boost=%s" % boost_pkg)
        return args

    # ── build environment ────────────────────────────────────────────

    def _writable_tmpdir(self):
        """Task-private writable temp dir (HMBS-injected TMPDIR preferred).

        Device /tmp is a read-only erofs mount (E002); the compiler driver,
        the shell (zsh TMPPREFIX) and autoconf mktemp all need a writable
        root. Mirrors cyrus-sasl-login/avr-binutils precedent: prefer the
        HMBS-injected TMPDIR/TMP/TEMP, else fall back to build_folder/.tmp.

        CI #50803 (configure dies with "C++ compiler cannot create
        executables" while the same clang++ passes a -print-target-triple
        probe): an isdir/makedirs check is not enough — a candidate may
        exist yet reject writes (missing dir, read-only mount, sandbox
        ACL), and clang then fails with "unable to make temporary file"
        which autoconf reports as a broken compiler (Error 77). So every
        candidate gets a real write probe (create + 1-byte write + unlink)
        before it is returned; failures fall through to the next
        candidate. build_folder/.tmp is always a candidate because conan
        has already written sources there. The chosen dir and any skipped
        candidates are logged for the next round's diagnosis.
        """
        def _probe(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError as exc:
                self.output.warning(
                    "tmpdir candidate %r makedirs failed: %s"
                    % (directory, exc))
                return False
            probe = os.path.join(directory, ".hmbs-write-probe")
            try:
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
            except OSError as exc:
                self.output.warning(
                    "tmpdir candidate %r not writable: %s"
                    % (directory, exc))
                return False
            try:
                os.unlink(probe)
            except OSError:
                pass
            return True
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and _probe(candidate):
                self.output.info(
                    "writable tmpdir from %s: %s" % (key, candidate))
                return candidate
            elif candidate:
                self.output.warning(
                    "tmpdir candidate from %s rejected: %s"
                    % (key, candidate))
        fallback = os.path.join(self.build_folder, ".tmp")
        if _probe(fallback):
            self.output.info("writable tmpdir fallback: %s" % fallback)
            return fallback
        # Last resort: return the fallback anyway so the failure surfaces
        # as an explicit tmpdir error, not a misleading compiler error.
        self.output.warning(
            "no writable tmpdir candidate; returning %s anyway" % fallback)
        return fallback

    def _mktemp_fallback_shim_for_ohos(self, tmpdir):
        """Shadow mktemp for ./conf* when HMBS requests the fallback.

        Direct reuse of the cyrus-sasl-login precedent for HMBS platform
        diagnosis [unsafe_local_mktemp]: when HMBS injects
        HMBS_AUTOCONF_MKTEMP_FALLBACK=1, a directory created by mktemp on
        the device filesystem cannot be written by Autoconf afterwards, so
        calls for "./conf*" must fail and let Autoconf fall back to its
        `mkdir` path. All other mktemp calls delegate to the real binary;
        TMPDIR itself stays writable.
        """
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "1":
            return ""
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!/system/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "for candidate in /system/bin/mktemp /bin/mktemp "
            "/usr/bin/mktemp; do\n"
            "  if [ -x \"$candidate\" ]; then\n"
            "    exec \"$candidate\" \"$@\"\n"
            "  fi\n"
            "done\n"
            "exec command -p mktemp \"$@\"\n"
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass
        except OSError:
            return ""
        return shim_dir

    def _prepare_run_environment(self, command=None):
        """Environment snapshot for raw configure/make subprocesses.

        Exports TMPDIR/TMP/TEMP/TMPPREFIX to the same writable root so the
        compiler, the shell and mktemp never touch read-only /tmp (E002),
        and prepends the autoconf mktemp shim to PATH only when HMBS
        requests it. Subprocesses are invoked as [shell, "-c", cmd] so the
        device /bin/sh (whose own temp lives in /tmp) is bypassed.

        Shell split (2026-09-17 preflight: `zsh:cd:21: no such file or
        directory: src include` + `Making all in src include`): configure
        needs bash-or-zsh (autoconf 2.71 `exec 7<&0` rejects toybox sh),
        but automake's recursive make needs POSIX word splitting
        (`list='src include ...'; for subdir in $list`), which zsh
        without SH_WORD_SPLIT does not do — the whole list becomes one
        `cd` argument.  So configure commands use _resolve_shell()
        (bash > zsh) while every make command uses _resolve_make_shell()
        (bash > /system/bin/sh > /bin/sh > zsh-shwordsplit wrapper).
        """
        environment = dict(os.environ)
        if command is not None and "configure" in command:
            shell = self._resolve_shell()
        elif command is None:
            # Callers without a command (legacy path) get the POSIX
            # make shell: it is safe for make and never chosen for
            # configure without an explicit "configure" command.
            shell = self._resolve_make_shell()
        else:
            shell = self._resolve_make_shell()
        environment["SHELL"] = shell
        # CONFIG_SHELL is only consumed by configure; always point it at
        # a configure-capable shell (bash > zsh) so a POSIX /system/bin/sh
        # SHELL never leaks into the configure probe.
        try:
            environment["CONFIG_SHELL"] = self._resolve_shell()
        except ConanInvalidConfiguration:
            environment["CONFIG_SHELL"] = shell
        tmpdir = self._writable_tmpdir()
        environment["TMPDIR"] = tmpdir
        environment["TMP"] = tmpdir
        environment["TEMP"] = tmpdir
        tmpprefix = os.path.join(tmpdir, "zsh")
        try:
            os.makedirs(tmpprefix, exist_ok=True)
        except OSError:
            pass
        environment["TMPPREFIX"] = tmpprefix
        shim_dir = self._mktemp_fallback_shim_for_ohos(tmpdir)
        if shim_dir:
            environment["PATH"] = shim_dir + os.pathsep + environment.get(
                "PATH", "")
        return shell, environment

    def _build_environment_items(self):
        """Shared environment for configure/make/make-check subprocesses.

        Everything a raw subprocess needs, since conan's toolchain script
        is only sourced by conan's own Autotools() helper (R33: compilers
        come from the declared profile conf, never from ambient PATH).
        """
        items = {}
        items.update(self._compiler_environment_items())
        # SHELL drives make's recipe shells → must be POSIX (bash or
        # /system/bin/sh); CONFIG_SHELL drives configure → must be
        # bash-or-zsh.  See _prepare_run_environment for the split.
        try:
            items["SHELL"] = self._resolve_make_shell()
        except ConanInvalidConfiguration:
            items["SHELL"] = self._resolve_shell()
        try:
            items["CONFIG_SHELL"] = self._resolve_shell()
        except ConanInvalidConfiguration:
            items["CONFIG_SHELL"] = items["SHELL"]
        tmpdir = self._writable_tmpdir()
        items["TMPDIR"] = tmpdir
        items["TMP"] = tmpdir
        items["TEMP"] = tmpdir
        tmpprefix = os.path.join(tmpdir, "zsh")
        try:
            os.makedirs(tmpprefix, exist_ok=True)
        except OSError:
            pass
        items["TMPPREFIX"] = tmpprefix
        items.update(self._dependency_environment_items())
        return items

    def _compiler_environment_items(self):
        """CC/CXX from the profile conf, with PATH fallback and evidence.

        The profile pins an absolute device path
        (/data/service/hnp/bin/clang[++]); when that file is absent on the
        executing worker, exporting it verbatim makes autoconf die with
        "C++ compiler cannot create executables" (the driver cannot even
        be exec'd). So each entry is verified with isfile; a missing entry
        falls back to a PATH lookup of the same basename (hmbs prepends
        the real tool directories to PATH, and the test_package recipe
        already resolves compilers the same way). Anything finally
        exported is logged with its target triple probe so the next
        preflight log shows exactly which driver ran.
        """
        raw = self.conf.get("tools.build:compiler_executables",
                            default=None)
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError:
                self.output.warning(
                    "tools.build:compiler_executables is not JSON: %r" % raw)
                raw = None
        if not isinstance(raw, dict):
            # Scoped-conf form (tools.build:compiler_executables:c / :cpp),
            # as used by the ADAPTATION_GUIDE Makefile template.
            scoped = {}
            for key in ("c", "cpp"):
                try:
                    value = self.conf.get(
                        "tools.build:compiler_executables:%s" % key,
                        default=None)
                except ConanException:
                    value = None
                if isinstance(value, str) and value:
                    scoped[key] = value
            raw = scoped or None
        if not raw:
            self.output.warning(
                "no tools.build:compiler_executables in conf; "
                "leaving CC/CXX to PATH")
            return {}
        mapping = {"c": ("CC", "clang"), "cpp": ("CXX", "clang++")}
        items = {}
        for key, (variable, basename) in mapping.items():
            candidate = raw.get(key) or raw.get(key.upper())
            resolved = None
            if candidate and os.path.isfile(candidate):
                resolved = candidate
            else:
                if candidate:
                    self.output.warning(
                        "%s=%r not found on this worker; falling back "
                        "to PATH lookup" % (variable, candidate))
                fallback = shutil.which(
                    os.path.basename(candidate) if candidate else basename)
                if fallback:
                    resolved = fallback
            if resolved:
                items[variable] = resolved
                self.output.info(
                    "compiler %s resolved to %s" % (variable, resolved))
                try:
                    proc = subprocess.run(
                        [resolved, "-print-target-triple"],
                        capture_output=True, text=True, timeout=60)
                    triple = (proc.stdout or "").strip()
                    self.output.info(
                        "compiler %s triple: %r (rc=%d)"
                        % (variable, triple, proc.returncode))
                except OSError as exc:
                    self.output.warning(
                        "compiler %s triple probe failed: %s"
                        % (variable, exc))
            else:
                self.output.warning(
                    "compiler %s has no candidate (%r) and no PATH "
                    "fallback; leaving it unset" % (variable, candidate))
        return items

    def _dependency_environment_items(self):
        """ZLIB_*/MDDS_* pairs for upstream's two PKG_CHECK_MODULES calls.

        The device has no pkg-config, so configure must be handed the
        variables it would otherwise ask pkg-config for; PKG_CHECK_MODULES
        uses them verbatim when they are non-empty (device-verified by
        libwpd 0.10.3 for three such pairs).
        """
        zlib = self.dependencies["zlib"].package_folder
        mdds = self.dependencies["mdds"].package_folder
        return {
            "ZLIB_CFLAGS": "-I%s" % os.path.join(zlib, "include"),
            "ZLIB_LIBS": "-L%s -lz" % os.path.join(zlib, "lib"),
            "MDDS_CFLAGS": "-I%s" % os.path.join(mdds, "include",
                                                 "mdds-3.0"),
            # mdds is header-only and its own mdds.pc.in carries no Libs:
            # line, so upstream's link flags for it are empty. pkg.m4 only
            # skips the pkg-config call for a non-empty variable, hence a
            # whitespace-only value — semantically empty, matching upstream
            # metadata exactly.
            "MDDS_LIBS": " ",
        }

    def _build_environment(self):
        environment = Environment()
        for name, value in self._build_environment_items().items():
            environment.define(name, value)
        return environment

    # ── OHOS build machinery ─────────────────────────────────────────

    def _stage_source_tree(self):
        """Copy the source tree into the build folder (in-tree build).

        With the shallow layout (src_folder=".", build=".") Conan uses
        an in-source build where source_folder and build_folder resolve
        to the same directory; copying would raise "src and dst must
        have different values". Skip the copy in that case (cyrus-sasl
        precedent builds directly in source_folder) and still restore
        script modes below.
        """
        try:
            same = os.path.normcase(os.path.abspath(self.source_folder)) == os.path.normcase(os.path.abspath(self.build_folder))
        except Exception:
            same = self.source_folder == self.build_folder
        if same:
            self.output.info("in-source build: source and build folders coincide, skipping copy")
        else:
            copy(self, "*", src=self.source_folder, dst=self.build_folder)
        for relative in ("configure", "config.guess", "config.sub",
                         "install-sh", "missing", "depcomp", "compile",
                         "ltmain.sh", "config.status", "ar-lib",
                         "mkinstalldirs", "test-driver"):
            path = Path(self.build_folder, relative)
            if path.is_file():
                try:
                    path.chmod(path.stat().st_mode | 0o111)
                except OSError:
                    pass

    def _relax_umask_in_configure(self):
        """Rewrite `umask 077` -> `umask 022` in the generated configure.

        The scratch dir is created with `umask 077` giving mode 2700, and
        hmdfs decides traversal on the group bits where `chmod` is a
        no-op, so the directory is untraversable (EACCES on everything
        inside it). 022 yields a traversable scratch dir.
        """
        path = Path(self.build_folder, "configure")
        if not path.is_file():
            raise ConanException("configure script is missing: %s" % path)
        content = path.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException(
                "umask contract changed in configure: expected 2 "
                "occurrences of %r, found %d"
                % (needle, content.count(needle)))
        path.write_text(content.replace(needle, "umask 022"),
                        encoding="utf-8", newline="\n")

    def _shell_passes_getcwd(self, path):
        """Reject shells whose getcwd() fails on the HMDFS build dir.

        CI #50593 (OpenHarmonyPCDeveloper-CI-032): the OHOS system bash
        (/data/service/hnp/bin/bash) prints `shell-init: error retrieving
        current directory: getcwd: cannot access parent directories` and
        configure dies with `working directory cannot be determined`
        (DRAFT-6487-classads-configshell-hmdfs-getcwd). A plain
        `-c "exit 0"` probe passes anywhere, so additionally run
        `-c "pwd"` with cwd=build_folder (falling back to source_folder
        when the build dir does not exist yet) and require rc==0 plus no
        "error retrieving current directory" text.
        """
        probe_dir = None
        try:
            candidate = getattr(self, "build_folder", None)
            if candidate and os.path.isdir(candidate):
                probe_dir = candidate
            else:
                candidate = getattr(self, "source_folder", None)
                if candidate and os.path.isdir(candidate):
                    probe_dir = candidate
        except Exception:
            probe_dir = None
        try:
            if probe_dir:
                probed = subprocess.run(
                    [path, "-c", "pwd"],
                    capture_output=True, text=True, timeout=60,
                    cwd=probe_dir)
            else:
                probed = subprocess.run(
                    [path, "-c", "pwd"],
                    capture_output=True, text=True, timeout=60)
        except OSError:
            return False
        except Exception:
            return False
        if probed.returncode != 0:
            return False
        combined = (probed.stdout or "") + (probed.stderr or "")
        if "error retrieving current directory" in combined:
            return False
        return True

    def _resolve_shell(self):
        # Probe order: hnp bash first (only shell verified against this
        # autoconf 2.71 tree: toybox /system/bin/sh rejects `exec 7<&0`,
        # and zsh breaks automake's recursive make word splitting, so
        # zsh is strictly a last resort). PATH's `bash` is checked before
        # zsh because hmbs prepends the real tool directories to PATH.
        # NOTE: hmdfs reports fixed 660 modes where chmod is a no-op, so
        # os.access(X_OK) can be False for a working executable — isfile
        # plus a real `-c "exit 0"` probe decides, never the mode bits.
        checked = []
        candidates = []
        hnp_bash = "/data/service/hnp/bin/bash"
        candidates.append(hnp_bash)
        path_bash = shutil.which("bash")
        if path_bash and path_bash not in candidates:
            candidates.append(path_bash)
        for fallback in ("/usr/bin/zsh", "bash"):
            if fallback not in candidates:
                candidates.append(fallback)
        for candidate in candidates:
            path = candidate
            if os.path.sep not in candidate:
                found = shutil.which(candidate)
                checked.append("%s->%r" % (candidate, found))
                if not found:
                    continue
                path = found
            elif not os.path.isfile(path):
                checked.append("%s (missing)" % path)
                continue
            try:
                probed = subprocess.run(
                    [path, "-c", "exit 0"],
                    capture_output=True, timeout=60)
                if probed.returncode == 0:
                    if not self._shell_passes_getcwd(path):
                        checked.append(
                            "%s (getcwd fails on HMDFS build dir)" % path)
                        continue
                    return path
                checked.append("%s (probe rc=%d)"
                               % (path, probed.returncode))
            except OSError as exc:
                checked.append("%s (exec failed: %s)" % (path, exc))
        raise ConanInvalidConfiguration(
            "no suitable shell found (checked: %s; need the hnp bash, "
            "PATH bash, or zsh as last resort)"
            % "; ".join(checked))

    def _resolve_make_shell(self):
        """POSIX shell for make recipe shells (never bare zsh).

        Probe order: hnp bash, PATH bash, /system/bin/sh (toybox, POSIX
        word splitting OK), /bin/sh, then the bash basenames.  Bare zsh
        is deliberately NOT a candidate: without SH_WORD_SPLIT it keeps
        `for subdir in $list` as one word, so automake's all-recursive
        collapses to `Making all in src include` + `cd: no such file or
        directory: src include` (this round's failure).  If no POSIX
        shell exists, fall back to a shwordsplit wrapper around the
        resolved zsh so both the outer `[shell, "-c"]` launch and make's
        inner `$(SHELL) -c` recipes split correctly.
        NOTE: same hmdfs rule as _resolve_shell — isfile + live probe,
        never the X_OK mode bits.
        """
        checked = []
        candidates = []
        hnp_bash = "/data/service/hnp/bin/bash"
        candidates.append(hnp_bash)
        path_bash = shutil.which("bash")
        if path_bash and path_bash not in candidates:
            candidates.append(path_bash)
        for candidate in ("/system/bin/sh", "/bin/sh",
                          "/system/bin/bash", "/bin/bash"):
            if candidate not in candidates:
                candidates.append(candidate)
        for candidate in candidates:
            path = candidate
            if os.path.sep not in candidate:
                found = shutil.which(candidate)
                checked.append("%s->%r" % (candidate, found))
                if not found:
                    continue
                path = found
            elif not os.path.isfile(path):
                checked.append("%s (missing)" % path)
                continue
            try:
                probed = subprocess.run(
                    [path, "-c", "exit 0"],
                    capture_output=True, timeout=60)
                if probed.returncode == 0:
                    # Reject zsh masquerading as sh (e.g. /bin/sh -> zsh):
                    # it must split `for w in $list` POSIX-style.
                    split_probe = subprocess.run(
                        [path, "-c",
                         'list="a b"; n=0; for w in $list; do '
                         'n=$((n+1)); done; test "$n" = "2"'],
                        capture_output=True, timeout=60)
                    if split_probe.returncode == 0:
                        if not self._shell_passes_getcwd(path):
                            checked.append(
                                "%s (getcwd fails on HMDFS build dir)" % path)
                            continue
                        return path
                    checked.append(
                        "%s (no POSIX word splitting)" % path)
                    continue
                checked.append("%s (probe rc=%d)"
                               % (path, probed.returncode))
            except OSError as exc:
                checked.append("%s (exec failed: %s)" % (path, exc))
        # Last resort: zsh with shwordsplit forced via wrapper script.
        zsh = None
        try:
            zsh = self._resolve_shell()
        except ConanInvalidConfiguration:
            pass
        if zsh is not None and os.path.basename(zsh) == "zsh":
            wrapper = self._zsh_shwordsplit_wrapper(zsh)
            if wrapper:
                self.output.warning(
                    "no POSIX shell found (%s); using zsh-shwordsplit "
                    "wrapper %s" % ("; ".join(checked), wrapper))
                return wrapper
        raise ConanInvalidConfiguration(
            "no POSIX shell for make found (checked: %s; need bash or "
            "/system/bin/sh, or zsh for the shwordsplit wrapper)"
            % "; ".join(checked))

    def _zsh_shwordsplit_wrapper(self, zsh):
        """Create a `zsh -o shwordsplit` wrapper usable as make SHELL."""
        try:
            tmpdir = self._writable_tmpdir()
        except OSError:
            return ""
        wrapper_dir = os.path.join(tmpdir, "hmbs-make-shell")
        try:
            os.makedirs(wrapper_dir, exist_ok=True)
        except OSError:
            return ""
        wrapper = os.path.join(wrapper_dir, "make-shell")
        script = (
            "#!/system/bin/sh\n"
            "exec \"%s\" -o shwordsplit -c \"$@\"\n" % zsh
        )
        try:
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(wrapper, 0o755)
            except OSError:
                pass
        except OSError:
            return ""
        # The wrapper's shebang needs /system/bin/sh; if that file is
        # absent the wrapper cannot run — verify before returning it.
        if not os.path.isfile("/system/bin/sh"):
            alt = os.path.join(wrapper_dir, "make-shell-binsh")
            try:
                with open(alt, "w", encoding="utf-8",
                          newline="\n") as handle:
                    handle.write(
                        "#!/bin/sh\n"
                        "exec \"%s\" -o shwordsplit -c \"$@\"\n" % zsh)
                try:
                    os.chmod(alt, 0o755)
                except OSError:
                    pass
            except OSError:
                return ""
            return alt
        return wrapper

    def _make_shell_assignment(self):
        """Command-line SHELL assignment for make (overrides Makefile).

        Second-attempt strategy (2026-09-17 round 2, same fingerprint as
        round 1): exporting SHELL in the environment was NOT enough — the
        automake-generated Makefiles hard-code `SHELL = /bin/sh`, which
        takes precedence over the environment, so the inner recipe shells
        still ran as zsh (`zsh:cd:21: no such file or directory: src
        include`).  Per GNU make precedence only a command-line `make
        SHELL=<posix>` beats a Makefile assignment, hence this helper.
        The value comes from _resolve_make_shell() (bash >
        /system/bin/sh > /bin/sh, never bare zsh; word-splitting
        probed, shwordsplit wrapper as last resort).
        """
        make_shell = self._resolve_make_shell()
        assignment = " SHELL=%s" % shlex.quote(make_shell)
        self.output.info("make SHELL override:%s" % assignment)
        return assignment

    def _run(self, command):
        shell, environment = self._prepare_run_environment(command)
        # Evidence for the next preflight round: which drivers the raw
        # subprocess actually sees (R33: conan's toolchain script is
        # never sourced here).
        if "configure" in command or command.startswith("make"):
            for variable in ("CC", "CXX", "SHELL", "CONFIG_SHELL",
                             "TMPDIR", "PATH"):
                self.output.info(
                    "build env %s=%r"
                    % (variable, environment.get(variable)))
        if command.startswith("make") and "SHELL=" not in command:
            command = command + self._make_shell_assignment()
            self.output.info("effective make command: %s" % command)
        completed = subprocess.run(
            [shell, "-c", command + " < /dev/null"], env=environment,
            cwd=self.build_folder, stdin=subprocess.DEVNULL)
        if completed.returncode != 0:
            if "configure" in command:
                self._dump_config_log()
            raise ConanException(
                "build step failed (rc=%d): %s"
                % (completed.returncode, command))

    def _dump_config_log(self):
        """Print the config.log failure context, not just the tail.

        CI #50803: the last 80 lines of config.log are only the autoconf
        variable dump (WITH_XLSX_FILTER_TRUE, ZLIB_LIBS, ...), while the
        real compiler error ("unable to make temporary file", the failing
        conftest command and its stderr) sits in the middle where the
        "checking whether the C/C++ compiler works" test failed. Dumping
        only the tail leaves the next round blind, so this emits:
        (1) a ±12-line window around each of the first 3 hits of the
        failure markers (cannot create executables / unable to make
        temporary file / failed program was / cannot run C), and
        (2) the last 40 lines as before. Both channels (self.output.info
        for the persisted log, print for the summarizer) carry the same
        content.
        """
        path = os.path.join(self.build_folder, "config.log")
        if not os.path.isfile(path):
            self.output.warning("config.log not found at %s" % path)
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                lines = handle.read().splitlines()
        except OSError as exc:
            self.output.warning("cannot read config.log: %s" % exc)
            return
        markers = ("cannot create executables",
                   "unable to make temporary file",
                   "failed program was",
                   "cannot run C",
                   "No such file or directory",
                   "Read-only file system",
                   "Permission denied")
        emitted = []
        hits = 0
        for index, line in enumerate(lines):
            lowered = line.lower()
            if any(m.lower() in lowered for m in markers):
                if hits >= 3:
                    break
                hits += 1
                start = max(0, index - 12)
                end = min(len(lines), index + 13)
                emitted.append("--- config.log context %d (lines %d-%d) ---"
                               % (hits, start + 1, end))
                emitted.extend(lines[start:end])
        emitted.append("--- config.log tail (%d lines total, last 40) ---"
                       % len(lines))
        emitted.extend(lines[-40:])
        self.output.info("config.log evidence (%d lines):" % len(lines))
        for line in emitted:
            self.output.info("[config.log] %s" % line)
        print("--- config.log evidence ---", flush=True)
        for line in emitted:
            print(line, flush=True)

    # ── upstream tests with machine evidence ─────────────────────────

    def _run_upstream_tests(self):
        """Run `make check` and emit the HMBS_UPSTREAM_TEST_RESULT marker.

        The automake summary (`# TOTAL:` / `# PASS:` / `# FAIL:` /
        `# SKIP:` / `# ERROR:`) is parsed per directory and aggregated;
        counts come from the real device output, never from estimates.
        Anything unexpected — no summary lines, skipped tests, any
        failure or error — fails the build closed.
        """
        shell, environment = self._prepare_run_environment("make check")
        check_cmd = "make check" + self._make_shell_assignment()
        self.output.info("Running upstream test suite: %s" % check_cmd)
        proc = subprocess.run(
            [shell, "-c", check_cmd + " < /dev/null"], env=environment,
            cwd=self.build_folder, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=3600)
        output = proc.stdout or ""
        for line in output.splitlines()[-30:]:
            self.output.info("[upstream] %s" % line)
        total = passed = failed = skipped = 0
        summaries = len(re.findall(r"# TOTAL:\s+(\d+)", output))
        for match in re.finditer(
                r"# (TOTAL|PASS|SKIP|FAIL|XFAIL|XPASS|ERROR):\s+(\d+)",
                output):
            value = int(match.group(2))
            kind = match.group(1)
            if kind == "TOTAL":
                total += value
            elif kind in ("PASS", "XFAIL"):
                # XFAIL is an expected failure: automake counts it toward
                # TOTAL as a non-failing outcome, so it belongs with PASS.
                # (Fixed 2026-09-17: automake pads single-digit counts as
                # `# PASS:  39` with two spaces, so the separator is \s+.)
                passed += value
            elif kind == "SKIP":
                skipped += value
            elif kind in ("FAIL", "ERROR"):
                failed += value
            elif kind == "XPASS":
                failed += value
        if summaries == 0 or total == 0:
            raise ConanException(
                "make check produced no automake test summary "
                "(rc=%d); refusing to pass silently" % proc.returncode)
        status = "passed" if (proc.returncode == 0 and failed == 0
                              and skipped == 0
                              and passed == total) else "failed"
        marker = {
            "status": status,
            "framework": "automake-check",
            "command": "make check",
            "discovered": total,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": total + len(EXCLUDED_UPSTREAM_TESTS),
            "excluded": len(EXCLUDED_UPSTREAM_TESTS),
            "excluded_cases": EXCLUDED_UPSTREAM_TESTS,
            "reason": EXCLUDED_REASON,
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(marker)
        print(line, flush=True)
        self.output.info(line)
        sys.stdout.flush()
        try:
            result_path = os.path.join(self.build_folder,
                                       "upstream_test_result.json")
            with open(result_path, "w", encoding="utf-8") as handle:
                json.dump(marker, handle, ensure_ascii=False)
            self.output.info("persisted upstream test result to %s"
                             % result_path)
        except OSError as exc:
            raise ConanException(
                "failed to persist upstream_test_result.json: %s" % exc)
        if skipped > 0:
            raise ConanException(
                "make check reported %d SKIPPED tests; the HMBS gate "
                "rejects skipped — fix or exclude with a documented reason "
                "(total=%d passed=%d failed=%d)"
                % (skipped, total, passed, failed))
        if status != "passed":
            raise ConanException(
                "upstream make check failed (total=%d passed=%d failed=%d "
                "rc=%d)" % (total, passed, failed, proc.returncode))
