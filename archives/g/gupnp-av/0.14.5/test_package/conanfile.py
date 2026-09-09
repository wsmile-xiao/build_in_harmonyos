#!/usr/bin/env python3
"""Conan test_package for gupnp-av 0.14.5 — Conan L1 official test.

Builds test_gupnp_av.c with CMake (CMakeDeps + CMakeToolchain) and runs it.
The test exercises real gupnp-av APIs: DIDL-Lite writer namespace getters,
object title/upnp_class roundtrip, GUPnPProtocolInfo string roundtrip and
the SearchCriteriaParser expression signal — see test_gupnp_av.c.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GupnpAvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # 【CI 兼容】CMake try-compile 探测编译器 ABI 时拉起 lld，CI worker
        # 环境 lld 动态依赖的 libxml2.so.16 加载失败（E120 变体，主包 PR
        # #7999 build #37856 实证：meson 已过、挂在本 test 的
        # CMakeTestCCompiler）。把编译器改写为 wrapper（内含
        # LD_LIBRARY_PATH=<SDK llvm/lib> 前置），try-compile/编译/链接统一
        # 经 wrapper。
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or shutil.which("clang") or ""
        sdk = self._sdk_llvm_libdir()
        if cc and os.path.isfile(cc) and sdk:
            bindir = os.path.join(self.generators_folder, "clang-wrappers")
            os.makedirs(bindir, exist_ok=True)
            for suffix in ("", "++"):
                w = os.path.join(bindir, "clang" + suffix)
                with open(w, "w", encoding="utf-8") as f:
                    f.write(
                        "#!/data/service/hnp/bin/bash\n"
                        f'export LD_LIBRARY_PATH="{sdk}:$LD_LIBRARY_PATH"\n'
                        f'exec "{cc}{suffix}" "$@"\n')
                os.chmod(w, 0o755)
            self.conf.update("tools.build:compiler_executables",
                             {"c": os.path.join(bindir, "clang"),
                              "cpp": os.path.join(bindir, "clang++"),
                              **{k: v for k, v in compilers.items()
                                 if k not in ("c", "cpp")}})
            self.output.info("test_package: clang wrapped for CMake try-compile")

    @staticmethod
    def _sdk_llvm_libdir():
        import glob as _glob
        dirs = sorted(_glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"))
        for d in reversed(dirs):
            if os.path.isdir(d):
                return d
        return None

    def build(self):
        # 【CI 兼容 hard v2】generate() 里 conf.update 对 CMakeToolchain 无效
        # （CI #37861 实证：toolchain 文件里仍是裸 clang）。改为 build() 里
        # 直接改写 conan_toolchain.cmake——CMAKE_C/CXX_COMPILER 替换为
        # wrapper（内含 LD_LIBRARY_PATH=<SDK llvm/lib> 前置），文件级替换
        # 时机在 toolchain 生成后、cmake configure 前，必然生效。
        self._wrap_toolchain_compilers()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _wrap_toolchain_compilers(self):
        import glob as _glob
        sdk = None
        dirs = sorted(_glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"))
        for d in reversed(dirs):
            if os.path.isdir(d):
                sdk = d
                break
        if not sdk:
            return  # 非 OHOS 环境，无需处理
        tc_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(tc_file):
            return
        with open(tc_file, encoding="utf-8") as f:
            content = f.read()
        if "clang-wrappers" in content:
            return  # 已处理
        bindir = os.path.join(self.generators_folder, "clang-wrappers")
        os.makedirs(bindir, exist_ok=True)
        for suffix in ("", "++"):
            w = os.path.join(bindir, "clang" + suffix)
            with open(w, "w", encoding="utf-8") as f:
                f.write(
                    "#!/data/service/hnp/bin/bash\n"
                    f'export LD_LIBRARY_PATH="{sdk}:$LD_LIBRARY_PATH"\n'
                    f'exec "/data/service/hnp/bin/clang{suffix}" "$@"\n')
            os.chmod(w, 0o755)
        changed = False
        for var, wrapper in (("CMAKE_C_COMPILER", os.path.join(bindir, "clang")),
                             ("CMAKE_CXX_COMPILER", os.path.join(bindir, "clang++"))):
            new_content = re.sub(
                rf'(set\(\s*{var}\s+)"[^"]*"',
                rf'\1"{wrapper}"', content)
            if new_content != content:
                content = new_content
                changed = True
        if changed:
            with open(tc_file, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("test_package: conan_toolchain.cmake compilers -> wrappers")

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} -c './test_gupnp_av'", env="conanrun")
