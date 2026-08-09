#!/usr/bin/env python3
"""Conan recipe — ADOL-C 2.7.2 (autotools).

ADOL-C: Automatic Differentiation of C/C++ programs (coin-or/ADOL-C).
Builds the libadolc shared library and adolc headers.
Optional deps (colpack/boost/openmp) are disabled: not published on ohpcd.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AdolcConan(ConanFile):
    name = "adolc"
    version = "2.7.2"
    description = "ADOL-C: Automatic Differentiation of C/C++ programs"
    # 上游 LICENSE 为双许可：EITHER EPL-1.0 OR GPL-2.0+（GPL-2.0-or-later）
    license = "EPL-1.0 OR GPL-2.0-or-later"
    homepage = "https://github.com/coin-or/ADOL-C"
    url = "https://github.com/coin-or/ADOL-C"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 所有依赖均为可选（colpack/boost/openmp），ohpcd 未发布 colpack -> sparse 驱动保持禁用
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _builtins_path(self):
        """定位 compiler-rt builtins 静态库（提供 __addtf3/__multf3 等 quad-float 符号）。

        taylor.o（Taylor ODE 驱动）用 long double，libtool 以 clang++ -nostdlib 链接共享库时
        不带 -lclang_rt.builtins，导致 .so 运行期缺 __addtf3 等符号 (E098/E205 模式)。
        把 builtins.a 追加到 LDFLAGS，使 libadolc.so 自包含。

        找不到有效文件时返回空串，由 generate() 的 if 守卫跳过追加（避免把不存在的
        硬编码路径喂给链接器——AI review P2 / 跨 Worker 失败模式）。
        """
        import subprocess

        known = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/"
            "lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a"
        )
        if os.path.isfile(known):
            return known

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        clang = compilers.get("c") or compilers.get("cpp") or ""
        if not clang or not os.path.isfile(clang):
            self.output.warning(
                "libclang_rt.builtins.a not found (no clang); skip LDFLAGS append"
            )
            return ""

        try:
            res = (
                subprocess.check_output(
                    [clang, "--print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
            self.output.warning(
                f"clang --print-resource-dir failed ({exc}); skip builtins LDFLAGS"
            )
            return ""

        for cand in ("aarch64-linux-ohos", "aarch64-unknown-linux-ohos"):
            path = os.path.join(res, "lib", cand, "libclang_rt.builtins.a")
            if os.path.isfile(path):
                return path

        self.output.warning(
            f"libclang_rt.builtins.a not under {res}; skip LDFLAGS append"
        )
        return ""

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-sparse=no")
        tc.configure_args.append("--without-boost")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # E098：仅当 builtins.a 真实存在时追加，避免无效路径导致链接失败
        builtins = self._builtins_path()
        if builtins:
            tc.extra_ldflags.append(builtins)
        else:
            self.output.warning(
                "building without libclang_rt.builtins.a; "
                "libadolc.so may lack quad-float symbols at runtime"
            )
        tc.generate()

    def build(self):
        # 平台补丁（config.guess/config.sub 的 HarmonyOS 三元组 E205/E072、
        # configure umask 077->022 E129、adolc_settings.h 生成态）在 conandata.yml 注册
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # .la 里烤死绝对 libdir 路径，删除以免下游 libtool 误用
        for _la in glob.glob(os.path.join(self.package_folder, "**", "*.la"), recursive=True):
            try:
                os.remove(_la)
            except OSError:
                pass

    def package_info(self):
        self.cpp_info.libs = ["adolc"]
        # 说明：手动 autotools 构建会装到 lib64，但 conan AutotoolsToolchain
        # 强制 --libdir=${prefix}/lib，conan 包内统一在 lib/，用默认 libdirs。
        self.cpp_info.set_property("cmake_file_name", "adolc")
        self.cpp_info.set_property("cmake_target_name", "adolc::adolc")
        self.cpp_info.set_property("pkg_config_name", "adolc")
