#!/usr/bin/env python3
"""Conan recipe for libheif-svtenc 1.23.0 — libheif 树内 SVT-AV1 编码后端插件模块。

本包交付面 = 上游 libheif 1.23.0 树内的 CMake 目标 ``heif-svtenc``，其产物
``libheif-svtenc.so`` 是 libheif 的 **SVT-AV1（AV1）编码插件模块**：

    libheif/plugins/CMakeLists.txt
        set(SvtEnc_sources encoder_svt.cc encoder_svt.h)
        plugin_compilation(svtenc SvtEnc SvtEnc_FOUND SvtEnc SvtEnc)
    →  add_library(heif-svtenc MODULE ...)         # 插件装载开启时
        install(TARGETS heif-svtenc LIBRARY DESTINATION <libdir>/libheif)

``svtenc`` 是**上游目标名里就带的子模块名**（``heif-${name}`` → ``heif-svtenc``），
包名按仓库惯例取「交付库的文件名去掉前后缀」= ``libheif-svtenc``（同族先例：
``archives/l/libhwy_test`` ← 树内目标 ``hwy_test`` → ``libhwy_test.a``）。

**SVT-AV1 本体是外部依赖，且制品仓没有它** —— 树内 ``third-party/`` 只有
``svt.cmd``（Windows 辅助脚本），``find . -iname '*svt*'`` 只命中
``cmake/modules/FindSvtEnc.cmake`` 与 ``libheif/plugins/encoder_svt.{cc,h}``；
上游用 ``find_package(SvtEnc)`` 找外部库。而 W0 实测（真实 ``conan install
--build=never`` / ``conan download --only-recipe``，非 ``conan list/search``）表明
``svt-av1`` 在 ohpcd 制品仓**任何版本都不存在**，``archives/s/svt-av1/4.1.0/`` 与
``archives/l/libSvtAv1Enc/3.1.2/`` 都只是元数据孤儿（只有 manifest/notes/patch，
没有 ``conanfile.py``）。逐条读数见 notes.md「W0 依赖判定」。

因此本包**不声明任何 Conan 依赖**，改为在包内树构建官方 SVT-AV1 v3.1.2：
理由与先例——R36 是机械门禁（``finish`` step[5/10] 与 CI L0i 都对 ``requires()``
逐条跑 ``conan download --only-recipe``），声明一个不存在的依赖必然 HANDOFF/红 CI；
而「内树构建所需的编码器、因此没有 Conan 包依赖」在本仓库有**已合并先例**：
``archives/h/handbrake/1.11.2/conanfile.py`` 明写
"All 33 contribs (ffmpeg/x264/x265/libvpx/libass/dav1d/svt-av1/...) are built in-tree
by HandBrake's own build system, so there are no Conan package dependencies
(R36: nothing to publish beforehand)."

交付面（自包含，因为插件模块无法脱离宿主运行）：

  * ``lib/libheif/libheif-svtenc.so``（+ VERSION/SOVERSION 软链）—— 本包命名产物，
    由树内 ``encoder_svt.cc`` 编译，链接内树构建的 ``libSvtAv1Enc.so``；
  * ``lib/libSvtAv1Enc.so*`` —— 内树构建的 SVT-AV1 编码器运行时（插件 DT_NEEDED）；
  * 宿主 ``lib/libheif.so``（同源同版本、``ENABLE_PLUGIN_LOADING=ON``）—— 插件以
    ``target_link_libraries(heif-svtenc PRIVATE ... heif)`` 依赖它，且运行期必须由它
    ``dlopen`` 插件才能注册 AV1 编码器；仓库既有 ``archives/l/libheif/1.22.2`` 是
    ``ENABLE_PLUGIN_LOADING=OFF`` 的 codec-free 核心，**装不了插件**，故不能作为本包的
    依赖（跨版本插件 ABI 也不匹配）；
  * ``include/libheif/*.h``、``lib/pkgconfig/libheif.pc``、``lib/cmake/libheif/*``。

上游构建开关说明（R1：参数最少化，只开交付面必需的）：

  * ``ENABLE_PLUGIN_LOADING=ON`` + ``WITH_SvtEnc=ON`` + ``WITH_SvtEnc_PLUGIN=ON``：
    三者共同构成本包交付面（缺一则不产生 ``heif-svtenc`` 目标，改为静态编入宿主）；
  * ``BUILD_TESTING=OFF``：上游测试目标不被 ``install()``，不属交付面；本包的上游
    用例清点与归因见 notes.md，消费者验证由 ``test_package/`` 承担；
  * 其余后端（libde265/x265/aom/dav1d/x264/kvazaar/uvg266/vvdec/vvenc/ffmpeg/
    openh264/rav1e/jpeg/openjpeg/openjph/zlib/brotli/libsharpyuv/未压缩编码）全部显式
    OFF：不属交付面，且会引入未发布依赖（R36）。

插件目录：上游把默认插件目录**编译期钉死**在 ``heif_version.h`` 的
``LIBHEIF_PLUGIN_DIRECTORY``（= 构建时的 ``${CMAKE_INSTALL_FULL_LIBDIR}/libheif``，
即本包在 Conan 缓存里的绝对路径），跨缓存/跨机不可移植。因此 ``package_info()`` 用
``runenv_info`` 导出 ``LIBHEIF_PLUGIN_PATH``，让 ``VirtualRunEnv``/``conanrun`` 环境
自动带上（上游 ``libheif/plugins_unix.cc:37`` 优先读该环境变量；头文件
``heif_library.h:182`` 注释里的复数 ``LIBHEIF_PLUGIN_PATHS`` 是过期文档）。
"""
import glob
import hashlib
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# 内树构建的 SVT-AV1 源码目录名（== source() 里 get() 的落点 == 补丁的 base_path）。
_SVT_DIR = "svt-av1"

