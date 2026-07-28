#!/usr/bin/env python3
"""Conan recipe — opencv 4.12.0 (cmake)"""
from conan import ConanFile
from conan.tools.files import get, download, apply_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.cmake import cmake_layout
from conan.errors import ConanInvalidConfiguration
import os


class OpencvConan(ConanFile):
    name = "opencv"
    version = "4.12.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # OpenCV 自身无鸿蒙支持（platforms/ 无 ohos、全树无 OHOS 分支），适配全靠 SDK ohos.toolchain
    # + 构建参数，不改上游源码。

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # C++ 库：源码不含 C-only 组件，settings 保留 compiler.libcxx/cppstd 参与 package_id。

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._prefetch_ade()

    def _prefetch_ade(self):
        # 把 ADE 预置进 OpenCV 自己的下载缓存，让配置期的 ocv_download 直接命中、零网络。
        # 缓存路径约定见 cmake/OpenCVDownload.cmake：<源码>/.cache/<小写ID>/<md5>-<filename>
        ade = self.conan_data["ade"]
        cache = os.path.join(self.source_folder, ".cache", "ade")
        os.makedirs(cache, exist_ok=True)
        download(self, ade["url"],
                 os.path.join(cache, "%s-%s" % (ade["md5"], ade["filename"])),
                 sha256=ade["sha256"])

    def requirements(self):
        # 制品仓已有的一律走 conan，避免与系统/vendored 副本重复。
        self.requires("zlib/1.3.1.1")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libpng/1.6.58")
        self.requires("libwebp/1.6.0")
        self.requires("openjpeg/2.5.4")
        self.requires("eigen/3.4.0")
        self.requires("ffmpeg/7.1.5")
        # 制品仓暂缺 → 用 OpenCV 自带 3rdparty 静态编入：libtiff、protobuf(dnn 用)。
        # openexr / jasper / jpegxl / avif 直接关闭（见 build() 的 WITH_* ）。

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        # videoio 的 ffmpeg 探测走 ocv_check_modules(FFMPEG libavcodec libavformat libavutil libswscale)
        # → 本质是 pkg_check_modules，须有按 conan 依赖真实路径写的 .pc。
        PkgConfigDeps(self).generate()

    # ------------------------------------------------------------------ 工具

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

    _HNP_BIN = "/data/service/hnp/bin"

    def _tool(self, name):
        """找可用的工具链程序全路径。

        【必需】SDK 的 llvm/bin 里**只有 llvm-ar，没有 llvm-ranlib**，而 ohos.toolchain 会把
        CMAKE_RANLIB 指到那个并不存在的 llvm/bin/llvm-ranlib；cmake 造静态库的规则是
        `<AR> qc <lib> <objs> && <RANLIB> <lib>`，于是 AR 成功、RANLIB 一步报
        `Error running link command: no such file or directory`（libquirc.a / liblibtiff.a /
        liblibprotobuf.a 全挂在这）。hnp bin 下有 llvm-ranlib → llvm-ar 的软链（LLVM 工具按
        argv[0] 改行为），指到它即可。
        """
        import shutil
        cand = os.path.join(self._HNP_BIN, name)
        if os.path.isfile(cand) or os.path.islink(cand):
            return cand
        return shutil.which(name) or ""

    def _dep(self, name):
        return self.dependencies[name].package_folder

    def _dep_lib(self, name, *stems):
        """在依赖包 lib/ 下找库文件，优先 .so 再 .a——制品仓里 zlib 等按 R26 是静态、
        libjpeg/png 等是动态，硬编码后缀会随依赖形态变化而断。"""
        import glob
        libdir = os.path.join(self._dep(name), "lib")
        for stem in stems:
            for pat in ("lib%s.so" % stem, "lib%s.a" % stem):
                hit = sorted(glob.glob(os.path.join(libdir, pat)))
                if hit:
                    return hit[0]
        raise ConanInvalidConfiguration(
            "依赖 %s 的 lib/ 下找不到 %s 的 .so/.a：%s" % (name, "/".join(stems), libdir))

    def _dep_incdir(self, name, *subdirs):
        """取依赖的 include 目录；subdirs 给定时返回第一个真实存在的子目录。"""
        base = os.path.join(self._dep(name), "include")
        for s in subdirs:
            p = os.path.join(base, s)
            if os.path.isdir(p):
                return p
        return base

    # ------------------------------------------------------------------ 构建

    def _configure_defs(self):
        tc = self._ohos_toolchain()
        d = [
            '-DCMAKE_TOOLCHAIN_FILE="%s"' % tc,
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            "-DCMAKE_INSTALL_LIBDIR=lib",      # ohos.toolchain 64 位默认 lib64/，conan 找 lib/
            "-DBUILD_SHARED_LIBS=%s" % ("ON" if self.options.shared else "OFF"),
            "-DCMAKE_CXX_STANDARD=17",         # 与 profile 的 compiler.cppstd=17 对齐（影响 ABI）
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
        ]

        # 归档器：覆盖 ohos.toolchain 指向的、SDK 里并不存在的 llvm-ranlib（见 _tool 注释）
        for _var, _name in (("CMAKE_RANLIB", "llvm-ranlib"), ("CMAKE_AR", "llvm-ar")):
            _p = self._tool(_name)
            if _p:
                d.append('-D%s="%s"' % (_var, _p))

        # ---- 不需要的构建产物（大幅缩短编译时长）----
        d += [
            "-DBUILD_TESTS=OFF", "-DBUILD_PERF_TESTS=OFF", "-DBUILD_EXAMPLES=OFF",
            "-DBUILD_DOCS=OFF", "-DBUILD_opencv_apps=OFF", "-DBUILD_ITT=OFF",
            "-DBUILD_JAVA=OFF", "-DBUILD_opencv_java=OFF",
            "-DBUILD_opencv_python2=OFF", "-DBUILD_opencv_python3=OFF",
            "-DBUILD_opencv_js=OFF", "-DBUILD_opencv_world=OFF",
            "-DINSTALL_C_EXAMPLES=OFF", "-DINSTALL_PYTHON_EXAMPLES=OFF",
            "-DINSTALL_TESTS=OFF", "-DOPENCV_SKIP_PYTHON_LOADER=ON",
            "-DOPENCV_GENERATE_PKGCONFIG=ON",
            # 本包不提供任何命令行工具。setup_vars 脚本是给独立安装前缀用的，装进 conan cache
            # 后里面的路径也无意义；关掉它，bin/ 便完全不存在，与 package_type=library 一致。
            "-DOPENCV_GENERATE_SETUPVARS=OFF",
        ]

        # ---- 目标平台上不存在/不适用的后端 ----
        d += [
            "-DWITH_CUDA=OFF", "-DWITH_CUFFT=OFF", "-DWITH_CUBLAS=OFF", "-DWITH_NVCUVID=OFF",
            "-DWITH_VTK=OFF", "-DWITH_IPP=OFF", "-DWITH_HALIDE=OFF", "-DWITH_OPENVINO=OFF",
            "-DWITH_INF_ENGINE=OFF", "-DWITH_WEBNN=OFF", "-DWITH_VULKAN=OFF",
            # 无 X11/GTK/Qt/Wayland → highgui 为 headless（imshow 不可用，见 notes）
            "-DWITH_GTK=OFF", "-DWITH_QT=OFF", "-DWITH_WAYLAND=OFF", "-DWITH_OPENGL=OFF",
            "-DWITH_FRAMEBUFFER=OFF", "-DWITH_GSTREAMER=OFF",
            "-DWITH_V4L=OFF", "-DWITH_1394=OFF", "-DWITH_LIBREALSENSE=OFF",
            "-DWITH_OPENNI=OFF", "-DWITH_OPENNI2=OFF", "-DWITH_PVAPI=OFF",
            "-DWITH_ARAVIS=OFF", "-DWITH_XIMEA=OFF", "-DWITH_UEYE=OFF", "-DWITH_OBSENSOR=OFF",
            "-DWITH_GDCM=OFF", "-DWITH_GDAL=OFF", "-DWITH_CLP=OFF", "-DWITH_HPX=OFF",
            "-DWITH_OPENMP=OFF", "-DWITH_TBB=OFF", "-DWITH_PTHREADS_PF=ON",
            "-DWITH_CPUFEATURES=OFF",          # Android 专用库
            "-DWITH_FASTCV=OFF", "-DWITH_KLEIDICV=OFF",
            "-DWITH_LAPACK=OFF",               # 制品仓无 lapack；core 自带实现足够
        ]

        # ---- 图像编解码：制品仓已有的走 conan ----
        # 交叉 toolchain 会 set(CMAKE_FIND_ROOT_PATH_MODE_{LIBRARY,INCLUDE} ONLY) 覆盖命令行，
        # find_package/find_library 搜不到 conan 依赖 → 直接预设各 Find 模块的结果缓存变量。
        # 注：OpenCV 的 ocv_clear_internal_cache_vars 只清 TYPE=INTERNAL 的，命令行 -D 建的是
        # UNINITIALIZED，不会被清掉。
        d += [
            "-DWITH_ZLIB=ON", "-DBUILD_ZLIB=OFF", "-DWITH_ZLIB_NG=OFF",
            '-DZLIB_LIBRARY="%s"' % self._dep_lib("zlib", "z"),
            '-DZLIB_INCLUDE_DIR="%s"' % self._dep_incdir("zlib"),

            "-DWITH_JPEG=ON", "-DBUILD_JPEG=OFF",
            '-DJPEG_LIBRARY="%s"' % self._dep_lib("libjpeg-turbo", "jpeg"),
            '-DJPEG_INCLUDE_DIR="%s"' % self._dep_incdir("libjpeg-turbo"),

            "-DWITH_PNG=ON", "-DBUILD_PNG=OFF", "-DWITH_SPNG=OFF",
            '-DPNG_LIBRARY="%s"' % self._dep_lib("libpng", "png16", "png"),
            '-DPNG_PNG_INCLUDE_DIR="%s"' % self._dep_incdir("libpng"),

            "-DWITH_WEBP=ON", "-DBUILD_WEBP=OFF",
            '-DWEBP_LIBRARY="%s"' % self._dep_lib("libwebp", "webp"),
            '-DWEBP_INCLUDE_DIR="%s"' % self._dep_incdir("libwebp"),

            "-DWITH_OPENJPEG=ON", "-DBUILD_OPENJPEG=OFF",
            "-DWITH_JASPER=OFF",               # OpenJPEG 已覆盖 JPEG2000

            "-DWITH_EIGEN=ON",
            '-DEIGEN_INCLUDE_PATH="%s"' % self._dep_incdir("eigen", "eigen3"),
        ]
        _ojp = self._openjpeg_cmake_dir()
        if _ojp:
            d.append('-DOpenJPEG_DIR="%s"' % _ojp)

        # ---- 制品仓暂缺 → 用 OpenCV 自带 3rdparty 静态编入 ----
        d += [
            "-DWITH_TIFF=ON", "-DBUILD_TIFF=ON",           # libtiff 制品仓无
            "-DBUILD_PROTOBUF=ON",                         # dnn 用，OpenCV 自带 3.19.x
            "-DWITH_PROTOBUF=ON",
            "-DWITH_OPENEXR=OFF",                          # 重量级 C++，制品仓无
            "-DWITH_AVIF=OFF", "-DWITH_JPEGXL=OFF",        # 制品仓无 libavif/libjxl
            "-DWITH_QUIRC=ON",                             # QR 解码，自带 quirc
        ]

        # ---- videoio 接 ffmpeg ----
        # OpenCV 顶层 CMakeLists 有一条自己的闸：交叉编译时若环境里没有 PKG_CONFIG_LIBDIR /
        # PKG_CONFIG_SYSROOT_DIR，且没显式 OPENCV_ENABLE_PKG_CONFIG，就**根本不调
        # find_package(PkgConfig)**（"OpenCV disables pkg-config to avoid using of host libraries"），
        # 于是 ocv_check_modules(FFMPEG …) 一次都不跑、FFMPEG 直接判 NO。
        # 只给 PKG_CONFIG_PATH 不满足任何一条豁免——须给 PKG_CONFIG_LIBDIR（见 build()）。
        d += ["-DWITH_FFMPEG=ON", "-DOPENCV_ENABLE_PKG_CONFIG=ON"]

        # 让 find_* 在交叉根路径模式下也能看到 conan 依赖（与上面预设变量互为兜底）
        roots = ";".join(self._dep(n) for n in (
            "zlib", "libjpeg-turbo", "libpng", "libwebp", "openjpeg", "eigen", "ffmpeg"))
        d += ['-DCMAKE_FIND_ROOT_PATH="%s"' % roots, '-DCMAKE_PREFIX_PATH="%s"' % roots]
        return d

    def _openjpeg_cmake_dir(self):
        """openjpeg 的 CONFIG 包目录（lib/cmake/openjpeg-2.x），版本目录名随上游变，故 glob。"""
        import glob
        hits = sorted(glob.glob(os.path.join(self._dep("openjpeg"), "lib", "cmake", "openjpeg-*")))
        return hits[-1] if hits else ""

    def _clean_env(self):
        # 设备 HiShell 的 .zshrc 会全局导出 CFLAGS/LDFLAGS/CMAKE_PREFIX_PATH/PKG_CONFIG_PATH/
        # LD_LIBRARY_PATH，会漏进 cmake（链错库、find_package 捞到 ~/usr/local 的副本）。
        for _v in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS",
                   "PKG_CONFIG_PATH", "PKG_CONFIG_LIBDIR",
                   "CMAKE_PREFIX_PATH", "LD_LIBRARY_PATH"):
            os.environ.pop(_v, None)

    def _overlay_ffmpeg_pc(self):
        """用 ffmpeg 包自带的 .pc 覆盖 conan 生成的同名文件。

        【必需】conan 的 PkgConfigDeps 给每个 .pc 写的 `Version` 是 **conan 包版本**（7.1.5），
        而 OpenCV 的 detect_ffmpeg.cmake 比的是 libav* 的 **ABI 版本**下限
        （libavcodec>=54.35.0、libavformat>=54.20.4、libavutil>=52.3.0、libswscale>=2.1.1）。
        `7.1.5 VERSION_LESS 54.35.0` 成立 → HAVE_FFMPEG 被重新置 FALSE，于是出现
        「四个模块都 YES、FFMPEG 总判却是 NO」这种自相矛盾的摘要。

        ffmpeg 自带的 .pc 里 Version 是真实 ABI 版本（如 libavcodec 61.x），覆盖即解决；
        且真实 .pc 把编解码库放在 Libs.private，非静态模式下 pkg-config 不展开它们，
        ocv_check_modules 便不再对 openh264/vpx/opus 逐个 find_library 而刷警告。
        只改 prefix= 一行指到本机实际包目录（其余行 ffmpeg 配方已重定位成 ${prefix} 相对）。
        """
        import glob
        ffdir = self._dep("ffmpeg")
        src = os.path.join(ffdir, "lib", "pkgconfig")
        if not os.path.isdir(src):
            return
        for pc in sorted(glob.glob(os.path.join(src, "lib*.pc"))):
            with open(pc, encoding="utf-8") as f:
                lines = ["prefix=" + ffdir if ln.startswith("prefix=") else ln
                         for ln in f.read().splitlines()]
            dst = os.path.join(self.generators_folder, os.path.basename(pc))
            with open(dst, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            self.output.info("覆盖 .pc 为 ffmpeg 自带版本（真实 ABI 版本）：%s"
                             % os.path.basename(pc))

    def build(self):
        apply_conandata_patches(self)
        self._clean_env()
        self._overlay_ffmpeg_pc()
        # HMDFS 上默认 TMPDIR 不可写，cmake 的 try_compile 会失败
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        bdir = os.path.join(self.build_folder, "build-ohos")
        jobs = self.conf.get("tools.build:jobs", default=os.cpu_count() or 4, check_type=int)
        # PKG_CONFIG_LIBDIR 一石二鸟：① 满足 OpenCV 解禁 pkg-config 的条件（见 _configure_defs）；
        # ② 它**替换**默认搜索路径（不同于只做前置的 PKG_CONFIG_PATH），把 pkg-config 限定在 conan
        # 生成目录内，杜绝捞到设备 ~/usr/local 下的同名 .pc。
        # 用命令行内联赋值：conan 的 self.run 会套 generate() 阶段的 conanbuild 环境，
        # 只设 os.environ 未必稳（ffmpeg 配方实证）。
        self.run('PKG_CONFIG_LIBDIR="{pc}" PKG_CONFIG_PATH="{pc}" cmake -B "{b}" -S "{s}" {d}'.format(
            pc=self.generators_folder, b=bdir, s=self.source_folder,
            d=" ".join(self._configure_defs())))
        self.run('cmake --build "{b}" -j {j}'.format(b=bdir, j=jobs))

    # ------------------------------------------------------------------ 打包

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "%s" --prefix "%s"' % (bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted（cmake/SDK-toolchain 产的自签无效，且 install 复制会破坏链接器自签）。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    # ------------------------------------------------------------------ 消费

    def package_info(self):
        # OpenCV 头装在 include/opencv4/opencv2/…，而消费方写 #include <opencv2/opencv.hpp>
        # → 必须把 include/opencv4 声明进 includedirs（见 SKILL「包必须设 cpp_info.includedirs」）。
        self.cpp_info.includedirs = ["include/opencv4", "include"]
        # BUILD_SHARED_LIBS=ON 时 3rdparty 静态库（libtiff/protobuf/quirc/ade）全部**内链**进各
        # opencv_*.so，不单独 install，故 lib/opencv4/3rdparty 是空的、不进 libdirs。
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = []      # 不产命令行工具（已关 apps 与 setup_vars）

        # 模块间有链接序依赖，按「上层在前」排（core 最后）。
        self.cpp_info.libs = [
            "opencv_gapi", "opencv_stitching", "opencv_video", "opencv_objdetect",
            "opencv_dnn", "opencv_calib3d", "opencv_features2d", "opencv_flann",
            "opencv_highgui", "opencv_videoio", "opencv_imgcodecs", "opencv_photo",
            "opencv_ml", "opencv_imgproc", "opencv_core",
        ]

        # OpenCV 自带 OpenCVConfig.cmake，定义全部 opencv_* target 并处理内链的 3rdparty 静态库，
        # 比 conan 生成的更完整 → 关掉 conan 的 config 生成，让消费方 find_package(OpenCV) 用上游的。
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", "OpenCV")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake", "opencv4")]
        self.cpp_info.set_property("pkg_config_name", "opencv4")

        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m", "pthread"]
