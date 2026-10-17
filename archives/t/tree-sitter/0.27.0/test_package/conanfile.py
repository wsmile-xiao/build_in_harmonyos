#!/usr/bin/env python3
"""Conan test_package — direct compilation test for tree-sitter.

Uses direct clang invocation instead of CMake to avoid CI worker lld/libxml2
issues during CMake try-compile. The OHOS SDK's lld linker may be broken on
some CI workers (missing libxml2), so we use GNU ld via -fuse-ld flag.

On OHOS CI workers, executing user-compiled binaries is blocked by SELinux
(seclabel on tmpfs). The test() method verifies the binary via nm instead of
direct execution, which still validates headers + library linkage.

File location: archives/{letter}/tree-sitter/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile


class TreeSitterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["tree-sitter"]
        pkg = dep.package_folder

        # Use clang (in PATH from conanbuild env) with GNU ld
        # to bypass broken OHOS SDK lld (missing libxml2 on CI workers)
        self.run(
            f"clang -o test_tree-sitter test.c "
            f"-I{pkg}/include -L{pkg}/lib -ltree-sitter "
            f"-fuse-ld=/data/service/hnp/bin/ld",
            env="conanbuild"
        )

    def test(self):
        # OHOS SELinux blocks execution of user-compiled binaries from tmpfs.
        # Verify the binary was built correctly by checking its symbols with nm.
        # This validates: (1) headers compile, (2) library links, (3) API symbols present.
        # CI L0d requires self.run() in test()
        self.run(
            "nm test_tree-sitter | grep -q 'ts_parser_new' && "
            "nm test_tree-sitter | grep -q 'ts_parser_delete' && "
            "echo 'test tree-sitter 0.27.0: OK (symbols verified)'",
            env="conanbuild"
        )
