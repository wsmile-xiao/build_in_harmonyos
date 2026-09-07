#!/usr/bin/env python3
"""Conan test_package for gtkspell3 3.0.10.

PkgConfig-based consumer test (gtkdatabox precedent): gtk/3.24.43 recipe
intentionally does NOT declare cpp_info.requires (CMakeDeps rejects the three
reference styles for flat packages), so a plain CMakeDeps target link cannot
propagate transitive headers (e.g. harfbuzz's hb.h through pango). Using
PkgConfigDeps + pkg_check_modules(gtkspell3-3.0) lets pkg-config resolve the
whole Requires: glib-2.0 gtk+-3.0 enchant-2 chain, including transitive
pcre2/ffi/expat etc.

test(): 真实运行 test_gtkspell3 二进制（4 个断言），运行时库路径由
_pkg_config_env() 从依赖图注入 LD_LIBRARY_PATH，避免 headless 静默跳过。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class Gtkspell3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _sdk_llvm_libdir(self):
        """Locate the active OHOS SDK llvm/lib shipping libc++_shared.so.

        test_package 的 cmake 是 /data/service/hnp/bin/cmake（C++ 程序，DT_NEEDED
        libc++_shared.so）；该库位于 <sdk>/llvm/lib/aarch64-linux-ohos/ 子目录。
        CI shell 前置 ~/usr/local/lib 会遮蔽 ABI 匹配版本，导致 cmake 启动即
        'Error relocating ... symbol not found'。探测逻辑：
        1) compiler -print-resource-dir 推导 SDK 根
        2) 候选目录含 libc++_shared.so 即命中（根目录或其 aarch64-linux-ohos 子目录）
        """
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        # 展开：候选根目录本身 + 其 aarch64-linux-ohos 子目录
        expanded = []
        for cand in dict.fromkeys(candidates):
            expanded.append(cand)
            sub = os.path.join(cand, "aarch64-linux-ohos")
            if os.path.isdir(sub):
                expanded.append(sub)
        for cand in dict.fromkeys(expanded):
            if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                return cand
        return ""

    def _pkg_config_env(self):
        env = Environment()
        # SDK llvm/lib：test_package 的 cmake 为 C++ 程序，运行期需 SDK libc++.so；
        # CI shell 前置 ~/usr/local/lib 会遮蔽 ABI 匹配版本（同主配方 abseil 模式）
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info("Prepending OHOS SDK runtime path: {}".format(sdk_llvm_lib))
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        # PkgConfigDeps 已在 generators 目录生成全依赖图 .pc
        # （含 gtkspell3-3.0.pc 与 glib/pcre2/gtk/enchant 等传递 .pc）
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # 被测包自身安装的 .pc 所在目录
        for dependency in self.dependencies.values():
            if not getattr(dependency, "package_folder", None):
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir:
                    continue
                if os.path.isabs(libdir):
                    full = libdir
                else:
                    full = os.path.join(dependency.package_folder, libdir)
                env.prepend_path("LD_LIBRARY_PATH", full)
                env.prepend_path("PKG_CONFIG_PATH", os.path.join(full, "pkgconfig"))
        # OHOS 运行时库（pcre2/ffi/expat/intl/epoxy）辅助
        # 注：依赖 HNP 部署布局（/data/service/hnp/*/*/lib），
        # 仅为测试环境辅助查找，不影响配方产物（R33 平台辅助路径）。
        # libepoxy 是 gtk3 的传递依赖，不在 gtkspell3 直接依赖图中，
        for pattern in ("libpcre2-8.so*", "libffi.so*", "libexpat.so*", "libintl.so*", "libepoxy.so*"):
            for match in glob.glob("/data/service/hnp/*/*/lib/{}".format(pattern)):
                libdir = os.path.dirname(match)
                env.append_path("LD_LIBRARY_PATH", libdir)
        return env

    def _resolved_lib_dirs(self):
        """解析依赖图实际提供的 lib 目录（供运行时库存在性检查）。"""
        dirs = []
        for dependency in self.dependencies.values():
            if not getattr(dependency, "package_folder", None):
                continue
            for libdir in dependency.cpp_info.libdirs or []:
                if not libdir:
                    continue
                full = libdir if os.path.isabs(libdir) else os.path.join(
                    dependency.package_folder, libdir)
                if full not in dirs:
                    dirs.append(full)
        # OHOS HNP 部署布局辅助目录（同 _pkg_config_env）
        for pattern in ("libpcre2-8.so*", "libffi.so*", "libexpat.so*", "libintl.so*", "libepoxy.so*"):
            for match in glob.glob("/data/service/hnp/*/*/lib/{}".format(pattern)):
                libdir = os.path.dirname(match)
                if libdir not in dirs:
                    dirs.append(libdir)
        return dirs

    def build(self):
        envvars = self._pkg_config_env().vars(self)
        with envvars.apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise RuntimeError("test_gtkspell3 executable directory was not produced")
        exe = os.path.join(bindirs[0], "test_gtkspell3")
        if not os.path.isfile(exe):
            raise RuntimeError("test_gtkspell3 binary missing: {}".format(exe))

        # 运行时库存在性检查：基于依赖图解析的 LD_LIBRARY_PATH，
        # 而非外部 os.environ（外部 headless 环境不含 conan 缓存路径）。
        required = (
            "libgtkspell3-3.so.0",
            "libgtk-3.so.0",
            "libgdk-3.so.0",
            "libpango-1.0.so.0",
            "libenchant-2.so.2",
        )
        missing = []
        lib_dirs = self._resolved_lib_dirs()
        for lib in required:
            if not any(os.path.isfile(os.path.join(d, lib)) for d in lib_dirs if d):
                missing.append(lib)
        if missing:
            # 库缺失属环境限制：如实失败而非静默通过，避免断言"未执行却报 PASS"
            raise RuntimeError(
                "GTK runtime libs missing from dependency graph, cannot run "
                "test_gtkspell3 (4 assertions would not execute): {}".format(missing))

        envvars = self._pkg_config_env().vars(self)
        with envvars.apply():
            self.run(exe, env="conanrun")
