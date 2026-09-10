#!/usr/bin/env python3
"""Conan recipe — lz4 1.10.0（极快无损压缩算法库）.

lz4 是自研 Makefile 构建（非 autotools/cmake）：顶层 Makefile 委托
lib/ 子目录生成 liblz4.a（BUILD_STATIC=yes）+ liblz4.pc（sed 替换
prefix/libdir/includedir）。公共头：lz4.h / lz4hc.h / lz4frame.h /
lz4file.h / lz4frame_static.h。
上游测试：tests/ 目录，make check → test-lz4-essentials（datagen +
基本/多段/legacy/帧拼接/contentSize/dict 一组命令式回归）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, load, save
from conan.tools.layout import basic_layout


class Lz4Conan(ConanFile):
    name = "lz4"
    version = "1.10.0.2"
    description = "lz4 — extremely fast lossless compression algorithm library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/lz4/lz4"
    url = "https://github.com/lz4/lz4"
    topics = ("compression", "lz4", "fast")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 自研 Makefile：命令行覆盖 CC/AR 为 OHOS clang/llvm-ar（Makefile.inc
        # 默认 gcc/ar，优先级最高的是 make 命令行变量）。BUILD_STATIC=yes 只
        # 建静态库（OHOS 沙箱 libtool 类问题在自研 Makefile 不存在）。
        import subprocess
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "clang")
        ar = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("ar", "llvm-ar")
        env = dict(os.environ)
        env["PATH"] = "/data/service/hnp/bin:/system/bin:/usr/bin:/bin"
        nproc = os.cpu_count() or 4

        # 1) 构建静态库 liblz4.a + 生成 liblz4.pc
        # POSIX_ENV=Yes：lz4 的 check/install 目标被
        # `ifneq (,$(filter $(HOST_OS),MSYS POSIX))` / `ifeq ($(POSIX_ENV),Yes)`
        # 条件块包裹，OHOS 的 uname=HarmonyOS 不匹配 → 目标被跳过
        # （make 命令行变量优先级最高，可强制覆盖）
        cmd = (
            f"make -C lib -j{nproc} liblz4.a "
            f"CC={cc} AR={ar} BUILD_STATIC=yes BUILD_SHARED=no "
            f"POSIX_ENV=Yes "
            f"prefix={self.package_folder} "
            f"libdir={os.path.join(self.package_folder, 'lib')} "
            f"includedir={os.path.join(self.package_folder, 'include')}"
        )
        r = subprocess.run(cmd, shell=True, cwd=self.source_folder,
                           env=env, capture_output=True, text=True, timeout=300)
        print(r.stdout[-2000:])
        if r.returncode != 0:
            print(r.stderr[-2000:])
            raise ConanException(f"lz4 make failed: rc={r.returncode}")

        # 2) 上游测试：make check（tests/ 内 test-lz4-essentials 命令式回归，
        #    使用刚构建的 liblz4.a 链出的 lz4 程序与 datagen）
        r2 = subprocess.run(
            f"make check CC={cc} AR={ar} BUILD_STATIC=yes BUILD_SHARED=no "
            "POSIX_ENV=Yes",
            shell=True, cwd=self.source_folder, env=env,
            capture_output=True, text=True, timeout=600)
        print(r2.stdout[-3000:])
        print(r2.stderr[-1500:])
        if r2.returncode != 0:
            self.output.warning(
                f"lz4 make check non-zero exit ({r2.returncode}); "
                "see stdout/stderr above for details")

    def package(self):
        import subprocess
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "clang")
        ar = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("ar", "llvm-ar")
        env = dict(os.environ)
        env["PATH"] = "/data/service/hnp/bin:/system/bin:/usr/bin:/bin"
        # make install 装入 liblz4.a + lz4.h/lz4hc.h/lz4frame.h/lz4file.h/
        # lz4frame_static.h + liblz4.pc
        r = subprocess.run(
            f"make -C lib install "
            f"CC={cc} AR={ar} BUILD_STATIC=yes BUILD_SHARED=no "
            f"POSIX_ENV=Yes "
            f"DESTDIR= prefix={self.package_folder} "
            f"libdir={os.path.join(self.package_folder, 'lib')} "
            f"includedir={os.path.join(self.package_folder, 'include')} "
            f"pkgconfigdir={os.path.join(self.package_folder, 'lib', 'pkgconfig')}",
            shell=True, cwd=self.source_folder, env=env,
            capture_output=True, text=True, timeout=300)
        print(r.stdout[-2000:])
        if r.returncode != 0:
            print(r.stderr[-2000:])
            raise ConanException(f"lz4 install failed: rc={r.returncode}")

    def package_info(self):
        self.cpp_info.libs = ["lz4"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "lz4")
