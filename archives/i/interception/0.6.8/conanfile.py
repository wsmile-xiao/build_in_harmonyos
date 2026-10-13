#!/usr/bin/env python3
"""Conan recipe — interception-tools 0.6.8 (CMake, application, OHOS PC).

interception-tools 是 Linux 输入设备拦截生态的核心:
  udevmon  — 监听 udev 事件的守护(核心,链 libevdev/libudev/yaml-cpp)
  intercept — 读 evdev 设备的捕获工具(链 libevdev)
  uinput   — 虚拟设备注入工具(链 libevdev/libudev/yaml-cpp)
  mux      — 多路复用器(需 Boost.Interprocess,**本配方裁剪**,见补丁说明)

依赖全部经 pkg-config 解析(上游本就走 pkg_check_modules 拿 libevdev;
补丁把 udev/yaml-cpp 也统一到 pkg_check_modules),由 conan 依赖图 +
PkgConfigDeps 供给。
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.layout import basic_layout


class InterceptionToolsConan(ConanFile):
    name = "interception"
    version = "0.6.8"
    description = "Small composable utility suite for input device interception on Linux (udevmon/intercept/uinput)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.com/interception/linux/tools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # libevdev:intercept/udevmon/uinput 共用;main 已发布 1.13.7
        self.requires("libevdev/1.13.7", transitive_headers=True, transitive_libs=True)
        # libudev:udevmon/uinput 运行与链接;eudev 配方声明 pkg_config_name=libudev
        # (package_type=application 会被 conan 默认丢 traits,必须显式声明)
        self.requires("eudev/3.2.14", headers=True, libs=True,
                      transitive_headers=True, transitive_libs=True)
        # yaml-cpp:udevmon/uinput 的配置解析
        self.requires("yaml-cpp/0.9.0", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"interception-tools requires a Linux-kernel input stack, not {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"],
            sha256=source_data.get("sha256", ""), strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def generate(self):
        self._ensure_tmpdir()
        # 上游 CMakeLists 用 pkg_check_modules(LIBEVDEV) 且补丁后 udev/yaml-cpp
        # 同走 pkg-config;PkgConfigDeps 为三个依赖生成 .pc
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        with open(os.path.join(self.source_folder, 'CMakeLists.txt'), encoding='utf-8') as stream:
            cmake_source = stream.read()
        if 'add_test(' in cmake_source or 'enable_testing(' in cmake_source:
            raise ConanException('Official upstream test inventory changed; full suite required')
        self.output.info('UPSTREAM_TEST_INVENTORY=0; OFFICIAL_SOURCE_NO_TEST_SUITE')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Exact official parser for a device-independent consumer. Its device
        # creation main is never invoked by that test.
        copy(self, "uinput.cpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "interception", "testable"))
        if self.settings.os == "OHOS":
            self._resign_installed_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    # ── Helper methods ──────────────────────────────────────────

    def _ensure_tmpdir(self):
        # HarmonyOS 的 /tmp 是只读 erofs(E002)— 指到可写目录
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resign_installed_elfs(self):
        """cmake install 原样复制 ELF 时签名仍有效,但保险起见按 libinput
        同法重签(llvm-objcopy 剥 .codesign + binary-sign-tool 自签)。"""
        objcopy = shutil.which("llvm-objcopy")
        signer = shutil.which("binary-sign-tool")
        for tool in (objcopy, signer):
            if not tool or not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        for root, _dirs, files in os.walk(self.package_folder):
            for name in sorted(files):
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                if not self._is_elf(path):
                    continue
                self.run(f'{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(path)}')
                self.run(f'{shlex.quote(signer)} sign -inFile {shlex.quote(path)} -outFile {shlex.quote(path)} -selfSign 1')
