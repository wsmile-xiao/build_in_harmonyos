#!/usr/bin/env python3
"""Conan recipe — libuvc 0.0.7 (CMake).

libuvc: a cross-platform library for USB Video Class devices, built on top of
libusb-1.0. Source: https://github.com/libuvc/libuvc (tag v0.0.7).
"""
import json
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rm, rmdir, save


class LibuvcConan(ConanFile):
    name = "libuvc"
    version = "0.0.7"
    description = "Cross-platform library for USB Video Class devices"
    license = "BSD-3-Clause"
    homepage = "https://github.com/libuvc/libuvc"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # libuvc 通过 libusb-1.0 访问 USB 设备，使用制品仓中的 libusb/1.0.27。
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        self._override_find_libusb()

    def _override_find_libusb(self):
        """改写 libuvc 自带的 cmake/FindLibUSB.cmake。

        上游 FindLibUSB.cmake 依赖 pkg-config 探测 libusb-1.0，而 headless
        OHOS 构建器上 pkg-config 不可靠。改为从 Conan 配方注入的
        LIBUSB_INCLUDE_DIR / LIBUSB_LIBRARIES 缓存变量直接构造
        LibUSB::LibUSB imported 目标，与 airspy/airspyhf 配方注入
        FindUSB1.cmake 的方式一致。
        """
        find_module = os.path.join(self.source_folder, "cmake", "FindLibUSB.cmake")
        content = """# FindLibUSB.cmake — Conan-friendly override for libuvc.
# 上游原版依赖 pkg-config 探测 libusb-1.0；OHOS 构建器上改由 Conan 配方
# 注入 LIBUSB_INCLUDE_DIR + LIBUSB_LIBRARIES 缓存变量，本模块据此构造
# LibUSB::LibUSB imported 目标，无需 pkg-config。
if(TARGET LibUSB::LibUSB)
  return()
endif()

if(NOT DEFINED LIBUSB_INCLUDE_DIR OR NOT LIBUSB_INCLUDE_DIR)
  message(FATAL_ERROR
    "LIBUSB_INCLUDE_DIR not set; inject it from the libusb Conan dependency")
endif()
if(NOT DEFINED LIBUSB_LIBRARIES OR NOT LIBUSB_LIBRARIES)
  message(FATAL_ERROR
    "LIBUSB_LIBRARIES not set; inject it from the libusb Conan dependency")
endif()

add_library(LibUSB::LibUSB UNKNOWN IMPORTED GLOBAL)
set_target_properties(LibUSB::LibUSB PROPERTIES
  INTERFACE_INCLUDE_DIRECTORIES "${LIBUSB_INCLUDE_DIR}"
  IMPORTED_LOCATION "${LIBUSB_LIBRARIES}")
set(LibUSB_FOUND TRUE)
set(LibUSB_INCLUDE_DIRS "${LIBUSB_INCLUDE_DIR}")
set(LibUSB_LIBRARIES "${LIBUSB_LIBRARIES}")
"""
        save(self, find_module, content)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake 不识别 HarmonyOS，libuvc 的 if(UNIX AND NOT APPLE)
        # pthread 探测依赖 UNIX 变量，将系统名别名为 Linux。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # libuvc 用 cmake_minimum_required(VERSION 3.1)，CMake 4.x 需要策略
        # 下限以解析 project() 调用。
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 只构建库本身：example 需摄像头、test 需 OpenCV+摄像头，均无法运行。
        tc.variables["BUILD_EXAMPLE"] = False
        tc.variables["BUILD_TEST"] = False
        # 按 shared 选项只构建单一目标，避免 shared+static 同名安装冲突。
        tc.variables["CMAKE_BUILD_TARGET"] = "Shared" if self.options.shared else "Static"
        # 注入 libusb 位置（来自 libusb/1.0.27 Conan 依赖）。
        libusb = self.dependencies["libusb"]
        usb_inc = os.path.join(libusb.package_folder, libusb.cpp_info.includedirs[0])
        tc.cache_variables["LIBUSB_INCLUDE_DIR"] = usb_inc
        usb_lib_name = "libusb-1.0.so" if self.options.shared else "libusb-1.0.a"
        usb_lib = os.path.join(libusb.package_folder, libusb.cpp_info.libdirs[0], usb_lib_name)
        tc.cache_variables["LIBUSB_LIBRARIES"] = usb_lib
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._emit_upstream_test_audit()

    def _emit_upstream_test_audit(self):
        """上游测试审计 + HMBS 机器证据标记。

        libuvc 0.0.7 没有任何可自动运行的测试框架：CMakeLists.txt 无
        enable_testing/add_test/ctest，无 gtest，无 make check 目标，无 tests/
        目录。按 hmbs 计数法（gtest TEST() / make check TOTAL / pytest def
        test_）= 0 个测试用例。

        唯一的 test-ish 文件 src/test.c 由 CMake 选项 BUILD_TEST（默认 OFF）
        控制：它 #include <opencv2/highgui/highgui_c.h>，构建需 OpenCV
        （opencv_core + opencv_highgui），运行需物理 UVC 摄像头 + GUI 显示
        （cvNamedWindow/cvShowImage/cvWaitKey）。它是 OpenCV 集成 demo，不是
        测试框架用例（无断言框架、无 ctest 注册）。src/example.c 是同类 demo。

        OHOS 制品仓无 OpenCV，headless 构建器无摄像头/显示。故 libuvc 在 OHOS
        上无任何可运行的自动化测试用例，按 hmbs "no_tests" 路径如实申报
        （MANIFEST upstream_tests_exist: false + 非空 upstream_test_audit
        已显式披露 test.c/example.c 的存在与不可运行原因）。
        """
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "audit: no test framework (no ctest/gtest/make-check); src/test.c is an OpenCV+camera demo",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "Audited libuvc 0.0.7: CMakeLists.txt has no enable_testing/add_test"
                "/ctest, no gtest, no make-check target, no tests/ dir. Counted 0 "
                "test-framework cases (gtest TEST()/make check TOTAL/pytest def test_). "
                "src/test.c (CMake BUILD_TEST, default OFF) and src/example.c are "
                "OpenCV+UVC-camera+display integration demos, not runnable test-"
                "framework cases; OpenCV is absent from the OHOS artifact repo and a "
                "physical camera/display is unavailable on the headless builder."
            ),
        }
        # 用 self.output.info 而非 print：Conan 2 默认 verbosity 下会抑制主配方
        # build() 中的 print() 输出，导致 HMBS 机器证据标记丢失。
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 移除上游安装的 CMake config（libuvcConfig.cmake / libuvcTargets.cmake，
        # 提供 LibUVC::UVCShared 等目标），避免与 Conan CMakeDeps 生成的配置
        # 冲突；消费者统一通过 cpp_info / cmake_file_name 解析 libuvc::libuvc。
        cmake_cfg = os.path.join(self.package_folder, "lib", "cmake")
        if os.path.isdir(cmake_cfg):
            rmdir(self, cmake_cfg)
        pkgconfig_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        if os.path.isdir(pkgconfig_dir):
            rm(self, "*.pc", pkgconfig_dir)
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        self._sign_elf()

    def _sign_elf(self):
        """HarmonyOS 要求 ELF 代码签名后才能被加载/执行（同 libusb / airspy）。"""
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
                signed = path + ".signed"
                result = subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
                    capture_output=True, text=True,
                )
                if result.returncode == 0 and os.path.isfile(signed):
                    os.replace(signed, path)
                    os.chmod(path, 0o755)

    def package_info(self):
        # libuvc 的共享目标名为 uvc（libuvc.so）/ 静态目标 OUTPUT_NAME 也为 uvc
        # （libuvc.a），按 shared 选项二选一构建。
        self.cpp_info.libs = ["uvc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libuvc")
        self.cpp_info.set_property("cmake_target_name", "libuvc::libuvc")
        self.cpp_info.set_property("pkg_config_name", "libuvc")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
