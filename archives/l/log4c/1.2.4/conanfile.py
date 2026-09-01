#!/usr/bin/env python3
"""Conan recipe — log4c 1.2.4 (autotools, C logging library)"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout


class Log4cConan(ConanFile):
    name = "log4c"
    version = "1.2.4"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        # host/build 三元组按目标架构推导：HarmonyOS PC 目标为 armv8。
        # 名义三元组用 -linux-gnu 后缀配合 build() 中的 uname-shim，让 autotools/config.sub
        # 按 Linux-ELF 处理；真实交叉目标由 profile 的 CC/CXX（OHOS clang）决定。
        _arch_triplet = {"armv8": "aarch64-linux-gnu", "x86_64": "x86_64-linux-gnu"}
        arch = str(self.settings.arch)
        triplet = _arch_triplet.get(arch)
        if triplet is None:
            raise ConanInvalidConfiguration(
                f"log4c 1.2.4 配方目标为 HarmonyOS PC，仅支持 armv8/x86_64，收到 arch='{arch}'"
            )
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-test")
        tc.configure_args.append(f"--host={triplet}")
        tc.configure_args.append(f"--build={triplet}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import glob, os
        # umask 077 → 022 workaround: autotools config.status creates temp files
        # with 0600 perms under umask 077, which breaks on OHOS (same as lame).
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        # uname shim: make autotools treat OHOS as Linux for config.sub compatibility.
        _shim = os.path.join(self.build_folder, '_uname_shim')
        os.makedirs(_shim, exist_ok=True)
        _u = os.path.join(_shim, 'uname')
        with open(_u, 'w') as _f:
            _f.write('#!/bin/sh\ncase "${1:-}" in\n  -s|"") echo Linux ;;\n  -r) echo 6.6 ;;\n  -m) echo aarch64 ;;\n  *) exec /system/bin/uname "$@" 2>/dev/null || exec /bin/uname "$@" ;;\nesac\n')
        os.chmod(_u, 0o755)
        os.environ['PATH'] = _shim + os.pathsep + os.environ.get('PATH', '')
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Run upstream official tests (CI L1 requirement).
        # check-local runs 4 tests: test_category, test_layout_r, test_rc, test_big.
        # Each runs with LOG4C_PRIORITY=notice, output normalized by sed, diff vs .ref.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ['log4c']
        self.cpp_info.set_property("cmake_file_name", "log4c")
        self.cpp_info.set_property("cmake_target_name", "log4c::log4c")
