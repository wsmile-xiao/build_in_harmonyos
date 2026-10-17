#!/usr/bin/env python3
"""Conan recipe for wyhash 0-2.gbp234f0c6 — header-only C/C++ library.

wyhash is a fast 64-bit non-cryptographic hash function plus a companion
PRNG (wyrand).  It ships as headers only: wyhash.h (main), wyhash32.h and
o1hash.h.

The task version ``0-2.gbp234f0c6`` pins the upstream snapshot at commit
234f0c6 ("Add copyright header").  The current upstream master is the
incompatible "final 4.x" algorithm and must NOT be used: it produces
different hash values and would silently change the test vectors.

Layer 1 of the test strategy (TEST_QUALITY_SPEC.md) runs here: the upstream
test_vector.cpp is compiled against the sources and its stdout is compared
with the recorded baseline.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# Exact stdout of upstream test_vector.cpp at commit 234f0c6.
_UPSTREAM_BASELINE = "\n".join([
    'wyhash("",0)=42bc986dc5eec4d3',
    'wyhash("a",1)=84508dc903c31551',
    'wyhash("abc",2)=bc54887cfc9ecb1',
    'wyhash("message digest",3)=adc146444841c430',
    'wyhash("abcdefghijklmnopqrstuvwxyz",4)=4c0977bd4f14f34a',
    'wyhash("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",5)=6f8bd609a8a276d2',
    'wyhash("1234567890123456789012345678901234567890123456789012345678901234567890'
    '1234567890",6)=498d7c21668259ad',
]) + "\n"


class WyhashConan(ConanFile):
    name = "wyhash"
    version = "0-2.gbp234f0c6"
    description = "Fastest-quality 64-bit non-cryptographic hash function and PRNG (header-only)"
    license = "Unlicense"
    homepage = "https://github.com/wangyi-fudan/wyhash"
    url = "https://github.com/wangyi-fudan/wyhash"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, key, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return str(executables.get(key) or fallback)

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def build(self):
        apply_conandata_patches(self)

        # Layer 1: run the official upstream test program against the pinned
        # snapshot and require its stdout to match the recorded baseline.
        cxx = self._compiler("cpp", "c++")
        binary = os.path.join(self.build_folder, "upstream_test_vector")
        actual_file = os.path.join(self.build_folder, "upstream_test_vector.out")
        compile_cmd = " ".join([
            shlex.quote(cxx),
            "-O2", "-Wall",
            "-I", shlex.quote(self.source_folder),
            shlex.quote(os.path.join(self.source_folder, "test_vector.cpp")),
            "-o", shlex.quote(binary),
        ])
        self.run(compile_cmd)

        redirect = f"{shlex.quote(binary)} > {shlex.quote(actual_file)}"
        if self.settings.os in ("Linux", "OHOS"):
            self.run(f"{shlex.quote(self._bash())} -c {shlex.quote(redirect)}")
        else:
            self.run(redirect)

        with open(actual_file, "r") as handle:
            observed = handle.read()
        if observed.strip() != _UPSTREAM_BASELINE.strip():
            raise ConanException(
                "upstream test_vector.cpp output differs from baseline\n"
                f"expected:\n{_UPSTREAM_BASELINE}\nobserved:\n{observed}"
            )
        print('HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": '
              '"upstream test_vector.cpp", "discovered": 1, "executed": 1, '
              '"passed": 1, "failed": 0, "skipped": 0}')

    def package(self):
        # Ship only the three public headers at the repository root.
        # old_versions/*.h are historical variants and stay out of the package.
        copy(self, "*.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"),
             excludes=("old_versions/*",))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        # Header-only: package contents do not depend on any setting.
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "wyhash")
        self.cpp_info.set_property("cmake_target_name", "wyhash::wyhash")
