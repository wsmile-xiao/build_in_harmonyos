#!/usr/bin/env python3
"""Conan recipe for the maintained MP4v2 2.1.3 release on OpenHarmony."""

import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, get


class Mp4v2Conan(ConanFile):
    name = "mp4v2"
    version = "2.1.3.1"
    package_type = "library"
    license = "MPL-1.1"
    homepage = "https://mp4v2.org/"
    description = "A C++ library for reading and writing MP4 files"

    exports_sources = "patches/*"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED"] = self.options.shared
        toolchain.variables["BUILD_UTILS"] = True
        # 上游 CMakeLists.txt 第一行的 cmake_minimum_required 低于 3.5，
        # 而设备 SDK 自带的是 CMake 4.x，已移除对 <3.5 的兼容：
        #   "Compatibility with CMake < 3.5 has been removed from CMake."
        # 不改上游文件，用官方给出的逃生开关放行。
        toolchain.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Mirror the 28 standardUsage.exp assertions from the upstream DejaGnu suite.
        if can_run(self):
            self.output.info("Running 28 upstream standardUsage.exp assertions")
            for tool in ("mp4art", "mp4file", "mp4subtitle", "mp4track"):
                self._test_standard_usage(os.path.join(self.build_folder, tool))
            self.output.info("Upstream standardUsage.exp assertions passed")
        else:
            self.output.info(
                "Skipping upstream standardUsage.exp assertions: target binaries cannot run on this build machine"
            )

    def _test_standard_usage(self, tool):
        environment = os.environ.copy()
        library_path = {
            "Macos": "DYLD_LIBRARY_PATH",
            "Windows": "PATH",
        }.get(str(self.settings.os), "LD_LIBRARY_PATH")
        environment[library_path] = self.build_folder + os.pathsep + environment.get(library_path, "")
        cases = (
            ((), 1, (r"^Usage: \S+", r"^Try.*-h.*--help")),
            (("-h",), 0, (r"^Usage: \S+", r"\s+--help", r"\s+--version")),
            (("--help",), 0, (r"^Usage: \S+", r"\s+--help", r"\s+--version", r"^VERBOSE LEVELS")),
            (("--version",), 0, (r"^\S+\s-\s\S+",)),
            (("--versionx",), 0, (r"^utility:\s+\S+", r"^product:\s+\S+", r"^version:\s+\S+")),
            (("-*",), 1, (r"^invalid",)),
            (("--bogusLongOption",), 1, (r"^unrecognized",)),
        )

        for arguments, expected_returncode, patterns in cases:
            completed = subprocess.run(
                [tool, *arguments],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
                env=environment,
            )
            if completed.returncode != expected_returncode:
                raise ConanException(
                    "{} {} returned {}, expected {}".format(
                        os.path.basename(tool), " ".join(arguments),
                        completed.returncode, expected_returncode,
                    )
                )
            for pattern in patterns:
                if not re.search(pattern, completed.stdout, re.MULTILINE):
                    raise ConanException(
                        "{} {} did not match {}".format(
                            os.path.basename(tool), " ".join(arguments), pattern
                        )
                    )

    def package(self):
        cmake = CMake(self)
        cmake.install()

        self._set_soname_and_resign(['libmp4v2.so'])

    def _set_soname_and_resign(self, sonames):
        """给缺 SONAME 的 .so 补上 SONAME 并**重新签名**。

        为何需要：本包产物无 DT_SONAME。后果不在本包，而在**下游** ——
        CMake 默认按完整路径链接无 SONAME 的库，于是把构建机的 conan cache
        绝对路径写进下游的 DT_NEEDED，换机器即无法加载。
        制品仓已实测到三个因此损坏的包（fontconfig / poppler / tbb）。

        为何用 patchelf 而不改构建系统：本包的 .so 本来就是**无版本名**
        （libfoo.so，没有 libfoo.so.X 实体），SONAME 设成文件名本身即完全正确，
        与上游本意一致；换构建方式的收益一样而风险更高。
        （若包里存在版本化实体文件，则说明上游有 SOVERSION 意图，
          那种情况应改构建方式而非 patchelf —— 见 skill 的 references/soname-repair.md）

        为何必须重签：改动 ELF 会破坏链接器自签，鸿蒙 PC 的 XPM 会拒绝 dlopen
        （报 Permission denied / Operation not permitted）。
        顺序必须是 patchelf → 剥旧签名段 → 自签。
        """
        import os
        patchelf = "/data/service/hnp/bin/patchelf"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for name in sonames:
            f = os.path.join(self.package_folder, "lib", name)
            if not os.path.isfile(f) or os.path.islink(f):
                self.output.warning("补 SONAME：找不到 %s，跳过" % f)
                continue
            self.run('{pe} --set-soname "{n}" "{f}"'.format(pe=patchelf, n=name, f=f))
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=f))
            self.output.info("已设 SONAME=%s 并重签" % name)

    def package_info(self):
        self.cpp_info.libs = ["mp4v2"]
        self.cpp_info.bindirs = ["bin"]
