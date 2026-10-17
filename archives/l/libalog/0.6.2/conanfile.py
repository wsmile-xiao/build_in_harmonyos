#!/usr/bin/env python3
"""Conan recipe — libalog 0.6.2 (Alog: stackable logging framework for Ada)

Alog (codelabs.ch) is a stackable logging framework for Ada: Logger /
Tasked_Logger / Active_Logger, File_Descriptor + Syslog facilities,
transforms and policies.  Upstream builds with GNAT project files
(alog.gpr / alog_tests.gpr) via gprbuild + gprinstall; no configure
or CMake is involved.

Ada toolchain: the published native OHOS GNAT, ``gcc-ada/9.5.0``
(consumed as a Conan tool requirement, adacgi/1.6 + libgmpada/1.6
precedent).  gnatmake drives the two build modes the recipe needs:

  static: compile src/*.adb (Alog library units) into obj/static-obj
          (+ src/glue_syslog.c via an aarch64-OHOS-gated C compiler)
          and archive everything into obj/static-lib/libalog.a.  The GPR's strict
          style/warning switches (-gnatyg* -gnatwa* -gnatwe) are
          diagnostics-only and are omitted (documented in notes.md).
  tests:  compile tests/test_runner.adb (Ahven 2.8 suite, fetched at
          build time from the official ahven-framework.com tarball,
          sha256-pinned) against the static objects; the binary is run
          from the source root (./data/*.ref fixtures) by build(),
          which parses the deterministic Ahven Text_Runner summary
          (Passed/Failed/Errors/Skipped lines).

Route history (see notes.md): rounds 1-6 bootstrapped an Alpine
aarch64 musl GNAT 13.2.1 toolchain (apk download + PT_INTERP rewrite
+ binary-sign-tool signing).  The 35MB compiler backends (gnat1, cc1)
segfault instantly (rc=-11, zero output) after signing on BOTH the
pristine/direct and objcopy sign paths, while small tools pass; stack
hardening, LD_PRELOAD isolation, pristine retry and NEEDED triage did
not change the fingerprint (triage: NEEDED reads back empty).  The
Alpine-13.2.1 route is therefore abandoned in favour of the
repository's validated native Ada compiler, exactly like the merged
Ada libraries adacgi/1.6 and libgmpada/1.6.

Upstream test count: 81 Add_Test_Routine registrations across 13
Ahven test cases (audited, see notes.md and
test_package/MANIFEST.yml); marker counts come from the Text_Runner
summary lines only, never from string counting.
"""
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


# ---------------------------------------------------------------------------
# Ahven 2.8 — upstream test framework (build-time only, never packaged)
#
# alog_tests.gpr does `with "ahven";` and every tests/*.adb does
# `with Ahven;`: the 81 upstream test routines cannot compile without
# it.  Ahven is a small (~3K SLOC) pure-Ada ISC-licensed framework;
# the 2.8 release (2020-10-17) matches the GNAT 9 era compiler used
# here.  Official tarball from ahven-framework.com, sha256 taken from
# the author's own sha256-sums.txt.  Unpacked into the build folder
# and compiled in-source via gnatmake -I flags (no install step);
# nothing from Ahven enters the package.
# ---------------------------------------------------------------------------
_AHVEN_VERSION = "2.8"
_AHVEN_TARBALL = "ahven-%s.tar.gz" % _AHVEN_VERSION
_AHVEN_SHA256 = "6ead94fbd1b95454e959cc2a343acfb2f733bcbf10d9a286214d1dec1b9e8e0c"
_AHVEN_URL = "https://www.ahven-framework.com/releases/%s" % _AHVEN_TARBALL

_ENV_SCRIPT = "libalog_gnat_env"


