#!/usr/bin/env python3
"""Conan recipe — kernelshark 2.4.0 (libkshark core layer)

Kernel Shark 2.4.0 分层交付的第一层：libkshark 核心库（libkshark.so +
开发头文件 + libkshark.pc）。plot 层（libkshark-plot，需 freeglut/GLU，仓内
与制品仓均无）与 GUI 层（libkshark-gui + kernelshark/kshark-record 可执行，
需 Qt6 + FreeSans 字体且依赖 plot 层）本次不构建，由 CMake 补丁显式门控。

依赖闭包处理（R36 证据，2026-09-17 检索）：
- libtraceevent 1.9.0 / libtracefs 1.8.3 / libtracecmd(trace-cmd v3.3.3)
  在本仓 archives/ 中无 conanfile.py（仅 manifest 笔记归档），ohpcd 制品仓
  亦无对应包 —— 无法 requires()。参照 archives/a/address-standardizer/3.7.0
  的 vendored 先例（PostgreSQL 18.3 整树 vendor + 构建期 bootstrap），
  三个库的官方源码在本 recipe 内 vendored 构建并随包交付（libkshark.so 的
  DT_NEEDED 运行时闭包）。
- json-c：制品仓有 json-c/0.18，正常 requires。
- zlib：trace-cmd 压缩支持自动探测到 OHOS SDK sysroot 的 libz，运行时由
  /system/lib64/ndk/libz.so 解析（系统 NDK 库，不随包交付）。
- OpenMP：内核 OHOS 运行时无 libomp.so（/system* 全量检索无），显式禁用
  （上游 find_package(OpenMP) 本就是可选）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, copy, patch, export_conandata_patches


class KernelsharkConan(ConanFile):
    name = "kernelshark"
    version = "2.4.0"
    description = "Kernel Shark: front-end reader of the Linux kernel tracing (ftrace) data (core libkshark layer)"
    license = "GPL-2.0-only"           # GUI; libkshark core is LGPL-2.1-only
    homepage = "https://kernelshark.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # 上游核心层纯 C；C++ 仅 plot/GUI 层使用（本次不构建）
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def export_sources(self):
        export_conandata_patches(self)
        # trace-btf-compat.h 是 vendored *新文件*（非补丁）：修补 libtraceevent
        # 在 OHOS 上缺失的 BTF kinds/qsort_r（同仓 libtraceevent 归档笔记的
        # 做法，compat 头本体随 patches/ 一起导出，address-standardizer 同款）
        copy(self, "trace-btf-compat.h",
             os.path.join(self.recipe_folder, "patches"),
             os.path.join(self.export_sources_folder, "patches"))

    def requirements(self):
        # libkshark-configio.c 硬依赖 json-c（find_package(JSONC REQUIRED)）
        self.requires("json-c/0.18")

    def validate(self):
        # R32：平台分支显式评估 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kernelshark is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 cmake_minimum_required(3.1.2) 低于本仓 CMake 的兼容下限
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # OHOS 运行时无 libomp.so，OpenMP 属上游可选加速，显式关闭
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = "True"
        # SONAME 门禁（L5a）：profile os=OHOS → CMAKE_SYSTEM_NAME=HarmonyOS，
        # 但 HNP CMake 4.1.2 无 Platform/HarmonyOS.cmake → soname flag 未定义
        # → 上游 set_target_properties(kshark SOVERSION 2) 被静默忽略，产出
        # 无 DT_SONAME 的 libkshark.so。按仓内 attica/attica5/expat 已验证
        # 模式：显式给 soname flag + 关闭版本化符号链接（单文件 libkshark.so，
        # SONAME=libkshark.so，DT_NEEDED 由包内 lib/ 解析）
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generator = "Unix Makefiles"
        tc.generate()

        # vendored make 库的构建环境（save_script 写入 conanbuild_*.sh，
        # 与默认 conanbuild 环境一起被 self.run(env="conanbuild") 加载）
        env = Environment()
        env.define("CC", self._cc())
        env.define("AR", self._ar())
        stage = os.path.join(self.build_folder, "stage")
        env.define_path("PKG_CONFIG_PATH", os.path.join(stage, "lib", "pkgconfig"))
        # 设备怪癖：HMDFS 上 HNP bash 的 getcwd() 随机 EPERM，显式导出
        # 与构建目录一致的 PWD（同仓 dieharder/gsl 已验证手法）
        env.define("PWD", self.build_folder)
        env.vars(self, scope="build").save_script("conanbuild_vendored")

    # ── 小工具 ─────────────────────────────────────────────────────
    def _cc(self):
        return self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict).get("c", "clang")

    def _ar(self):
        return os.path.join(os.path.dirname(self._cc()), "llvm-ar")

    def _set_pwd(self, directory):
        env = Environment()
        env.define("PWD", directory)
        env.vars(self, scope="build").save_script("conanbuild_pwd")

    def _symlink(self, base_dir, target, linkname):
        link = os.path.join(base_dir, linkname)
        if os.path.lexists(link):
            os.unlink(link)
        os.symlink(target, link)

    # ────────────────────────────────────────────────────────────────
    # vendored 依赖链：libtraceevent → libtracefs → libtracecmd
    # （每个库构建产物手工 stage 到 build/stage，不依赖设备缺失的
    #  /bin/install；make 一律 -j1，R9：HMDFS jobserver fifo EPERM）
    # ────────────────────────────────────────────────────────────────
    def _run_make(self, directory, targets, extra=None):
        stage = os.path.join(self.build_folder, "stage")
        args = ["make", "-j1", "CC=" + self._cc(), "AR=" + self._ar(),
                "prefix=" + stage,
                "libdir=" + os.path.join(stage, "lib"),
                "libdir_relative=lib"]
        if extra:
            args += extra
        args += targets
        # PWD 必须与 make cwd 一致（设备 getcwd 怪癖），逐目录覆盖
        self._set_pwd(directory)
        self.run(" ".join(args), cwd=directory, env="conanbuild")

    def _build_libtraceevent(self):
        src = os.path.join(self.build_folder, "lte")
        get(self, **self.conan_data["libtraceevent"], strip_root=True,
            retry=5, retry_wait=15, destination=src)
        # vendored compat 头 + include 补丁（conan 2 纯 Python patcher）
        copy(self, "trace-btf-compat.h",
             os.path.join(self.source_folder, "patches"),
             os.path.join(src, "src"))
        patch(self, base_path=src, strip=0,
              patch_file=os.path.join(self.source_folder, "patches",
                                      "0002-libtraceevent-ohos-btf-compat-include.patch"))
        self._run_make(src, ["all"])
        stage = os.path.join(self.build_folder, "stage")
        libdir = os.path.join(stage, "lib")
        incdir = os.path.join(stage, "include", "traceevent")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(os.path.join(libdir, "pkgconfig"), exist_ok=True)
        os.makedirs(os.path.join(libdir, "traceevent", "plugins"), exist_ok=True)
        os.makedirs(incdir, exist_ok=True)
        copy(self, "libtraceevent.so.1.9.0", os.path.join(src, "lib"), libdir)
        copy(self, "libtraceevent.a", os.path.join(src, "lib"), libdir)
        self._symlink(libdir, "libtraceevent.so.1.9.0", "libtraceevent.so.1")
        self._symlink(libdir, "libtraceevent.so.1", "libtraceevent.so")
        for header in ("event-parse.h", "event-utils.h", "kbuffer.h",
                       "trace-seq.h"):
            copy(self, header, os.path.join(src, "include", "traceevent"),
                 incdir)
        # libtraceevent.pc 由 make 用 stage prefix 生成（libdir_relative=lib）
        copy(self, "libtraceevent.pc", src,
             os.path.join(libdir, "pkgconfig"))
        # 插件：运行期由 TRACEEVENT_PLUGIN_DIR 覆盖加载路径（详见 notes.md）
        copy(self, "plugin_*.so", os.path.join(src, "plugins"),
             os.path.join(libdir, "traceevent", "plugins"))

    def _build_libtracefs(self):
        src = os.path.join(self.build_folder, "ltfs")
        get(self, **self.conan_data["libtracefs"], strip_root=True,
            retry=5, retry_wait=15, destination=src)
        patch(self, base_path=src, strip=0,
              patch_file=os.path.join(self.source_folder, "patches",
                                      "0003-libtracefs-ohos-vsock-header-conflict.patch"))
        self._run_make(src, ["all"])
        stage = os.path.join(self.build_folder, "stage")
        libdir = os.path.join(stage, "lib")
        incdir = os.path.join(stage, "include", "tracefs")
        os.makedirs(incdir, exist_ok=True)
        copy(self, "libtracefs.so.1.8.3", os.path.join(src, "lib"), libdir)
        copy(self, "libtracefs.a", os.path.join(src, "lib"), libdir)
        self._symlink(libdir, "libtracefs.so.1.8.3", "libtracefs.so.1")
        self._symlink(libdir, "libtracefs.so.1", "libtracefs.so")
        copy(self, "tracefs.h", os.path.join(src, "include"), incdir)
        copy(self, "libtracefs.pc", src,
             os.path.join(libdir, "pkgconfig"))

    def _build_libtracecmd(self):
        src = os.path.join(self.build_folder, "tc")
        get(self, **self.conan_data["tracecmd"], strip_root=True,
            retry=5, retry_wait=15, destination=src)
        # 快照 tarball 不含 lib/traceevent、lib/tracefs 子模块 → Makefile 走
        # pkg-config 外部依赖（>= 1.5 / >= 1.8），指向本 recipe 的 stage；
        # NO_VSOCK=1：vsock 探测在本交叉环境无意义且 libtracecmd 不用它
        self._run_make(src, ["libs"], extra=["NO_VSOCK=1"])
        stage = os.path.join(self.build_folder, "stage")
        libdir = os.path.join(stage, "lib")
        incdir = os.path.join(stage, "include", "trace-cmd")
        os.makedirs(incdir, exist_ok=True)
        copy(self, "libtracecmd.so.1.5.3",
             os.path.join(src, "lib", "trace-cmd"), libdir)
        self._symlink(libdir, "libtracecmd.so.1.5.3", "libtracecmd.so.1")
        self._symlink(libdir, "libtracecmd.so.1", "libtracecmd.so")
        copy(self, "trace-cmd.h", os.path.join(src, "include", "trace-cmd"),
             incdir)
        copy(self, "libtracecmd.pc", src,
             os.path.join(libdir, "pkgconfig"))

    def _cmake_cmd(self, *extra):
        # kernelshark 源树在 build/ks（vendored 树不放 source 缓存），
        # 不用 CMake() 助手的默认 source 目录，手动驱动 cmake
        toolchain = os.path.join(self.generators_folder,
                                 "conan_toolchain.cmake")
        parts = ["cmake",
                 "-S", '"' + os.path.join(self.build_folder, "ks") + '"',
                 "-B", '"' + self.build_folder + '"',
                 '-DCMAKE_TOOLCHAIN_FILE="' + toolchain + '"',
                 # 显式命令行传递（toolchain cache_variables 在本 conan 版本
                 # 未序列化到 conan_toolchain.cmake，双保险）
                 "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
                 "-DCMAKE_DISABLE_FIND_PACKAGE_OpenMP=TRUE"]
        parts += list(extra)
        return " ".join(parts)

    def build(self):
        # 主源（kernel-shark）与三个 vendored 依赖统一在 build() 取回，
        # 各自解包到 build/ 下独立子树。源走 GitHub 上游镜像（见
        # conandata 注释：CI worker 对 git.kernel.org 不可达）；GitHub
        # 偶发断流，显式加大 retry/retry_wait 覆盖默认值（同仓
        # abiword-plugin-wikipedia 先例），下列各下载点同样处理。
        ks_src = os.path.join(self.build_folder, "ks")
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=5, retry_wait=15, destination=ks_src)
        self._build_libtraceevent()
        self._build_libtracefs()
        self._build_libtracecmd()

        # ── kernelshark（核心层）──
        ks_src = os.path.join(self.build_folder, "ks")
        patch(self, base_path=ks_src, strip=0,
              patch_file=os.path.join(self.source_folder, "patches",
                                      "0001-kernelshark-cmake-ohos-core-layer.patch"))

        stage = os.path.join(self.build_folder, "stage")
        json_c = self.dependencies["json-c"]
        jc_inc = json_c.cpp_info.includedirs[0]
        jc_libdir = json_c.cpp_info.libdirs[0]

        self._set_pwd(self.build_folder)
        configure = self._cmake_cmd(
            # Find* 模块的 pkg-config 提示指向 vendored stage
            '-DCMAKE_PREFIX_PATH="' + stage + '"',
            # libkshark.h 用 <json-c/json.h>，上游 FindJSONC 模块
            # (PATH_SUFFIXES json-c) 返回的子目录对不上 → 显式给父目录
            '-DJSONC_INCLUDE_DIR="' + jc_inc + '"',
            '-DJSONC_LIBRARY="' + os.path.join(jc_libdir, "libjson-c.so") + '"',
            # 上游用绝对 DESTINATION 安装：直接落到最终 package 布局
            '-D_INSTALL_PREFIX="' + self.package_folder + '"',
            '-D_LIBDIR="' + os.path.join(self.package_folder, "lib") + '"',
            '-DPKG_CONGIG_DIR="' + os.path.join(self.package_folder, "lib",
                                                "pkgconfig") + '"',
            '-DCMAKE_INSTALL_PREFIX="' + self.package_folder + '"',
        )
        self.run(configure, cwd=self.build_folder, env="conanbuild")
        self.run("cmake --build . -- -j1", cwd=self.build_folder,
                 env="conanbuild")

    def package(self):
        self.run("cmake --install .", cwd=self.build_folder, env="conanbuild")

        # vendored 依赖库随包交付（libkshark.so 的运行时闭包；ohpcd 无独立包）
        stage_lib = os.path.join(self.build_folder, "stage", "lib")
        pkg_lib = os.path.join(self.package_folder, "lib")
        for real in ("libtraceevent.so.1.9.0", "libtracefs.so.1.8.3",
                     "libtracecmd.so.1.5.3"):
            copy(self, real, stage_lib, pkg_lib)
        for soname, real in (
                ("libtraceevent.so.1", "libtraceevent.so.1.9.0"),
                ("libtraceevent.so", "libtraceevent.so.1"),
                ("libtracefs.so.1", "libtracefs.so.1.8.3"),
                ("libtracefs.so", "libtracefs.so.1"),
                ("libtracecmd.so.1", "libtracecmd.so.1.5.3"),
                ("libtracecmd.so", "libtracecmd.so.1")):
            self._symlink(pkg_lib, real, soname)
        copy(self, "plugin_*.so",
             os.path.join(stage_lib, "traceevent", "plugins"),
             os.path.join(pkg_lib, "traceevent", "plugins"))
        stage_inc = os.path.join(self.build_folder, "stage", "include")
        copy(self, "*.h", os.path.join(stage_inc, "traceevent"),
             os.path.join(self.package_folder, "include", "traceevent"))
        copy(self, "*.h", os.path.join(stage_inc, "tracefs"),
             os.path.join(self.package_folder, "include", "tracefs"))
        copy(self, "*.h", os.path.join(stage_inc, "trace-cmd"),
             os.path.join(self.package_folder, "include", "trace-cmd"))

    def package_info(self):
        self.cpp_info.libs = ["kshark", "tracecmd", "tracefs", "traceevent"]
        # libtracecmd（vendored）的 zlib 压缩路径：链接闭包显式补系统 libz
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["z"]
        self.cpp_info.set_property("cmake_file_name", "kernelshark")
        self.cpp_info.set_property("cmake_target_name", "kernelshark::kernelshark")
        self.cpp_info.set_property("pkg_config_name", "libkshark")
        # 运行时闭包都在本包 lib/（vendored .so + 插件目录），供消费者与
        # test_package 通过 conanrun 的 LD_LIBRARY_PATH 直接获得
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))
