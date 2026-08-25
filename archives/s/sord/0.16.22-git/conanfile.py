#!/usr/bin/env python3
"""Conan recipe for sord 0.16.22-git — Meson build system.

Sord is a lightweight C library for storing RDF data in memory (in-memory
RDF model/quad store), built on serd and zix, used by the LV2 audio plugin
ecosystem.
"""
import os
import shutil
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SordConan(ConanFile):
    name = "sord"
    version = "0.16.22-git"
    description = "Lightweight C library for storing RDF data in memory"
    license = "ISC"
    homepage = "https://drobilla.net/software/sord"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sord is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # sord 依赖 serd（RDF 语法）+ zix（数据结构）
        self.requires("serd/0.32.9-git")
        self.requires("zix/0.8.1-git")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["docs"] = "disabled"
        tc.project_options["man"] = "disabled"
        tc.project_options["tests"] = "enabled"
        # 依赖（zix/serd）的 pkg-config 路径注入：sord 的 meson 显式
        # dependency('zix-0')/dependency('serd-0')，需 PKG_CONFIG_PATH 找到
        # 对应 .pc。MesonToolchain 的 pkg_config_path 默认只指向 generators_folder，
        # 覆盖环境变量 PKG_CONFIG_PATH，故把依赖的 pkgconfig 目录追加进
        # tc.pkg_config_path（meson 原生文件 pkg_config_path 项）
        dep_pc_paths = []
        for dep in ("zix", "serd"):
            if dep in self.dependencies:
                dep_pkg = self.dependencies[dep].package_folder
                dep_pc_paths.append(os.path.join(dep_pkg, "lib", "pkgconfig"))
                # 制品仓旧版依赖包的 .pc prefix 可能未修正（prefix=/ 指向根目录，
                # 或头文件布局与上游不同），meson 经 pkg-config 拿到错误的
                # Cflags（如 -I//include/zix-0 不存在）。显式探测依赖包真实
                # include 目录并注入 -isystem，覆盖 .pc 的错误 include 路径。
                for sub in (f"include/{dep}-0", f"include/{dep}", "include"):
                    cand = os.path.join(dep_pkg, sub)
                    if os.path.isdir(cand):
                        tc.c_args.append(f"-isystem{cand}")
                        tc.cpp_args.append(f"-isystem{cand}")
                        self.output.info(
                            f"sord: inject -isystem {cand} (dependency {dep})"
                        )
                        break
                # 同样注入真实 lib 目录，避免 .pc 的 -L 路径错误导致链接失败
                libdir = os.path.join(dep_pkg, "lib")
                if os.path.isdir(libdir):
                    tc.c_link_args.append(f"-L{libdir}")
                    tc.cpp_link_args.append(f"-L{libdir}")
        if dep_pc_paths:
            tc.pkg_config_path = os.pathsep.join(
                [tc.pkg_config_path] + dep_pc_paths
            )
        tc.generate()
        # 生成 conanrun.sh：注入依赖（serd/zix）共享库路径，meson test 运行时
        # 需要 libserd-0.so.0/libzix-0.so.0（否则 exit 127 找不到库）
        VirtualRunEnv(self).generate()
        # OHOS: meson cannot find llvm-ar via PATH, inject into native file
        ar_path = shutil.which("ar") or "/data/service/hnp/bin/ar"
        native_file = self.generators_folder + "/conan_meson_native.ini"
        with open(native_file) as f:
            content = f.read()
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nc ="
        )
        with open(native_file, "w") as f:
            f.write(content)
        # OHOS SDK 的 lld 运行时依赖 libxml2.so.16（llvm/lib 目录），
        # CI Worker 上 LD_LIBRARY_PATH 未含该目录导致 clang 调用 lld 时
        # 链接器检测/链接失败（libxkbcommon #6310 同款问题），注入即可
        llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib"
        )
        if os.path.isdir(llvm_lib):
            env = Environment()
            env.append_path("LD_LIBRARY_PATH", llvm_lib)
            env.vars(self).save_script("conanbuild_env")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # 上游测试：meson test（sord 单元测试）
        # 注意：self.run 的 cwd 已在 build-release 目录，直接 meson test；
        # conanrun 环境注入依赖（serd/zix）共享库路径，否则测试二进制
        # 加载 libserd-0.so.0 失败（exit 127）
        self.run("meson test", env=["conanbuild", "conanrun"])

    def package(self):
        meson = Meson(self)
        meson.install()
        # 修正 sord-0.pc 的 prefix：meson install 生成 prefix=/（根目录），
        # 导致下游（sratom）用 pkg-config 拿到 /include/sord-0 等不存在路径，
        # 头文件找不到。改写为包真实路径。
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "sord-0.pc")
        if os.path.isfile(pc_path):
            with open(pc_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace(
                "prefix=/",
                f"prefix={self.package_folder}",
            )
            with open(pc_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.output.info("Patched sord-0.pc prefix to package folder")

    def package_info(self):
        self.cpp_info.libs = ["sord-0"]
        self.cpp_info.includedirs = ["include/sord-0"]
        self.cpp_info.set_property("cmake_file_name", "sord")
        self.cpp_info.set_property("pkg_config_name", "sord-0")
