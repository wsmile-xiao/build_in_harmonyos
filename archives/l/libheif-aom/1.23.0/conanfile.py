#!/usr/bin/env python3
"""Conan recipe for libheif-aom 1.23.0 — libheif 树内 aom（AV1）编解码后端插件模块。

交付面 = 上游 libheif 1.23.0 树内的**两个** CMake MODULE 目标（aom 的编解码是分开的）：

    libheif/plugins/CMakeLists.txt
        set(AOM_DECODER_sources decoder_aom.cc decoder_aom.h)
        plugin_compilation(aomdec AOM AOM_DECODER_FOUND AOM_DECODER AOM_DECODER)
        set(AOM_ENCODER_sources encoder_aom.cc encoder_aom.h)
        plugin_compilation(aomenc AOM AOM_ENCODER_FOUND AOM_ENCODER AOM_ENCODER)
    →  add_library(heif-aomdec MODULE …) / add_library(heif-aomenc MODULE …)
        install(TARGETS heif-aomdec LIBRARY DESTINATION <libdir>/libheif)

产物：``lib/libheif/libheif-aomdec.so``（AV1 解码插件）与
``lib/libheif/libheif-aomenc.so``（AV1 编码插件）。包名取任务卡/分支名门禁要求的
``libheif-aom``（L0n：分支名去前缀 == 包目录名-版本），是这两个同族插件的合并交付单元；
上游目标名里 aom 的后缀是 ``dec``/``enc``（同类先例：heif-jpegdec/heif-jpegenc）。

上游开关说明（R1：参数最少化，只开交付面必需的）：

  * ``ENABLE_PLUGIN_LOADING=ON`` + ``WITH_AOM_DECODER=ON`` + ``WITH_AOM_ENCODER=ON``
    + ``WITH_AOM_DECODER_PLUGIN=ON`` + ``WITH_AOM_ENCODER_PLUGIN=ON``：aom 的
    ``*_PLUGIN`` 默认值是 **OFF**（与 dav1d/svt/openjpeg 默认 ON 相反），即上游默认把
    aom 静态编入宿主；要拿到独立插件模块必须显式打开这五个开关，缺一即不产生
    ``heif-aomdec``/``heif-aomenc`` 目标；
  * ``BUILD_TESTING=OFF``：上游测试目标不被 ``install()``，不属交付面；上游用例清点与
    逐项归因见 notes.md，消费者验证由 ``test_package/`` 承担；
  * 其余后端（libde265/x265/x264/dav1d/kvazaar/uvg266/vvdec/vvenc/openjpeg/openjph/
    ffmpeg/openh264/rav1e/svt/jpeg/libsharpyuv/未压缩编码）全部显式 OFF：不属交付面。

aom 本体（内树自包含，非 Conan 依赖）——见 conandata.yml 的判定依据与 handbrake 先例：

  * ``source()`` 取官方 libaom 3.9.1 源码到 ``aom/`` 子目录；
  * ``build()`` 先用本配方的 CMake toolchain 编出**静态** ``libaom.a``（PIC，
    ``AOM_TARGET_CPU=generic`` 关汇编——与 archives/a/aom/3.9.1 的设备实测一致），
    再用 cache 变量 ``AOM_INCLUDE_DIR``/``AOM_LIBRARY`` 钉住上游
    ``FindAOM.cmake`` 的探测结果（它是 MODULE 模式：pkg-config + 无 HINTS 的
    find_path/find_library，不认 CMakeDeps 的 config）；
  * aom 静态链进两个插件模块，**不**单独安装其头文件/静态库（它不是本包的交付面，
    也不冒充一个已发布的 aom 包）；因此 ``requirements()`` 为空（R36：没有需要事先
    发布的依赖）。

宿主 libheif（``libheif.so``）随包交付：插件以 ``target_link_libraries(heif-aomdec
PRIVATE aom heif)`` 依赖它，且运行期必须由宿主 ``dlopen`` 才能注册后端；仓库既有
``archives/l/libheif/1.22.2`` 是 ``ENABLE_PLUGIN_LOADING=OFF`` 的 codec-free 核心，
**装不了插件**，故不能作为本包的依赖（跨版本插件 ABI 也不匹配）。

插件目录：上游把默认插件目录**编译期钉死**在 ``heif_version.h`` 的
``LIBHEIF_PLUGIN_DIRECTORY``（= 构建时的 ``${CMAKE_INSTALL_FULL_LIBDIR}/libheif``，
即本包在 Conan 缓存里的绝对路径），跨缓存/跨机不可移植。因此 ``package_info()`` 用
``runenv_info`` 导出 ``LIBHEIF_PLUGIN_PATH``，让 ``VirtualRunEnv``/``conanrun`` 环境
自动带上（上游 ``libheif/plugins_unix.cc`` 优先读该环境变量）。

构建并发：``tools.build:jobs`` 配置存在时按其值，缺省 **1**。理由是本工作区为共享设备
（多任务并行、conan 取 ``os.cpu_count()``=20 而容器 affinity 只有 8），未限制的
``cmake --build`` 会拿 20 路并行放大内存峰值；``conan create`` 由 CI/工具直接调用，
不会替我们传 ``-c tools.build:jobs=1``，所以默认值必须落在配方里。
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


# 本包交付面之外的上游后端开关：显式 OFF（不属交付面）。
_DISABLED_PLUGIN_OPTIONS = (
    "LIBDE265", "X265", "X264", "DAV1D", "KVAZAAR", "UVG266", "VVDEC", "VVENC",
    "FFMPEG_DECODER", "OpenH264_DECODER", "RAV1E", "SvtEnc", "JPEG_DECODER",
    "JPEG_ENCODER", "OpenJPEG_DECODER", "OpenJPEG_ENCODER", "OPENJPH_ENCODER",
    "LIBSHARPYUV",
)

# libaom 侧构建参数（上游 CMake 选项，非平台补丁）：
#   AOM_TARGET_CPU=generic —— 关掉 ARM 汇编（设备上 aom 汇编路径不可用，
#                             archives/a/aom/3.9.1/notes.md 实测结论）；
#   CONFIG_PIC=1           —— 静态库必须带 -fPIC 才能链进 MODULE 插件。
_AOM_CMAKE_ARGS = (
    "-DAOM_TARGET_CPU=generic",
    "-DCONFIG_AV1_ENCODER=1",
    "-DCONFIG_AV1_DECODER=1",
    "-DENABLE_TESTS=0",
    "-DENABLE_EXAMPLES=0",
    "-DENABLE_TOOLS=0",
    "-DENABLE_DOCS=0",
    "-DBUILD_SHARED_LIBS=0",
    "-DCONFIG_PIC=1",
)


class LibheifAomConan(ConanFile):
    name = "libheif-aom"
    version = "1.23.0"
    description = ("aom (AV1) decoder+encoder backend plugin modules for libheif 1.23.0, "
                   "built in-tree from libheif/plugins/{decoder,encoder}_aom.cc as the "
                   "upstream CMake targets heif-aomdec/heif-aomenc "
                   "(libheif-aomdec.so, libheif-aomenc.so); vendors the official libaom "
                   "3.9.1 source in-recipe (no aom Conan package exists) and ships the "
                   "plugin-loading-enabled libheif host the plugins require")
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
        # 无 Conan 依赖：aom 本体按 handbrake/1.11.2 先例内树自包含构建
        # （仓库与 ohpcd 都没有 aom 配方），宿主 libheif 同源同包交付。
        # R36：没有需要事先发布的依赖。
        pass

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
        get(self, url=self.conan_data["aom"]["url"], sha256=self.conan_data["aom"]["sha256"],
            destination="aom", strip_root=True)

    # ---------------------------------------------------------------- helpers
    def _aom_prefix(self):
        # R49：内树依赖装进 build_folder 私有 prefix（不碰共享 /usr/local）。
        return os.path.join(self.build_folder, "aom-prefix")

    def _jobs(self):
        """构建并发上限。

        共享设备口径（notes/device-facts.md §一.7）：conan 取 ``os.cpu_count()``（本设备
        20）而容器 affinity 只有 8，**不限制就会 2.5× 超订**；该条给出的安全区间是
        ``tools.build:jobs=2..4``。本包内树自包含 aom，构建量比一般包大（实测 -j2：
        aom 5.5 min + 宿主 18 min），因此默认取区间下界 2，既避免超订，也让
        ``conan_verify`` 的 3600s create 预算留有余量。调用方显式给
        ``tools.build:jobs`` 时一律按调用方的值。
        """
        return self.conf.get("tools.build:jobs", default=2, check_type=int)

    def _build_aom(self):
        """把官方 libaom 源码编成静态库并装进 build_folder 私有 prefix。

        用本配方的 conan_toolchain.cmake（编译器/目标平台/编译标志全部来自
        profile conf，R33：不依赖未定义的 shell 环境变量），因此内树 aom 与宿主
        libheif 用同一套工具链与 sysroot。

        注意：``tc.cache_variables`` 只写进 ``generators/CMakePresets.json``（Conan 的
        ``CMake.__init__`` 从那里取 cacheVariables 再以 ``-D`` 传给**主工程**），
        ``conan_toolchain.cmake`` 里并没有它。本子构建只用 toolchain 文件、不走 preset，
        所以 ``CMAKE_SYSTEM_NAME`` 必须在这里**显式再传一次**（与主工程口径一致，
        同时消掉 aom 配置期上百行 ``System is unknown to cmake`` 噪声）。
        """
        src = os.path.join(self.source_folder, "aom")
        build = os.path.join(self.build_folder, "aom-build")
        prefix = self._aom_prefix()
        jobs = self._jobs()

        self.run(f'cmake -S "{src}" -B "{build}" -G "Unix Makefiles" '
                 f'-DCMAKE_TOOLCHAIN_FILE="{os.path.join(self.generators_folder, "conan_toolchain.cmake")}" '
                 f'-DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=Linux '
                 + " ".join(_AOM_CMAKE_ARGS))
        # 显式 -j：Conan 的 CMake.build() 会按 os.cpu_count()(=20) 传 -j20，
        # 与本配方的共享设备口径冲突，故 aom 与宿主都走显式命令行。
        self.run(f'cmake --build "{build}" -j{jobs}')
        self.run(f'cmake --install "{build}" --prefix "{prefix}"')
        if not os.path.isfile(os.path.join(prefix, "lib", "libaom.a")):
            # 这是**构建失败**（子构建没产出交付面输入），不是配置无效：用 ConanException，
            # 不用 ConanInvalidConfiguration（后者语义是"该配置组合不受支持"）。
            raise ConanException(
                f"{self.ref}: 内树 libaom.a 未生成于 {prefix}/lib —— 内树 codec 构建失败，"
                f"不能继续编宿主/插件（否则会交付一个没有 aom 后端的空壳包）")

    # ---------------------------------------------------------------- build
    def generate(self):
        tc = CMakeToolchain(self)
        # R33：全部构建配置经 CMakeToolchain 下发。宿主必须是共享库（插件 dlopen 语义）。
        tc.variables["BUILD_SHARED_LIBS"] = True

        # --- 交付面：aom 后端，且以独立插件模块形态构建 ---
        tc.variables["ENABLE_PLUGIN_LOADING"] = True
        tc.variables["WITH_AOM_DECODER"] = True
        tc.variables["WITH_AOM_ENCODER"] = True
        tc.variables["WITH_AOM_DECODER_PLUGIN"] = True
        tc.variables["WITH_AOM_ENCODER_PLUGIN"] = True

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

        # --- 安装期不得改写 ELF：**OHOS 上这是交付物可用性的硬条件** ---
        # 设备侧 clang launcher 在链接期给 ELF 写入 `.note.ohos.ident` 代码签名；
        # 而 CMake 默认（BUILD_WITH_INSTALL_RPATH=OFF）会在 `cmake --install` 时
        # **就地改写 RUNPATH**（把构建树 RUNPATH 清成安装 RUNPATH），改写后文件字节变了、
        # 签名失效，OHOS 加载器随即拒绝映射：`dlopen: … Permission denied`（本任务实测：
        # 安装前后 sha256 由 921d231f… 变 d5f87929…、RUNPATH 由 1 条变 0 条；同一份**未安装**
        # 的插件 `dlopen → OK`）。宿主也走同一条 install 路径，只因为它本来就无需改写才幸免。
        # 处置：让构建树直接用"安装 RPATH"（这里取空，不烘任何绝对路径），CMake 便不再改写，
        # 安装前后逐字节一致。运行期由 conanrun 的 LD_LIBRARY_PATH 提供 libheif.so.1 的搜索路径。
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["CMAKE_INSTALL_RPATH"] = ""

        # --- CMake 平台名：**不是可选的美化项，缺它交付物直接不可用** ---
        # 设备 uname -s == "HarmonyOS"，而 SDK 的 CMake 只有 Platform/OHOS.cmake
        # （内容就是 include(Platform/Linux)），**没有** Platform/HarmonyOS.cmake。
        # 不指定 CMAKE_SYSTEM_NAME 时 CMake 落到"未知平台"通用回退，后果是
        # **共享库既不写 SONAME、也不产生带版本的文件名**（本任务实测：
        #  build/libheif/libheif.so 只有这一个文件、readelf -d 无 SONAME；
        #  可用性探针见 notes.md）。宿主没有 SONAME 时，链接插件（MODULE）会把
        # **相对路径**写进 DT_NEEDED —— 实测插件里是 `NEEDED ../libheif.so`，
        # 该条目含斜杠，加载器按**当前工作目录**解析，安装后
        # `heif_init()` 直接失败：`dlopen: Error loading shared library ../libheif.so`。
        # 钉成 Linux（走 Platform/Linux.cmake，仓库内 693 个配方同口径；设备侧
        # aom 归档 notes 亦为同一 workaround）后宿主得到 SONAME `libheif.so.1`，
        # 插件 DT_NEEDED 变成无斜杠的 `libheif.so.1`，由 conanrun 的
        # LD_LIBRARY_PATH（cpp_info.libdirs）正常解析。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # --- FindAOM.cmake 的输入（见 _build_aom 注释）---
        aom_prefix = self._aom_prefix()
        tc.cache_variables["AOM_INCLUDE_DIR"] = os.path.join(aom_prefix, "include")
        tc.cache_variables["AOM_LIBRARY"] = os.path.join(aom_prefix, "lib", "libaom.a")

        # --- OHOS 平台必需：设备 libc++ (15.0.4) 在未定义该宏时通过
        #     _LIBCPP_HAS_NO_INCOMPLETE_RANGES 隐藏 std::ranges::all_of/find，
        #     而上游 libheif/box.cc 用到它们（编译期硬失败）。只加宏，不改上游源码。
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None

        # 插件目录：保持上游默认（<prefix>/<libdir>/libheif），不改上游语义。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._build_aom()

        cmake = CMake(self)
        cmake.configure()
        # 显式 -j（理由见 _build_aom）；只构建交付面目标：
        # heif 宿主 + 两个 aom 插件模块。找不到 AOM 时这两个目标不存在，
        # 构建会直接失败——这正是我们要的：不允许交付一个空壳包。
        self.run(f'cmake --build "{self.build_folder}" '
                 f'--target heif heif-aomdec heif-aomenc -j{self._jobs()}')

    def package(self):
        cmake = CMake(self)
        cmake.install()

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
