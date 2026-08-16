#!/usr/bin/env python3
"""test_package for abiword-plugin-opml 3.0.8.

Consumer-level test (R34): compiles a small program that dlopens the
installed plugin module and drives its exported ABI
(abi_plugin_supports_version / abi_plugin_register / abi_plugin_unregister).
"""
import glob
import os

from conan import ConanFile


def _real_cpp(conf):
    """OHOS SDK clang++ on PATH is a /bin/sh wrapper script; conan's
    subprocess domain cannot execute scripts, so resolve the real clang-<N>
    ELF binary (the wrapper just execs it)."""
    ccs = conf.get("tools.build:compiler_executables", default={}) or {}
    cpp = ccs.get("cpp") or "clang++"

    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    if cpp and os.path.isfile(cpp):
        try:
            with open(cpp, "rb") as f:
                if f.read(2) != b"#!":
                    return cpp
        except OSError:
            pass
    for d in (os.path.dirname(cpp) if cpp else None, "/data/service/hnp/bin"):
        if d and os.path.isdir(d):
            for name in sorted(os.listdir(d)):
                if name.startswith("clang-") and name[6:].isdigit():
                    cand = os.path.join(d, name)
                    if _is_elf(cand):
                        return cand
    for g in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang++-[0-9]*",
              "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang-[0-9]*",
              "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang++"):
        for cand in sorted(glob.glob(g)):
            if _is_elf(cand):
                return cand
    return cpp


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cpp = _real_cpp(self.conf)
        src = os.path.join(self.source_folder, "run_test.cpp")
        out = os.path.join(self.build_folder, "run_test")
        # clang-15 as CXX does not auto-add the C++ runtime: the dlopened
        # plugin module needs libc++ symbols (operator new etc.) resolved
        self.run(f"{cpp} {src} -o {out} -ldl -stdlib=libc++ -lc++")

    def test(self):
        dep = self.dependencies["abiword-plugin-opml"]
        so = os.path.join(dep.package_folder, "lib", "abiword-3.0",
                          "plugins", "libabiword-plugin-opml.so")
        if not os.path.exists(so):
            self.output.error("plugin module not found in package: " + so)
            raise SystemExit(1)
        exe = os.path.join(self.build_folder, "run_test")
        self.run(f"{exe} {so}")
