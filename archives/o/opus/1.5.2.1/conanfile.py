#!/usr/bin/env python3
"""Conan recipe — opus 1.5.2 (cmake)"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, get


class OpusConan(ConanFile):
    name = "opus"
    version = "1.5.2.1"
    description = "Totally open, royalty-free, highly versatile audio codec"
    license = "BSD-3-Clause"
    homepage = "https://opus-codec.org/"
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
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME
        # ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def build(self):
        # glfw/libjpeg-turbo/zstd/libxml2 同法：自发现 ohos.toolchain + 裸 cmake，绕开 conan_toolchain——
        # os=OHOS 下它把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值（ML-0035：System is unknown to cmake）。
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        shared = "ON" if self.options.shared else "OFF"
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            "-DBUILD_SHARED_LIBS={}".format(shared),          # 遵从 self.options.shared
            "-DOPUS_BUILD_SHARED_LIBRARY={}".format(shared),
        ]
        # 依赖接线（find_package/find_library/pkg-config）须按需在此手工补 -D（见 SKILL「cmake 库依赖库」）：
        #   find_package(X CONFIG) → -DX_DIR=self.dependencies["x"].package_folder+"/lib/cmake/x"
        #   find_library/find_path → 预设目标库的 find 缓存变量为依赖真实路径（绕交叉链 FIND_ROOT_PATH=ONLY）
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted（cmake/SDK-toolchain 产的自签无效，且 conan install 复制会破坏链接器自签）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（llvm-config/xxx CLI 等）——产可执行文件的包必须签 bin。
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        # 工具路径优先取环境变量，回退 CI/设备默认（同 _ohos_toolchain 的 env/默认回退链，
        # 不裸用可能为空的变量）。签名工具仅在 CI/设备环境存在。
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            # 本地非设备环境（无 /data/service/hnp/bin）跳过签名而非硬失败——设备加载需签名，
            # 请在 CI/设备环境执行，或经 BINARY_SIGN_TOOL 指定 binary-sign-tool 路径。
            self.output.warning(
                "binary-sign-tool 不存在（{}）：跳过代码签名。设备上 dlopen/exec 未签名产物会因 "
                "XPM 报 Permission denied，请在 CI/设备环境或经 BINARY_SIGN_TOOL 指定后重打包。".format(signer))
            return
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["opus"]
        # opus 的公开头装在 include/opus/（CMakeLists.txt:608 PUBLIC_HEADER DESTINATION
        # ${CMAKE_INSTALL_INCLUDEDIR}/opus），而上游 opus.pc 写的是 `Cflags: -I${includedir}/opus`，
        # 故所有消费方按 `#include <opus.h>` / `<opus_multistream.h>`（**不带 opus/ 前缀**）来写。
        # 不设 includedirs 时 conan 生成的 opus.pc 只给 -I<pkg>/include，消费方编译期找不到头——
        # FFmpeg 会报 "opus not found using pkg-config"（误导性报错：pkg-config 其实找得到，
        # 失败的是随后的 check_func_headers 编译探测）。
        # 参照同仓 freetype 包的做法（includedirs = ["include/freetype2", "include"]）。
        self.cpp_info.includedirs = ["include/opus", "include"]
        self.cpp_info.set_property("cmake_file_name", "opus")
        self.cpp_info.set_property("cmake_target_name", "opus::opus")
        self.cpp_info.set_property("pkg_config_name", "opus")
