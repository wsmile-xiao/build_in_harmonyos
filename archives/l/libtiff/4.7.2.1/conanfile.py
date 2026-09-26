#!/usr/bin/env python3
"""Conan recipe — libtiff 4.7.2.1 (cmake)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get
import os
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches


class LibtiffConan(ConanFile):
    name = "libtiff"
    version = "4.7.2.1"
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
        # zlib 必须 1.3.1.1（-fPIC 静态）：链进 libtiff.so，用 1.3.1 会 R_AARCH64 relocation。
        self.requires("zlib/1.3.1.1")
        self.requires("libdeflate/1.25")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("zstd/1.5.7")
        self.requires("libwebp/1.6.0")
        self.requires("lerc/4.1.1")
        self.requires("jbigkit/2.1")
        self.requires("xz/5.6.2")

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
        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            "-DBUILD_SHARED_LIBS=ON",
        ]
        defs.append("-Dzlib=ON")
        defs.append("-Dlibdeflate=ON")
        defs.append("-Djpeg=ON")
        defs.append("-Dzstd=ON")
        defs.append("-Dwebp=ON")
        defs.append("-Dlerc=ON")
        defs.append("-Djbig=ON")
        defs.append("-Dlzma=ON")
        # R51: 上游测试套件可通过 -c "user.libtiff:tests=ON" 打开（本地验证用；
        # CI 常规构建仍关，测试构建产物不进包）。注意：上游 ctest 需 tiff-tools。
        defs.append("-Dtiff-tools=ON" if self.conf.get("user.libtiff:tests", default=False)
                    else "-Dtiff-tools=OFF")
        defs.append("-Dtiff-tests={}".format(
            "ON" if self.conf.get("user.libtiff:tests", default=False) else "OFF"))
        defs.append("-Dtiff-docs=OFF")
        defs.append("-Dtiff-contrib=OFF")
        defs.append("-Dtiff-opengl=OFF")
        defs.append("-Dtiff-cxx=OFF")           # 纯 C 库，不建 libtiffxx
        # 依赖接线：libtiff 全用自带 FindXxx 模块（find_path/find_library）+ 标准 FindZLIB；JPEG 无 CONFIG
        # 时回退 FindJPEG。交叉链 FIND_ROOT_PATH_MODE=ONLY 覆盖命令行 → 直接预设各模块的 find 缓存变量
        # （<pkg>/include + 实际 lib 文件）即绕过搜索（已设的 cache 变量 find_* 不再搜）。
        import glob as _glob
        _wire = [
            # (conan 依赖, INCLUDE 变量, [LIBRARY 变量...], [lib 文件候选（优先 .so，回退 .a）])
            ("zlib",          "ZLIB_INCLUDE_DIR",    ["ZLIB_LIBRARY"],                                ["libz.a", "libz.so"]),
            ("libdeflate",    "Deflate_INCLUDE_DIR", ["Deflate_LIBRARY", "Deflate_LIBRARY_RELEASE"],  ["libdeflate.so", "libdeflate.a"]),
            ("libjpeg-turbo", "JPEG_INCLUDE_DIR",    ["JPEG_LIBRARY"],                                ["libjpeg.so", "libjpeg.a"]),
            ("zstd",          "ZSTD_INCLUDE_DIR",    ["ZSTD_LIBRARY", "ZSTD_LIBRARY_RELEASE"],        ["libzstd.so", "libzstd.a"]),
            ("libwebp",       "WebP_INCLUDE_DIR",    ["WebP_LIBRARY", "WebP_LIBRARY_RELEASE"],        ["libwebp.so", "libwebp.a"]),
            ("lerc",          "LERC_INCLUDE_DIR",    ["LERC_LIBRARY"],                                ["libLerc.so", "libLerc.a"]),
            ("jbigkit",       "JBIG_INCLUDE_DIR",    ["JBIG_LIBRARY", "JBIG_LIBRARY_RELEASE"],        ["libjbig.a", "libjbig.so"]),
            ("xz",            "LIBLZMA_INCLUDE_DIR", ["LIBLZMA_LIBRARY", "LIBLZMA_LIBRARY_RELEASE"],  ["liblzma.so", "liblzma.a"]),
        ]
        _ldirs = []
        for _dep, _incv, _libvs, _names in _wire:
            _pkg = self.dependencies[_dep].package_folder
            defs.append('-D{}="{}"'.format(_incv, os.path.join(_pkg, "include")))
            _lp = next((h for n in _names for h in _glob.glob(os.path.join(_pkg, "lib", n))),
                       os.path.join(_pkg, "lib", _names[0]))
            for _lv in _libvs:
                defs.append('-D{}="{}"'.format(_lv, _lp))
            _ldirs.append(os.path.join(_pkg, "lib"))
        # 链接 libtiff.so 会牵出各依赖 .so 的传递 NEEDED（lerc 的 libc++_shared 等）→ 链接期加 -L + -rpath-link。
        os.environ["LDFLAGS"] = " ".join("-L{0} -Wl,-rpath-link,{0}".format(d) for d in _ldirs) + " " + os.environ.get("LDFLAGS", "")
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # 鸿蒙 PC 对 dlopen 的 .so 校验代码签名：构建若在链接后改动 .so（如 zipfs 尾拼）会破坏链接器自签。
        # 剥旧 .codesign + binary-sign-tool -selfSign 1 重签。默认不需要（干净 .so 靠链接器自签，见 ML-0043）。
        import glob, os
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["tiff"]
        # 标准 CMake 消费方 find_package(TIFF) → TIFF::tiff。
        self.cpp_info.set_property("cmake_file_name", "TIFF")
        self.cpp_info.set_property("cmake_target_name", "TIFF::tiff")
        self.cpp_info.set_property("pkg_config_name", "libtiff-4")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
