#!/usr/bin/env python3
"""Conan recipe — libntru 0.5.0 (C implementation of NTRUEncrypt).

纯 Makefile 构建（Makefile.linux），无第三方依赖。OHOS 适配要点：
  - 工具链从 Conan conf 注入（R33，禁用 ${CC} 环境变量）：
    CC/AR/RANLIB 取自 tools.build:compiler_executables，保证 CI worker 上可用；
  - ntru_endian.h 补丁（0001）：OHOS/musl（__OHOS__ + __linux__、无 __GLIBC__）
    下 htole32/64/16 未声明，ld.lld 链接报 "undefined reference ... htole32"；
    补丁增加 __OHOS__/__linux__/__FreeBSD__ 分支 #include <endian.h>；
  - upstream `make test` 运行 testham（11 用例）+ testnoham（10 用例，
    专利规避宏 -DNTRU_AVOID_HAMMING_WT_PATENT），本机即 OHOS aarch64 可运行。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import chdir, copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibntruConan(ConanFile):
    name = "libntru"
    version = "0.5.0"
    description = "C implementation of NTRUEncrypt (IEEE P1363.1)"
    license = "MIT"
    homepage = "https://github.com/tbuktu/libntru"
    url = ""  # CI fills this

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

    def _cc(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get("c")
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which("clang")
        return found or configured or "clang"

    def _ar(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get("ar")
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which("llvm-ar") or shutil.which("ar")
        return found or configured or "ar"

    def _ranlib(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get("ranlib")
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which("llvm-ranlib") or shutil.which("ranlib")
        return found or configured or "ranlib"

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        ar = self._ar()
        ranlib = self._ranlib()
        # OHOS musl libc 已将 librt 功能并入 libc，Makefile.linux 的 LIBS+=-lrt
        # 在 OHOS sysroot 无 librt.a 时会导致链接失败；上游 test 目标仅用 -lm，
        # 因此通过 RT_LIBS 覆盖为空。静态库本身不需要链接时解析 rt。
        make = (
            f"make -f Makefile CC={cc} AR={ar} RANLIB={ranlib} "
            f"CFLAGS+=-fPIC LIBS=-lm -j1"
        )
        with chdir(self, self.source_folder):
            # 上游单元测试（testham 全功能 11 用例 + testnoham 专利规避 10 用例；
            # test 目标内部会 clean+lib，运行时会临时重建共享库）
            self.run(make + " test", ignore_errors=False)
            # 测试目标里的 clean 会删除 libntru.a，最后重新生成一次供打包
            if self.options.shared:
                self.run(make + " lib")
            else:
                self.run(make + " static-lib")

    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")
        if self.options.shared:
            copy(self, "libntru.so", self.source_folder, lib_dir, keep_path=False)
        else:
            copy(self, "libntru.a", self.source_folder, lib_dir, keep_path=False)
        for header in (
            "ntru.h", "types.h", "key.h", "encparams.h", "hash.h", "rand.h", "err.h",
        ):
            copy(self, header, os.path.join(self.source_folder, "src"), inc_dir, keep_path=False)
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["ntru"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libntru")
        self.cpp_info.set_property("cmake_target_name", "libntru::libntru")
        self.cpp_info.set_property("pkg_config_name", "libntru")
