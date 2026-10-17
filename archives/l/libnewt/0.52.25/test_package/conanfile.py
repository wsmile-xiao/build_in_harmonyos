#!/usr/bin/env python3
"""Conan test_package — libnewt 0.52.25

L1 test (consumer view): link libnewt and check the headless-safe API
surface (test_newt), plus execute the shipped whiptail --version, which
exits before newtInit and needs no terminal.

NOTE: direct-compile on purpose (no CMake). Three rounds of
CMakeToolchain all died in cmake.configure() on this image
("System is unknown to cmake" / "C compiler identification is unknown"
for /data/service/hnp/bin/clang), while the main-package Autotools
configure with the same compiler + --target passes. Compiling the one-file
consumer straight with the profile compiler avoids CMake's
platform/compiler-ID machinery entirely (bsdconv/11.6 precedent).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class LibnewtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # readonly_tmp: keep clang temp files off read-only /tmp.
        tmp = self._writable_tmpdir()
        env = Environment()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        env.define_path("SHELL", "/bin/sh")
        env.define_path("CONFIG_SHELL", "/bin/sh")
        env.vars(self, scope="build").save_script("conanfixenv")

    def test(self):
        # Upstream ships no automated tests (audited: no make check target,
        # no test framework; demos need an interactive TTY; BLFS confirms no
        # test suite). Emit the no_tests marker; MANIFEST.yml holds the audit.
        print(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none",'
            '"command":"audit: no upstream test target or framework",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,'
            '"reason":"newt 0.52.25 has no automated test suite: no make check '
            'target, no gtest/pytest/criterion bindings; test.c/testgrid.c/'
            'testtree.c are interactive TTY demos, not assertions."}'
        )
        if not can_run(self):
            return
        # Process-level tmp channel (complements the buildenv script above):
        # the direct clang invocation below inherits this process env.
        tmp = self._writable_tmpdir()
        os.makedirs(tmp, exist_ok=True)
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = tmp
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        # Case 1: compile the consumer test with the profile compiler
        # (same HNP clang the main-package configure proved works) plus
        # --target, link static libnewt (+ transitive slang/popt), run it.
        cc = self._profile_cc()
        inc_flags, lib_flags = self._dep_flags()
        src = os.path.join(self.source_folder, "test_newt.c")
        out = os.path.join(self.build_folder, "test_newt")
        target = "--target=aarch64-unknown-linux-ohos" if self.settings.os == "OHOS" else ""
        self.run(f'{cc} "{src}" -o "{out}" {target} {inc_flags} {lib_flags}')
        self.run(f'"{out}"', env="conanrun")
        # Case 2: shipped whiptail binary; --version exits 0 before newtInit.
        pkg_folder = self.dependencies["libnewt"].package_folder
        whiptail = os.path.join(pkg_folder, "bin", "whiptail")
        self.run(f'"{whiptail}" --version', env="conanrun")
        print(
            'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
            '"command":"test_newt + whiptail --version",'
            '"discovered":2,"passedCount":2}'
        )

    # ── helpers ────────────────────────────────────────────────

    def _writable_tmpdir(self):
        import tempfile
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        d = os.path.join(self.build_folder, "tmp")
        os.makedirs(d, exist_ok=True)
        return d

    def _cand_works(self, prog):
        """True if prog can actually run --version (proven executable)."""
        if not prog:
            return False
        prog = prog.strip().split()[0].strip("\"'")
        if not prog:
            return False
        try:
            r = subprocess.run([prog, "--version"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=30)
            return r.returncode == 0
        except Exception:
            return False

    def _profile_cc(self):
        """Profile C compiler binary (bare path, no extra args).

        Same-image precedent (main recipe _resolve_cc, cassbeam/1.1):
        /data/service/hnp/bin/clang can be 'inaccessible or not found'
        from the conan test domain (Error 127). Probe the toolchain
        value first; only fall back when it is actually unrunnable.
        Prefer PATH-resolved `clang` so HMBS-prepended tool dirs win.
        """
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict)
        except Exception:
            exes = {}
        conf_c = (exes.get("c") if isinstance(exes, dict) else None) or ""
        conf_prog = conf_c.strip().split()[0].strip("\"'") if conf_c else ""
        if conf_prog and self._cand_works(conf_prog):
            self.output.info(f"HMBS: toolchain CC works verbatim: {conf_prog}")
            return conf_prog
        if conf_prog:
            self.output.warning(
                f"HMBS: toolchain CC unrunnable: {conf_c!r}; searching fallback")
        for cand in (os.environ.get("CC", ""), "clang", "cc", "gcc",
                     "/data/service/hnp/bin/clang"):
            prog = cand.strip().split()[0].strip("\"'") if cand else ""
            if not prog:
                continue
            resolved = (shutil.which(prog) if "/" not in prog else prog) or prog
            if self._cand_works(resolved):
                if resolved != prog:
                    self.output.warning(f"HMBS: CC fallback in use: {resolved}")
                return resolved
        self.output.warning("HMBS: no working CC found; keeping PATH clang")
        return "clang"

    def _dep_flags(self):
        """-I/-L/-l flags covering libnewt plus transitive deps.

        libnewt is linked by its explicit .a path (not -lnewt): while the
        .so is still in the package, -lnewt resolves to libnewt.so and the
        binary then needs libnewt.so.0.52 on LD_LIBRARY_PATH at runtime.
        That lookup is flaky — it fails exactly when the main recipe's
        static whiptail relink failed and left the .so files behind
        (CI build #49404: 'Error loading shared library libnewt.so.0.52').
        Linking the .a makes the consumer deterministic; slang/popt stay
        dynamic via -l and the conanrun env provides them. Falls back to
        -lnewt only when the .a is absent (shared build).
        """
        incs, libdirs, libs = [], [], []
        for dep in self.dependencies.values():
            try:
                info = dep.cpp_info
            except Exception:
                continue
            for d in getattr(info, "includedirs", []) or []:
                if d and os.path.isdir(d) and d not in incs:
                    incs.append(d)
            for d in getattr(info, "libdirs", []) or []:
                if d and os.path.isdir(d) and d not in libdirs:
                    libdirs.append(d)
            for lib in getattr(info, "libs", []) or []:
                if lib and lib not in libs and lib != "newt":
                    libs.append(lib)
        for lib in ("slang", "popt"):
            if lib not in libs:
                libs.append(lib)
        newt_a = os.path.join(self.dependencies["libnewt"].package_folder,
                              "lib", "libnewt.a")
        newt_link = f'"{newt_a}"' if os.path.isfile(newt_a) else "-lnewt"
        inc_flags = " ".join(f'"{p}"' if " " in p else p
                             for p in (f"-I{d}" for d in incs))
        lib_flags = " ".join(f'"{p}"' if " " in p else p
                             for p in ([f"-L{d}" for d in libdirs] +
                                       [newt_link] + [f"-l{lib}" for lib in libs]))
        return inc_flags, lib_flags
