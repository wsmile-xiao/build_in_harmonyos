#!/usr/bin/env python3
"""Conan test_package for juce/8.0.5 — OHOS 消费式验证（find_package(JUCE)）。

消费方视角走完整官方路径：CMakeToolchain（强制 CMAKE_SYSTEM_NAME=Linux，
E092 先例）+ PkgConfigDeps 生成依赖 .pc（E468：PKG_CONFIG_PATH 注入
conanbuild，供 find_package(JUCE) 后 juce_add_module 的 linuxPackages
pkg_check_modules 解析），juce 包前缀经工具链变量传给 CMake 解析包内原始
JUCEConfig.cmake。

E505：字体链（freetype/fontconfig/libxml2）为共享依赖，OHOS musl 加载器
无法经版本化符号链接别名解析 .so，且用户存储上的 .so 必须经 binary-sign-tool
自签名才允许 dlopen（否则 EACCES）——generate() 把三者实体化为本构建目录下
conan-runtime-views/（真实文件，每个别名名一份）并逐个自签名，向测试可执行
文件注入 DT_RPATH（--disable-new-dtags）；test() 运行时 unset LD_LIBRARY_PATH，
避免其压过 DT_RPATH。
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps

TEST_CHECKS = 13
_FONT_CHAIN_PACKAGES = ("freetype", "fontconfig", "libxml2")


def sign_elf(path):
    """OHOS ELF 自签名（binary-sign-tool selfSign）；签名产物固定 640，
    需恢复执行位（经验仓 mlton-20241230 / alsa-lib / bam 先例）。"""
    signer = (shutil.which("binary-sign-tool")
              or "/storage/Users/currentUser/usr/local/bin/binary-sign-tool")
    objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
    clean, signed = path + ".clean", path + ".signed"
    subprocess.run([objcopy, "--remove-section", ".codesign", path, clean],
                   check=True)
    subprocess.run([signer, "sign", "-inFile", clean, "-outFile", signed,
                    "-selfSign", "1"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.chmod(signed, 0o750)
    os.replace(signed, path)
    if os.path.exists(clean):
        os.remove(clean)


class JuceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)
        # xorgproto 真实 .pc 目录（X11 协议头，libx11 包不含；消费者编译
        # juce_gui_basics 源时 linuxPackages 的 xproto 由此解析）。
        try:
            _xp_pc = os.path.join(
                self.dependencies["xorgproto"].package_folder,
                "share", "pkgconfig")
            if os.path.isdir(_xp_pc):
                self.buildenv_info.append_path("PKG_CONFIG_PATH", _xp_pc)
        except KeyError:
            pass
        # E505 实体化视图 + 逐文件自签名 + 测试可执行 DT_RPATH。
        view = os.path.join(self.build_folder, "conan-runtime-views")
        os.makedirs(view, exist_ok=True)
        for name in _FONT_CHAIN_PACKAGES:
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isdir(libdir):
                    continue
                for fn in os.listdir(libdir):
                    if ".so" not in fn:
                        continue
                    src = os.path.join(libdir, fn)
                    if not os.path.isfile(src):
                        continue
                    dst = os.path.join(view, fn)
                    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                        fdst.write(fsrc.read())
                    sign_elf(dst)
        tc = CMakeToolchain(self)
        # E092（ableton-link 先例）：强制上游 Linux 平台分支。
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["JUCE_PACKAGE_DIR"] = self.dependencies["juce"].package_folder
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = \
            "-Wl,--disable-new-dtags -Wl,-rpath,{}".format(view)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        result = {
            "executed": True,
            "passed": False,
            "command": "ctest --output-on-failure -R test_juce_app",
            "discovered": TEST_CHECKS,
            "passedCount": 0,
        }
        # OHOS: /system/bin/sh (mksh) 不能直接 exec ELF，用 buildenv 的 bash 包装；
        # 同时 unset LD_LIBRARY_PATH（E505：避免压过二进制内嵌 DT_RPATH）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        try:
            self.run(f'{bash} -c "unset LD_LIBRARY_PATH; '
                     f'ctest --output-on-failure -R test_juce_app"',
                     env="conanrun")
        except Exception as exc:
            self.output.info("juce test_package failed: {}".format(exc))
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
            raise
        result["passed"] = True
        result["passedCount"] = TEST_CHECKS
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
