#!/usr/bin/env python3
"""Conan L1 test_package for lowdown.

Verifies:
  1. C API: include <lowdown.h>, link liblowdown, parse Markdown → HTML
     via lowdown_buf(), and assert the output contains expected content.
  2. CLI smoke: run the packaged `lowdown` binary on Markdown input and
     assert HTML output (only when with_cli=True).
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class LowdownTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ── OHOS SDK linker runtime path ────────────────────────────────────
    # The test_package compiles test_lowdown.c with the SDK clang, which
    # invokes lld as the linker.  lld dynamically links libxml2.so.16 from
    # <sdk>/llvm/lib; without that dir on LD_LIBRARY_PATH, lld fails to
    # start and the compile link step aborts.  We prepend the SDK lib dir
    # into the *conanrun* scope (saved by generate()) so every
    # self.run(env="conanrun") below — the compile, the test binary, and
    # the CLI smoke run — inherits it.  Mirrors the main recipe's helpers.

    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or compilers.get("cpp")
        candidates = []
        if cc:
            compiler = os.path.realpath(cc)
            try:
                resource_dir = subprocess.check_output(
                    [cc, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )

        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _usable_sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""

        cached = getattr(self, "_checked_sdk_llvm_libdir", None)
        if cached is not None:
            return cached

        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            lld = os.path.join(os.path.dirname(sdk_llvm_lib), "bin", "lld")
            probe_env = os.environ.copy()
            old_ld = probe_env.get("LD_LIBRARY_PATH", "")
            probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                part for part in (sdk_llvm_lib, old_ld) if part
            )
            try:
                probe = subprocess.run(
                    [lld, "-flavor", "gnu", "--version"],
                    env=probe_env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as error:
                raise ConanException(
                    f"Cannot execute the OHOS SDK linker {lld}: {error}"
                ) from error
            if probe is not None and probe.returncode == 0:
                self._checked_sdk_llvm_libdir = sdk_llvm_lib
                return sdk_llvm_lib
            raise ConanException(
                f"The active OHOS SDK linker failed its GNU-flavor probe: {lld}; "
                f"stderr={probe.stderr.strip()!r}"
            )

        raise ConanException(
            "Cannot locate the active OHOS SDK llvm/lib containing "
            "libxml2.so.16"
        )

    def generate(self):
        sdk_lib = self._usable_sdk_llvm_libdir()
        if sdk_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_lib}"
            )
            env = Environment()
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
            env.vars(self, scope="run").save_script("conanrun_lld_rpath")

    def build(self):
        # Resolve the lowdown package folder and its subdirs.
        pkg = self.dependencies["lowdown"].package_folder
        inc = os.path.join(pkg, "include")
        libdir = os.path.join(pkg, "lib")

        # R33: compiler from Conan conf, not the bare CC env var.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        src_c = os.path.join(self.recipe_folder, "test_lowdown.c")
        out_bin = os.path.join(self.build_folder, "test_lowdown")

        # Static link against liblowdown.a; lowdown has no deps.
        # env="conanrun" picks up the SDK lib dir saved by generate() so lld
        # can resolve libxml2.so.16 during the link step.
        self.run(
            f'{cc} -static -O2 -I{inc} '
            f'{src_c} -L{libdir} -llowdown '
            f'-o {out_bin}',
            env="conanrun",
        )

    def test(self):
        # 1. C API conversion test — Markdown → HTML
        bin_path = os.path.join(self.build_folder, "test_lowdown")
        # lowdown_buf writes HTML to stdout; assert the <h1> heading appears.
        self.run(f'"{bin_path}"', env="conanrun")

        # 2. CLI smoke test — run the packaged `lowdown` binary
        pkg = self.dependencies["lowdown"].package_folder
        lowdown_bin = os.path.join(pkg, "bin", "lowdown")
        if os.path.exists(lowdown_bin):
            # Feed Markdown and assert the <h1> appears in HTML output.
            # Accept optional attributes on the <h1> element while verifying its text.
            md = "# Hello from lowdown CLI"
            self.run(
                f'printf \'%s\\n\' \'{md}\' | "{lowdown_bin}" '
                f'| grep -q "Hello from lowdown CLI</h1>"',
                env="conanrun",
            )
            self.output.success("CLI smoke test passed")
        else:
            self.output.warning(
                "lowdown CLI binary not found — skipping CLI smoke test"
            )
