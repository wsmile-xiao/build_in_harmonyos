#!/usr/bin/env python3
"""Conan recipe — wavpack 5.9.0 (cmake)

WavPack hybrid lossless/lossy audio compression library.
Build system: CMake (source also ships autotools, but CMake is used here
for better cross-compilation support with the OHOS toolchain).

Only the library (libwavpack) is built; command-line programs are disabled
(WAVPACK_BUILD_PROGRAMS=OFF) to avoid the iconv dependency.
"""
import os
import glob
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class WavpackConan(ConanFile):
    name = "wavpack"
    version = "5.9.0"
    description = "Hybrid lossless/lossy audio compression codec library"
    license = "BSD-3-Clause"
    homepage = "https://www.wavpack.com/"
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

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake: 设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _ohos_arch(self):
        arch_map = {
            "armv8": "arm64-v8a",
            "armv7": "armeabi-v7a",
            "x86": "x86",
            "x86_64": "x86_64",
        }
        arch = str(self.settings.arch)
        if arch not in arch_map:
            raise ConanInvalidConfiguration("不支持的 OHOS 架构: {}".format(arch))
        return arch_map[arch]

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")
        shared = "ON" if self.options.shared else "OFF"
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH={}".format(self._ohos_arch()),
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DBUILD_SHARED_LIBS={}".format(shared),
            "-DWAVPACK_BUILD_PROGRAMS=OFF",
            "-DWAVPACK_ENABLE_THREADS=ON",
            "-DWAVPACK_ENABLE_DSD=ON",
            "-DWAVPACK_INSTALL_CMAKE_MODULE=ON",
            "-DWAVPACK_INSTALL_PKGCONFIG_MODULE=ON",
            "-DWAVPACK_INSTALL_DOCS=OFF",
            # BUILD_TESTING=ON: 构建上游 wvtest (cli/wvtest.c)。
            # wvtest 仅链接 libwavpack + Threads + m，不依赖 iconv
            # (iconv 仅 wavpack/wvunpack 等 CLI 程序需要，已由
            #  WAVPACK_BUILD_PROGRAMS=OFF 关闭)，可在 OHOS 原生运行。
            "-DBUILD_TESTING=ON",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, self.source_folder, defs))
        self.run('cmake --build "{}"'.format(bdir))
        # L1: 在 OHOS 环境实际运行上游 wvtest (ctest 注册了
        # `wvtest --exhaustive --short --no-extras`，即 164 个子测试)。
        # CI build_and_test.sh 会从 conan create 日志中校验 ctest 执行痕迹。
        self.run('ctest --test-dir "{}" --output-on-failure'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        if self.options.shared:
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue
            # Distinguish the harmless ".codesign section absent" case (typical
            # for fresh builds) from real llvm-objcopy failures (tool missing,
            # file corrupt, permission denied). The former must not abort the
            # build; the latter must — otherwise binary-sign-tool would sign a
            # .so whose stale .codesign section was never stripped, producing
            # a corrupt double-signed artifact. subprocess is used instead of
            # self.run() so the return code and stderr can be inspected.
            try:
                proc = subprocess.run(
                    [objcopy, "--remove-section", ".codesign", so],
                    capture_output=True, text=True,
                )
            except FileNotFoundError:
                raise ConanException(
                    f"llvm-objcopy not found at {objcopy} — cannot strip .codesign"
                )
            if proc.returncode != 0:
                stderr = (proc.stderr or "").strip()
                low = stderr.lower()
                if "not found" in low or "no such" in low or "does not exist" in low:
                    self.output.info(
                        f"no .codesign section in {so} (fresh build) — skip strip"
                    )
                else:
                    raise ConanException(
                        f"llvm-objcopy failed on {so} (rc={proc.returncode}): {stderr}"
                    )
            # binary-sign-tool failure is fatal — re-raise with a clear message.
            try:
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))
            except ConanException:
                raise ConanException(
                    f"binary-sign-tool failed while signing {so}"
                )

    def package_info(self):
        self.cpp_info.libs = ["wavpack"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "WavPack")
        self.cpp_info.set_property("cmake_target_name", "WavPack::WavPack")
        self.cpp_info.set_property("pkg_config_name", "wavpack")
