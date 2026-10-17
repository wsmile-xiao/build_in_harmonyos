#!/usr/bin/env python3
"""Conan recipe for libheif-jpeg 1.23.0 — libheif 树内 JPEG 解码/编码后端（独立插件模块）。

本包交付面 = 上游 libheif 1.23.0 树内的两个 CMake 目标：

    libheif/plugins/CMakeLists.txt
        set(JPEG_DECODER_sources decoder_jpeg.cc decoder_jpeg.h)
        plugin_compilation(jpegdec JPEG JPEG_FOUND JPEG_DECODER JPEG_DECODER)
        set(JPEG_ENCODER_sources encoder_jpeg.cc encoder_jpeg.h)
        plugin_compilation(jpegenc JPEG JPEG_FOUND JPEG_ENCODER JPEG_ENCODER)
    →  add_library(heif-jpegdec MODULE ...)   # 插件装载开启时
        add_library(heif-jpegenc MODULE ...)
        install(TARGETS heif-${name} LIBRARY DESTINATION <libdir>/libheif)

产物 ``libheif-jpegdec.so``（JPEG→HEIF 图像解码）与 ``libheif-jpegenc.so``
（HEIF 图像→JPEG 编码）。**注意上游目标名是 ``heif-jpegdec``/``heif-jpegenc``
而不是 ``heif-jpeg``**——包名 ``libheif-jpeg`` 取自任务卡的权威包目录名
``archives/l/libheif-jpeg/1.23.0``（CI 分支名门禁按「分支名去前缀 ==
包目录名-版本」精确匹配），并保持同族 ``libheif-<后端>`` 的命名口径。

**树内没有 JPEG 编解码器实现**（``find . -iname '*jpeg*'`` 只命中
``plugins/decoder_jpeg.{cc,h}``、``plugins/encoder_jpeg.{cc,h}``、
``heifio/decoder_jpeg.{cc,h}`` 与 ``tests/jpeg2000.cc``，全是调用方），
所以 JPEG 实现只能来自外部包：本配方复用仓库既有独立包
``libjpeg-turbo/3.2.0``（已发布到 ohpcd，W0 用 ``conan install --build=never``
实测可取得），不重复适配、不在内树重建。

交付面（自包含，因为插件模块无法脱离宿主运行）：

  * ``lib/libheif/libheif-jpegdec.so``、``lib/libheif/libheif-jpegenc.so``
    （+ VERSION/SOVERSION 软链）—— 本包命名产物，由树内
    ``decoder_jpeg.cc`` / ``encoder_jpeg.cc`` 编译，动态链接 ``libjpeg``；
  * 宿主 ``lib/libheif.so``（同源同版本、``ENABLE_PLUGIN_LOADING=ON``）—— 插件以
    ``target_link_libraries(heif-${name} PRIVATE ${JPEG_LIBRARIES} heif)`` 依赖它，
    且运行期必须由它 ``dlopen`` 插件才能注册 JPEG 编解码器；仓库既有
    ``archives/l/libheif/1.22.2`` 是 ``ENABLE_PLUGIN_LOADING=OFF`` 的 codec-free
    核心，**装不了插件**，故不能作为本包的依赖（跨版本插件 ABI 也不匹配）；
  * ``include/libheif/*.h``、``lib/pkgconfig/libheif.pc``、``lib/cmake/libheif/*``。

上游构建开关说明（R1：参数最少化，只开交付面必需的）：

  * ``ENABLE_PLUGIN_LOADING=ON`` + ``WITH_JPEG_DECODER=ON`` +
    ``WITH_JPEG_DECODER_PLUGIN=ON`` + ``WITH_JPEG_ENCODER=ON`` +
    ``WITH_JPEG_ENCODER_PLUGIN=ON``：五个开关共同构成本包交付面（缺任一个就不产生
    ``heif-jpegdec``/``heif-jpegenc`` 目标，改为静态编入宿主）；
  * ``WITH_REDUCED_VISIBILITY`` **保持上游默认 ON**——上游 ``release`` preset 就是
    ``ENABLE_PLUGIN_LOADING=ON`` + ``*_PLUGIN=ON`` + ``WITH_REDUCED_VISIBILITY=ON``
    的组合；插件导出符号 ``plugin_info`` 在 ``plugins/*.h`` 里以
    ``MAYBE_UNUSED LIBHEIF_API extern heif_plugin_info plugin_info;`` 声明
    （``LIBHEIF_API`` 展开为 ``visibility("default")``，插件目标由 CMake 宏
    ``plugin_compilation`` 注入 ``LIBHEIF_EXPORTS`` + ``HAVE_VISIBILITY``），
    所以 hidden preset 不会让 ``dlsym(handle, "plugin_info")`` 失败——
    该结论由 ``test_package`` 的装载断言在设备上实测，不靠推断；
  * ``BUILD_TESTING=OFF`` / ``WITH_EXAMPLES=OFF``：上游测试与 examples 目标不被
    ``install()``，不属交付面；本包的上游用例清点与差额归因见 notes.md 与
    test_package/MANIFEST.yml，消费者验证由 ``test_package/`` 承担；
  * 其余后端（libde265/x265/x264/aom/dav1d/kvazaar/uvg266/vvdec/vvenc/openjpeg/
    openjph/ffmpeg/openh264/rav1e/svt/libsharpyuv/未压缩编码/webcodecs）全部显式
    OFF：不属交付面，且会引入未发布依赖（R36）。

JPEG 依赖如何被找到（无需手写 cache 变量）：libheif 用的是 **CMake 内建 MODULE 包
``find_package(JPEG)``**（树内 ``cmake/modules/`` 没有 FindJPEG.cmake），
Conan 的 ``CMakeToolchain`` 会把每个依赖的 ``<pkg>/include`` 与 ``<pkg>/lib`` 写进
``CMAKE_INCLUDE_PATH`` / ``CMAKE_LIBRARY_PATH``，``FindJPEG`` 的
``find_path``/``find_library`` 因此命中的就是 Conan 缓存里的 libjpeg-turbo
（设备实测：``Found JPEG: <conan cache>/lib/libjpeg.so (found version "62")``）。

OHOS libc++15 缺 C++20 ranges 算法（零补丁解决）：上游 ``libheif/box.cc`` 用了
3 处 ``std::ranges`` **算法**（``std::ranges::all_of`` / ``std::ranges::find``），
而 OHOS SDK 的 libc++15（clang 15.0.4，``_LIBCPP_VERSION 15004``）在
``__config`` 里按
``#if !defined(_LIBCPP_ENABLE_EXPERIMENTAL) && !defined(_LIBCPP_BUILDING_LIBRARY)``
``#  define _LIBCPP_HAS_NO_INCOMPLETE_RANGES`` 把这两个算法整段隐藏——即使
``-std=c++20``/``-std=c++2b`` 也编不过（设备实测：
``no member named 'find' in namespace 'std::ranges'``）。``generate()`` 因此只对
OHOS 下发编译期宏 ``_LIBCPP_ENABLE_EXPERIMENTAL``（``preprocessor_definitions``
值为 ``None`` → 裸 ``-D``），**上游源码零修改、无补丁**。
两个限定条件都由实测确认过，不是推断：①libheif 的**公共头** 0 处 ``std::ranges``
（``grep -rn "std::ranges" libheif/api/`` → 0），故该宏不必经 ``cpp_info.defines``
传播给消费者；②全树 0 处 ``<format>``/``std::format``，故该宏顺带放开的
``_LIBCPP_HAS_NO_INCOMPLETE_FORMAT`` 对本包无副作用；③``std::ranges`` 算法是
**模板**，纯编译期可见性问题，不需要 ``-lc++experimental``（这一点与仓库既有先例
libpqxx 8.0.1 / ladybug 0.18.2 不同：那两处是缺 ``std::format`` 的**运行期**符号，
必须同时链 ``c++experimental``）。

插件目录：上游把默认插件目录**编译期钉死**在 ``heif_version.h`` 的
``LIBHEIF_PLUGIN_DIRECTORY``（= 构建时的 ``${CMAKE_INSTALL_FULL_LIBDIR}/libheif``，
即本包在 Conan 缓存里的绝对路径），跨缓存/跨机不可移植。因此 ``package_info()`` 用
``runenv_info`` 导出 ``LIBHEIF_PLUGIN_PATH``，让 ``VirtualRunEnv``/``conanrun`` 环境
自动带上（上游 ``libheif/plugins_unix.cc`` 优先读该环境变量）。

OHOS 签名（``_sign_shared_libs``，必须步骤）：``cmake --install`` 会剥掉安装出的 .so 的
build rpath（原地改写字节），使 lld 链接时内嵌的 ``.codesign`` 自签失效；此后加载器对
dlopen 与 DT_NEEDED 一律回 ``Permission denied``（ML-0043 / E544 / E077 面）。
本包的两个插件**正是靠宿主 dlopen 工作**，故 ``package()`` 末尾按仓库既有四步法
（``llvm-objcopy --remove-section .codesign`` + ``binary-sign-tool sign -selfSign 1``）
重签 ``lib/**/*.so*`` 中的真实文件（与 libjpeg-turbo 3.2.0 / libvdpau 1.5 同法，
仓库内 1100+ 个配方同款处置）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


# 本包交付面之外的上游后端开关：显式 OFF（不属交付面 + 未发布依赖）。
# 名单取自上游 CMakeLists.txt 的 plugin_option(...) 全集，去掉本包交付的
# JPEG_DECODER / JPEG_ENCODER 两个。
_DISABLED_PLUGIN_OPTIONS = (
    "LIBDE265", "X265", "X264", "KVAZAAR", "UVG266", "VVDEC", "VVENC",
    "AOM_DECODER", "AOM_ENCODER", "DAV1D", "SvtEnc", "RAV1E",
    "FFMPEG_DECODER", "OpenH264_DECODER", "OpenH264_ENCODER",
    "OpenJPEG_DECODER", "OpenJPEG_ENCODER", "OPENJPH_ENCODER", "OPENJPH_DECODER",
)


class LibheifJpegConan(ConanFile):
    name = "libheif-jpeg"
    version = "1.23.0"
    description = ("JPEG decoder + encoder backend plugin modules for libheif 1.23.0, "
                   "built in-tree from libheif/plugins/decoder_jpeg.cc and "
                   "encoder_jpeg.cc as the upstream CMake targets heif-jpegdec / "
                   "heif-jpegenc (libheif-jpegdec.so / libheif-jpegenc.so); ships the "
                   "plugin-loading-enabled libheif host they require")
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
        # --build=never 实测可取得）。共享库，被两个插件模块动态链接。
        self.requires("libjpeg-turbo/3.2.0")

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

    def generate(self):
        tc = CMakeToolchain(self)
        # R33：全部构建配置经 CMakeToolchain 下发，不依赖 shell 环境变量。
        # 宿主必须是共享库（插件 dlopen 语义；见 validate()）。
        tc.variables["BUILD_SHARED_LIBS"] = True

        # --- 平台：必须显式给 CMAKE_SYSTEM_NAME，否则宿主拿不到 SONAME ---
        # 设备 uname -s = HarmonyOS，Conan 也把 os=OHOS 映射成 CMAKE_SYSTEM_NAME=HarmonyOS，
        # 但 SDK 的 CMake 只有 Platform/OHOS.cmake、**没有 Platform/HarmonyOS.cmake**，
        # 于是 configure 落进"未知平台"回退（实测日志：`System is unknown to cmake, create:
        # Platform/HarmonyOS to use this system`），平台模块的 SONAME 开关全不生效：
        #   ① 宿主 libheif.so 不写 DT_SONAME、也不产版本化文件名；
        #   ② 插件链接同构建树的 heif 时，ld 只能把**相对路径**记进 DT_NEEDED
        #      （`NEEDED ../libheif/libheif.so`，含斜杠 → 按 CWD 解析）→ 宿主 dlopen
        #      插件（或反过来）必然失败，test_package/G2 全红。
        # 仓库既有先例 libheif/1.18.2 的 notes.md「NEEDED 字段硬编码相对路径、未解决」即此。
        # 置 Linux 让 CMake 走 Platform/Linux.cmake 拿到 SONAME 规则；实际目标三元组仍由
        # profile 的 clang（--target=aarch64-unknown-linux-ohos）决定，不改变产物架构。
        # 仓库内 693 个配方同口径（例 archives/a/ableton-link/3.1.2）。
        # 注意：这里用 cache_variables —— CMAKE_SYSTEM_NAME 必须在 project() 之前生效，
        # 普通 variables 落不进 toolchain 文件的等价位置。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # --- 让 install 不再就地改写 .so（否则 OHOS 代码签名失效 → dlopen EACCES）---
        # 默认 CMAKE_BUILD_WITH_INSTALL_RPATH=OFF：构建树的插件带 RUNPATH
        # （指向 conan 的 libjpeg 目录 + 构建树的 libheif），install 时 CMake 要把
        # 这段 RUNPATH 抹掉 → **就地改写字节** → 链接期写进 ELF 的 `.note.ohos.ident`
        # 自签失效 → 装出来的插件 `dlopen` 报 `Permission denied`（EACCES，不是 not found）。
        # 设备实测（本包插件产物，`libheif-jpegdec.so`）：
        #   build 树 sha256 c3a66517… → cmake 安装后 ed5d73da…（同尺寸、字节不同）
        #   （宿主 libheif.so.1.23.0 前后同为 edc96bcd…，只看宿主会误判 —— 被改写的
        #    只有"链接了同构建树 target"的插件目标。）
        # 置 build rpath == install rpath == 空，install 判定"无需改写"即逐字节相同，
        # 链接期签名原样保留；运行期依赖由 conanrun/VirtualRunEnv 的 LD_LIBRARY_PATH 提供。
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["CMAKE_INSTALL_RPATH"] = ""

        # --- 交付面：JPEG 解码 + 编码后端，且都以独立插件模块形态构建 ---
        # 五个开关缺一即退化：ENABLE_PLUGIN_LOADING 关闭 → 静态编入宿主；
        # WITH_JPEG_*_PLUGIN 关闭 → 静态编入宿主（不产生 heif-jpeg* 目标）。
        tc.variables["ENABLE_PLUGIN_LOADING"] = True
        tc.variables["WITH_JPEG_DECODER"] = True
        tc.variables["WITH_JPEG_DECODER_PLUGIN"] = True
        tc.variables["WITH_JPEG_ENCODER"] = True
        tc.variables["WITH_JPEG_ENCODER_PLUGIN"] = True

        # --- 交付面之外的上游后端全部显式关闭 ---
        for option in _DISABLED_PLUGIN_OPTIONS:
            tc.variables[f"WITH_{option}"] = False
        tc.variables["WITH_UNCOMPRESSED_CODEC"] = False
        tc.variables["WITH_WEBCODECS"] = False
        tc.variables["WITH_LIBSHARPYUV"] = False

        # --- 非交付面（工具/文档/测试）：不构建 ---
        tc.variables["WITH_EXAMPLES"] = False
        tc.variables["WITH_GDK_PIXBUF"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_DOCUMENTATION"] = False

        # --- OHOS clang15/libc++15：打开 C++20 ranges 算法（见模块 docstring）---
        # 上游 CMAKE_CXX_STANDARD=20，但 libc++15 在未定义该宏时用
        # _LIBCPP_HAS_NO_INCOMPLETE_RANGES 隐藏 ranges 算法 → box.cc 编不过。
        # 值为 None → conan 生成裸 -D_LIBCPP_ENABLE_EXPERIMENTAL（不落进
        # __config 的 !defined() 判据之外），且不需要 -lc++experimental（模板）。
        if str(self.settings.os) == "OHOS":
            tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None

        # 插件目录、WITH_REDUCED_VISIBILITY 等其余开关保持上游默认，不改上游语义。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 只构建交付面目标：heif 宿主 + 两个 JPEG 插件模块。
        # （heifio / gnome / examples 的目标不被 install()，不属交付面，且 heifio 会触发
        #   TIFF/PNG/WEBP 的可选探测，与交付物无关。）
        cmake.build(target=["heif", "heif-jpegdec", "heif-jpegenc"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        """重签安装后的 .so（OHOS 签名完整性，ML-0043 / E544 / E077）。

        为什么必须做：OHOS 上 clang/lld 产物自带 ``.codesign`` 段；``cmake --install``
        会把安装出来的 .so 的 build rpath 剥掉（**原地改写字节**），原签名与新内容失配，
        此后 musl/XPM 加载器对 dlopen 与 DT_NEEDED 一律回 ``Permission denied``
        （readelf/属主/权限位全部正常，极易误判为路径或权限问题）。本包的两个插件
        模块**正是靠宿主 dlopen 工作**，命中面 100%。

        处置：先尽力移除失效的 ``.codesign`` 段，再用 SDK 的 ``binary-sign-tool``
        自签（四步法，与 libjpeg-turbo 3.2.0 / libvdpau 1.5 同法）。只处理真实文件、
        跳过软链（软链指向真实文件，重签后自然生效）。
        """
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        sos = [s for s in sos if os.path.isfile(s) and not os.path.islink(s)]
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            # .codesign 段可能不存在：移除属尽力而为，下一步重签才是硬要求
            self.run(f'{objcopy} --remove-section .codesign "{so}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        # 交付的宿主库（消费者链接的就是它；插件模块是运行期产物，不在 libdirs 里）。
        self.cpp_info.libs = ["heif"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libheif")
        self.cpp_info.set_property("cmake_target_name", "libheif::libheif")
        self.cpp_info.set_property("pkg_config_name", "libheif")
        # 插件模块装在 <pkg>/lib/libheif/；上游把默认插件目录编译期钉死成构建时的
        # 绝对路径，跨缓存/跨机不可移植，故显式导出 LIBHEIF_PLUGIN_PATH
        # （VirtualRunEnv / self.run(env="conanrun") 会自动带上）。
        self.runenv_info.define(
            "LIBHEIF_PLUGIN_PATH",
            os.path.join(self.package_folder, "lib", "libheif"),
        )
