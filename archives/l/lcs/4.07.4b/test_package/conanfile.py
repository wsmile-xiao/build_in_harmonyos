#!/usr/bin/env python3
"""Conan test_package — lcs 4.07.4b.

Consumer test: the package must provide a runnable crimesquad binary
with its data.  The test runs the REAL game in a PTY (see
run_game_test.py for the protocol), which verifies in one pass:

  * the binary and the installed share/lcs/art/ data work together
    (seven gameplay XMLs + sitemaps.txt are loaded from the package
    data dir before the title screen appears — a data failure aborts
    with a nonzero exit or the "Failed to load sitemaps.txt!" message),
  * the upstream quit path works: ESC on the title screen ->
    end_game() -> exit(0),
  * the binary is an OHOS AArch64 ELF dynamically linked against musl
    with no host RPATH leakage.
"""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run

# The target-side C++ runtime the crimesquad binary is linked against.
# Its directory is resolved from the Conan/compiler context at test time
# (see _find_libcxx_dir), never from hardcoded machine paths.
LIBCXX_SONAME = "libc++_shared.so"
# libdir component the OHOS aarch64 toolchains use for target libraries
LIBCXX_ARCH_LIBDIR = "aarch64-linux-ohos"


class LcsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # direct requirement: the run test needs the ncurses terminfo
        # database from the same package lcs was built against
        self.requires("ncurses/6.5")

    def build(self):
        pass

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["lcs"]
        bin_path = os.path.join(dep.cpp_info.bindirs[0], "crimesquad")
        assert os.path.isfile(bin_path), f"missing {bin_path}"

        # 1) ELF sanity for the OHOS target: ELF64 + AArch64 + musl loader.
        #    The host `file` command is a toybox shell alias that is not
        #    visible to non-interactive CI shells, so the ELF is inspected
        #    with readelf-style tools instead (repo pattern from alsa-lib):
        #    resolved from the compiler executable's directory first, then
        #    from PATH.  -h, -d and --string-dump behave the same on GNU
        #    readelf, llvm-readelf and llvm-readobj, while -l cannot be
        #    used because llvm-readobj does not print the interpreter path.
        tool = self._elf_tool()
        header = self._elf_output(tool, ["-h"], bin_path)
        low = header.lower()
        assert "elf64" in low and "aarch64" in low, \
            f"not an ELF64 aarch64 binary:\n{header[:400]}"
        interp = self._elf_output(tool, ["--string-dump=.interp"], bin_path)
        assert "/lib/ld-musl-aarch64.so.1" in interp, \
            f"not musl-linked: interpreter missing\n{interp[:400]}"
        # no host library leakage through RPATH/RUNPATH
        dynamic = self._elf_output(tool, ["-d"], bin_path)
        for line in dynamic.splitlines():
            if "RPATH" in line or "RUNPATH" in line:
                assert "/storage/" not in line and "/home/" not in line, \
                    f"host path leaked into {line.strip()!r}"

        # 2) real gameplay run on a PTY: data load + clean ESC exit
        ncurses = self.dependencies["ncurses"]
        terminfo = os.path.join(ncurses.package_folder, "share", "terminfo")
        assert os.path.isdir(terminfo), f"terminfo dir missing: {terminfo}"
        libcxx_dir = self._find_libcxx_dir()

        sandbox = os.path.join(self.build_folder, "game_home")
        os.makedirs(sandbox, exist_ok=True)
        script = os.path.join(self.source_folder, "run_game_test.py")
        self.run(
            f'"python3" "{script}" "{bin_path}" "{terminfo}" '
            f'"{libcxx_dir}" 60',
            cwd=sandbox, env="conanrun")
        self.output.success("lcs PTY run test passed")

    # ── ELF inspection helpers (alsa-lib test_package pattern) ─────────

    def _elf_output(self, tool, args, path):
        completed = subprocess.run(
            [tool, *args, path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=30)
        if completed.returncode != 0:
            raise ConanException(
                f"{os.path.basename(tool)} failed for "
                f"{os.path.basename(path)}: {completed.stdout}")
        return completed.stdout

    def _elf_tool(self):
        """Find an ELF inspector: llvm-readelf/readelf/llvm-readobj next
        to the profile's compiler executables first, then on PATH.  Never
        falls back to skipping the ELF checks."""
        names = ("llvm-readelf", "readelf", "llvm-readobj")
        candidates = []
        for _lang, compiler in self._compiler_executables():
            bindir = os.path.dirname(os.path.abspath(compiler))
            candidates += [os.path.join(bindir, name) for name in names]
        candidates += [shutil.which(name) for name in names]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) \
                    and os.access(candidate, os.X_OK):
                return candidate
        raise ConanInvalidConfiguration(
            "an ELF inspection tool (llvm-readelf, readelf or "
            "llvm-readobj) is required: none found next to the compiler "
            "or on PATH")

    # ── compiler + libc++_shared.so resolution ────────────────────────

    def _compiler_executables(self):
        """Profile compiler executables as (lang, path) pairs, C++
        first (cpp, cxx, c).  The single source of compiler-path
        discovery, shared by _elf_tool and _find_libcxx_dir."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        return [(lang, executables[lang])
                for lang in ("cpp", "cxx", "c") if executables.get(lang)]

    def _find_libcxx_dir(self):
        """Directory holding the target OHOS libc++_shared.so, resolved
        from the Conan/compiler context (never hardcoded machine paths).

        Candidate order (fail-closed):
          1. ask the compiler drivers: `<cxx> --print-file-name=
             libc++_shared.so` — accepted only when the answer is an
             absolute path to an existing file; a bare soname echo is a
             "not found" answer, not a success
          2. toolchain layout candidates derived from each compiler
             location, both as configured and after realpath() (CI
             entries like /data/.../bin/clang++ may be wrappers or
             symlinks whose realpath lies inside the real toolchain)
          3. already-present LD_LIBRARY_PATH entries, each verified

        Raises ConanInvalidConfiguration with the full trace (conf
        contents, compiler paths and realpaths, every --print-file-name
        answer, every candidate checked) when nothing resolves, so the
        next CI failure pinpoints the missing piece directly."""
        conf = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        diag = [f"compiler_executables: {conf!r}"]
        compilers = self._compiler_executables()
        if not compilers:
            diag.append("no compiler executable configured for cpp/cxx/c")

        # executables to try: each configured path plus its realpath,
        # deduplicated (symlinked wrappers resolve into the real SDK)
        exes = []
        for _lang, raw in compilers:
            for exe in self._exe_variants(raw):
                if exe not in exes:
                    exes.append(exe)
        diag.append("compiler paths tried (configured + realpath): "
                    + (", ".join(exes) or "none"))

        # 1) the driver knows its own runtime location
        answers = []
        for exe in exes:
            out = self._print_file_name(exe)
            answers.append(f"{exe} -> {out!r}")
            hit = self._absolute_existing(out)
            if hit:
                self.output.info(f"libc++_shared.so via {exe}: {hit}")
                return os.path.dirname(hit)
        diag.append("--print-file-name answers: "
                    + ("; ".join(answers) or "none"))

        # 2) toolchain layout candidates around the compiler locations
        # 3) LD_LIBRARY_PATH entries as the last limited fallback
        checked = []
        for candidate in self._layout_candidates(
                [raw for _lang, raw in compilers]):
            checked.append(candidate)
            if os.path.isfile(candidate):
                self.output.info("libc++_shared.so via toolchain layout: "
                                 f"{candidate}")
                return os.path.dirname(candidate)
        for entry in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep):
            if not entry:
                continue
            candidate = os.path.join(entry, LIBCXX_SONAME)
            checked.append(candidate)
            if os.path.isfile(candidate):
                self.output.info("libc++_shared.so via LD_LIBRARY_PATH: "
                                 f"{candidate}")
                return entry
        diag.append("candidates checked, all missing: "
                    + ("; ".join(checked) or "none"))

        raise ConanInvalidConfiguration(
            f"{LIBCXX_SONAME} not found: the PTY run test needs the "
            "target OHOS C++ runtime directory (it becomes the game's "
            "LD_LIBRARY_PATH).  Resolver trace:\n  "
            + "\n  ".join(diag))

    # resolver internals — pure static helpers, easy to test in isolation

    @staticmethod
    def _exe_variants(raw):
        """A configured compiler path and its realpath, deduplicated."""
        variants = []
        for exe in (os.path.abspath(raw), str(Path(raw).resolve())):
            if exe not in variants:
                variants.append(exe)
        return variants

    @staticmethod
    def _print_file_name(exe):
        """`<compiler> --print-file-name=libc++_shared.so`; returns the
        trimmed answer, or "" when the driver cannot be executed."""
        try:
            completed = subprocess.run(
                [exe, f"--print-file-name={LIBCXX_SONAME}"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace", timeout=30)
        except (OSError, subprocess.SubprocessError):
            return ""
        return (completed.stdout or "").strip()

    @staticmethod
    def _absolute_existing(out):
        """Interpret a --print-file-name answer: only an absolute path
        (after normalizing '..' segments) to an existing file counts —
        drivers that do not know the runtime echo the bare soname."""
        if not out or not os.path.isabs(out):
            return None
        path = os.path.normpath(out)
        return path if os.path.isfile(path) else None

    @staticmethod
    def _layout_candidates(compiler_paths):
        """Limited, evidence-backed candidates for libc++_shared.so
        derived from the compiler locations: for each configured path
        and its realpath, walk at most three parent directories of the
        compiler's bin dir and apply the libdir layouts OHOS toolchains
        actually use:

          <dir>/lib/<triple>/libc++_shared.so
          <dir>/lib/<triple>/c++/libc++_shared.so
          <dir>/sysroot/usr/lib/<triple>/libc++_shared.so

        covering the usr-local layout (bin/../lib/aarch64-linux-ohos)
        and the OHOS SDK layout (native/llvm/bin ->
        native/sysroot/usr/lib and native/llvm/lib) alike.  Strictly
        bounded: no SDK version numbers, no filesystem-wide search —
        only isfile() probes on these explicit paths."""
        candidates = []
        for raw in compiler_paths:
            for base in (os.path.abspath(raw), str(Path(raw).resolve())):
                bindir = Path(base).parent
                for ancestor in (bindir, *bindir.parents[:3]):
                    for rel in (
                        f"lib/{LIBCXX_ARCH_LIBDIR}/{LIBCXX_SONAME}",
                        f"lib/{LIBCXX_ARCH_LIBDIR}/c++/{LIBCXX_SONAME}",
                        f"sysroot/usr/lib/{LIBCXX_ARCH_LIBDIR}/"
                        f"{LIBCXX_SONAME}",
                    ):
                        candidate = str(ancestor / rel)
                        if candidate not in candidates:
                            candidates.append(candidate)
        return candidates
