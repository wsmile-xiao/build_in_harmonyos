#!/usr/bin/env python3
"""Conan recipe — schroot 1.6.13 (CMake, OHOS aarch64)."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class SchrootConan(ConanFile):
    name = "schroot"
    version = "1.6.13"
    description = "Execute commands in a chroot environment"
    license = "GPL-3.0-or-later"
    homepage = "https://codeberg.org/shelter/reschroot"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "with_upstream_tests": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "schroot requires POSIX chroot/mount interfaces"
            )

    def requirements(self):
        # sbuild 的公共头文件会引入 boost，包内 libsbuild.a 也链接 boost/libuuid/
        # gettext 的实现，因此这些依赖需要向消费者转发；否则消费者依赖图中它们的
        # 二进制会被跳过，头文件与库都取不到（消费者用例实测）。
        self.requires("boost/1.84.0", transitive_headers=True, transitive_libs=True)
        self.requires("linux-pam/1.7.2")
        self.requires("libuuid/2.40.4", transitive_libs=True)
        # OHOS 的 libc 不带 gettext（sysroot 的 libintl.h 是空壳、无 libintl），
        # 而 PAM 会话要按提示串匹配，必须用真实的 libintl 提供 dgettext()。
        self.requires("gettext/0.22.5.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        if self.options.with_upstream_tests:
            self.test_requires("cppunit/1.15.1")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _abs_dirs(self, name, attr):
        """依赖包在某属性上的绝对路径（跨平台，不依赖 conan 版本细节）。"""
        dep = self.dependencies[name]
        dirs = []
        for path in getattr(dep.cpp_info.aggregated_components(), attr):
            dirs.append(path if os.path.isabs(path) else os.path.join(dep.package_folder, path))
        return dirs

    def _dep_dirs(self):
        """依赖的头文件/库目录。

        上游 CMake 只对 Boost 走 find_package，PAM/uuid/cppunit 是按库名直接
        链接的，因此统一经 CPATH/LIBRARY_PATH 注入，避免依赖上游的探测结果。
        """
        includes, libs = [], []
        names = ["boost", "libuuid", "linux-pam", "gettext"]
        if self.options.with_upstream_tests:
            names.append("cppunit")
        for name in names:
            includes += self._abs_dirs(name, "includedirs")
            libs += self._abs_dirs(name, "libdirs")
        return includes, libs

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            # CMake 没有 HarmonyOS 平台模块，用 linux 平台模块构建（OHOS 的
            # clang/musl 工具链与 Linux 目标 ABI 兼容），否则 CMake 报
            # "System is unknown to cmake, create: Platform/HarmonyOS"。
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # schroot 1.6.13 声明 cmake_minimum_required(2.8.12)，CMake 4 拒绝兼容
        # 3.5 以下的工程；给策略下限放行，其余检查逻辑保持上游原样。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Boost 由 conan 提供；FindBoost 模块只认系统路径，改走 BoostConfig。
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "ON"
        tc.cache_variables["BOOST_ROOT"] = self.dependencies["boost"].package_folder
        # 探针结果直接给定：交叉编译下 check_library_exists 的试链接不可靠，
        # 头文件与库的实际路径由 _dep_dirs() 经 CPATH/LIBRARY_PATH 注入。
        tc.cache_variables["UUID_HEADER"] = "1"
        tc.cache_variables["UUID_FUNC"] = "1"
        tc.cache_variables["uuid"] = "ON"
        tc.cache_variables["PAM_HEADER"] = "1"
        tc.cache_variables["PAM_FUNC"] = "1"
        tc.cache_variables["pam"] = "ON"
        if self.options.with_upstream_tests:
            tc.cache_variables["CPPUNIT_CLASS"] = "1"
            tc.cache_variables["test"] = "ON"
        else:
            tc.cache_variables["CPPUNIT_CLASS"] = "0"
            tc.cache_variables["test"] = "OFF"
        # 稳定化取舍：personality 特性在 OHOS 上未做运行时验证——构建日志显示
        # sys/personality.h 与 personality() 探测均为 found（不是"缺头"），但相关
        # syscall 在沙箱/运行时受限风险高，故显式关闭；快照/回环特性依赖 Linux
        # 专有工具（lvcreate/zfs/btrfs/losetup），构建机上不存在即由上游探测自动
        # 关闭，这里同样显式关闭以保证产物稳定。
        tc.cache_variables["personality"] = "OFF"
        tc.cache_variables["lvm-snapshot"] = "OFF"
        tc.cache_variables["zfs-snapshot"] = "OFF"
        tc.cache_variables["btrfs-snapshot"] = "OFF"
        tc.cache_variables["loopback"] = "OFF"
        tc.cache_variables["nls"] = "OFF"
        tc.cache_variables["doxygen"] = "OFF"
        # OHOS 的 libc 头未声明 pthread_setcancelstate()，Boost 的
        # sp_thread_sleep.hpp 会因此编译失败；该宏让 Boost 走 nanosleep 分支。
        tc.preprocessor_definitions["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"] = "1"
        # OHOS 的 libc++ 不提供 <tr1/memory>，上游 cmake/CompilerChecks.cmake
        # 的 tr1 探测因此失败，落到 "A shared_ptr implementation is not
        # available"。改用 boost 版 shared_ptr（boost 已是依赖），等价于
        # 上游头文件自带的 HAVE_BOOST_SHARED_PTR_HPP 分支。
        tc.preprocessor_definitions["HAVE_BOOST_SHARED_PTR_HPP"] = "1"
        # 依赖的头/库目录统一经工具链旗标注入。上游只对 Boost 走 find_package，
        # 且链接用的是 ${Boost_<COMPONENT>_LIBRARY_RELEASE} 这类旧式变量，而
        # CMake 4 起已经没有 FindBoost 模块（BoostConfig 只提供 imported target），
        # 所以这里显式给出组件库文件路径，并给所有依赖补 -I/-L。
        dep_includes, dep_libs = self._dep_dirs()
        include_flags = ["-I" + d for d in dep_includes]
        # gettext 由 conan 包提供（OHOS 的 libc 既无 libintl 也无对应函数），
        # 上游 CMake 只是在 glibc 上假定它在 libc 里、从不链接 intl；libsbuild
        # 与各前端都调用 dgettext()/bindtextdomain()，显式补 intl。
        link_flags = ["-L" + d for d in dep_libs] + ["-lintl"]
        # 测试可执行文件要在构建树里直接运行，必须能找到共享依赖（libintl 等）。
        # 依赖是以 -L/-l 原始旗标接入的，CMake 无法据此推导 RPATH，须显式给出。
        tc.cache_variables["CMAKE_BUILD_RPATH"] = ";".join(dep_libs)
        # cmake 在 install 阶段会把与构建期不同的 RPATH 重链进二进制，而重链产物
        # 在 HarmonyOS 的文件安全策略下无法执行（execve 返回 EPERM）。让安装期
        # RPATH 与构建期一致，cmake 即跳过重链，安装产物保持为构建产物的拷贝。
        tc.cache_variables["CMAKE_INSTALL_RPATH"] = ";".join(dep_libs)
        # conan 工具链把 CMAKE_INSTALL_LIBEXECDIR 设为 bin，使 helper 程序的安装
        # 目录变成 <prefix>/bin/schroot，与同名可执行文件冲突（install 阶段报
        # "destination ... is not a directory"）。上游该路径是 CACHE 变量，显式
        # 覆盖可保留上游预期的 helper 布局（libexec/schroot）。
        tc.cache_variables["SCHROOT_LIBEXEC_DIR"] = os.path.join(
            self.package_folder, "libexec", "schroot"
        )
        tc.extra_cflags = include_flags
        tc.extra_cxxflags = include_flags
        tc.extra_exelinkflags = link_flags
        tc.extra_sharedlinkflags = link_flags
        boost_libdir = self._abs_dirs("boost", "libdirs")[0]
        for component in ("filesystem", "iostreams", "program_options", "system", "regex"):
            for suffix in (".a", ".so"):
                candidate = os.path.join(boost_libdir, "libboost_" + component + suffix)
                if os.path.exists(candidate):
                    cache_var = "Boost_" + component.upper() + "_LIBRARY_RELEASE"
                    tc.cache_variables[cache_var] = candidate
                    break
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        _, libs = self._dep_dirs()
        env = Environment()
        # 构建机上运行测试可执行文件时要能找到共享依赖（libintl/libpam/libuuid）；
        # 头文件与链接目录已由 generate() 经工具链旗标注入，不依赖环境变量。
        env.append("LD_LIBRARY_PATH", os.pathsep.join(libs))
        cmake = CMake(self)
        with env.vars(self).apply():
            cmake.configure()
            cmake.build()
            if self.options.with_upstream_tests:
                # sbuild-chroot-config 的 testdata 必须是 root 属主：
                # sbuild/sbuild-chroot-config.cc 的 load_data() 显式拒绝非 root 属主
                # 的配置文件（安全设计，非缺陷）。构建沙箱以普通用户运行，且本机
                # FUSE 挂载下 chown 无效，无法伪造 root 属主，该套件在非特权环境下
                # 无法执行；其余 7 个套件照常运行（详见 notes.md）。
                # 上游的 test 目标直接调 ctest、不接受额外参数，故这里自行调用
                # ctest（工作目录即构建目录，Testing/ 与 testdata 布局不变）。
                self.run(
                    "ctest --output-on-failure -E sbuild-chroot-config",
                    cwd=self.build_folder,
                )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游的 install 不包含 configure 生成的 sbuild-config.h，但已安装的公共
        # 头文件（sbuild-i18n.h 等）会引用它，缺失会让消费者无法编译；从构建树
        # 取出该生成头一并装入包内。
        for root, _, files in os.walk(self.build_folder):
            if "sbuild-config.h" in files:
                copy(
                    self,
                    "sbuild-config.h",
                    src=root,
                    dst=os.path.join(self.package_folder, "include", "sbuild"),
                )
                break
        # cmake 的 install 步骤会重写可执行文件；本机实测该产物无法执行
        # （execve 返回 EPERM），而链接器直接产出的构建树副本可以执行。用构建树
        # 产物覆盖安装副本，保证包内二进制在 HarmonyOS 上可用。
        for name in ("schroot", "schroot-listmounts", "schroot-mount"):
            built = os.path.join(self.build_folder, "bin", name, name)
            if not os.path.isfile(built):
                continue
            for subdir in ("bin", os.path.join("libexec", "schroot")):
                installed = os.path.join(self.package_folder, subdir, name)
                if os.path.isfile(installed):
                    shutil.copyfile(built, installed)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["sbuild"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
