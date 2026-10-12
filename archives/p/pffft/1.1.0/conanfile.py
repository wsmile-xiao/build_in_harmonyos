#!/usr/bin/env python3
"""Conan recipe — pffft 1.1.0 (marton78 PFFFT: pretty fast FFT, SIMD-optimized).

上游 https://github.com/marton78/pffft tag v1.1.0。CMake 工程，核心目标 PFFFT
（src/pffft.c + src/pffft_common.c [float] + src/pffft_double.c [double]），
零第三方依赖（W0 天然通过：FFTPACK 对照实现为树内 src/fftpack.c，bench 对照
子模块 greenffts/kissfft/pocketfft 为可选项且 tarball 不含、本配方显式关闭）。

形态：
- 双精度 API 同库：float (pffft_*) + double (pffftd_*)，产物 libpffft.a +
  include/pffft/{pffft.h, pffft.hpp, pffft_double.h}
- SIMD：aarch64 走 NEON 路径。关键点：PFFFT_ENABLE_NEON 宏不经上游任何默认
  CMake 选项激活（README 提及的 PFFFT_USE_SIMD_NEON 选项在 v1.1.0 中不存在；
  target_optimizations.cmake 仅在 TARGET_C_EXTRA=neon_* 分支注入，而 neon_*
  extra 值仅 arm32 环境提供，非 Apple aarch64 的 GCC_EXTRA_VALUES 为空）——
  本配方经 CMAKE_C_FLAGS 注入 -DPFFFT_ENABLE_NEON=1。aarch64 NEON 为基线
  指令集，无需 -march：TARGET_C_ARCH 保持上游默认 none，与 OHOS 交叉工具链
  零 -march 冲突（派工留意点实测不触发）。
- 上游测试：PFFFT_BUILD_TESTS/BENCHMARKS=ON（上游顶层默认形态），ctest 注册
  9 项在 build() 内执行；测试二进制经 binary-sign-tool 自签后在 OHOS 设备
  运行（bitarray 0.0-git.f444eb4 先例）。
"""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get


class PffftConan(ConanFile):
    name = "pffft"
    version = "1.1.0"
    description = (
        "PFFFT: a pretty fast FFT and fast convolution library "
        "(1D single/double precision real & complex FFT with SSE/AVX/NEON SIMD)"
    )
    license = "BSD-3-Clause"  # BSD-like (UCAR/Pommier/mborgerding), see LICENSE.txt
    homepage = "https://github.com/marton78/pffft"
    url = "https://github.com/marton78/pffft"
    topics = ("fft", "simd", "neon", "dsp", "signal-processing")
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        pass  # W0: 零第三方依赖

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (no Platform/HarmonyOS module
        # in CMake). OHOS is POSIX: force the Linux platform (chain-wide
        # convention; abcmidi/adios2/kpeople5 precedent).
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # NEON activation (aarch64): PFFFT_ENABLE_NEON is not set by any default
        # upstream CMake option (see class docstring / notes.md). NEON is a
        # baseline instruction set on aarch64, so no -march is needed.
        arch = str(self.settings.arch)
        if arch.startswith("armv8") or arch in ("arm64", "aarch64"):
            tc.variables["CMAKE_C_FLAGS"] = "-DPFFFT_ENABLE_NEON=1"
        # HMBS readonly_tmp: /tmp is erofs read-only on device runners.
        # Pass through the HMBS-injected writable TMPDIR/TMP/TEMP into the
        # build scope so cmake/compiler/ctest temp files avoid /tmp.
        tmp_env = Environment()
        for _var in ("TMPDIR", "TMP", "TEMP"):
            _val = os.environ.get(_var)
            if _val:
                tmp_env.define(_var, _val)
        tmp_env.vars(self, scope="build").save_script("hmbs_tmpdir")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={
            # upstream default toplevel shape: tests + benchmarks ON
            "PFFFT_BUILD_TESTS": "ON",
            "PFFFT_BUILD_BENCHMARKS": "ON",
            "PFFFT_BUILD_EXAMPLES": "OFF",
            # FFTPACK reference implementation is in-tree (src/fftpack.c)
            "PFFFT_USE_FFTPACK": "ON",
            # benchmark comparison submodules are not in the release tarball
            # (same as upstream CI, which also disables them)
            "PFFFT_USE_BENCH_GREEN": "OFF",
            "PFFFT_USE_BENCH_KISS": "OFF",
            "PFFFT_USE_BENCH_POCKET": "OFF",
        })
        cmake.build()
        if can_run(self):
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        # Resolve the directory actually containing CTestTestfile.cmake
        # (cmake_layout may nest the configured project one level down).
        build_folder = self.build_folder
        test_dir = build_folder
        ctest_file = os.path.join(build_folder, "CTestTestfile.cmake")
        if not os.path.isfile(ctest_file):
            found = None
            for _root, _dirs, _files in os.walk(build_folder):
                if "CTestTestfile.cmake" in _files:
                    found = _root
                    break
            if found:
                test_dir = found
                self.output.info(f"hmbs upstream tests: using CTest dir {test_dir}")
        # sign every upstream test/bench executable before execution
        # (OHOS execution gate; bitarray precedent)
        for _root, _dirs, _files in os.walk(build_folder):
            for _f in _files:
                if _f.startswith(("test_", "bench_")) and "." not in _f:
                    self._sign(os.path.join(_root, _f))
        ctest = shutil.which("ctest") or "ctest"
        self.run(
            f"{shlex.quote(ctest)} --test-dir {shlex.quote(str(test_dir))} "
            f"--output-on-failure",
            env="conanbuild",
        )
        # NOTE: upstream builds test_pffft_float/double but does NOT register
        # them in ctest; their --test-simd entry point (validate_pffft_simd_ex)
        # is never run by upstream CI either. On the NEON float path that
        # validator deterministically reports the "!VALIGNED() should have
        # found at least 4 occurences" accounting error: NEON's VALIGNED is
        # 4-byte (pf_neon_float.h:80) so unaligned float pointers cannot
        # exist in its probe loop — an SSE-perspective harness assumption,
        # not a library defect. Library correctness on NEON is covered by
        # the 9 ctest entries (incl. FFTPACK reference comparisons) plus the
        # consumer test (simd_size==4 / simd_arch==NEON assertions). See
        # notes.md.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["pffft"]
        self.cpp_info.set_property("cmake_file_name", "pffft")
        self.cpp_info.set_property("cmake_target_name", "pffft::pffft")
        self.cpp_info.set_property("pkg_config_name", "pffft")

    @staticmethod
    def _sign(executable):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute upstream tests on OHOS"
            )
        signed = executable + ".signed"
        if os.path.isfile(objcopy):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", executable],
                check=False,
            )
        subprocess.run(
            [signer, "sign", "-inFile", executable, "-outFile", signed,
             "-selfSign", "1"],
            check=True,
        )
        shutil.move(signed, executable)
        os.chmod(executable, 0o755)
