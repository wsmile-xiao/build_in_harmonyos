#!/usr/bin/env python3
"""Conan test_package for wandio 4.2.7 -- Conan L1 official test.

Builds the consumer exercise (test_wandio.c) against the packaged
libwandio and runs it. The binary emits the HMBS hard-gate markers
itself; they flow through self.run into the conan/preflight log.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


class WandioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _resolve_c_compiler(self):
        # Library build proved the profile compiler can compile plain
        # objects, but CMakeToolchain hard-codes that same absolute path
        # into conan_toolchain.cmake and the CMake configure step still
        # fails in the preflight sandbox (Error 1, CMAKE_C_COMPILER
        # = /data/service/hnp/bin/clang). Rather than fighting the
        # toolchain FORCE/cache precedence, build the single-file consumer
        # directly with the probed compiler -- same route as the library.
        execs = self.conf.get("tools.build:compiler_executables", default={},
                              check_type=dict)
        cands = []
        if execs.get("c"):
            cands.append(execs.get("c"))
        cc_env = os.environ.get("CC")
        if cc_env:
            cands.append(cc_env)
        cands.append("/storage/Users/currentUser/usr/local/bin/clang")
        for bare in ("clang", "clang-15", "cc", "gcc"):
            cands.append(bare)
            w = shutil.which(bare)
            if w and w not in cands:
                cands.append(w)
        seen = set()
        ordered = []
        for c in cands:
            if c and c not in seen:
                seen.add(c)
                ordered.append(c)
        for cand in ordered:
            if os.path.isabs(cand) and not os.path.isfile(cand):
                continue
            if not os.path.isabs(cand) and shutil.which(cand) is None:
                continue
            try:
                self.run(f'"{cand}" --version', env="conanbuild")
                self.output.info(f"wandio test: selected C compiler '{cand}'")
                return cand
            except Exception:
                continue
        fallback = execs.get("c") or "clang"
        self.output.warning(f"wandio test: no probed compiler worked, using '{fallback}'")
        return fallback

    def build(self):
        cc = self._resolve_c_compiler()
        pf = self.dependencies["wandio"].package_folder
        inc = os.path.join(pf, "include")
        libdir = os.path.join(pf, "lib")
        lib_a = os.path.join(libdir, "libwandio.a")
        lib_so = os.path.join(libdir, "libwandio.so")
        if os.path.isfile(lib_a):
            libarg = f'"{lib_a}"'
        elif os.path.isfile(lib_so):
            libarg = f'"{lib_so}"'
        else:
            libarg = f'-L"{libdir}" -lwandio'
        src = os.path.join(self.source_folder, "test_wandio.c")
        out = os.path.join(self.build_folder, "test_wandio")
        self.run(f'"{cc}" -O2 -I"{inc}" "{src}" {libarg} -pthread -o "{out}"',
                 env="conanbuild")

    def test(self):
        # Prefer an explicit shell wrapper (OHOS mksh historically could not
        # execute ELF binaries directly), but only when the shell actually
        # exists: profiles may point CONFIG_SHELL at a helper path that is
        # absent from minimal build sandboxes. Fall back to direct execution
        # (proven by a52dec's test_package, which runs its binary directly).
        # Direct-cc layout: binary is in build_folder (no CMake bindirs).
        test_bin = os.path.join(self.build_folder, "test_wandio")
        shell = os.environ.get("CONFIG_SHELL")
        if not (shell and os.path.exists(shell)):
            shell = shutil.which("bash")
        if shell:
            self.run(f"{shell} -c '{test_bin}'", env="conanrun")
        else:
            self.run(test_bin, env="conanrun")
