import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class GtkvncTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # test_package 是独立 recipe 上下文。测试二进制链接 gvnc/gtk-vnc 及其
        # 传递依赖（gnutls/nettle/gmp 等），运行时需完整 LD_LIBRARY_PATH：
        # ① 全部 host 依赖的 libdir（conanrun env 可能因包可见性缺失个别
        #    libdir，这里显式收集保证完整）；
        # ② SDK 的 libc++_shared.so 目录（libharfbuzz 等 C++ 依赖需要）。
        libdirs = []
        for dep in self.dependencies.host.values():
            for ld in dep.cpp_info.libdirs:
                if not os.path.isabs(ld):
                    ld = os.path.join(dep.package_folder, ld)
                if os.path.isdir(ld) and ld not in libdirs:
                    libdirs.append(ld)
        for ld in self.cpp_info.libdirs:
            if not os.path.isabs(ld):
                ld = os.path.join(self.package_folder, ld)
            if os.path.isdir(ld) and ld not in libdirs:
                libdirs.append(ld)
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc and os.path.sep in cc:
            # 解析符号链接拿到真实 LLVM bin 目录（/data/service/hnp/bin/clang →
            # ohos-sdk.org/.../llvm/bin/clang），SDK C++ 运行时库位于
            # <llvm>/lib/aarch64-linux-ohos[/c++]/libc++_shared.so
            real_cc = os.path.realpath(cc)
            llvm_bin = os.path.dirname(real_cc)
            for rel in ("../lib/aarch64-linux-ohos/c++", "../lib/aarch64-linux-ohos"):
                sdk_cxx = os.path.normpath(os.path.join(llvm_bin, rel))
                if os.path.isfile(os.path.join(sdk_cxx, "libc++_shared.so")) and sdk_cxx not in libdirs:
                    libdirs.append(sdk_cxx)

        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gtk-vnc")
        if not os.path.isfile(bin_path):
            raise Exception(f"test binary not found: {bin_path}")

        # Conan 2.x self.run() 不接受 dict env，用包装脚本注入 LD_LIBRARY_PATH
        # 后 exec 测试二进制（脚本自身无其他依赖，规避 loader 启动问题）。
        wrapper = os.path.join(self.build_folder, "run_test.sh")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as h:
            h.write("#!/bin/sh\n")
            h.write('export LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}"\n'.format(":".join(libdirs)))
            h.write("exec {} \"$@\"\n".format(shlex.quote(bin_path)))
        os.chmod(wrapper, 0o755)
        self.run(f"sh {shlex.quote(wrapper)}", env="conanrun")
