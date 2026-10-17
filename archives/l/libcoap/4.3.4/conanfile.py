#!/usr/bin/env python3
"""Conan recipe for libcoap 4.3.4 (CMake)."""

import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibcoapConan(ConanFile):
    name = "libcoap"
    version = "4.3.4"
    description = "Implementation of CoAP, a lightweight REST-based transfer protocol"
    license = "BSD-2-Clause"
    homepage = "https://github.com/obgm/libcoap"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("cunit/2.1.3")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        # 上游测试 (tests/testdriver.c, CUnit) 由 ENABLE_TESTS 打开；
        # testdriver 裸链 -lcunit，无 find_package，需要显式注入 cunit 包的 include/lib 目录
        tc.cache_variables["ENABLE_TESTS"] = True
        tc.cache_variables["ENABLE_EXAMPLES"] = False
        tc.cache_variables["ENABLE_DOCS"] = False
        # DTLS 默认 ON 且会 find_package(OpenSSL) 摸到设备系统路径，
        # 产生不可传递的隐性系统依赖（消费者链接 undefined symbol），显式关闭
        tc.cache_variables["ENABLE_DTLS"] = False
        cunit = self.dependencies["cunit"]
        incdirs = [
            d if os.path.isabs(d) else os.path.join(cunit.package_folder, d)
            for d in cunit.cpp_info.includedirs
        ]
        libdirs = [
            d if os.path.isabs(d) else os.path.join(cunit.package_folder, d)
            for d in cunit.cpp_info.libdirs
        ]
        tc.cache_variables["CMAKE_C_FLAGS"] = " ".join(f"-I{d}" for d in incdirs)
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = " ".join(f"-L{d}" for d in libdirs)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # 上游测试：tests/testdriver.c 汇总注册全部 CUnit 套件（无 add_test/ctest 注册），
        # 必须真实执行并以 CUnit 汇总的 Failed 数判定，不用退出码（CUnit 失败不影响退出码）
        testdriver = None
        for root, _dirs, files in os.walk(self.build_folder):
            if "testdriver" in files:
                testdriver = os.path.join(root, "testdriver")
                break
        if not testdriver:
            raise ConanException("ENABLE_TESTS=ON 但未找到 testdriver 可执行文件")
        run = subprocess.run([testdriver], capture_output=True, text=True)
        self.output.info(run.stdout)
        if run.stderr:
            self.output.warning(run.stderr)
        m = re.search(r"^\s*tests\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", run.stdout, re.M)
        if not m:
            raise ConanException(f"testdriver 未输出 CUnit Run Summary (rc={run.returncode})")
        total, ran, passed, failed = (int(g) for g in m.groups())
        if run.returncode != 0 or failed > 0 or ran != total:
            raise ConanException(
                f"上游 CUnit 测试失败: total={total} ran={ran} passed={passed} failed={failed}"
            )
        self.output.info(f"上游 CUnit 测试: {passed}/{total} 通过")

    def package(self):
        src_inc = os.path.join(self.source_folder, "include", "coap3")
        pkg_inc = os.path.join(self.package_folder, "include", "coap3")
        copy(self, "*.h", src=src_inc, dst=pkg_inc)
        # configure_file 生成的公共头（coap.h 与 coap_config.h）
        copy(
            self,
            "coap_config.h",
            src=self.build_folder,
            dst=pkg_inc,
            keep_path=False,
        )
        gen_inc = os.path.join(self.build_folder, "include", "coap3")
        if os.path.isdir(gen_inc):
            copy(self, "*.h", src=gen_inc, dst=pkg_inc)
        for root, _dirs, files in os.walk(self.build_folder):
            for name in files:
                if re.match(r"^libcoap.*\.(a|so(\.[0-9]+)*)$", name):
                    copy(self, name, src=root, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["coap-3"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
