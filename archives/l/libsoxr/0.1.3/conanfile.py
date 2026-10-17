#!/usr/bin/env python3
"""Conan recipe — libsoxr 0.1.3 (cmake)"""
from conan import ConanFile
from conan.tools.files import get
import os
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches


class LibsoxrConan(ConanFile):
    name = "libsoxr"
    version = "0.1.3"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}


    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain ② 环境 OHOS_NDK_HOME
        # ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        import glob
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
        # OHOS_ARCH 由 profile 的 settings.arch 推导，避免非 arm64 profile 下静默产出 arm64 二进制。
        ohos_arch = {"armv8": "arm64-v8a", "armv7": "armeabi-v7a"}.get(
            str(self.settings.arch), str(self.settings.arch))
        shared = "ON" if self.options.shared else "OFF"   # 遵从 -o libsoxr/*:shared，不硬编码
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH={}".format(ohos_arch),
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            "-DBUILD_SHARED_LIBS={}".format(shared),
        ]
        defs.append("-DWITH_OPENMP=OFF")
        defs.append("-DBUILD_TESTS=OFF")
        defs.append("-DBUILD_EXAMPLES=OFF")
        defs.append("-DWITH_LSR_BINDINGS=OFF")
        defs.append("-DCMAKE_POLICY_VERSION_MINIMUM=3.5")
        # soxr 的 doc 装到 CMAKE_INSTALL_FULL_DOCDIR（configure 时按 prefix 烤成绝对路径）——不设 prefix
        # 则默认 /usr/local → package() 时 install 到 /usr/local 报 permission denied。configure 就把 prefix
        # 指到 package_folder，FULL_* 全落包内。
        defs.append('-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder))
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
        import glob, os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        if not targets:
            return
        # 工具路径优先取环境变量，回退到设备 CI 默认路径（与 _ohos_toolchain 的发现策略一致）。
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            # 签名不可省（未签 .so 在鸿蒙 PC dlopen 报 Permission denied）——缺工具时显式报错，不静默放过。
            raise ConanInvalidConfiguration(
                "找不到 binary-sign-tool：设 BINARY_SIGN_TOOL 指向签名工具（鸿蒙 PC 下 .so 须代码签名，见 ML-0043）")
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            # remove-section 允许不存在旧签名段而失败（|| true）；sign 本身不兜底，失败即中止构建。
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["soxr"]
        self.cpp_info.set_property("cmake_file_name", "libsoxr")
        self.cpp_info.set_property("cmake_target_name", "libsoxr::libsoxr")
        self.cpp_info.set_property("pkg_config_name", "soxr")