# 本包交付面之外的上游后端开关：显式 OFF（不属交付面 + 未发布依赖）。
_DISABLED_PLUGIN_OPTIONS = (
    "LIBDE265", "X265", "X264", "AOM_DECODER", "AOM_ENCODER", "DAV1D", "KVAZAAR",
    "UVG266", "VVDEC", "VVENC", "FFMPEG_DECODER", "OpenH264_DECODER", "RAV1E",
    "JPEG_DECODER", "JPEG_ENCODER", "OpenJPEG_DECODER", "OpenJPEG_ENCODER",
    "OPENJPH_ENCODER", "LIBSHARPYUV",
)


class LibheifSvtencConan(ConanFile):
    name = "libheif-svtenc"
    version = "1.23.0"
    description = ("SVT-AV1 (AV1) encoder backend plugin module for libheif 1.23.0, built "
                   "in-tree from libheif/plugins/encoder_svt.cc as the upstream CMake target "
                   "heif-svtenc (libheif-svtenc.so); the SVT-AV1 encoder itself is also built "
                   "in-tree (official v3.1.2 source) because no Conan package for it is "
                   "published; ships the plugin-loading-enabled libheif host it requires")
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
        # 零 Conan 依赖：SVT-AV1 本体由本包内树构建（官方 v3.1.2 源码 + OHOS 补丁）。
        # 为什么不能写成 self.requires("svt-av1/4.1.0")：该 ref 在 ohpcd 制品仓不存在，
        # R36 机械门禁（finish step[5/10] / CI L0i 的 conan download --only-recipe）
        # 必然 HANDOFF；逐条证据见 notes.md「W0 依赖判定」与 w0-deps.txt。
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
        # 1) 父 tarball：libheif 1.23.0（交付面源码）
        get(self, **self.conan_data["sources"], strip_root=True)

        # 2) 内树构建的 SVT-AV1 v3.1.2（官方源，url 列表含官方 GitHub 镜像回退）
        get(self,
            destination=os.path.join(self.source_folder, _SVT_DIR),
            strip_root=True,
            **self.conan_data["svt_av1"])

        # 3) OHOS 补丁：作用于 SVT-AV1 子目录（base_path=svt-av1），不动父 tarball 一行
        apply_conandata_patches(self)

    # ---------------------------------------------------------------- helpers
    def _svt_prefix(self):
        """SVT-AV1 的私有安装前缀（R49：只用 build_folder 下的私有 prefix）。"""
        return os.path.join(self.build_folder, "svt-av1-prefix")

    def _svt_include_dir(self):
        return os.path.join(self._svt_prefix(), "include")

    def _svt_library(self):
        return os.path.join(self._svt_prefix(), "lib", "libSvtAv1Enc.so")

    # ------------------------------------------------- 共享库 install 自证与装后重签
    @staticmethod
    def _sha256(path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    def _real_so_map(self, root, recursive=False):
        """{basename: sha256} —— 只看真实文件，跳软链（.so → .so.1 → .so.1.23.0）。"""
        pattern = os.path.join(root, "**", "*.so*") if recursive else os.path.join(root, "*.so*")
        out = {}
        for path in sorted(glob.glob(pattern, recursive=recursive)):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            out[os.path.basename(path)] = self._sha256(path)
        return out

    def _report_install_rewrites(self, before_plugin, before_host):
        """安装前后 sha256 自证：install 就地改写 RUNPATH 会让字节变（同尺寸）。

        写进构建日志是为了让"是否被改写"在每一轮都有原始读数，而不是靠事后回忆。
        命中时 package() 末尾的 _sign_ohos_elf() 会把签名重新打上。
        """
        after_plugin = self._real_so_map(os.path.join(self.package_folder, "lib", "libheif"), True)
        after_host = self._real_so_map(os.path.join(self.package_folder, "lib"))
        for label, before, after in (("plugin", before_plugin, after_plugin),
                                     ("host", before_host, after_host)):
            for name, sha_before in sorted(before.items()):
                sha_after = after.get(name)
                if sha_after is None:
                    self.output.info(f"[install-sha256] {label} {name}: 仅构建树有")
                elif sha_after == sha_before:
                    self.output.info(f"[install-sha256] {label} {name}: 安装前后一致 {sha_before}")
                else:
                    self.output.warning(
                        f"[install-sha256] {label} {name}: 安装**就地改写** "
                        f"{sha_before} → {sha_after}（ELF 签名将被 _sign_ohos_elf() 重打）")

    def _sign_ohos_elf(self):
        """装后重签：OHOS 上 install 就地改写 RUNPATH 会破坏 clang launcher 写的
        `.note.ohos.ident` 签名，运行期 dlopen 报 `Permission denied`（EACCES，**不是**
        找不到文件）→ 宿主 heif_init() 失败、插件永远注册不上（构建期全绿）。
        已合并先例：archives/o/openh264/2.6.0、archives/f/ffmpeg/8.1.2。
        只签真实 ELF，跳过版本化 .so 的软链（否则对同一目标重复签）。
        """
        if str(self.settings.os) != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        targets = []
        for pattern in ("*.so", "*.so.*"):
            targets += glob.glob(os.path.join(self.package_folder, "lib", "**", pattern), recursive=True)
        signed = []
        for path in sorted(set(targets)):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
            signed.append(path)
            self.output.info(f"[codesign] re-signed {path} sha256={self._sha256(path)}")
        if not signed:
            raise ConanInvalidConfiguration(
                f"{self.ref}: 包内没有可重签的 ELF 共享库（{self.package_folder}/lib/**/*.so*）")

    def _build_svt_av1(self):
        """内树构建 SVT-AV1 并安装到私有 prefix。

        R33：编译器等构建配置全部来自 profile——这里复用 CMakeToolchain 生成的
        ``conan_toolchain.cmake``（与父项目同一份），不读 shell 的 CC/CFLAGS。
        BUILD_APPS=OFF：不构建 SvtAv1EncApp（本包不交付可执行文件，故无 R38 commands.json）。
        SVT_AV1_LTO=OFF：静态/共享链接都不依赖 LTO 插件，避免交叉工具链的
        llvm-ar/LTO 链路风险（设备与 CI worker 都是 clang+lld）。
        """
        src = os.path.join(self.source_folder, _SVT_DIR)
        build = os.path.join(self.build_folder, "svt-av1-build")
        prefix = self._svt_prefix()
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        jobs = self.conf.get("tools.build:jobs", default=1)

        self.run(" ".join([
            "cmake",
            f'-S "{src}"',
            f'-B "{build}"',
            f'-DCMAKE_TOOLCHAIN_FILE="{toolchain}"',
            f'-DCMAKE_INSTALL_PREFIX="{prefix}"',
            '-DCMAKE_BUILD_TYPE=Release',
            # 子工程也要走 Linux 平台分支：否则 CMAKE_SHARED_LIBRARY_SONAME_* 未定义，
            # libSvtAv1Enc.so 不带 SONAME，插件 DT_NEEDED 会写成构建期路径（运行期必失败）。
            # toolchain 里已经有一份（generate() 的 tc.variables），这里再显式传一遍兜底。
            "-DCMAKE_SYSTEM_NAME=Linux",
            # 同因：子工程的 install 也不能就地改写 RPATH（否则 ELF 签名失效 → dlopen EACCES）。
            # 本包的 SVT-AV1 只链系统库、通常无构建树 RPATH，但两处口径保持一致更稳。
            "-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON",
            "-DCMAKE_INSTALL_RPATH=",
            "-DBUILD_SHARED_LIBS=ON",
            "-DBUILD_APPS=OFF",
            "-DBUILD_TESTING=OFF",
            "-DSVT_AV1_LTO=OFF",
        ]))
        self.run(f'cmake --build "{build}" --target install -j {jobs}')

    # ---------------------------------------------------------------- build
    def generate(self):
        # 先把 SVT-AV1 的私有 prefix 路径钉进 FindSvtEnc.cmake 的 cache 变量。
        # 上游 FindSvtEnc.cmake 是 MODULE 模式（pkg-config + 无 HINTS 的
        # find_path/find_library），不认 CMakeDeps 生成的 config；直接钉路径既避免
        # 命中设备上的系统 libSvtAv1Enc，也不依赖 pkg-config 是否可用/是否被污染。
        tc = CMakeToolchain(self)
        tc.cache_variables["SvtEnc_INCLUDE_DIR"] = self._svt_include_dir()
        tc.cache_variables["SvtEnc_LIBRARY"] = self._svt_library()

        if str(self.settings.os) == "OHOS":
            # OHOS 的 clang 同时定义 __linux__ 与 __OHOS__，Linux-only 分支会被选中；
            # 设备 libc++（实测 _LIBCPP_VERSION 15004）在未定义
            # _LIBCPP_ENABLE_EXPERIMENTAL 时会定义 _LIBCPP_HAS_NO_INCOMPLETE_RANGES，
            # 把 std::ranges::all_of/find 从 <algorithm> 里隐藏；而上游 libheif 用
            # CMAKE_CXX_STANDARD 20 且 box.cc:4155/4156/4166 直接调用这两个算法 →
            # 必然编译失败（'no member named all_of in namespace std::ranges'）。
            # 这是编译期宏，无需链接 -lc++experimental；libheif 公共头 0 处 std::ranges，
            # 故不需要向消费者传播（先例：archives/l/libpqxx/8.0.1、archives/l/ladybug/0.18.2）。
            tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None

            # 设备 `uname -s` 报 HarmonyOS，而 SDK 的 CMake 只有 Platform/OHOS.cmake、
            # 没有 Platform/HarmonyOS.cmake → 落到「未知平台」回退，于是
            # CMAKE_SHARED_LIBRARY_SONAME_* 未定义：宿主 libheif.so **不带 SONAME**
            # （连版本化文件名都没有），插件 MODULE 链接时会把构建期路径写进 DT_NEEDED
            # （带斜杠 → 按 CWD 解析）→ 运行期宿主 dlopen 插件必失败（实测
            # readelf -d 内树库无 SONAME 行）。显式走 Linux 平台分支（仓库 693 个配方同口径）。
            # 用 variables 而非 cache_variables：这样它落进 conan_toolchain.cmake，
            # 内树构建的 SVT-AV1 子工程复用同一份 toolchain 时也一并生效（_build_svt_av1()
            # 另外还显式传了一遍 -DCMAKE_SYSTEM_NAME，两处都不落下）。
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # RPATH 与 install 就地改写：clang launcher 在链接期给 ELF 写 .note.ohos.ident
        # 签名；CMake 默认 BUILD_WITH_INSTALL_RPATH=OFF，于是 install 阶段会把插件里
        # 的构建树 RPATH 改写成安装 RPATH —— **同尺寸但字节变**（sha256 变）⇒ 签名失效
        # ⇒ 运行期宿主 dlopen 报 `Permission denied`（EACCES，不是 not found），
        # test_package/G2 必红。命中判据：只要链了**同一构建树内的 target**（本包的
        # 插件链树内宿主 heif）就会被打上构建树 RPATH。处置：让构建期直接用安装 RPATH
        # 且置空 —— 从源头不触发改写（宿主/内树库安装前后 sha256 应完全相同，见 notes）。
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["CMAKE_INSTALL_RPATH"] = ""

        # R33：全部构建配置经 CMakeToolchain 下发，不依赖 shell 环境变量。
        # 宿主必须是共享库（插件 dlopen 语义；见 validate()）。
        tc.variables["BUILD_SHARED_LIBS"] = True

        # --- 交付面：SVT-AV1 编码后端，且以独立插件模块形态构建 ---
        tc.variables["ENABLE_PLUGIN_LOADING"] = True
        tc.variables["WITH_SvtEnc"] = True
        tc.variables["WITH_SvtEnc_PLUGIN"] = True

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

        # 插件目录：保持上游默认（<prefix>/<libdir>/libheif），不改上游语义。
        tc.generate()

    def build(self):
        # 1) 内树构建内嵌依赖（SVT-AV1 → 私有 prefix）
        self._build_svt_av1()

        # 2) 只构建交付面目标：heif 宿主 + heif-svtenc 插件模块。
        #   （heifio 等其它目标不被 install()，不属交付面，且会触发 TIFF/JPEG/PNG/WEBP
        #    可选探测，与交付物无关。）
        cmake = CMake(self)
        cmake.configure()
        # 自限并发：设备 os.cpu_count()=20 而 sched_getaffinity=8，且**经工具**（conan_verify /
        # finish）的 create 没有 jobs 旋钮（工具不注入 tools.build:jobs）⇒ CMake 助手会按
        # cpu_count 追加 -j20。这里在 conan 的 -j 之后再追加一个 -j<jobs>（make 取最后一个生效），
        # 使"配方自限"在工具驱动路径下同样成立（同批 libde265 已验证该手法：合成夹具 8s 串行 +
        # 进程表逐字 + 37min 全量）。
        jobs = self.conf.get("tools.build:jobs", default=1)
        cmake.build(target=["heif", "heif-svtenc"], build_tool_args=[f"-j{jobs}"])

    def package(self):
        # 安装前先记构建树 sha256（用于安装前后自证，见 _report_install_rewrites）
        before_plugin = self._real_so_map(
            os.path.join(self.build_folder, "libheif", "plugins"), recursive=True)
        before_host = self._real_so_map(os.path.join(self.build_folder, "libheif"))

        cmake = CMake(self)
        cmake.install()

        # 内树构建的 SVT-AV1 运行时装进本包 libdir：插件 DT_NEEDED 它，
        # VirtualRunEnv/conanrun 会把本包 libdir 加进 LD_LIBRARY_PATH。
        # 逐个按类型搬运以保留 SONAME 软链结构（libSvtAv1Enc.so → .so.3 → .so.3.1.2），
        # 避免同一份 5MB 库被复制三遍。
        svt_libdir = os.path.join(self._svt_prefix(), "lib")
        if not os.path.isdir(svt_libdir):
            raise ConanInvalidConfiguration(
                f"{self.ref}: 内树构建的 SVT-AV1 库目录缺失：{svt_libdir}")
        dst_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(dst_dir, exist_ok=True)
        copied = []
        for name in sorted(os.listdir(svt_libdir)):
            if not name.startswith("libSvtAv1Enc.so"):
                continue
            src = os.path.join(svt_libdir, name)
            dst = os.path.join(dst_dir, name)
            if os.path.islink(src):
                if os.path.lexists(dst):
                    os.remove(dst)
                os.symlink(os.readlink(src), dst)
            else:
                shutil.copy2(src, dst)
            copied.append(name)
        if not copied:
            raise ConanInvalidConfiguration(
                f"{self.ref}: {svt_libdir} 下没有 libSvtAv1Enc.so*，内树构建未产出编码器运行时")
        self.output.info(f"packaged SVT-AV1 runtime: {', '.join(copied)}")

        # 安装前后 sha256 自证（写进日志），再对包内所有真实 ELF 共享库装后重签
        self._report_install_rewrites(before_plugin, before_host)
        self._sign_ohos_elf()

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
