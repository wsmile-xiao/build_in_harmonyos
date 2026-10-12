#!/usr/bin/env python3
"""Link test_wandder.c against the packaged libwandder and run it."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class LibwandderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _tool_works(self, tool):
        if os.path.isabs(tool) and not os.path.isfile(tool):
            return False
        if not os.path.isabs(tool) and shutil.which(tool) is None:
            return False
        try:
            self.run(f'"{tool}" --version', env="conanbuild")
            return True
        except Exception:
            return False

    def _resolve_c_compiler(self):
        execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cands = []
        if execs.get("c"):
            cands.append(execs.get("c"))
        cc_env = os.environ.get("CC")
        if cc_env:
            cands.append(cc_env)
        cands.append("/storage/Users/currentUser/usr/local/bin/clang")
        for bare in ("clang", "clang-15", "cc", "gcc"):
            cands.append(bare)
            found = shutil.which(bare)
            if found:
                cands.append(found)
        seen = set()
        for cand in cands:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if self._tool_works(cand):
                self.output.info(f"libwandder test: selected C compiler '{cand}'")
                return cand
        fallback = execs.get("c") or "clang"
        self.output.warning(f"libwandder test: using '{fallback}'")
        return fallback

    def _pick_lib(self, libdir, stem):
        static = os.path.join(libdir, f"lib{stem}.a")
        if os.path.isfile(static):
            return static, False
        names = [f"lib{stem}.so"]
        names.extend(sorted(glob.glob(os.path.join(libdir, f"lib{stem}.so*"))))
        for path in names:
            full = path if os.path.isabs(path) else os.path.join(libdir, path)
            if os.path.isfile(full):
                return full, True
        raise ConanException(f"missing lib{stem} under {libdir}")

    def build(self):
        cc = self._resolve_c_compiler()
        wand = self.dependencies["libwandder"]
        uthash = self.dependencies["uthash"]
        openssl = self.dependencies["openssl"]
        inc = [
            os.path.join(wand.package_folder, "include"),
            os.path.join(uthash.package_folder, "include"),
            os.path.join(openssl.package_folder, "include"),
        ]
        inc_flags = " ".join(f'-I"{path}"' for path in inc)
        wand_lib, wand_shared = self._pick_lib(os.path.join(wand.package_folder, "lib"), "wandder")
        crypto_lib, crypto_shared = self._pick_lib(
            os.path.join(openssl.package_folder, "lib"), "crypto"
        )
        rpath = []
        if wand_shared:
            rpath.append(os.path.dirname(wand_lib))
        if crypto_shared:
            rpath.append(os.path.dirname(crypto_lib))
        rpath_flags = " ".join(f'-Wl,-rpath,"{path}"' for path in rpath)
        src = os.path.join(self.source_folder, "test_wandder.c")
        out = os.path.join(self.build_folder, "test_wandder")
        self.run(
            f'"{cc}" -O2 {inc_flags} "{src}" "{wand_lib}" "{crypto_lib}" '
            f"{rpath_flags} -lpthread -lm -o \"{out}\"",
            env="conanbuild",
        )

    def test(self):
        test_bin = os.path.join(self.build_folder, "test_wandder")
        shell = os.environ.get("CONFIG_SHELL")
        if not (shell and os.path.exists(shell)):
            shell = shutil.which("bash")
        if shell:
            self.run(f"{shell} -c '\"{test_bin}\"'", env="conanrun")
        else:
            self.run(f'"{test_bin}"', env="conanrun")
