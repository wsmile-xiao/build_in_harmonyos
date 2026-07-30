#!/usr/bin/env python3
"""Conan recipe — freeimage 3.18.0 (Makefile)"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class FreeimageConan(ConanFile):
    name = "freeimage"
    version = "3.18.0"
    description = (
        "Open Source library for popular graphics image formats (PNG, BMP, JPEG, "
        "TIFF, WebP, JPEG2000, JPEG-XR, OpenEXR, RAW and 20+ more), with all "
        "codecs bundled in-tree"
    )
    license = "FreeImage-1.0 OR GPL-2.0-or-later OR GPL-3.0-or-later"
    homepage = "https://freeimage.sourceforge.io/"
    topics = ("image", "codec", "png", "jpeg", "tiff", "webp", "raw")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _HNP_BIN = "/data/service/hnp/bin"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 无外部依赖：LibPNG / LibJPEG / LibTIFF4 / LibOpenJPEG / LibWebP / LibJXR /
        # LibRawLite / OpenEXR / ZLib 九个编解码器全在上游 Source/ 内自带并一同编译。
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---- 上游构建系统是手写 Makefile（无 CMakeLists / configure / meson.build），
    #      故不用 CMakeToolchain / AutotoolsToolchain，直接驱动 make。 ----
    @property
    def _cc(self):
        return self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", os.path.join(self._HNP_BIN, "clang"))

    @property
    def _cxx(self):
        return self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("cpp", os.path.join(self._HNP_BIN, "clang++"))

    @property
    def _ar(self):
        # 上游用 $(AR)（非硬编码 ar），命令行可覆盖；OHOS 无 GNU ar，用 hnp 的 llvm-ar。
        # ⚠ 不要写成 self.conf.get("tools.gnu:ar", default=None)：`tools.gnu:ar` **不是** Conan
        #   注册过的 conf（2.29.1 实测），`conf.get` 对未注册键会直接抛
        #   ConanException: [conf] 'tools.gnu:ar' does not exist in configuration list，
        #   连 default 都不返回。同 jbigkit 的做法，直接用 hnp 路径。
        return os.path.join(self._HNP_BIN, "llvm-ar")

    def build(self):
        # CFLAGS/CXXFLAGS 上游是 `?=`（Makefile.gnu:18/26），命令行传入即整体覆盖，
        # 故必须自己带全上游默认值 + 自带 codec 需要的宏（Makefile.gnu:20-28）：
        #   -fPIC                      静态库也要，方能被共享消费者链接
        #   -fexceptions               上游默认
        #   -fvisibility=hidden        上游默认；FreeImage 用 DLL_API 显式导出
        #   -DOPJ_STATIC               自带 OpenJPEG
        #   -DNO_LCMS                  自带 LibRaw（不接 lcms2）
        #   -DDISABLE_PERF_MEASUREMENT -D__ANSI__   自带 LibJXR
        base = "-O3 -fPIC -fexceptions -fvisibility=hidden"

        # -DNDEBUG：settings.build_type=Release 的语义要求，而上游 Makefile.gnu 不带它，
        # 本 recipe 又没有 toolchain generator 替我们加 → 不补就会构出「带 assert 的 Release」。
        # 实测后果：跑上游自带 TestAPI 套件时，读 exif.jxr 触发
        # `Assertion failed: FALSE (PluginJXR.cpp: ReadPropVariant: 493)` 直接 abort。
        # 那行是 switch 的 default 分支（上游注释 "This case is not handled"，某种 JXR EXIF
        # 变体类型上游没处理），是**平台无关**的上游既有缺口；Release 下 assert 本应编译掉。
        if self.settings.build_type == "Release":
            base += " -DNDEBUG"

        # aarch64 专属缺陷修正：-DPNG_ARM_NEON_OPT=0
        #   FreeImage 自带的 LibPNG **裁掉了 Source/LibPNG/arm/ 整个目录**（NEON 实现），
        #   Makefile.srcs 的 SRCS 里自然也没有它；而 libpng 的 pngpriv.h 在 __aarch64__ 上
        #   **默认把 PNG_ARM_NEON_OPT 置 2**（启用 NEON）→ pngrutil.c 引用
        #   png_init_filter_functions_neon，而该函数的实现文件不存在。
        #   x86 上永不触发，所以上游从未发现。实测后果：libfreeimage.so 自身能链出来
        #   （链接 .so 默认容忍未定义符号），但消费方**直接链接**时
        #   `ld.lld: error: undefined reference due to --no-allow-shlib-undefined:
        #    png_init_filter_functions_neon` —— 即这是真实缺陷，不是测试写法问题。
        #   代价：PNG 解码不走 NEON 加速（纯性能，功能不变）。
        base += " -DPNG_ARM_NEON_OPT=0"

        # 显式 -std=c++17：CI/设备 profile 都声明 compiler.cppstd=17，而本 recipe 直接驱动
        # make、**没有任何 toolchain generator 注入 -std=**，clang 15 会退到默认 gnu++14
        #（设备实测 __cplusplus=201402）。那样构出来的二进制与 package_id 声明的 cppstd=17
        # 名实不符，故显式补上——补上之后，下面三个逃生旗标才真正被需要（否则不触发）。
        # FreeImage 3.18.0 是 2018 年代码，自带 OpenEXR/LibRawLite 用了 C++17 移除的东西。
        # clang 15 + -std=c++17 实测三者都是 **error**，且都可用旗标关掉，**无需改一行源码**：
        #   register 关键字（55 个文件）   → error [-Wregister]               → -Wno-register
        #   throw(...) 动态异常规范        → error [-Wdynamic-exception-spec] → -Wno-dynamic-exception-spec
        #       命中 Source/OpenEXR/Imath/{ImathVec.h, ImathMatrix.h}
        #   std::auto_ptr（3 个源文件）    → error: no member named 'auto_ptr'
        #       → -D_LIBCPP_ENABLE_CXX17_REMOVED_AUTO_PTR（libc++ 文档化的逃生开关）
        #       命中 Source/LibRawLite/libraw/libraw_datastream.h、
        #            Source/LibRawLite/src/libraw_datastream.cpp、Source/FreeImage/MultiPage.cpp
        # 取旗标而非 patch：两个 -Wno- 只是把「ISO 不允许」降级，逃生宏是上游支持的用法；
        # 改 500+ 行老代码风险远大于收益，且不引入需长期维护的补丁。
        cxx17_escapes = (
            "-std=c++17 -Wno-register -Wno-dynamic-exception-spec "
            "-D_LIBCPP_ENABLE_CXX17_REMOVED_AUTO_PTR"
        )

        # ⚠ CFLAGS/CXXFLAGS 必须走**环境变量**，不能写成 make 的命令行赋值。
        #   GNU make 的命令行赋值会**压掉 makefile 里对同名变量的一切赋值，含 `+=` 追加**；
        #   而上游 Makefile.gnu:25/29 正是用 `CFLAGS += $(INCLUDE)` 把那一长串
        #   `-I. -ISource -ISource/LibJPEG -ISource/OpenEXR/...`（Makefile.srcs:6，共 20 余项）
        #   追加进去的。实测传命令行 CFLAGS → 整个 INCLUDE 被废 →
        #   `fatal error: 'FreeImage.h' file not found`，531 个源文件全挂。
        #   改走 env：上游 `CFLAGS ?= ...` 见环境已定义即跳过（我们的值生效），
        #   随后 `+=` 的 codec 宏（-DOPJ_STATIC/-DNO_LCMS/-DDISABLE_PERF_MEASUREMENT/-D__ANSI__）
        #   与 $(INCLUDE) 照常追加，两边都要的效果同时拿到。
        env_prefix = 'CFLAGS="{}" CXXFLAGS="{} -Wno-ctor-dtor-privacy {}"'.format(
            base, base, cxx17_escapes
        )
        # 这三个仍走命令行：makefile 对它们无 `+=` 追加，且 LIBRARIES 在 makefile 里是
        # 硬 `=` 赋值（Makefile.gnu:14 `LIBRARIES = -lstdc++`），只有命令行才压得住。
        args = [
            "-C", '"{}"'.format(self.source_folder),
            "-f", "Makefile.gnu",
            'CC="{}"'.format(self._cc),
            'CXX="{}"'.format(self._cxx),
            'AR="{}"'.format(self._ar),
            # 显式给 libc++。上游是 `LIBRARIES = -lstdc++`（Makefile.gnu:14）；
            # 设备实测 -lstdc++ 与 -lc++ **都能链接成功**（clang 把前者当别名），
            # 故这不是必需修正，只是让 OHOS/libc++ 工具链下的意图更明确。
            'LIBRARIES="-lc++"',
        ]
        make = os.path.join(self._HNP_BIN, "make")
        self.run("{} {} {} -j{}".format(
            env_prefix, make, " ".join(args), os.cpu_count() or 4))
        self._run_upstream_tests(cxx17_escapes)

    def _run_upstream_tests(self, cxx17_escapes):
        # 跑**上游自带**的 TestAPI 套件（13 个 .cpp，MainTestSuite.cpp 里 38 次断言调用：
        # AllocateCloneUnload / ImageType / ImageTypeTIFF / MemIO(png + jxr) / MultiPage /
        # StreamMultiPage / MultiPageMemory / JPEG / ImageChannels / HeaderOnly /
        # SupportsNoPixels×25 / ExifRaw / Thumbnail / WrappedBuffer / CreateView）。
        # 上游 TestAPI/Makefile 写死 `g++ -I../Dist/ *.cpp ../Dist/libfreeimage.a`，
        # OHOS 上要三处调整，故照其编译行用 clang++ 复现而不直接 make：
        #   ① g++ → clang++；② 同 CXXFLAGS 的 C++17 逃生旗标；
        #   ③ -Wl,--allow-multiple-definition —— 静态库里含构建工具 b44ExpLogTable 的 main，
        #      静态链接会撞符号（上游既有问题，见本目录 notes.md 预编译包一节）。
        # 数据文件（exif.jpg / exif.jxr / sample.png）按相对路径读，故 cwd 必须是 TestAPI。
        testdir = os.path.join(self.source_folder, "TestAPI")
        if not os.path.isfile(os.path.join(testdir, "MainTestSuite.cpp")):
            self.output.warning("上游 TestAPI 套件不存在，跳过")
            return
        self.run(
            '"{cxx}" {esc} -I../Dist/ *.cpp ../Dist/libfreeimage.a -o testAPI '
            "-Wl,--allow-multiple-definition".format(cxx=self._cxx, esc=cxx17_escapes),
            cwd=testdir,
        )
        self.run("./testAPI", cwd=testdir)

    def package(self):
        # 不用上游 `make install`：它写死 `install -m 644 -o root -g root` 装到 /usr/lib
        #（Makefile.gnu:73-79），非 root 必失败、路径也不对。改手工拷。
        src = self.source_folder
        copy(self, "FreeImage.h", src=os.path.join(src, "Source"),
             dst=os.path.join(self.package_folder, "include"))
        libdir = os.path.join(self.package_folder, "lib")
        copy(self, "*.a", src=src, dst=libdir, keep_path=False)
        copy(self, "*.so", src=src, dst=libdir, keep_path=False)
        for lic in ("license-fi.txt", "license-gplv2.txt", "license-gplv3.txt"):
            copy(self, lic, src=src, dst=os.path.join(self.package_folder, "licenses"))
        if self.options.get_safe("shared", True):
            self._link_soname_chain(libdir)
            self._sign_shared_libs()

    def _link_soname_chain(self, libdir):
        # 上游产物名 libfreeimage-3.18.0.so，SONAME 却是 libfreeimage.so.3
        #（Makefile.gnu:38 SHAREDLIB / :40 VERLIBNAME），两者都不是 `-lfreeimage` 要找的
        # libfreeimage.so。补齐 libfreeimage.so → libfreeimage.so.3 → libfreeimage-3.18.0.so：
        # 缺 .so 则消费方链不上；缺 .so.3 则运行期按 SONAME 解析失败。
        real = "libfreeimage-3.18.0.so"
        if not os.path.exists(os.path.join(libdir, real)):
            raise ConanException("未找到共享库产物 {}（构建失败？）".format(real))
        for link in ("libfreeimage.so.3", "libfreeimage.so"):
            path = os.path.join(libdir, link)
            if os.path.lexists(path):
                os.remove(path)
            os.symlink(real, path)

    def _sign_shared_libs(self):
        # 鸿蒙 PC 对 dlopen 的 .so 校验代码签名。本库共享库的链接行带 **`-s`**
        #（Makefile.gnu:70 `$(CC) -s -shared ...`）—— 链接期 strip 会把链接器自签的
        # .codesign 段一并剥掉，故必须显式重签，否则设备 dlopen 报 Permission denied。
        import glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = os.path.join(self._HNP_BIN, "llvm-objcopy")
        signer = os.path.join(self._HNP_BIN, "binary-sign-tool")
        for so in sos:
            if os.path.islink(so):
                continue  # 只签真实 ELF，跳过软链
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=so))
            self.run('{sg} display-sign -inFile "{f}"'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["freeimage"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "freeimage")
        self.cpp_info.set_property("cmake_target_name", "freeimage::freeimage")
        self.cpp_info.set_property("pkg_config_name", "freeimage")
        if self.settings.os in ("Linux", "OHOS"):
            # C++ 实现（对外是 C ABI）：消费方链接期仍需 C++ 运行时
            self.cpp_info.system_libs = ["c++", "m"]
