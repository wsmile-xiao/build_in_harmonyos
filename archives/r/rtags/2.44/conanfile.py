#!/usr/bin/env python3
"""Conan recipe — rtags 2.44 (cmake, 鸿蒙 PC 真机原生编译).

rtags 是基于 libclang 的 C/C++ 代码索引器（CLI: rdm/rc/rp）。
- 依赖制品仓 clang/22.1.8（提供 libclang.so + llvm-config + clang 头）。
- 上游 GitHub 官方 tarball 不含 src/rct 子模块，conandata.yml 双官方源补齐
  （rct pinned commit 9121fb0a，Andersbakken/rct）。
- FindLibClang.cmake 经 LIBCLANG_ROOT_DIR / LIBCLANG_LLVM_CONFIG_EXECUTABLE
  显式定位 conan clang 包，不依赖系统路径。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class RtagsConan(ConanFile):
    name = "rtags"
    version = "2.44"
    description = "rtags — 基于 libclang 的 C/C++/Objective-C 代码索引器（rdm 守护进程 + rc 命令行客户端）"
    license = "GPL-3.0-only"
    homepage = "https://github.com/Andersbakken/rtags"
    url = "https://github.com/Andersbakken/rtags"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 提供 libclang.so（动态库）、llvm-config、clang 头与资源目录
        self.requires("clang/22.1.8")

    def layout(self):
        # 源码 CMakeLists 在顶层；build 目录用 build-ohos 与 clang/llvm 配方先例一致
        self.folders.source = "."
        self.folders.build = "build-ohos"

    def source(self):
        get(self, **self.conan_data["sources"][0], filename="rtags-2.44.tar.gz", strip_root=True)      # rtags v2.44
        get(self, **self.conan_data["sources"][1], filename="rct-9121fb0.tar.gz", strip_root=True)     # rct → src/rct

    def _clang_pkg_root(self):
        return self.dependencies["clang"].package_folder

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        bdir = self.build_folder
        clang_root = self._clang_pkg_root()
        cc = "/data/service/hnp/bin/clang"
        cxx = "/data/service/hnp/bin/clang++"
        llvm_config = os.path.join(clang_root, "bin", "llvm-config")
        # 上游 CMakeLists 直接 "${CMAKE_MODULE_PATH}/Uninstall.cmake.in" 拼路径 →
        # CMAKE_MODULE_PATH 必须是单目录（= src/cmake）；把 Platform/HarmonyOS.cmake 拷进去。
        _pm = os.path.join(src, "cmake")
        os.makedirs(os.path.join(_pm, "Platform"), exist_ok=True)
        with open(os.path.join(_pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as _f:
            _f.write("include(Platform/Linux)\n")
        defs = " ".join([
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(_pm),
            '-DCMAKE_C_COMPILER="{}"'.format(cc),
            '-DCMAKE_CXX_COMPILER="{}"'.format(cxx),
            "-DCMAKE_BUILD_TYPE=Release",
            # —— 定位 conan clang 包的 libclang（cmake/FindLibClang.cmake 消费）——
            '-DLIBCLANG_ROOT_DIR="{}"'.format(clang_root),
            '-DLIBCLANG_LLVM_CONFIG_EXECUTABLE="{}"'.format(llvm_config),
            # —— 关闭非必需组件 ——
            "-DWITH_TESTS=OFF",
            "-DWITH_MANUAL_TESTS=OFF",
            "-DSKIP_CTEST=ON",                     # install(CODE ctest) 在 CI 无法运行
            "-DRTAGS_NO_CORES=OFF",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, defs))
        self.run('cmake --build "{}"'.format(bdir))
        # smoke：llvm-config 可执行且版本匹配
        out = subprocess.run([llvm_config, "--version"], capture_output=True, text=True)
        if out.returncode != 0 or not out.stdout.strip().startswith("22"):
            raise ConanException("llvm-config from clang/22.1.8 unusable: rc=%s out=%r" % (out.returncode, out.stdout))

    def package(self):
        bdir = self.build_folder
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # OHOS XPM：被 exec 的可执行文件必须代码签名，否则 Permission denied（对齐 clang 配方先例）。
        bindir = os.path.join(self.package_folder, "bin")
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isdir(bindir) and os.path.exists(signer)):
            self.output.warn("binary-sign-tool 不可用，跳过签名")
            return
        for name in sorted(os.listdir(bindir)):
            p = os.path.join(bindir, name)
            if not (os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p)):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=p))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=p))

    def package_info(self):
        # CLI 工具（rdm/rc/rp），无库导出；工具命令声明见软件级 commands.json（R38）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
