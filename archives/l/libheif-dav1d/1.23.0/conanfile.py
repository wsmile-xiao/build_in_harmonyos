#!/usr/bin/env python3
"""Conan recipe — libheif 1.23.0 的 AV1 解码插件子包（dav1d 后端）。

交付面（判定依据，非推测）
--------------------------
上游顶层 CMakeLists.txt:217-219 声明
    plugin_option(DAV1D "Dav1d AV1 decoder" OFF ON)
即 WITH_DAV1D 默认 OFF、WITH_DAV1D_PLUGIN 默认 ON；配合默认
ENABLE_PLUGIN_LOADING=ON，libheif/plugins/CMakeLists.txt:56-58 的
    plugin_compilation(dav1d DAV1D DAV1D_FOUND DAV1D DAV1D)
走 PLUGIN_LOADING_SUPPORTED_AND_ENABLED 分支，生成
    add_library(heif-dav1d MODULE ...)   →   libheif-dav1d.so
并 install 到 COMPUTED_PLUGIN_INSTALL_DIRECTORY
（= PLUGIN_DIRECTORY = ${CMAKE_INSTALL_FULL_LIBDIR}/libheif），
该目录同时被 configure 进 heif_version.h 的 LIBHEIF_PLUGIN_DIRECTORY 宏
（libheif/api/libheif/heif_version.h.in:36），由 libheif 运行时 dlopen 扫描。

因此本包交付：
  1) lib/libheif/libheif-dav1d.so —— 本包的主交付物（AV1 解码插件）；
  2) 插件宿主 lib/libheif.so 与 include/libheif/*.h、lib/pkgconfig/libheif.pc。
     （插件是 MODULE，target_link_libraries(... heif)，脱离宿主无法使用；
      上游同一棵树里产出，故同包交付，自包含、无未发布前置依赖。）

依赖边界：dav1d 是外部 Conan 包，不是内树捆绑
--------------------------------------------
上游用 find_package(DAV1D)（cmake/modules/FindDAV1D.cmake），内部是
libfind_pkg_check_modules(DAV1D_PKGCONF dav1d) + find_path(dav1d/dav1d.h) +
find_library(libdav1d dav1d)。树内没有任何 dav1d 源码副本（-iname '*dav1d*'
只命中该 Find 模块与 plugins/decoder_dav1d.cc/.h），故只能来自外部包；
复用仓库既有 archives/d/dav1d/1.5.0。
CMakeToolchain 的 PkgConfigBlock 会把 generators 目录前置进 PKG_CONFIG_PATH，
PkgConfigDeps 生成的 dav1d.pc 因此能被 FindDAV1D.cmake 的 pkg_check_modules 命中。

其余可选后端全部显式 OFF：本包只提供 AV1 解码能力，不做其它编解码器。
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class LibheifDav1dConan(ConanFile):
    name = "libheif-dav1d"
    version = "1.23.0"
    description = ("libheif 1.23.0 with the dav1d AV1 decoder plugin "
                   "(AVIF decoding; all other codecs disabled)")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/strukturag/libheif"
    url = "https://github.com/strukturag/libheif"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        # 本包当前 `conandata.yml` 是 `patches: {}`（零补丁、上游源码零修改），
        # 这两处调用因此是 no-op；保留它们是仓库既有惯例（同族先例
        # archives/l/libheif/1.22.2 在 patches 为空时同样保留），
        # 也让将来真需要加补丁时落点已在正确位置（conan_verify 的 G1
        # 配方完整性门禁同样按此结构检查）。
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # 唯一直接依赖；版本与 archives/d/dav1d/1.5.0 一致（registry binary 实测可取得）。
        self.requires("dav1d/1.5.0")

    def generate(self):
        # FindDAV1D.cmake 走 pkg-config（libfind_pkg_check_modules），
        # 必须生成 dav1d.pc；CMakeToolchain 的 PkgConfigBlock 会自动把
        # generators 目录前置到 PKG_CONFIG_PATH，无需手工注入。
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)

        # --- 设备 uname 是 HarmonyOS，SDK 的 CMake 没有 Platform/HarmonyOS.cmake ---
        # Conan 的 CMakeToolchain 会为 os=OHOS 设 CMAKE_SYSTEM_NAME=HarmonyOS，而该
        # Platform 模块不存在 → CMake 落"未知平台"回退（configure 日志实证：
        # "System is unknown to cmake, create: Platform/HarmonyOS to use this system"）
        # → CMAKE_SHARED_LIBRARY_SONAME_* 不生效 → 宿主不写 SONAME、不出带版本的
        # 文件名（实测包里只有 libheif.so，没有 libheif.so.1.23.0 / libheif.so.1）
        # → 插件 MODULE 链接宿主时把**含斜杠的相对路径**记进 DT_NEEDED
        # （实测 readelf -d lib/libheif/libheif-dav1d.so → NEEDED [../libheif.so]），
        # 而含斜杠的 NEEDED 按 CWD 解析 → heif_init() 的 dlopen 必然失败。
        # 强制走 Platform/Linux.cmake：宿主获得 SONAME libheif.so.1，插件 DT_NEEDED
        # 变成无斜杠的 libheif.so.1（仓库既有 693 个配方同口径，如
        # archives/a/ableton-link/3.1.2 的 E092）。libheif 自身无 CMAKE_SYSTEM_NAME
        # 分支（全树 grep 为空），故不影响其平台探测。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # --- OHOS SDK 的 libc++ 缺省隐藏 C++20 ranges 算法，必须显式放行 ---
        # libheif 顶层 CMakeLists.txt:54 声明 CMAKE_CXX_STANDARD 20（实际编译行确为
        # -std=c++20），而 libheif/box.cc:4155/4156/4166 用了 std::ranges::all_of /
        # std::ranges::find。OHOS SDK 的 libc++ 是 15004：__config 里
        # `#if !defined(_LIBCPP_ENABLE_EXPERIMENTAL) && !defined(_LIBCPP_BUILDING_LIBRARY)`
        # 会定义 _LIBCPP_HAS_NO_INCOMPLETE_RANGES，而 <__algorithm/*.h> 的 ranges 重载
        # 全部 gated 在 `!defined(_LIBCPP_HAS_NO_INCOMPLETE_RANGES)` 上 —— 于是算法
        # **已实现但被隐藏**，报 "no member named 'find'/'all_of' in namespace 'std::ranges'"。
        # 实测探针（设备）：
        #   clang++ -std=c++20 -stdlib=libc++ -c probe.cc          → 上述两条 error
        #   clang++ -std=c++20 -stdlib=libc++ -D_LIBCPP_ENABLE_EXPERIMENTAL -c probe.cc → OK
        # 故用编译期宏放行，不改上游源码、不需要 -lc++experimental、不需要补丁。
        # 不污染消费者：libheif/api/libheif/ 下 0 处 std::ranges/std::views，
        # 该宏只作用于本包自身构建。
        # 同口径已合并先例：archives/l/libpqxx/8.0.1、archives/l/ladybug/0.18.2。
        if str(self.settings.os) == "OHOS":
            tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None

        # --- 本包交付的编解码后端：只开 dav1d AV1 解码，且以独立插件形态 ---
        tc.variables["ENABLE_PLUGIN_LOADING"] = True
        tc.variables["WITH_DAV1D"] = True
        tc.variables["WITH_DAV1D_PLUGIN"] = True

        # --- 其余后端全部显式 OFF（其中 LIBDE265/X265/X264/OpenH264/AOM */
        #     SvtEnc/RAV1E 上游默认 ON，不显式关掉会去探测系统同名库）---
        tc.variables["WITH_LIBDE265"] = False
        tc.variables["WITH_LIBDE265_PLUGIN"] = False
        tc.variables["WITH_X265"] = False
        tc.variables["WITH_X265_PLUGIN"] = False
        tc.variables["WITH_X264"] = False
        tc.variables["WITH_X264_PLUGIN"] = False
        tc.variables["WITH_KVAZAAR"] = False
        tc.variables["WITH_UVG266"] = False
        tc.variables["WITH_VVDEC"] = False
        tc.variables["WITH_VVENC"] = False
        tc.variables["WITH_OpenH264_DECODER"] = False
        tc.variables["WITH_OpenH264_DECODER_PLUGIN"] = False
        tc.variables["WITH_AOM_DECODER"] = False
        tc.variables["WITH_AOM_DECODER_PLUGIN"] = False
        tc.variables["WITH_AOM_ENCODER"] = False
        tc.variables["WITH_AOM_ENCODER_PLUGIN"] = False
        tc.variables["WITH_SvtEnc"] = False
        tc.variables["WITH_SvtEnc_PLUGIN"] = False
        tc.variables["WITH_RAV1E"] = False
        tc.variables["WITH_RAV1E_PLUGIN"] = False
        tc.variables["WITH_JPEG_DECODER"] = False
        tc.variables["WITH_JPEG_DECODER_PLUGIN"] = False
        tc.variables["WITH_JPEG_ENCODER"] = False
        tc.variables["WITH_JPEG_ENCODER_PLUGIN"] = False
        tc.variables["WITH_OpenJPEG_DECODER"] = False
        tc.variables["WITH_OpenJPEG_DECODER_PLUGIN"] = False
        tc.variables["WITH_OpenJPEG_ENCODER"] = False
        tc.variables["WITH_OpenJPEG_ENCODER_PLUGIN"] = False
        tc.variables["WITH_OPENJPH_ENCODER"] = False
        tc.variables["WITH_OPENJPH_ENCODER_PLUGIN"] = False
        tc.variables["WITH_FFMPEG_DECODER"] = False
        tc.variables["WITH_UNCOMPRESSED_CODEC"] = False
        tc.variables["WITH_WEBCODECS"] = False

        # --- 与交付面无关的可选件：一律关掉，保持构建自包含 ---
        tc.variables["WITH_EXAMPLES"] = False
        tc.variables["WITH_GDK_PIXBUF"] = False
        tc.variables["WITH_LIBSHARPYUV"] = False
        tc.variables["WITH_HEADER_COMPRESSION"] = False
        tc.variables["WITH_FUZZERS"] = False
        # 上游测试的驱动方式见 notes.md / reports/：上游 ctest 在独立的
        # BUILD_TESTING=ON 原生构建里跑，不塞进 conan create 的产物构建，
        # 以免把 39 个测试可执行文件混进交付包。
        tc.variables["BUILD_TESTING"] = False
        # WITH_REDUCED_VISIBILITY 保持上游默认 ON（不改与交付面无关的开关）。
        tc.generate()

    def build(self):
        # patches: {} → 本调用不应用任何补丁（保留为仓库标准落点，见 export_sources 注释）。
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # 资源纪律（显式上限，非静默）：tools.build:jobs 未注入时 conan 取
        # os.cpu_count()（本设备 20，而容器 affinity 只有 8，2.5× 超订）；
        # 本包约 110 个源文件，-j20 在共享设备上会撞内存耗尽窗口（长构建被 SIGKILL），
        # 而 -j1 又逼近 conan_verify G2 的硬编码 3600s 超时。取 4 作上限，
        # 调用方显式给了 tools.build:jobs 时尊重但仍不超过 4。
        # 仓库既有 125/200 抽样配方同样在配方内显式限流（如 archives/a/afmize/2.0.2 用 -j1）。
        jobs = self.conf.get("tools.build:jobs", default=0, check_type=int) or 4
        cmake.build(build_tool_args=["-j{}".format(min(jobs, 4))])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_elf()

    def _sign_elf(self):
        """鸿蒙 PC XPM 要求可执行文件与被 dlopen 的 .so 带有效 .codesign 段才能加载。

        libheif 的插件正是运行时 dlopen 的对象，且 cmake install 的复制会破坏
        链接器自签，故装包后重签（与仓库既有 1102 个配方同口径：llvm-objcopy 去旧段
        → binary-sign-tool -selfSign 1）。只签真实 ELF，跳过版本化软链，避免重复签。
        """
        if str(self.settings.os) != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        targets = []
        libdir = os.path.join(self.package_folder, "lib")
        for root, _, files in os.walk(libdir):
            for filename in files:
                path = os.path.join(root, filename)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                if path.endswith(".so") or ".so." in filename:
                    targets.append(path)
        for path in targets:
            subprocess.run([objcopy, "--remove-section", ".codesign", path],
                           capture_output=True, text=True, check=False)
            signed = path + ".signed"
            r = subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed,
                                "-selfSign", "1", "-signAlg", "SHA256withECDSA"],
                               capture_output=True, text=True)
            if r.returncode == 0 and os.path.isfile(signed):
                os.replace(signed, path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["heif"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libheif")
        self.cpp_info.set_property("cmake_target_name", "libheif::libheif")
        self.cpp_info.set_property("pkg_config_name", "libheif")

        # 【必须】把插件目录导出给运行期环境。
        # libheif 的插件搜索顺序（libheif/init.cc:51-66）是：
        #   ① 环境变量 LIBHEIF_PLUGIN_PATH（空则忽略）② 编译期宏 LIBHEIF_PLUGIN_DIRECTORY。
        # ② 的值是 configure 期由 heif_version.h.in 的 @PLUGIN_DIRECTORY@ 烧进去的
        # **构建期绝对路径**：Conan 的 CMakeToolchain 在 configure 前把
        # CMAKE_INSTALL_PREFIX 设成构建期 package_folder（实测
        # `-DCMAKE_INSTALL_PREFIX=.../p/b/<hash>/p`），而 conan create 结束后包会被搬到
        # 最终缓存目录 `.../p/<name><hash>/p`——下载安装的消费者那里更是从来不存在
        # 这个构建目录。所以靠内置宏找不到插件，必须由配方导出 ①。
        # 用 runenv_info（不是 cpp_info）：这是运行期环境变量，不是编译/链接信息，
        # 不会传播给消费者的编译命令。
        self.runenv_info.define_path(
            "LIBHEIF_PLUGIN_PATH",
            os.path.join(self.package_folder, "lib", "libheif"))
