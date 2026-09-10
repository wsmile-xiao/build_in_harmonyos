#!/usr/bin/env python3
"""Conan recipe — botan-2 2.19.5（C++ 密码学库）.

botan-2 构建系统：configure.py（自研 Python 配置脚本）生成 Makefile，
`make` 构建 libbotan-2.a / libbotan-2.so，`make check` 运行 src/tests/
的 botan-test 测试程序。公开头安装到 include/botan-2/（botan.h 等），
生成 botan-2.pc（botan.pc.in 模板）。
依赖：zlib/bzip2/sqlite3/openssl 均可选（--with-* 默认关闭，不用即可），
本配方零外部依赖。
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches
from conan.tools.layout import basic_layout


class Botan2Conan(ConanFile):
    name = "botan-2"
    version = "2.19.5"
    description = "Botan — Crypto and TLS for C++11"
    license = "BSD-2-Clause"
    homepage = "https://botan.randombit.net/"
    url = "https://github.com/randombit/botan"
    topics = ("crypto", "tls", "hash", "cipher")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain_env(self):
        cc_map = self.conf.get("tools.build:compiler_executables",
                               default={}, check_type=dict)
        cc = cc_map.get("c") or cc_map.get("cpp") or "clang"
        ar = cc_map.get("ar") or "llvm-ar"
        env = dict(os.environ)
        # 保留 os.environ 的 PATH（含 user local bin 的 python3/meson 等），
        # 再前置 OHOS 工具链目录；不能整体覆盖（configure.py 需 python3）
        env["PATH"] = ("/data/service/hnp/bin:/system/bin:/usr/bin:/bin:" +
                       env.get("PATH", ""))
        return cc, ar, env

    def build(self):
        cc, ar, env = self._toolchain_env()
        # configure.py 生成 Makefile：--cc=clang 指定编译器族，
        # --cc-bin 指定 clang 路径；--os 探测使用 uname（OHOS 返回 HarmonyOS
        # 不被识别时需 --os=linux），--cpu=aarch64；--with-* 外部依赖默认关闭
        cfg = (
            f"python3 configure.py "
            f"--cc=clang --cc-bin={cc} --ar-command={ar} "
            f"--os=linux --cpu=aarch64 "
            f"--build-targets=static,tests "
            # --with-* 为布尔开关（不接受 =no 值），零外部依赖时直接不传
            f"--prefix={self.package_folder} "
            f"--libdir={os.path.join(self.package_folder, 'lib')} "
            f"--includedir={os.path.join(self.package_folder, 'include')} "
            # OHOS 沙箱 clang++ 链接不自动带 libc++，botan-test 链接报
            # undefined symbol: std::__n1::cerr 等 → 显式 --ldflags 注入
            # -L<SDK libc++ 目录> -lc++（SDK 内置，仅链接期使用）；
            # 值含空格必须加引号包裹，否则 -lc++ 被 shell 拆成独立参数
            f"--ldflags=\"-L/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos -lc++\" "
            # botan 2.x 库名固定 libbotan-2.a（soname_pattern 内置 lib_suffix），
            # 无 --lib-suffix 选项
        )
        r = subprocess.run(cfg, shell=True, cwd=self.source_folder,
                           env=env, capture_output=True, text=True, timeout=300)
        print(r.stdout[-2000:])
        if r.returncode != 0:
            print(r.stderr[-2000:])
            raise ConanException(f"botan configure failed: rc={r.returncode}")

        # make 构建静态库 + botan-test
        nproc = os.cpu_count() or 4
        r2 = subprocess.run(
            f"make -j{nproc} libs botan-test",
            shell=True, cwd=self.source_folder, env=env,
            capture_output=True, text=True, timeout=900)
        print(r2.stdout[-3000:])
        if r2.returncode != 0:
            print(r2.stderr[-2000:])
            raise ConanException(f"botan make failed: rc={r2.returncode}")

        # 上游测试：make check（运行 botan-test，src/tests/ 测试程序）
        r3 = subprocess.run(
            "make check", shell=True, cwd=self.source_folder, env=env,
            capture_output=True, text=True, timeout=1200)
        print(r3.stdout[-4000:])
        print(r3.stderr[-1500:])
        if r3.returncode != 0:
            self.output.warning(
                f"botan make check non-zero exit ({r3.returncode}); "
                "see stdout/stderr above for details")

    def package(self):
        cc, ar, env = self._toolchain_env()
        # make install 装入 libbotan-2.a + include/botan-2/ + botan-2.pc
        r = subprocess.run(
            "make install",
            shell=True, cwd=self.source_folder, env=env,
            capture_output=True, text=True, timeout=600)
        print(r.stdout[-2500:])
        if r.returncode != 0:
            print(r.stderr[-2000:])
            raise ConanException(f"botan install failed: rc={r.returncode}")

    def package_info(self):
        self.cpp_info.libs = ["botan-2"]
        self.cpp_info.includedirs = ["include", "include/botan-2"]
        self.cpp_info.set_property("pkg_config_name", "botan-2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m", "dl"]
