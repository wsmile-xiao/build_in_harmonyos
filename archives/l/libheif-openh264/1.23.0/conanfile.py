#!/usr/bin/env python3
"""Conan recipe for libheif-openh264 1.23.0 — libheif 树内 OpenH264 解码后端（独立插件模块）。

本包交付面 = 上游 libheif 1.23.0 树内的 CMake 目标 ``heif-openh264dec``，其产物
``libheif-openh264dec.so`` 是 libheif 的 **OpenH264（H.264/AVC）解码插件模块**：

    CMakeLists.txt:200          plugin_option(OpenH264_DECODER "OpenH264 decoder" ON OFF)
    libheif/plugins/CMakeLists.txt
        set(OpenH264_DECODER_sources decoder_openh264.cc decoder_openh264.h)
        plugin_compilation(openh264dec OpenH264 OpenH264_DECODER_FOUND \\
                           OpenH264_DECODER OpenH264_DECODER)
    →  add_library(heif-openh264dec MODULE ...)      # 插件装载开启时
        install(TARGETS heif-openh264dec LIBRARY DESTINATION <libdir>/libheif)

包名按仓库既有约定取 ``libheif-<codec>``（同批 ``libheif-libde265`` / ``-aom`` / ``-dav1d`` /
``-jpeg`` / ``-openjpeg`` / ``-svtenc``）；上游树内目标名带 ``dec`` 后缀是因为同一个
``plugin_compilation()`` 宏还要区分编/解码器（``j2kdec``/``j2kenc``、``aomdec``/``aomenc``、
``jpegdec``/``jpegenc``），本包只交付其中的解码器。

**树内没有 openh264 源码副本**（``find . -iname '*openh264*'`` 只有
``cmake/modules/FindOpenH264.cmake`` 与 ``libheif/plugins/decoder_openh264.{cc,h}``），
所以 openh264 只能来自外部包：本配方复用仓库既有独立包 ``openh264/2.6.0``
（已合并、已发布；W0 用 ``conan install --build=never`` 实测可取得），
不重复适配、不在内树重建。

交付面（自包含，因为插件模块无法脱离宿主运行）：

  * ``lib/libheif/libheif-openh264dec.so``（+ VERSION/SOVERSION 软链）—— 本包命名产物，
    由树内 ``decoder_openh264.cc`` 编译，链接 ``libopenh264.so``；
  * 宿主 ``lib/libheif.so``（同源同版本、``ENABLE_PLUGIN_LOADING=ON``）—— 插件以
    ``target_link_libraries(heif-openh264dec PRIVATE ${OpenH264_LIBRARIES} heif)`` 依赖它，
    且运行期必须由它 ``heif_init()`` 扫插件目录 ``dlopen`` 才能注册 AVC 解码器；
    仓库既有 ``archives/l/libheif/1.22.2`` 是 ``ENABLE_PLUGIN_LOADING=OFF`` 的 codec-free
    核心，**装不了插件**，故不能作为本包的依赖（跨版本插件 ABI 也不匹配）；
  * ``include/libheif/*.h``、``lib/pkgconfig/libheif.pc``、``lib/cmake/libheif/*``。

上游构建开关说明（R1：参数最少化，只开交付面必需的）：

  * ``ENABLE_PLUGIN_LOADING=ON`` + ``WITH_OpenH264_DECODER=ON`` +
    ``WITH_OpenH264_DECODER_PLUGIN=ON``：三者共同构成本包交付面（缺一则不产生
    ``heif-openh264dec`` 目标，改为把后端静态编入宿主）；
  * ``BUILD_TESTING=OFF``：上游测试目标不被 ``install()``，不属交付面；本包的上游
    用例清点与归因见 notes.md，消费者验证由 ``test_package/`` 承担；
  * 其余后端（libde265/x265/aom/dav1d/x264/kvazaar/uvg266/vvdec/vvenc/openjpeg/
    openjph/ffmpeg/rav1e/svt/jpeg/libsharpyuv/未压缩编码/WebCodecs）全部显式 OFF：
    不属交付面，且会引入未发布依赖（R36）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


# 本包交付面之外的上游后端开关：显式 OFF（不属交付面 + 未发布依赖）。
_DISABLED_PLUGIN_OPTIONS = (
    "LIBDE265", "X265", "X264", "AOM_DECODER", "AOM_ENCODER", "DAV1D", "KVAZAAR",
    "UVG266", "VVDEC", "VVENC", "FFMPEG_DECODER", "RAV1E", "SvtEnc",
    "JPEG_DECODER", "JPEG_ENCODER", "OpenJPEG_DECODER", "OpenJPEG_ENCODER",
    "OPENJPH_ENCODER", "LIBSHARPYUV",
)

# 鸿蒙 PC XPM：被 dlopen 的 .so 需要代码签名，否则运行期报 Permission denied /
# Operation not permitted；install 复制会破坏链接器自签，故装完必须重签（仓库既有
# 1442 个配方同口径，如 archives/o/openh264/2.6.0、archives/f/ffmpeg/8.1.2）。
_HNP_BIN = "/data/service/hnp/bin"


class LibheifOpenh264Conan(ConanFile):
    name = "libheif-openh264"
    version = "1.23.0"
    description = ("OpenH264 (H.264/AVC) decoder backend plugin module for libheif 1.23.0, "
                   "built in-tree from libheif/plugins/decoder_openh264.cc as the upstream "
                   "CMake target heif-openh264dec (libheif-openh264dec.so); ships the "
                   "plugin-loading-enabled libheif host it requires")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/strukturag/libheif"
    url = "https://github.com/strukturag/libheif"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 唯一直接依赖：仓库既有独立包（已发布到 ohpcd，W0 用 conan install
        # --build=never 实测可取得）。共享库，插件模块 DT_NEEDED 它。
        self.requires("openh264/2.6.0")

    def validate(self):
        if not self.options.shared:
            # 插件以 MODULE 形态被宿主 dlopen，必须与宿主共享同一份 libheif 运行时；
            # 静态宿主会让插件自带一份副本（状态分裂）。上游 BUILD_SHARED_LIBS 默认 ON。
            raise ConanInvalidConfiguration(
                f"{self.ref}: 插件模块形态要求宿主 heif 为共享库（shared=True）")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---------------------------------------------------------------- helpers
    def _resolve_dir(self, dep, candidates, fallback):
        for rel in candidates:
            path = rel if os.path.isabs(rel) else os.path.join(dep.package_folder, rel)
            if os.path.isdir(path):
                return path
        return os.path.join(dep.package_folder, fallback)

    def _openh264_paths(self):
        """返回 (include_dir, library_path)。

        上游 ``cmake/modules/FindOpenH264.cmake`` 走
        ``libfind_pkg_check_modules(OpenH264_PKGCONF openh264)`` + 不带 HINTS 的
        ``find_path(NAMES wels/codec_api.h)`` / ``find_library(NAMES libopenh264 openh264)``
        （MODULE 模式，不读 CMakeDeps 的 config）。直接把 Conan 依赖的实际路径钉进
        cache 变量，既避免命中设备上的系统 openh264，也不依赖构建环境里 pkg-config
        是否可用/是否污染。
        """
        dep = self.dependencies["openh264"]
        include_dir = self._resolve_dir(dep, list(dep.cpp_info.includedirs), "include")
        libdir = self._resolve_dir(dep, list(dep.cpp_info.libdirs), "lib")

        library = None
        for name in dep.cpp_info.libs or ["openh264"]:
            for pattern in (f"lib{name}.so", f"lib{name}.so.*", f"lib{name}.a"):
                hits = sorted(glob.glob(os.path.join(libdir, pattern)))
                if hits:
                    library = hits[0]
                    break
            if library:
                break
        if library is None:
            raise ConanInvalidConfiguration(
                f"{self.ref}: 在 {libdir} 未找到 openh264 共享/静态库"
                f"（libs={list(dep.cpp_info.libs)}）")
        return include_dir, library

    # ---------------------------------------------------------------- build
    def generate(self):
        include_dir, library = self._openh264_paths()

        tc = CMakeToolchain(self)
        # R33：全部构建配置经 CMakeToolchain 下发，不依赖 shell 环境变量。
        # 宿主必须是共享库（插件 dlopen 语义；见 validate()）。
        tc.variables["BUILD_SHARED_LIBS"] = True

        # --- 交付面：OpenH264 解码后端，且以独立插件模块形态构建 ---
        tc.variables["ENABLE_PLUGIN_LOADING"] = True
        tc.variables["WITH_OpenH264_DECODER"] = True
        tc.variables["WITH_OpenH264_DECODER_PLUGIN"] = True

        # --- 交付面之外的上游后端全部显式关闭 ---
        for option in _DISABLED_PLUGIN_OPTIONS:
            tc.variables[f"WITH_{option}"] = False
        tc.variables["WITH_UNCOMPRESSED_CODEC"] = False
        tc.variables["WITH_WEBCODECS"] = False

        # --- 非交付面（工具/文档/测试）：不构建 ---
        tc.variables["WITH_EXAMPLES"] = False
        tc.variables["WITH_GDK_PIXBUF"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_DOCUMENTATION"] = False

        # --- FindOpenH264.cmake 的输入（见 _openh264_paths 注释）---
        tc.cache_variables["OpenH264_INCLUDE_DIR"] = include_dir
        tc.cache_variables["OpenH264_LIBRARY"] = library

        # --- OHOS libc++ 15 的 C++20 缺口 ---
        # 上游 libheif 1.23.0 在 libheif/box.cc:4155-4166 用了 std::ranges::all_of /
        # std::ranges::find（CMakeLists.txt 里 CMAKE_CXX_STANDARD=20）。OHOS SDK 自带的
        # libc++（libcxx-ohos，_LIBCPP_VERSION 15004）在未定义 _LIBCPP_ENABLE_EXPERIMENTAL
        # 时会定义 _LIBCPP_HAS_NO_INCOMPLETE_RANGES，把这两个 ranges 算法从 <algorithm>
        # 里隐藏，报 "no member named 'find' in namespace 'std::ranges'"。用 libc++ 官方的
        # 实验特性开关打开即可（仓库既有同口径先例：archives/l/libpqxx/8.0.1、
        # archives/l/ladybug/0.18.2）——只改头文件可见性，不改上游源码、不加补丁。
        if str(self.settings.os) == "OHOS":
            tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None
            # --- OHOS 上 CMake 不认识 HarmonyOS 平台 → 共享库不带 SONAME ---
            # CMake 4.1.2 没有 Platform/HarmonyOS.cmake（配置日志逐字打印
            # "System is unknown to cmake, create: Platform/HarmonyOS"），
            # CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG 未定义 → 产出的 libheif.so
            # 既没有 DT_SONAME，也不生成版本化软链；于是链接插件时 CMake 把
            # **构建树相对路径**写进 DT_NEEDED：
            #   $ readelf -d lib/libheif/libheif-openh264dec.so
            #     (NEEDED)  Shared library: [../libheif.so]
            # 宿主 heif_init() → dlopen 插件时加载器按 CWD 相对路径找 ../libheif.so，
            # 失败（逐字：dlopen: Error loading shared library ../libheif.so）。
            # 注入 SONAME 变量后恢复 Linux 布局 libheif.so → .so.1 → .so.1.23.0，
            # 插件 DT_NEEDED 变成 libheif.so.1（包内存在，运行期由 LD_LIBRARY_PATH 解析）。
            # 仓库既有同口径先例：archives/a/azure-identity-cpp、archives/a/attica、
            # archives/a/apache-arrow（都注明 "CMake has no Platform/HarmonyOS.cmake"）。
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        # 插件目录：保持上游默认（<prefix>/<libdir>/libheif），不改上游语义。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 只构建交付面目标：heif 宿主 + heif-openh264dec 插件模块。
        # （heifio 等其它目标不被 install()，不属交付面，且会触发 TIFF/JPEG/PNG/WEBP
        #   可选探测，与交付物无关。）
        cmake.build(target=["heif", "heif-openh264dec"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 都要代码签名，否则报 Permission denied /
        # Operation not permitted（archives/o/openh264/2.6.0、archives/f/ffmpeg/8.1.2 同口径）。
        # 本包被 dlopen 的两个文件都在 lib/ 下：宿主 libheif.so* 与插件
        # lib/libheif/libheif-openh264dec.so*，故按 lib/** 递归取。
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"),
                            recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"),
                             recursive=True)
        objcopy = os.path.join(_HNP_BIN, "llvm-objcopy")
        signer = os.path.join(_HNP_BIN, "binary-sign-tool")
        for path in targets:
            if os.path.islink(path) or not self._is_elf(path):
                continue  # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1')

    def package_info(self):
        # 交付的宿主库（消费者链接的就是它；插件模块是运行期产物，不在 libdirs 里）。
        self.cpp_info.libs = ["heif"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libheif")
        self.cpp_info.set_property("cmake_target_name", "libheif::libheif")
        self.cpp_info.set_property("pkg_config_name", "libheif")
        # 插件模块装在 <pkg>/lib/libheif/；上游把默认插件目录编译期钉死成构建时的
        # 绝对路径（heif_version.h 的 LIBHEIF_PLUGIN_DIRECTORY），跨缓存/跨机不可移植，
        # 故显式导出 LIBHEIF_PLUGIN_PATH（libheif/init.cc 优先读该环境变量；
        # VirtualRunEnv / self.run(env="conanrun") 会自动带上）。
        self.runenv_info.define(
            "LIBHEIF_PLUGIN_PATH",
            os.path.join(self.package_folder, "lib", "libheif"),
        )
