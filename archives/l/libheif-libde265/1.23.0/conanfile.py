#!/usr/bin/env python3
"""Conan recipe for libheif-libde265 1.23.0 — libheif 树内 libde265 解码后端（独立插件模块）。

本包交付面 = 上游 libheif 1.23.0 树内的 CMake 目标 ``heif-libde265``，其产物
``libheif-libde265.so`` 是 libheif 的 **libde265（HEVC）解码插件模块**：

    libheif/plugins/CMakeLists.txt
        set(LIBDE265_sources decoder_libde265.cc decoder_libde265.h)
        plugin_compilation(libde265 LIBDE265 LIBDE265_FOUND LIBDE265 LIBDE265)
    →  add_library(heif-libde265 MODULE ...)      # 插件装载开启时
        install(TARGETS heif-libde265 LIBRARY DESTINATION <libdir>/libheif)

``libde265`` 是**上游目标名里就带的子模块名**（``heif-${name}`` → ``heif-libde265``），
包名按仓库惯例取「交付库的文件名去掉前后缀」= ``libheif-libde265``（同族先例：
``archives/l/libhwy_test`` ← 树内目标 ``hwy_test`` → ``libhwy_test.a``）。

**树内没有 libde265 源码副本**（``find . -iname '*de265*'`` 只有
``cmake/modules/FindLIBDE265.cmake`` 与 ``libheif/plugins/decoder_libde265.{cc,h}``），
所以 libde265 只能来自外部包：本配方复用仓库既有独立包 ``libde265/1.0.18``
（已合并、已发布），不重复适配、不在内树重建。

交付面（自包含，因为插件模块无法脱离宿主运行）：

  * ``lib/libheif/libheif-libde265.so``（+ VERSION/SOVERSION 软链）—— 本包命名产物，
    由树内 ``decoder_libde265.cc`` 编译，静态链入 ``libde265.a``；
  * 宿主 ``lib/libheif.so``（同源同版本、``ENABLE_PLUGIN_LOADING=ON``）—— 插件以
    ``target_link_libraries(heif-libde265 PRIVATE ... heif)`` 依赖它，且运行期必须由它
    ``dlopen`` 插件才能注册 HEVC 解码器；仓库既有 ``archives/l/libheif/1.22.2`` 是
    ``ENABLE_PLUGIN_LOADING=OFF`` 的 codec-free 核心，**装不了插件**，故不能作为本包的
    依赖（跨版本插件 ABI 也不匹配）。这与同批兄弟包 ``libhwy_test`` 自包含交付其
    PUBLIC 依赖 ``hwy`` 的口径一致；
  * ``include/libheif/*.h``、``lib/pkgconfig/libheif.pc``、``lib/cmake/libheif/*``。

上游构建开关说明（R1：参数最少化，只开交付面必需的）：

  * ``ENABLE_PLUGIN_LOADING=ON`` + ``WITH_LIBDE265=ON`` + ``WITH_LIBDE265_PLUGIN=ON``：
    三者共同构成本包交付面（缺一则不产生 ``heif-libde265`` 目标，改为静态编入宿主）；
  * ``BUILD_TESTING=OFF``：上游测试目标不被 ``install()``，不属交付面；本包的上游
    用例清点与归因见 notes.md，消费者验证由 ``test_package/`` 承担；
  * 其余后端（x265/aom/dav1d/x264/kvazaar/uvg266/vvdec/vvenc/openjpeg/openjph/ffmpeg/
    openh264/rav1e/svt/jpeg/zlib/brotli/libsharpyuv/未压缩编码）全部显式 OFF：
    不属交付面，且会引入未发布依赖（R36）。

插件目录：上游把默认插件目录**编译期钉死**在 ``heif_version.h`` 的
``LIBHEIF_PLUGIN_DIRECTORY``（= 构建时的 ``${CMAKE_INSTALL_FULL_LIBDIR}/libheif``，
即本包在 Conan 缓存里的绝对路径），跨缓存/跨机不可移植。因此 ``package_info()`` 用
``runenv_info`` 导出 ``LIBHEIF_PLUGIN_PATH``，让 ``VirtualRunEnv``/``conanrun`` 环境
自动带上（上游 ``libheif/plugins_unix.cc`` 优先读该环境变量）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


# 本包交付面之外的上游后端开关：显式 OFF（不属交付面 + 未发布依赖）。
_DISABLED_PLUGIN_OPTIONS = (
    "X265", "X264", "AOM_DECODER", "AOM_ENCODER", "DAV1D", "KVAZAAR", "UVG266",
    "VVDEC", "VVENC", "FFMPEG_DECODER", "OpenH264_DECODER", "RAV1E", "SvtEnc",
    "JPEG_DECODER", "JPEG_ENCODER", "OpenJPEG_DECODER", "OpenJPEG_ENCODER",
    "OPENJPH_ENCODER", "LIBSHARPYUV",
)


class LibheifLibde265Conan(ConanFile):
    name = "libheif-libde265"
    version = "1.23.0"
    description = ("libde265 (HEVC) decoder backend plugin module for libheif 1.23.0, "
                   "built in-tree from libheif/plugins/decoder_libde265.cc as the "
                   "upstream CMake target heif-libde265 (libheif-libde265.so); ships the "
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
        # --build=never 实测可取得）。静态库，链接进插件模块。
        self.requires("libde265/1.0.18")

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

    def _libde265_paths(self):
        """返回 (include_dir, library_path)。

        上游 ``cmake/modules/FindLIBDE265.cmake`` 走
        ``libfind_pkg_check_modules(LIBDE265_PKGCONF libde265)`` + 不带 HINTS 的
        ``find_path``/``find_library``（MODULE 模式，不读 CMakeDeps 的 config）。
        直接把 Conan 依赖的实际路径钉进 cache 变量，既避免命中设备上的系统
        libde265，也不依赖构建环境里 pkg-config 是否可用/是否污染。
        """
        dep = self.dependencies["libde265"]
        include_dir = self._resolve_dir(dep, list(dep.cpp_info.includedirs), "include")
        libdir = self._resolve_dir(dep, list(dep.cpp_info.libdirs), "lib")

        library = None
        for name in dep.cpp_info.libs or ["de265"]:
            for pattern in (f"lib{name}.a", f"lib{name}.so", f"lib{name}.dylib"):
                hits = sorted(glob.glob(os.path.join(libdir, pattern)))
                if hits:
                    library = hits[0]
                    break
            if library:
                break
        if library is None:
            raise ConanInvalidConfiguration(
                f"{self.ref}: 在 {libdir} 未找到 libde265 静态/共享库"
                f"（libs={list(dep.cpp_info.libs)}）")
        return include_dir, library

    # ---------------------------------------------------------------- build
    def generate(self):
        include_dir, library = self._libde265_paths()

        tc = CMakeToolchain(self)
        # R33：全部构建配置经 CMakeToolchain 下发，不依赖 shell 环境变量。
        # 宿主必须是共享库（插件 dlopen 语义；见 validate()）。
        tc.variables["BUILD_SHARED_LIBS"] = True

        # 平台名必须显式钉成 Linux：设备 `uname -s` = HarmonyOS，而 SDK 的 CMake
        # 只有 Platform/OHOS.cmake、**没有** Platform/HarmonyOS.cmake；Conan 默认把
        # os=OHOS 映射成 CMAKE_SYSTEM_NAME=HarmonyOS → CMake 落到「未知平台」通用
        # 回退 → 共享库**既不写 SONAME 也没有版本化文件名**。设备最小探针实测
        # （同一 add_library(SHARED) 工程）：
        #   不覆盖 → 只有 libfoo.so，readelf -d 无 SONAME；
        #   覆盖 Linux → libfoo.so + libfoo.so.1 + libfoo.so.1.2.3，SONAME=libfoo.so.1。
        # 对本包是**致命**的：插件 MODULE 链接宿主时会把相对路径写进 DT_NEEDED
        # （../libheif.so），运行期 heif_init() dlopen 失败 → HEVC 解码器注册不上
        # → test_package/G2 必红。覆盖后编译器与目标仍由 toolchain 决定
        # （仍是 aarch64-linux-ohos 产物）；仓库 693 个配方同口径。
        # Conan 的 GenericSystemBlock 生成的是 `if(NOT DEFINED CMAKE_SYSTEM_NAME)`，
        # 故这里的 cache 变量优先。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # libheif 1.23.0 用 C++20 ranges 算法（libheif/box.cc 的 Box_rref 调
        # std::ranges::all_of/find）。OHOS SDK 的 libc++ 是 15004（clang 15.0.4）：
        # __config 里 `!defined(_LIBCPP_ENABLE_EXPERIMENTAL) && !defined(_LIBCPP_BUILDING_LIBRARY)`
        # 时定义 _LIBCPP_HAS_NO_INCOMPLETE_RANGES，<algorithm> 的 ranges 重载全部
        # 被该宏 gate 掉 → 即使 -std=c++20 也报 "no member named 'all_of' in
        # namespace 'std::ranges'"（设备实测，见 notes.md 第 4 节）。
        # 打开 libc++ 官方开关即可，**不改上游源码、不需要 -lc++experimental**
        # （ranges 算法是 header-only）；公共头 libheif/api/** 0 处 std::ranges，
        # 故不需要向消费者传播该定义。仓内先例：archives/l/libpqxx/8.0.1、
        # archives/l/ladybug/0.18.2。
        if str(self.settings.os) == "OHOS":
            tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None

        # --- 交付面：libde265 后端，且以独立插件模块形态构建 ---
        tc.variables["ENABLE_PLUGIN_LOADING"] = True
        tc.variables["WITH_LIBDE265"] = True
        tc.variables["WITH_LIBDE265_PLUGIN"] = True

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

        # --- FindLIBDE265.cmake 的输入（见 _libde265_paths 注释）---
        tc.cache_variables["LIBDE265_INCLUDE_DIR"] = include_dir
        tc.cache_variables["LIBDE265_LIBRARY"] = library

        # 插件目录：保持上游默认（<prefix>/<libdir>/libheif），不改上游语义。
        tc.generate()

    def _jobs(self):
        """显式限制 make 并发。

        conan 的 ``tools.build:jobs`` 缺省取 ``os.cpu_count()``（本设备 20，而容器
        affinity 只有 8），共享设备上会超订。调用方可用 ``-c tools.build:jobs=N``
        显式覆盖；未给时按 1 路构建。实测 ``make -j20 -j1`` 以**最后一个** ``-j``
        为准（4 个各 sleep 2s 的目标串行 8s），故把该值作为 ``build_tool_args``
        追加在 conan 自己生成的那一个之后。
        """
        conf_jobs = self.conf.get("tools.build:jobs", default=None, check_type=int)
        return conf_jobs if conf_jobs else 1

    def build(self):
        apply_conandata_patches(self)
        jobs = self._jobs()
        cmake = CMake(self)
        cmake.configure()
        # 只构建交付面目标：heif 宿主 + heif-libde265 插件模块。
        # （heifio 等其它目标不被 install()，不属交付面，且会触发 TIFF/JPEG/PNG/WEBP
        #   可选探测，与交付物无关。）
        cmake.build(target=["heif", "heif-libde265"], build_tool_args=[f"-j{jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """给装出的 ELF 重新自签（鸿蒙 PC XPM 要求 dlopen 的 .so 必须有有效代码签名）。

        为什么必须做（本包设备实测）：链接器在**链接期**用设备 clang launcher 给 ELF
        写入代码签名（`readelf -n` 可见 `.note.ohos.ident`）；而 `cmake --install`
        会把构建树 RUNPATH **就地改写**成安装态（本包插件：安装前
        `RUNPATH=<build>/libheif/`、安装后无 RUNPATH，**同尺寸但 sha256 变化**
        `eb04f0f6…` → `abb4b2be…`，`cmp -l` 计 182 字节差异）→ 字节一变签名失效 →
        OHOS 加载器拒绝映射，`dlopen` 报 **Permission denied**（不是 not found）→
        `heif_init()` code=11 → `heif_have_decoder_for_format(HEVC)==0`。

        注意：**宿主 `libheif.so.1.23.0` 安装前后 sha256 完全相同**（它不链接同构建树
        的其它 target，没有构建树 RUNPATH），所以只查宿主会误判"交付物没问题"——
        必须查插件（本包命名产物）。

        处置与同族先例一致（`archives/o/openh264/2.6.0`、`archives/f/ffmpeg/8.1.2`，
        均已合并）：`llvm-objcopy --remove-section .codesign` 清掉失效签名后
        `binary-sign-tool sign -selfSign 1` 重签；只签真实 ELF、跳版本化软链。
        设备实测：重签前 `dlopen` = Permission denied，重签后 = OK 且
        `heif_have_decoder_for_format(HEVC) == 1`（同一文件同一进程）。
        """
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"),
                            recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"),
                             recursive=True)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        signed = 0
        for path in targets:
            if os.path.islink(path) or not self._is_elf(path):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
            signed += 1
        self.output.info(f"re-signed {signed} ELF file(s) with binary-sign-tool (OHOS XPM)")

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
