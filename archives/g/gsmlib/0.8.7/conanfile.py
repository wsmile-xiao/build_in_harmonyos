#!/usr/bin/env python3
"""Conan recipe for gsmlib 0.8.7 — GSM TA/ME library (autotools).

Upstream: https://github.com/vbouchaud/gsmlib
Build: autotools (configure + make), produces libgsmme (shared+static),
header tree include/gsmlib/, and CLI tools gsmsmsstore/gsmctl/gsmsmsd/
gsmpb/gsmsendsms. Adapted for HarmonyOS OHOS (aarch64-linux-ohos).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class GsmlibConan(ConanFile):
    name = "gsmlib"
    version = "0.8.7"
    description = "gsmlib - library and tools to access GSM mobile phones through GSM modems or IrDA devices (SMS, phonebook)"
    license = "LGPL-2.0"
    homepage = "https://github.com/vbouchaud/gsmlib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # R3: apply conandata-declared patches to source tree before build copy
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # do not try to install translations into system locale dirs
        tc.configure_args.append("--disable-nls")
        # E293: C++17 turns legacy `throw(...)`/`register` diagnostics into errors;
        # downgrade them to warnings (old 2003-era codebase)
        tc.extra_cxxflags.append("-Wno-error=dynamic-exception-spec")
        tc.extra_cxxflags.append("-Wno-error=register")
        # legacy code: non-constant int->unsigned char narrowing in initializer lists
        tc.extra_cxxflags.append("-Wno-error=c++11-narrowing")
        # R04: CI 沙箱（AppSpawn, USER=100）拒绝 ~/.cache 下"新建 0700 私有目录+写入"
        # 组合（config.status 经 0005 补丁读 ${TMPDIR}）。把 TMPDIR/TMP/TEMP 指向沙箱
        # 原生可写缓存 /data/storage/el2/base/cache（/data 真实分区，保留 POSIX 权限位，
        # 实测 drwx------ 700 且 0700 私有目录内写入成功），通过 conan env 脚本注入
        # 构建进程。注意：必须 define() 覆盖（append() 是追加语义会将原值拼接成
        # 无效路径，导致 clang "unable to make temporary file"）。
        env = Environment()
        for var in ("TMPDIR", "TMP", "TEMP"):
            env.define(var, "/data/storage/el2/base/cache")
        env.vars(self).save_script("conanbuild_tmpdir")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # upstream builds libgsmme.la; headers installed under include/gsmlib
        self.cpp_info.libs = ["gsmme"]
        self.cpp_info.includedirs = ["include"]
        # CLI tools (gsmctl/gsmpb/gsmsendsms/gsmsmsd/gsmsmsstore + ext tools)
        # are installed to bin/ by autotools install (R38/L0k alignment)
        self.cpp_info.bindirs = ["bin"]