class LibalogConan(ConanFile):
    name = "libalog"
    version = "0.6.2"
    description = "Alog: stackable logging framework for Ada (loggers, file-descriptor/syslog facilities, transforms)"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.codelabs.ch/alog"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "The OHOS libalog package supports AArch64/armv8 only"
            )

    def build_requirements(self):
        # Native OHOS GNAT (adacgi/1.6 + libgmpada/1.6 precedent).
        self.tool_requires("gcc-ada/9.5.0")
        # GNU as/ld/ar for the GNAT driver and the static-archive step
        # (libgmpada/1.6 precedent).  The preflight runner may not carry
        # /data/service/hnp/bin at all, so the assembler/linker/archiver
        # must come from a Conan toolchain package, never from a fixed
        # device path alone.
        self.tool_requires("binutils/2.46.0")

    def generate(self):
        env = Environment()
        if str(self.settings.os) == "OHOS":
            # gcc-ada's GNAT driver resolves `as`/`ld` via execvp on PATH.
            # The device's GNU binutils live in /data/service/hnp/bin.
            # (adacgi/1.6 precedent, same device family.)
            env.prepend_path("PATH", "/data/service/hnp/bin")
        env.vars(self).save_script(_ENV_SCRIPT)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # Native GNAT helpers (adacgi/1.6 pattern)
    # ------------------------------------------------------------------
    def _tool(self, name):
        dependency = self.dependencies.build["gcc-ada"]
        bindirs = dependency.cpp_info.bindirs or ["bin"]
        executable = os.path.join(
            dependency.package_folder, bindirs[0], name
        )
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The gcc-ada build requirement does not provide {}: {}".format(
                    name, executable
                )
            )
        return executable

    def _sign_program(self, path):
        """Sign a freshly linked OHOS ELF so the kernel lets it exec
        (adacgi/1.6 _sign_program pattern: readelf type check, temp-dir
        objcopy + self-sign, .codesign presence check, mode restore).
        gcc-ada produces native OHOS ELFs, so no PT_INTERP/NEEDED
        rewriting is needed — signing only.
        """
        if str(self.settings.os) != "OHOS":
            return
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = (
            shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        readelf = (
            shutil.which("llvm-readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "Running GNAT output on OHOS requires binary-sign-tool, "
                "llvm-objcopy and llvm-readelf"
            )
        header = subprocess.run(
            [readelf, "-h", path],
            capture_output=True,
            text=True,
            check=True,
        )
        if not re.search(r"Type:\s+(?:EXEC|DYN)\b", header.stdout):
            raise ConanInvalidConfiguration(
                "GNAT did not produce a runnable ELF file: {}".format(path)
            )
        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            os.chmod(temp_dir, 0o775)
            unsigned = os.path.join(temp_dir, "unsigned")
            signed = os.path.join(temp_dir, "signed")
            shutil.copy2(path, unsigned)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", unsigned],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            subprocess.run(
                [signer, "sign", "-inFile", unsigned,
                 "-outFile", signed, "-selfSign", "1"],
                check=True,
            )
            sections = subprocess.run(
                [readelf, "-S", signed],
                capture_output=True,
                text=True,
                check=True,
            )
            if ".codesign" not in sections.stdout:
                raise ConanInvalidConfiguration(
                    "Signing did not add .codesign: {}".format(path)
                )
            os.replace(signed, path)
            os.chmod(
                path,
                original_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )
        self.output.info("  [ok] signed " + path)

    def _ensure_ahven(self):
        """Fetch (shared cache, sha256-pinned) and unpack Ahven 2.8."""
        root = os.path.join(self.build_folder, "ahven-2.8")
        probe = os.path.join(root, "src", "ahven-text_runner.adb")
        if os.path.isfile(probe):
            return
        cache = os.path.join(
            os.path.expanduser("~"), ".cache", "alog-ahven")
        os.makedirs(cache, exist_ok=True)
        archive = os.path.join(cache, _AHVEN_TARBALL)
        if os.path.isfile(archive):
            actual = hashlib.sha256(open(archive, "rb").read()).hexdigest()
            if actual != _AHVEN_SHA256:
                self.output.warning(
                    "cached %s fails sha256 (got %s); re-downloading"
                    % (_AHVEN_TARBALL, actual))
                try:
                    os.remove(archive)
                except OSError:
                    pass
        if not os.path.isfile(archive):
            self.output.info("downloading %s" % _AHVEN_TARBALL)
            with urllib.request.urlopen(_AHVEN_URL, timeout=120) as resp, \
                    open(archive, "wb") as out:
                shutil.copyfileobj(resp, out)
            actual = hashlib.sha256(open(archive, "rb").read()).hexdigest()
            if actual != _AHVEN_SHA256:
                raise ConanInvalidConfiguration(
                    "sha256 mismatch for %s: got %s expected %s"
                    % (_AHVEN_TARBALL, actual, _AHVEN_SHA256))
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(self.build_folder)
        if not os.path.isfile(probe):
            raise ConanInvalidConfiguration(
                "Ahven unpack failed: %s not found" % probe)

    def _library_units(self):
        """Top-level library bodies in the upstream ``src/`` subdir.

        The release tarball extracts (strip_root) to
        ``{src,tests,data,...}`` directly under the source folder, so
        the compilable units live in ``src/`` — the same directory
        that holds ``glue_syslog.c`` and the ``*.ads`` specs (see
        _build_c_glue and package()).  The source-folder ROOT holds no
        .adb files (preflight proved: scanning it yields zero units).

        Subunit files (``separate (...)`` bodies) cannot be compiled
        standalone — gcc refuses them ("cannot generate code for file
        ... (subunit)"); gnatmake pulls subunits in automatically when
        compiling the parent unit, so only non-subunit .adb files are
        returned.  A file is a subunit iff its first declaration line
        (skipping blank lines, ``--`` comments and ``with ...;``
        context clauses) starts with ``separate``.
        """
        unit_dir = os.path.join(self.source_folder, "src")
        try:
            names = sorted(os.listdir(unit_dir))
        except OSError as exc:
            raise ConanInvalidConfiguration(
                "upstream src/ dir not listable ({}); source root holds: {}"
                .format(exc, sorted(os.listdir(self.source_folder))))
        units = []
        for name in names:
            if not name.endswith(".adb"):
                continue
            path = os.path.join(unit_dir, name)
            if not os.path.isfile(path):
                continue
            is_subunit = False
            with open(path, "r", errors="replace") as fh:
                for line in fh:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("--"):
                        continue
                    if stripped.lower().startswith("with "):
                        continue  # context clause, before `separate`
                    if stripped.lower().startswith("separate"):
                        is_subunit = True
                    break
            if not is_subunit:
                units.append(name)
        return units

    def _device_truth(self):
        """Log broad, read-only device facts (runs first in build()).

        The previous round assumed /data/service/hnp (HNP clang + SDK
        sysroot) exists; preflight falsified it (clang missing, baked
        sysroot tree absent, single candidate).  Assume nothing here:
        dump the raw conf compilers, the ancestry of /data/service/hnp
        and of the baked sysroot, PATH tool hits, common SDK roots and
        OHOS env hints.  All lines carry [device-truth] so the next
        round — pass or fail — has facts instead of guesses.
        """
        import glob as _glob

        def _note(line):
            self.output.info("  [device-truth] " + line)

        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        _note("tools.build:compiler_executables={!r}".format(configured))
        for key in ("c", "cpp", "ar", "ranlib"):
            val = configured.get(key, "")
            _note("conf[{}]={} exists={}".format(
                key, repr(val),
                os.path.isfile(val) if val else False))
        # Ancestry of the HNP tree and of the baked sysroot.
        for path in (
            "/data", "/data/service", "/data/service/hnp",
            "/data/service/hnp/bin",
            "/data/service/hnp/ohos-sdk.org",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
            "/ohos/native/sysroot",
        ):
            _note("path {} isdir={} isfile={}".format(
                path, os.path.isdir(path), os.path.isfile(path)))
        try:
            _note("HNP bin listing: {}".format(
                sorted(os.listdir("/data/service/hnp/bin"))[:40]))
        except OSError as exc:
            _note("HNP bin not listable: {}".format(exc))
        for tool in ("cc", "c++", "clang", "clang++", "gcc", "g++",
                     "as", "ld", "ar", "llvm-ar", "llvm-objcopy",
                     "llvm-readelf", "objcopy", "binary-sign-tool",
                     "cmake", "ninja", "make", "python3"):
            _note("which({})={}".format(tool, shutil.which(tool)))
        for var in ("OHOS_NDK_HOME", "OHOS_SDK_HOME", "OHOS_SDK_PATH",
                    "OHOS_SYSROOT", "HMBS_INSTALL", "PATH"):
            val = os.environ.get(var, "")
            _note("{}={!r}".format(
                var, val if len(val) < 600 else val[:600] + "..."))
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot",
            "/data/service/hnp/ohos-sdk/*/ohos/native/sysroot",
            "/opt/ohos-sdk*/**/sysroot",
            "/opt/hnp*/**/sysroot",
        ):
            try:
                hits = sorted(_glob.glob(pattern, recursive=True))[:10]
            except OSError as exc:
                hits = ["glob-error:{}".format(exc)]
            _note("glob {} -> {}".format(pattern, hits))
        # binutils tool_requires presence (libgmpada/1.6 precedent).
        try:
            dep = self.dependencies.build.get("binutils")
            _note("binutils dep present={} folder={}".format(
                dep is not None,
                dep.package_folder if dep is not None else None))
        except Exception as exc:  # noqa: BLE001 - diagnostics only
            _note("binutils dep lookup failed: {}".format(exc))

    def _binutils_bindir(self):
        """Return the binutils/2.46.0 bindir carrying as/ld/ar (or '')."""
        try:
            dep = self.dependencies.build.get("binutils")
        except Exception:  # noqa: BLE001 - optional toolchain
            return ""
        if dep is None or not dep.package_folder:
            return ""
        candidates = [os.path.join(dep.package_folder, d)
                      for d in (dep.cpp_info.bindirs or ["bin"])]
        candidates.append(os.path.join(dep.package_folder, "bin"))
        for path in candidates:
            if path and os.path.isfile(os.path.join(path, "as")):
                return path
        self.output.warning(
            "binutils package present but no 'as' under {}".format(candidates))
        return ""

    def _dumpmachine(self, cc):
        """Run `<cc> -dumpmachine`, return (ok, triple-or-error)."""
        try:
            proc = subprocess.run(
                [cc, "-dumpmachine"],
                capture_output=True, text=True, timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, str(exc)
        out = (proc.stdout.strip() or proc.stderr.strip())[:120]
        return proc.returncode == 0, out

    def _select_c_compiler(self):
        """Pick a C compiler whose target is aarch64-OHOS (gated).

        Follows the validated pattern for missing profile compilers:
        conf value when present and executable, otherwise PATH
        discovery — but every candidate is gated by `-dumpmachine`
        containing both ``aarch64`` and ``ohos``.  A Linux host gcc
        must never silently build the glue object (it would poison
        libalog.a with the wrong machine code).  Each candidate and
        its triple is logged; with no match an explicit environment
        failure is raised for infra routing.
        """
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ordered = []
        for cand in ([configured.get("c")] + ["/data/service/hnp/bin/clang"]
                     + [shutil.which("clang"), shutil.which("cc")]):
            if cand and cand not in ordered:
                ordered.append(cand)
        for candidate in ordered:
            usable = (candidate and os.path.isfile(candidate)
                      and os.access(candidate, os.X_OK))
            if not usable:
                self.output.info(
                    "  [c-compiler] {} missing/inaccessible".format(candidate))
                continue
            ok, triple = self._dumpmachine(candidate)
            self.output.info(
                "  [c-compiler] {} dumpmachine ok={} triple={!r}".format(
                    candidate, ok, triple))
            if ok and "aarch64" in triple and "ohos" in triple:
                return candidate
        raise ConanInvalidConfiguration(
            "No aarch64-OHOS C compiler on this device (conf + HNP clang "
            "+ PATH clang/cc all missing or wrong-target); candidates "
            "tried: {}.  Route to infra: toolchain absent on runner."
            .format(ordered)
        )

    def _discover_ohos_sysroot(self):
        """Find a usable OHOS sysroot, or (None, None) when absent.

        gcc-ada's wrapper derives its sysroot from ``gcc.real
        -print-sysroot`` (baked at gcc-ada package time) and exits 1
        when that tree is gone.  Preflight proved the baked tree AND
        the conf clang can both be absent, so every source here is
        optional: baked value, clang derivations (conf/HNP/PATH),
        OHOS env hints, and SDK globs.  Layout facts are logged;
        (None, None) degrades the shim to pass-through (``-c``
        compiles may still proceed; links then fail with genuine
        linker errors instead of the wrapper block).
        """
        import glob as _glob

        target = "aarch64-linux-ohos"
        candidates = []

        def _note(line):
            self.output.info("  [sysroot-probe] " + line)

        try:
            real = self._tool("gcc.real")
        except ConanInvalidConfiguration as exc:
            real = ""
            _note("gcc.real lookup failed: {}".format(exc))
        baked = ""
        if real:
            try:
                proc = subprocess.run(
                    [real, "-print-sysroot"],
                    capture_output=True, text=True, timeout=60,
                )
                baked = proc.stdout.strip()
                _note("gcc.real -print-sysroot exit={} value={!r}".format(
                    proc.returncode, baked))
            except (OSError, subprocess.TimeoutExpired) as exc:
                _note("gcc.real -print-sysroot failed: {}".format(exc))
        if baked:
            candidates.append(baked)

        # Clang derivations from every plausible clang, not just conf.
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        clangs = []
        if configured.get("c"):
            clangs.append(configured.get("c"))
        clangs.append("/data/service/hnp/bin/clang")
        hit = shutil.which("clang")
        if hit and hit not in clangs:
            clangs.append(hit)
        for clang in clangs:
            if not (clang and os.path.isfile(clang)):
                _note("clang candidate absent: {}".format(clang))
                continue
            try:
                proc = subprocess.run(
                    [clang, "-print-resource-dir"],
                    capture_output=True, text=True, timeout=60,
                )
                resource = proc.stdout.strip()
                _note("clang {} -print-resource-dir exit={} value={!r}"
                      .format(clang, proc.returncode, resource))
                if proc.returncode == 0 and resource:
                    candidates.append(os.path.normpath(os.path.join(
                        resource, "..", "..", "..", "..", "sysroot")))
            except (OSError, subprocess.TimeoutExpired) as exc:
                _note("clang {} resource-dir failed: {}".format(clang, exc))
            for exe in (os.path.realpath(clang), os.path.abspath(clang)):
                d = os.path.dirname(exe)
                candidates.append(os.path.normpath(
                    os.path.join(d, "..", "..", "sysroot")))
                candidates.append(os.path.normpath(
                    os.path.join(d, "..", "sysroot")))

        for var in ("OHOS_NDK_HOME", "OHOS_SDK_HOME", "OHOS_SDK_PATH",
                    "OHOS_SYSROOT"):
            val = os.environ.get(var, "")
            if val:
                _note("{}={!r}".format(var, val))
                candidates.append(val)
                candidates.append(os.path.join(val, "sysroot"))

        for pattern in (
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot",
            "/data/service/hnp/ohos-sdk/*/ohos/native/sysroot",
            "/data/service/hnp/sysroot",
            "/opt/ohos-sdk*/**/sysroot",
            "/opt/hnp*/**/sysroot",
        ):
            try:
                hits = sorted(_glob.glob(pattern, recursive=True))
            except OSError as exc:
                _note("glob {} error: {}".format(pattern, exc))
                continue
            for found in hits[:10]:
                candidates.append(found)
        _note("total candidates: {}".format(len(candidates)))

        seen = set()
        for candidate in candidates:
            sysroot = os.path.normpath(candidate)
            if not sysroot or sysroot in seen:
                continue
            seen.add(sysroot)
            has_include = os.path.isdir(
                os.path.join(sysroot, "usr", "include"))
            triplet_lib = os.path.join(
                sysroot, "usr", "lib", target)
            plain_lib = os.path.join(sysroot, "usr", "lib")
            triplet_crt = os.path.isfile(
                os.path.join(triplet_lib, "Scrt1.o"))
            plain_crt = os.path.isfile(
                os.path.join(plain_lib, "Scrt1.o"))
            _note("candidate {} include={} triplet_lib={} "
                  "triplet_Scrt1.o={} plain_Scrt1.o={}".format(
                      sysroot, has_include,
                      os.path.isdir(triplet_lib),
                      triplet_crt, plain_crt))
            if not has_include:
                continue
            if triplet_crt:
                return sysroot, triplet_lib
            if plain_crt:
                return sysroot, plain_lib
        self.output.warning(
            "No usable OHOS sysroot on this device; probed: {}".format(
                "; ".join(sorted(seen)) if seen else "none"))
        return None, None

    def _ensure_gcc_shim(self):
        """Write a ``gcc`` shim bypassing gcc-ada's stale wrapper.

        The shim execs ``gcc.real`` directly, adding an explicit
        ``--sysroot`` (+ ``-B`` libdir + triplet ``-isystem`` + the
        availability define) only when _discover_ohos_sysroot found a
        usable tree; otherwise it is a plain pass-through (lets ``-c``
        compiles run so failures surface as genuine compiler/linker
        errors, never as the wrapper block).  The wrapper's
        link/compile classification (libunwind whole-archive injection
        on links only) is replicated.

        NOTE (round 7): gnatmake does NOT resolve its ``gcc`` driver
        via PATH — it invokes its sibling ``bin/gcc`` proxy by
        absolute path (proxy ELF → ``gcc.ohos-wrapper``, whose baked
        ``-print-sysroot`` check aborts every call on rotated-SDK
        runners; this round's evidence: shim OK + C glue OK, yet
        ``gcc -c ... alog-active_logger.adb`` still died with
        ``GCC Ada OHOS sysroot is unavailable``).  The PATH prefix in
        build() therefore only supplies as/ld/ar; every gnatmake
        command must pass ``--GCC=<shim>`` explicitly (proven to cover
        compile+bind; the link phase needs its own ``--GNATLINK=``
        wrapper, see below, because gnatmake does not forward --GCC
        to gnatlink).  Returns the (gcc shim, gnatlink wrapper) file
        paths.  Always rewritten (build folders may be reused across
        preflight retries).
        """
        shim_dir = os.path.join(self.build_folder, "fixed-ohos-gcc")
        shim = os.path.join(shim_dir, "gcc")
        sysroot, libdir = self._discover_ohos_sysroot()
        target = "aarch64-linux-ohos"
        real = self._tool("gcc.real")
        # The wrapper also passes -B<gcc-ada pkg>/lib/gcc/<target>/<ver>/
        # (home of crtbegin.o/crtend.o/libgcc); omitting it breaks only
        # the link (`ld: cannot find crtbegin.o`, round-9 evidence —
        # compiles need no gcc-private objects).  Locate the dir holding
        # crtbegin.o instead of hard-coding the gcc-ada version.
        pkg_root = os.path.normpath(
            os.path.join(os.path.dirname(real), ".."))
        gcc_lib_base = os.path.join(pkg_root, "lib", "gcc", target)
        gcc_lib = ""
        try:
            versions = sorted(os.listdir(gcc_lib_base))
        except OSError as exc:
            self.output.warning(
                "  [shim] gcc private lib not listable ({}): {}".format(
                    gcc_lib_base, exc))
            versions = []
        for version in versions:
            candidate = os.path.join(gcc_lib_base, version)
            if os.path.isfile(os.path.join(candidate, "crtbegin.o")):
                gcc_lib = candidate
                break
        if gcc_lib:
            self.output.info(
                "  [shim] gcc private lib: {}".format(gcc_lib))
        else:
            self.output.warning(
                "  [shim] no crtbegin.o under {}; links are expected "
                "to fail with genuine linker errors".format(gcc_lib_base))
        lines = [
            "#!/bin/sh",
            "# libalog fixed OHOS gcc shim: bypasses gcc-ada's wrapper.",
            "set -eu",
            "real=%s" % shlex.quote(real),
        ]
        if sysroot:
            lines.extend([
                "sysroot=%s" % shlex.quote(sysroot),
                "libdir=%s" % shlex.quote(libdir),
                "set -- \"--sysroot=$sysroot\" \"-B$libdir/\" \"$@\"",
            ])
            triplet_inc = os.path.join(sysroot, "usr", "include", target)
            if os.path.isdir(triplet_inc):
                lines.append("set -- -isystem %s \"$@\""
                             % shlex.quote(triplet_inc))
            lines.append("set -- '-D__availability__(...)=' \"$@\"")
        else:
            lines.append("sysroot=; libdir=")
            self.output.warning(
                "  [shim] no sysroot: pass-through mode, links are "
                "expected to fail with genuine linker errors")
        if gcc_lib:
            # Prepended last so it ends up first, mirroring the
            # wrapper's final flag order (-B<pkg> before -B<sysroot>).
            lines.append("pkg_gcc_lib=%s" % shlex.quote(gcc_lib))
            lines.append("set -- \"-B$pkg_gcc_lib/\" \"$@\"")
        lines.extend([
            "link=1",
            "has_input=0",
            "takes_value=0",
            'for argument in "$@"; do',
            '    if [ "$takes_value" -eq 1 ]; then',
            "        takes_value=0",
            "        continue",
            "    fi",
            '    case "$argument" in',
            "        -c|-S|-E|-M|-MM|-fsyntax-only) link=0 ;;",
            "        -o|-x|-isystem|-include|-imacros|-MF|-MT|-MQ|-B|-L|-I|-D|-U|-specs)",
            "            takes_value=1 ;;",
            "        -) has_input=1 ;;",
            "        -*) ;;",
            "        *) has_input=1 ;;",
            "    esac",
            "done",
            'if [ -n "$sysroot" ] && [ "$link" -eq 1 ] && [ "$has_input" -eq 1 ]; then',
            '    sdk_native=$(CDPATH= cd "$sysroot/.." && pwd -P)',
            '    libunwind="$sdk_native/llvm/lib/%s/libunwind.a"' % target,
            '    if [ -f "$libunwind" ]; then',
            '        set -- -Wl,--whole-archive "$libunwind" '
            '"-Wl,--no-whole-archive" "$@"',
            "    fi",
            "fi",
            'exec "$real" "$@"',
        ])
        os.makedirs(shim_dir, exist_ok=True)
        with open(shim, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        os.chmod(shim, 0o755)
        self.output.info(
            "  [ok] fixed gcc shim: {} (sysroot={} libdir={})".format(
                shim, sysroot, libdir))
        # The link phase needs its own override: gnatmake does NOT
        # forward --GCC to gnatlink (proven: every --GCC compile
        # succeeded, then bare `gnatlink ... -o obj/test_runner` hit
        # the stale wrapper again).  gnatlink itself accepts --GCC,
        # so wrap it in a script and select it via --GNATLINK=<path>
        # (single-token path, no nested-space parsing).
        real_gnatlink = self._tool("gnatlink")
        link_wrap = os.path.join(shim_dir, "gnatlink")
        with open(link_wrap, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(
                "#!/bin/sh\n"
                "# libalog fixed gnatlink wrapper: forces the Ada link\n"
                "# through the fixed gcc shim.\n"
                "exec {} {} \"$@\"\n".format(
                    shlex.quote(real_gnatlink),
                    shlex.quote("--GCC=" + shim)))
        os.chmod(link_wrap, 0o755)
        self.output.info(
            "  [ok] fixed gnatlink wrapper: {}".format(link_wrap))
        return shim, link_wrap

    def _build_c_glue(self):
        """Compile src/glue_syslog.c with the profile C compiler.

        alog_common.gpr lists Languages ("Ada", "C"): the Syslog
        facility imports C functions implemented in glue_syslog.c, so
        its object must be archived into libalog.a and linked into
        every consumer.  This uses _select_c_compiler (an
        aarch64-OHOS-gated C compiler: conf value, else PATH
        discovery), NEVER gcc-ada's gcc wrapper (whose baked sysroot
        check aborts every invocation on runners without the SDK tree).
        """
        obj_dir = os.path.join(self.source_folder, "obj", "static-obj")
        os.makedirs(obj_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "src", "glue_syslog.c")
        out = os.path.join(obj_dir, "glue_syslog.o")
        cc = self._select_c_compiler()
        self.output.info("  [c-glue] compiler: {}".format(cc))
        self.run(
            "{} -c -O2 -Wall {} -o {}".format(
                shlex.quote(cc), shlex.quote(src), shlex.quote(out)),
            cwd=self.source_folder,
            env=["conanbuild", _ENV_SCRIPT],
        )
        if not os.path.isfile(out):
            raise ConanInvalidConfiguration(
                "glue_syslog.c compile produced no object: %s" % out)

    @staticmethod
    def _parse_ahven_summary(output):
        """Parse the deterministic Ahven Text_Runner summary.

        Ahven 2.8 src/ahven-text_runner.adb Report_Results always prints
        `Passed : <n>` and prints `Skipped :`, `Failed :`, `Errors :`
        lines only when the count is > 0.  These four summary lines are
        the single source for all counts (individual per-routine PASS /
        FAIL lines exist but are never counted).  Returns
        (passed, failed, errors, skipped, failed_names); raises
        RuntimeError with the searched locations when no Passed line is
        found (missing mark, never guessed).
        """
        counts = {}
        for name in ("Passed", "Failed", "Errors", "Skipped"):
            m = re.search(
                r"^" + name + r"\s*:\s*(\d+)\s*$", output, re.MULTILINE)
            counts[name] = int(m.group(1)) if m else 0
        if not re.search(r"^Passed\s*:\s*\d+\s*$", output, re.MULTILINE):
            raise RuntimeError(
                "Ahven summary 'Passed :' line not found in test output "
                "(searched line-anchored Passed/Failed/Errors/Skipped "
                "patterns over %d chars); refusing to guess counts"
                % len(output))
        failed_names = []
        for line in output.splitlines():
            m = re.match(
                r"^\s{2,}(.{1,60}?)\s{2,}(FAIL|ERROR)\s+\S", line)
            if m:
                failed_names.append(m.group(1).strip() + ":" + m.group(2))
        return (counts["Passed"], counts["Failed"], counts["Errors"],
                counts["Skipped"], failed_names)

    def _run_upstream_tests(self):
        """Run the upstream Ahven suite and emit the HMBS marker.

        tests/test_runner.adb registers 81 routines in 13 Ahven test
        cases (see test_package/MANIFEST.yml for the per-file audit).
        A zero exit status plus the Text_Runner summary is the verdict;
        counts come from the summary lines only (see
        _parse_ahven_summary).  The runner executes with cwd at the
        source root because the FD/helper tests open ./data/*.ref
        fixtures by relative path.
        """
        run_dir = self.source_folder
        exe = os.path.join(self.source_folder, "obj", "test_runner")
        if not os.path.isfile(exe):
            raise ConanInvalidConfiguration(
                "upstream test binary not produced: %s" % exe)
        self._sign_program(exe)
        # FD/helper cases create logfiles as ./obj/<name> relative to
        # run_dir (upstream Object_Dir); build() created obj/, but
        # ensure it here so a reused/cleaned source tree cannot hit
        # OPEN_FILE_ERROR "No such file or directory".
        os.makedirs(os.path.join(run_dir, "obj"), exist_ok=True)
        proc = subprocess.run(
            [exe],
            cwd=run_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1800,
        )
        log_path = os.path.join(self.build_folder, "upstream-tests.log")
        try:
            with open(log_path, "w", encoding="utf-8") as fh:
                fh.write(proc.stdout)
            self.output.info("full upstream output saved: %s" % log_path)
        except OSError:
            pass
        (npass, nfail, nerr, nskip, failed_names) = \
            self._parse_ahven_summary(proc.stdout)
        discovered = npass + nfail + nerr + nskip
        executed = npass + nfail + nerr
        failed_total = nfail + nerr
        self.output.info(
            "upstream test_runner exit={} passed={} failed={} errors={} "
            "skipped={}".format(
                proc.returncode, npass, nfail, nerr, nskip))
        ok = (proc.returncode == 0 and failed_total == 0
              and discovered > 0)
        upstream = {
            "status": "passed" if ok else "failed",
            "framework": "ahven",
            "command": "./obj/test_runner",
            "discovered": discovered,
            "executed": executed,
            "passed": npass,
            "failed": failed_total,
            "skipped": nskip,
        }
        if not ok:
            gaps = []
            if failed_names:
                gaps.append({
                    "count": failed_total,
                    "category": "test_failure",
                    "detail": "failed routines: "
                              + "; ".join(failed_names[:20]),
                    "evidence": "upstream-tests.log + Ahven FAIL/ERROR "
                                "lines above",
                })
            else:
                gaps.append({
                    "count": discovered - npass,
                    "category": "test_failure",
                    "detail": "exit=%s with no passing summary; see "
                              "upstream-tests.log tail" % proc.returncode,
                    "evidence": proc.stdout[-2000:],
                })
            upstream["gaps"] = gaps
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        )
        if not ok:
            self.output.error(
                "=== test_runner output tail ===\n" + proc.stdout[-2000:])
            raise ConanInvalidConfiguration(
                "upstream tests failed: exit={} passed={} failed={} "
                "errors={} skipped={}".format(
                    proc.returncode, npass, nfail, nerr, nskip))

    def build(self):
        apply_conandata_patches(self)
        self._device_truth()
        self._ensure_ahven()
        gnatmake = self._tool("gnatmake")
        self._tool("gnatbind")
        self._tool("gnatlink")
        env = ["conanbuild", _ENV_SCRIPT]
        # Tool PATH for every gnat/ar invocation: binutils/2.46.0
        # (as/ld/ar when the runner has no /data/service/hnp/bin).
        # The fixed gcc shim is deliberately NOT resolved via PATH
        # (see _ensure_gcc_shim: gnatmake uses its absolute sibling
        # bin/gcc proxy), so it is passed as --GCC=<shim> on every
        # gnatmake command below.  `export ... &&` prefixes the
        # &&-chain deterministically, independent of conan env
        # aggregation order.
        shim, gnatlink_wrap = self._ensure_gcc_shim()
        gcc_opt = shlex.quote("--GCC=" + shim)
        link_opt = shlex.quote("--GNATLINK=" + gnatlink_wrap)
        self.output.info("  [gnat] driver override: {}".format(gcc_opt))
        self.output.info("  [gnat] linker override: {}".format(link_opt))
        path_dirs = []
        binutils_dir = self._binutils_bindir()
        if binutils_dir:
            path_dirs.append(binutils_dir)
            self.output.info(
                "  [tools] binutils bindir: {}".format(binutils_dir))
        else:
            self.output.warning(
                "  [tools] no binutils bindir: as/ld/ar rely on PATH/HNP")
        path_prefix = "export PATH={}:$PATH && ".format(
            shlex.quote(":".join(path_dirs))) if path_dirs else ""
        # C glue first: obj/static-obj/glue_syslog.o is archived into
        # the static lib and linked into the test executable below.
        self._build_c_glue()
        # Static library: compile the top-level library units (-c) and
        # archive the objects (plus the C glue object) into libalog.a.
        # NOTE: GNAT 9 is contemporary with this 2014-era codebase, so a
        # plain -O2 suffices; the GPR's strict style/warning switches
        # (-gnatyg* -gnatwa* -gnatwe) are diagnostics-only and omitted.
        units = " ".join(self._library_units())
        if not units:
            raise ConanInvalidConfiguration(
                "no compilable library units under {} (root holds: {})"
                .format(os.path.join(self.source_folder, "src"),
                        sorted(os.listdir(self.source_folder))))
        self.run(
            path_prefix +
            "mkdir -p obj/static-obj obj/static-lib && "
            "{g} {gcc} {link} -c -D obj/static-obj -Isrc -O2 {units} && "
            "ar rcs obj/static-lib/libalog.a obj/static-obj/*.o".format(
                g=shlex.quote(gnatmake), gcc=gcc_opt, link=link_opt,
                units=units),
            cwd=self.source_folder,
            env=env,
        )
        # Upstream test executable (alog_tests.gpr Main
        # tests/test_runner.adb, ALOG_BUILD=tests).  The binary is run
        # below so a fresh conan create always executes the real
        # upstream suite; test_package/test() re-runs it as well so a
        # cached build() still emits the marker.
        ahven_src = os.path.join(self.build_folder, "ahven-2.8", "src")
        ahven_unix = os.path.join(ahven_src, "unix")
        self.run(
            path_prefix +
            "mkdir -p obj && "
            "{g} {gcc} {link} -D obj -Isrc -Itests -I{ah} -I{ahu} -O2 "
            "-o obj/test_runner tests/test_runner.adb "
            "-largs obj/static-obj/glue_syslog.o".format(
                g=shlex.quote(gnatmake), gcc=gcc_opt, link=link_opt,
                ah=shlex.quote(ahven_src), ahu=shlex.quote(ahven_unix)),
            cwd=self.source_folder,
            env=env,
        )
        if can_run(self):
            self._run_upstream_tests()
        else:
            self.output.warning(
                "cross-building: upstream test binary built but not executed")

    def package(self):
        copy(
            self,
            "libalog.a",
            src=os.path.join(self.source_folder, "obj", "static-lib"),
            dst=os.path.join(self.package_folder, "lib"),
        )
        # ALI files are required by GNAT consumers to bind against the library.
        copy(
            self,
            "*.ali",
            src=os.path.join(self.source_folder, "obj", "static-obj"),
            dst=os.path.join(self.package_folder, "lib"),
        )
        # Specs go to include/alog, mirroring upstream gprinstall
        # --sources-subdir=include/alog (consumers: -I<package>/include/alog).
        copy(
            self,
            "*.ads",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include", "alog"),
        )

    def package_info(self):
        self.cpp_info.libs = ["alog"]
        self.cpp_info.includedirs = ["include/alog"]
        self.cpp_info.libdirs = ["lib"]
