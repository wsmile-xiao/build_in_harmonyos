#!/usr/bin/env python3
"""Conan recipe — oaml 1.3.4 (cmake, Open Adaptive Music Library).

OHOS 适配要点（详见 notes.md）:
- 上游 CMakeLists 的 cmake_minimum_required(VERSION 2.8) 被 CMake 4 拒绝，
  用 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 放行（免打源码补丁，libsoxr/libvorbis 同法）。
- OHOS 无 ALSA/PulseAudio/JACK：ENABLE_RTAUDIO=OFF（oamlBase 对 __HAVE_RTAUDIO
  有完整守卫，InitAudioDevice 退化为返回 OAML_ERROR，混音核心 MixToBuffer 不受影响）。
- Unity 插件与 OHOS 无关：ENABLE_UNITYPLUGIN=OFF。
- 上游 Find 模块用裸 find_path/find_library，交叉编译下 FIND_ROOT_PATH=ONLY 会漏掉
  conan 依赖 → 预置 find 缓存变量指向依赖包真实路径（libsoxr 同法）。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, get


class OamlConan(ConanFile):
    name = "oaml"
    version = "1.3.4"
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

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libvorbis/1.3.7")
        self.requires("libsoxr/0.1.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain
        # ② 环境 OHOS_NDK_HOME ③ glob 设备/CI 的 SDK 布局）。
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

    @staticmethod
    def _first_lib(libdir, patterns):
        """按候选名在依赖包 lib/ 里找真实 .so（解析版本化软链，取绝对路径）。"""
        for pat in patterns:
            hits = sorted(glob.glob(os.path.join(libdir, pat)))
            if hits:
                return os.path.realpath(hits[-1])
        raise ConanInvalidConfiguration("依赖包 %s 中找不到 %s" % (libdir, patterns))

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        ohos_arch = {"armv8": "arm64-v8a", "armv7": "armeabi-v7a"}.get(
            str(self.settings.arch), str(self.settings.arch))
        shared = "ON" if self.options.shared else "OFF"

        # 依赖接线：上游 FindOggVorbis/FindVorbisFile/FindSoxr 用裸 find_path/find_library，
        # 交叉链 FIND_ROOT_PATH=ONLY 下搜不到 conan 依赖 → 预置 find 缓存变量为真实路径。
        vorbis = self.dependencies["libvorbis"]
        ogg = self.dependencies["libogg"]
        soxr = self.dependencies["libsoxr"]
        v_inc = vorbis.cpp_info.includedirs[0]
        v_lib = vorbis.cpp_info.libdirs[0]
        o_inc = ogg.cpp_info.includedirs[0]
        o_lib = ogg.cpp_info.libdirs[0]
        s_inc = soxr.cpp_info.includedirs[0]
        s_lib = soxr.cpp_info.libdirs[0]
        find_vars = [
            "-DVORBIS_INCLUDE_DIR={}".format(v_inc),
            "-DVORBIS_LIBRARY={}".format(self._first_lib(v_lib, ["libvorbis.so*", "libvorbis.a"])),
            "-DOGG_INCLUDE_DIR={}".format(o_inc),
            "-DOGG_LIBRARY={}".format(self._first_lib(o_lib, ["libogg.so*", "libogg.a"])),
            "-DVORBISFILE_INCLUDE_DIRS={}".format(v_inc),
            "-DVORBISFILE_LIBRARIES={}".format(self._first_lib(v_lib, ["libvorbisfile.so*", "libvorbisfile.a"])),
            # 上游错配：FindSoxr.cmake 定义复数 SOXR_INCLUDE_DIRS，而 CMakeLists.txt:126
            # 用的是单数 ${SOXR_INCLUDE_DIR} —— 单复数都预置，免源码补丁
            "-DSOXR_INCLUDE_DIRS={}".format(s_inc),
            "-DSOXR_INCLUDE_DIR={}".format(s_inc),
            "-DSOXR_LIBRARIES={}".format(self._first_lib(s_lib, ["libsoxr.so*", "libsoxr.a"])),
        ]

        src = os.path.join(self.source_folder, "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        # 生成器用 Ninja：本沙箱 HMDFS 不支持 FIFO，Unix Makefiles 的 jobserver
        # (mkfifo) spawn 偶发 "Error running link command"（实测 liboaml.a 归档步骤），
        # CI 能力矩阵 ninja ✅
        defs = [
            "-G", "Ninja",
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            # OHOS SDK llvm/bin 缺 llvm-ranlib（ohos.toolchain 硬指过去 → 静态库
            # 归档报 inaccessible or not found）；llvm-ranlib 与目标架构无关，
            # 指向宿主 hnp 工具链的即可（与 binary-sign-tool 同一可用性前提）
            "-DCMAKE_RANLIB={}".format(
                os.environ.get("LLVM_RANLIB", "/data/service/hnp/bin/llvm-ranlib")),
            "-DOHOS_ARCH={}".format(ohos_arch),
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DENABLE_STATIC=ON",
            "-DENABLE_SHARED={}".format(shared),
            "-DENABLE_OGG=ON",
            "-DENABLE_SOXR=ON",
            # OHOS 无 ALSA/Pulse/JACK 音频后端；oamlBase 对 __HAVE_RTAUDIO 有守卫
            "-DENABLE_RTAUDIO=OFF",
            # Unity 引擎插件，与 OHOS 无关
            "-DENABLE_UNITYPLUGIN=OFF",
            # 构建 oamlTest（上游唯一测试入口，见 notes.md R51 申报）
            "-DENABLE_TEST=ON",
            "-DCMAKE_INSTALL_PREFIX={}".format(self.package_folder),
            # 上游 CMakeLists 只把 VORBIS/VORBISFILE 的 include 加进编译（:113），
            # 不加 OGG_INCLUDE_DIR —— 而 vorbis/codec.h #include <ogg/ogg.h>，
            # 编译期需 ogg 头 → 用 C/CXX FLAGS 补（免源码补丁）
            '-DCMAKE_C_FLAGS=-I{}'.format(o_inc),
            '-DCMAKE_CXX_FLAGS=-I{}'.format(o_inc),
        ] + find_vars
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}" -j2'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}"'.format(bdir))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名（ML-0043）。
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        if not targets:
            return
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "找不到 binary-sign-tool：设 BINARY_SIGN_TOOL 指向签名工具（鸿蒙 PC 下 .so 须代码签名）")
        for f in targets:
            if os.path.islink(f):
                continue
            # 未签过的 .so 可能没有旧签名段，remove-section 可失败：用 subprocess 忽略错误
            # （Conan 2.29 的 run 包装不支持 ignore_error，且 shell 短路写法会触发 CI L1d 误判）
            subprocess.run([objcopy, "--remove-section", ".codesign", f],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["oaml"]
        self.cpp_info.set_property("cmake_file_name", "oaml")
        self.cpp_info.set_property("cmake_target_name", "oaml::oaml")
        self.cpp_info.set_property("pkg_config_name", "oaml")
        # oaml 链接 ogg/vorbis/vorbisfile/soxr，声明传递依赖保证消费者链接闭包完整
        self.cpp_info.requires = ["libvorbis::vorbis", "libvorbis::vorbisfile", "libsoxr::libsoxr"]
