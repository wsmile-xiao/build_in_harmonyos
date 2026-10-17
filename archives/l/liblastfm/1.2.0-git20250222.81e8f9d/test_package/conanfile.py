#!/usr/bin/env python3
"""Conan test_package for liblastfm 1.2.0-git20250222.81e8f9d.

链路级验证（R34: 实质调用被测包 API）：
  - find_package(lastfm5)：消费上游 install(EXPORT) 的 lastfm5Config.cmake
  - 构建调用 UrlBuilder::encode() / Track setter+getter / ws::scheme() /
    Audioscrobbler 的测试可执行文件（无网络 I/O——Scrobble 提交流程
    本身需 Last.fm 服务端与 API key，不属包可用性验证范畴）
  - OHOS 运行：依赖库拷贝到 bindir + XPM 自签（libical 4.0.1 同款）
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LiblastfmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = os.path.join(
            self.dependencies["qt5-qtbase"].package_folder, "bin", "moc"
        )
        tc.generate()
        self._write_cmake_paths()

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            package_folder = dep.package_folder.replace("\\", "/")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")',
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")',
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        with open(
            os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w", encoding="utf-8"
        ) as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._prepare_runtime_links()
        if self.settings.os == "OHOS":
            self._sign_runtime_elfs()
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(test_home, exist_ok=True)
        env.define("HOME", test_home)
        runtime_var = "LD_LIBRARY_PATH"
        # bindirs[0] 在 test() 阶段解析不可靠（DIAG 实测缺失）——用
        # build_folder 绝对路径（_prepare_runtime_links 拷贝目标）
        env.prepend_path(runtime_var, self.build_folder)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(runtime_var, os.path.join(dep.package_folder, "lib"))
        # SDK libc++_shared.so（qt5 系运行时依赖）
        sdk_libcxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++"
        if os.path.isdir(sdk_libcxx):
            env.prepend_path(runtime_var, sdk_libcxx)
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_liblastfm"))

    def _prepare_runtime_links(self):
        """把依赖库拷到测试 bindir（相对 NEEDED 解析兜底）."""
        runtime_dir = self.cpp.build.bindirs[0]
        os.makedirs(runtime_dir, exist_ok=True)
        for dep in self.dependencies.values():
            package_folder = dep.package_folder
            if not package_folder:
                continue
            for libdir in (
                os.path.join(package_folder, "lib"),
                os.path.join(package_folder, "bin"),
            ):
                if os.path.isdir(libdir):
                    for src in glob.glob(os.path.join(libdir, "lib*.so*")):
                        dst = os.path.join(runtime_dir, os.path.basename(src))
                        if os.path.exists(dst):
                            continue
                        shutil.copy2(src, dst)

    def _sign_runtime_elfs(self):
        """OHOS XPM: 测试可执行与拷贝的依赖库需自签（libical 同款）."""
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            raise ConanInvalidConfiguration(
                "OHOS llvm-objcopy and binary-sign-tool are required for ELF signing"
            )
        runtime_dir = self.cpp.build.bindirs[0]
        paths = {os.path.join(runtime_dir, "test_liblastfm")}
        for name in glob.glob(os.path.join(runtime_dir, "lib*.so*")):
            paths.add(name)
        for path in sorted(paths):
            if os.path.islink(path) or not os.path.isfile(path) or not self._is_elf(path):
                continue
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true'
            )
            self.run(
                f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1'
            )

    @staticmethod
    def _is_elf(path):
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"
