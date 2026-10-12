#!/usr/bin/env python3
"""Conan recipe — juce 8.0.5 (CMake INTERFACE modules + juceaide build tool).

JUCE 8 的官方分发形态：23 个模块均为 INTERFACE 目标（模块源码由消费方目标编
译），官方 install 产出 JUCEConfig.cmake + JUCEConfigVersion.cmake
（DESTINATION lib/cmake/JUCE-8.0.5）与构建期原生工具 juceaide /
juce_lv2_helper / juce_vst3_helper（bin/JUCE-8.0.5）。因此本配方走官方
configure/build/install 全流程：configure 期 juceaide 由上游自带引导流程
（juceaide/CMakeLists 的递归 CMake）原生构建，install 期以 IMPORTED
juce::juceaide 形式写入包内 config——消费方 find_package(JUCE) 后无需再嵌套
构建任何原生工具。

OHOS 适配（全部为最小 diff，源内联于 source()，JUCE 源为 CRLF，一律单行锚点）：
  1. CMake 平台分支（JUCEModuleSupport.cmake）：HarmonyOS 并入 Linux 族——
     架构探测 / _linux 源选择 / LINUX=1 / linuxPackages·linuxLibs 元数据链接
     四处分支解锁，保证未设 CMAKE_SYSTEM_NAME=Linux 的消费方也能正常
     find_package(JUCE)；配方与 test_package 仍按 ableton-link E092 先例强制
     CMAKE_SYSTEM_NAME=Linux（双保险）。
  2. juce_gui_basics.h 补 linuxPackages 元数据：NOLINK x11（核心 X11 头）。
     上游 Linux 依赖 /usr/include 的 X11 头；conan 环境无系统头，故声明
     pkg-config 模块。NOLINK 只取 Cflags——JUCE X11 家族运行期全部 dlopen
     精确 soname，链接期零符号引用，不产生 DT_NEEDED（E505 加载器语义）。
     X11 扩展 XRANDR/XINERAMA/XSHM/XCURSOR 包级默认关 0（OHOS 无 X server，
     核心几何回退路径足够；并规避 libxrender 源码重建被 OHOS uname 打挂
     config.guess 与 xorgproto 2024.1/2025.1 图内冲突）。
  3. musl/OHOS libc 缺失面：
     - juce_core.h JUCE_USE_CURL 默认 1→0（上游 juceaide 与 UnitTestRunner
       均以 JUCE_USE_CURL=0 构建，juce_Network_linux.cpp 存在完整非 curl
       路径；避免把 libcurl 强加给全部消费方）。
     - juce_SystemStats_linux.cpp 的 glibc _NL_ADDRESS_LANG_AB /
       _NL_ADDRESS_COUNTRY_AB2 langinfo 宏在 OHOS musl langinfo.h 中不存
       在，加 __OHOS__ 分支返回空串。
     - juce_Threads_linux.cpp Thread::killThread 的 pthread_cancel 在 OHOS
       musl 不可用，注释为 no-op（同 adlplug 1.0.2 先例）。
  4. 字体链运行期（E505）：freetype/fontconfig/libxml2 取已发布共享库；
     juceaide 经 juce_graphics 真链接它们，而 OHOS musl 加载器无法经版本化
     符号链接别名解析 .so——generate() 把这三个 .so 以真实文件实体化进包内
     lib-juceaide-runtime/，逐个经 binary-sign-tool selfSign 签名（OHOS
     安全策略：用户存储 .so 未签名 dlopen 即 EACCES），并改写生成的
     freetype2.pc/fontconfig.pc 的 Libs 行注入 DT_RPATH（--disable-new-dtags，
     绝对路径 + $ORIGIN 相对路径），juceaide 在配方构建期与消费方 configure
     期均可直接运行。消费方二进制
     同样链接字体链 .so，需按同一 E505 范式实体化+嵌 rpath（test_package
     内置示范）。

上游测试：无 CTest；自带 UnitTest 框架（extras/UnitTestRunner，JUCE 8.0.5
真机执行 24 类目 / 1086 个 beginTest 组、142 个执行用例类；GUI 44 组与
Audio 系类目全部通过，仅余偏差为 NamedPipe 7 组 HMDFS mkfifo EPERM 与
Files/Writing 1 组超时），由 rule4 流程在设备上真实构建运行并按通过/环境
受限分类记录（见 test_package/MANIFEST.yml 与 builder 报告），不在
conan create 内重复执行。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, load, replace_in_file, save
from conan.tools.gnu import PkgConfigDeps


class JuceConan(ConanFile):
    name = "juce"
    version = "8.0.5"
    description = "JUCE C++ application framework: audio, GUI, graphics, networking modules."
    # modules 双许可 AGPLv3 / JUCE 8 商业 EULA（tag 树 LICENSE.md）；此处登记
    # FOSS 侧，examples 为 ISC、内嵌第三方见 manifest.yaml。
    license = "AGPL-3.0-or-later"
    homepage = "https://juce.com"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # 注意：包内 bin/JUCE-8.0.5/{juceaide,juce_lv2_helper,juce_vst3_helper} 是
    # 官方 install 布局的构建期工具（消费方经 IMPORTED target 调用），不是
    # 面向用户的 CLI 软件，故不声明 cpp_info.bindirs / commands.json（R38）。
    settings = "os", "arch", "compiler", "build_type"

    # 依赖全部取已发布默认（shared）：freetype/fontconfig/libxml2 走 ohpcd
    # 已发布共享库（fontconfig 2.18.3 的 meson 上游要求 >=1.11，本机系统
    # meson 1.5.1 无法静态重建，发布二进制为 worker 产物）。其运行期加载
    # 按 E505 处理：generate() 为 juceaide 实体化 runtime 视图并嵌 DT_RPATH，
    # 消费方按同一范式处理（见 test_package 与 notes.md）。
    default_options = {}

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "juce/8.0.5 OHOS adaptation currently targets os=OHOS arch=armv8 only"
            )

    def requirements(self):
        # 版本选型与仓内已发布图谱一致（全部 ohpcd 已发布）：
        #  - X11：OHOS 无 X server，X11 扩展（XRANDR/XINERAMA/XSHM/XCURSOR）
        #    包级默认关 0（见 source() 补丁），仅保留核心 libx11 头（NOLINK，
        #    运行期 JUCE 全 dlopen，不产生 DT_NEEDED）。不引 libxext/libxrandr/
        #    libxinerama/libxcursor——它们的传递依赖 libxrender/0.9.12 在本机
        #    无二进制可复用，源码重建被 OHOS uname 打挂 config.guess（且其
        #    recipe 钉 xorgproto/2024.1 与 6.4.0 轨 2025.1 图内冲突）。
        #  - juce_graphics linuxPackages = freetype2 fontconfig；freetype/2.14.3
        #    与 fontconfig/2.18.3 配方自身的 pin 一致。
        #  - juce_audio_devices linuxPackages = alsa（alsa-lib asound 组件）。
        #  - juce_opengl linuxPackages = gl（mesa 产物；test_package 不编译
        #    juce_opengl，仅供 rule4 UnitTestRunner / 下游使用）。
        self.requires("freetype/2.14.3")
        self.requires("fontconfig/2.18.3")
        self.requires("alsa-lib/1.2.16.1")
        self.requires("mesa/24.3.4.1.1")
        self.requires("libx11/6.4.0")
        # X11 协议头（X11/Xatom.h / X11/Xmd.h / X11/keysym.h）由 xorgproto
        # 提供——libx11/6.4.0 包内只含 libX11 自身构建的头（clxclient/3.9.0
        # 同款先例）。钉住与 libx11 相同的 2025.1，避免 2024.1/2025.1 图内
        # 版本冲突。
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # ── 1. CMake 平台分支：HarmonyOS 并入 Linux 族（最小 diff、单行锚点） ──
        ms = os.path.join("extras", "Build", "CMake", "JUCEModuleSupport.cmake")
        # 1a. 目标架构探测（VST3 bundle 命名 / 模块内置库路径）
        replace_in_file(
            self, ms,
            '   OR (CMAKE_SYSTEM_NAME STREQUAL "Linux")',
            '   OR (CMAKE_SYSTEM_NAME STREQUAL "Linux")\r\n'
            '   OR (CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")')
        # 1b. _linux/_windows/... 源文件后缀过滤正则：保留 *_linux 源
        replace_in_file(
            self, ms,
            '"linux\\;Linux|.*BSD"',
            '"linux\\;Linux|.*BSD|HarmonyOS"')
        # 1c. LINUX=1 编译定义分支
        replace_in_file(
            self, ms,
            '    if((CMAKE_SYSTEM_NAME STREQUAL "Linux") OR (CMAKE_SYSTEM_NAME MATCHES ".*BSD"))',
            '    if((CMAKE_SYSTEM_NAME STREQUAL "Linux") OR '
            '(CMAKE_SYSTEM_NAME MATCHES ".*BSD|HarmonyOS"))')
        # 1d. linuxPackages/linuxLibs 元数据链接分支（模块内置库路径分支
        # libs/Linux/<arch> 一并解锁，对本包所用模块无副作用）
        replace_in_file(
            self, ms,
            '    elseif((CMAKE_SYSTEM_NAME STREQUAL "Linux") OR (CMAKE_SYSTEM_NAME MATCHES ".*BSD"))',
            '    elseif((CMAKE_SYSTEM_NAME STREQUAL "Linux") OR '
            '(CMAKE_SYSTEM_NAME MATCHES ".*BSD|HarmonyOS"))')

        # ── 2. juce_gui_basics.h：X11 头经 pkg-config 提供（NOLINK：只取
        #    Cflags 不取 Libs，避免 DT_NEEDED；运行期 JUCE 全 dlopen）；X11
        #    扩展（XRANDR/XINERAMA/XSHM/XCURSOR）包级默认关 0——OHOS 无 X
        #    server，核心 X11 几何回退路径足够，同时甩掉 libxrender 重建墙。 ──
        gui_basics = os.path.join("modules", "juce_gui_basics", "juce_gui_basics.h")
        replace_in_file(
            self, gui_basics,
            "  dependencies:       juce_graphics juce_data_structures",
            "  dependencies:       juce_graphics juce_data_structures\r\n"
            "  linuxPackages:      NOLINK x11 xproto")
        for flag in ("JUCE_USE_XRANDR", "JUCE_USE_XINERAMA",
                     "JUCE_USE_XSHM", "JUCE_USE_XCURSOR"):
            replace_in_file(
                self, gui_basics,
                " #define {} 1".format(flag),
                " #define {} 0".format(flag))

        # ── 3a. JUCE_USE_CURL 包级默认 0（上游原生工具同款配置） ──
        replace_in_file(
            self, os.path.join("modules", "juce_core", "juce_core.h"),
            " #define JUCE_USE_CURL 1",
            " #define JUCE_USE_CURL 0")
        # ── 3b. glibc 专有 langinfo 宏（juce_SystemStats_linux.cpp 编入
        #    juce_core，OHOS musl langinfo.h 无 _NL_ADDRESS_*） ──
        sysstats = os.path.join("modules", "juce_core", "native",
                                "juce_SystemStats_linux.cpp")
        replace_in_file(
            self, sysstats,
            "    return getLocaleValue (_NL_ADDRESS_LANG_AB);",
            "   #if defined(__OHOS__)\r\n"
            "    return {};  // OHOS musl langinfo.h lacks glibc _NL_ADDRESS_*\r\n"
            "   #else\r\n"
            "    return getLocaleValue (_NL_ADDRESS_LANG_AB);\r\n"
            "   #endif")
        replace_in_file(
            self, sysstats,
            "    return getLocaleValue (_NL_ADDRESS_COUNTRY_AB2);",
            "   #if defined(__OHOS__)\r\n"
            "    return {};  // OHOS musl langinfo.h lacks glibc _NL_ADDRESS_*\r\n"
            "   #else\r\n"
            "    return getLocaleValue (_NL_ADDRESS_COUNTRY_AB2);\r\n"
            "   #endif")
        # ── 3c. pthread_cancel 在 OHOS musl 不可用（adlplug 1.0.2 同款先例）。
        #    killThread 变 no-op：线程取消语义本就不安全，musl 无此接口。
        #    单行锚点替换，保持 if 体为合法表达式语句（CRLF 安全）。 ──
        replace_in_file(
            self, os.path.join("modules", "juce_core", "native",
                               "juce_Threads_linux.cpp"),
            "        pthread_cancel ((pthread_t) threadHandle.load());",
            "        (void) threadHandle;  // pthread_cancel unavailable in "
            "OHOS musl (killThread is best-effort)")

        # ── 3d. JUCE_WEB_BROWSER 包级默认 0：webkit2gtk 全仓无配方，且本仓
        #    gtk/3.24.43 为 broadway-only（经验仓 lablgtk3-3.1.5 编译错证据） ──
        replace_in_file(
            self, os.path.join("modules", "juce_gui_extra", "juce_gui_extra.h"),
            " #define JUCE_WEB_BROWSER 1",
            " #define JUCE_WEB_BROWSER 0")

    def generate(self):
        # 为全部依赖（含传递）生成 .pc：juce_add_module 的 linuxPackages
        # 分支（juceaide 引导构建、消费方 configure 均会触发）按 pkg-config
        # 名解析（x11/xext/xrandr/xinerama/xcursor/freetype2/fontconfig/alsa/gl，
        # 各依赖配方已声明对应 pkg_config_name）。
        PkgConfigDeps(self).generate()
        # E468 先例：PKG_CONFIG_PATH 指向 generators folder，经 conanbuild
        # 环境对 CMake configure 生效（juceaide 递归构建亦继承该环境）。
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)
        # xorgproto 自带真实 .pc（share/pkgconfig，${pcfiledir} 相对前缀）；
        # 其包未声明 pkg_config_name，PkgConfigDeps 不会代生成，这里把其
        # pc 目录并入 PKG_CONFIG_PATH 供 linuxPackages 的 xproto 解析。
        try:
            _xp_pc = os.path.join(self.dependencies["xorgproto"].package_folder,
                                  "share", "pkgconfig")
            if os.path.isdir(_xp_pc):
                self.buildenv_info.append_path("PKG_CONFIG_PATH", _xp_pc)
        except KeyError:
            pass
        # E505：OHOS musl 加载器无法经版本化符号链接别名解析 .so。juceaide
        # （构建期工具）经 juce_graphics 真链接 freetype2/fontconfig，为其把
        # 字体链 .so 实体化进包内，并把 DT_RPATH 注入 .pc Libs（绝对路径 +
        # $ORIGIN 相对路径双保险，包内自洽、跨机可用）。
        view = self._materialise_fontchain_runtime_view()
        self._append_rpath_to_pc(("freetype2.pc", "fontconfig.pc"), view)
        self._patch_juceaide_libcxx(
            os.path.join(self.source_folder, "extras", "Build", "juceaide",
                         "CMakeLists.txt"))
        tc = CMakeToolchain(self)
        # E092 先例：CMake 无 HarmonyOS 平台模块，强制上游 Linux 分支
        # （linuxPackages/linuxLibs 元数据链接与 *_linux 源选择）。
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_INSTALL_PREFIX"] = self.package_folder
        tc.generate()

    _FONT_CHAIN_PACKAGES = ("freetype", "fontconfig", "libxml2")
    _RUNTIME_VIEW_DIRNAME = "lib-juceaide-runtime"

    def _materialise_fontchain_runtime_view(self):
        """把字体链共享库按 E505 实体化视图复制为真实文件（每个别名名一份），
        并逐个自签名（OHOS 安全策略：用户存储上的 .so 必须经 binary-sign-tool
        签名才允许 dlopen/mmap PROT_EXEC，否则 EACCES；经验仓 mlton-20241230
        binary-sign-tool 流程先例）。"""
        view = os.path.join(self.package_folder, self._RUNTIME_VIEW_DIRNAME)
        os.makedirs(view, exist_ok=True)
        for name in self._FONT_CHAIN_PACKAGES:
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isdir(libdir):
                    continue
                for fn in os.listdir(libdir):
                    if ".so" not in fn:
                        continue
                    src = os.path.join(libdir, fn)
                    if not os.path.isfile(src):
                        continue
                    dst = os.path.join(view, fn)
                    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                        fdst.write(fsrc.read())
                    self._sign_elf(dst)
        return view

    def _sign_elf(self, path):
        """OHOS ELF 自签名（binary-sign-tool selfSign），签名产物固定 640，
        需恢复执行位（mlton/alsa-lib/bam 先例）。"""
        signer = self._find_tool("binary-sign-tool",
                                 ("/storage/Users/currentUser/usr/local/bin",
                                  "/data/service/hnp/bin"))
        objcopy = self._find_tool("llvm-objcopy", ("/data/service/hnp/bin",))
        clean, signed = path + ".clean", path + ".signed"
        subprocess.run([objcopy, "--remove-section", ".codesign", path, clean],
                       check=True)
        subprocess.run([signer, "sign", "-inFile", clean, "-outFile", signed,
                        "-selfSign", "1"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.chmod(signed, 0o750)
        os.replace(signed, path)
        if os.path.exists(clean):
            os.remove(clean)

    @staticmethod
    def _find_tool(name, extra_dirs):
        found = shutil.which(name)
        if found:
            return found
        for d in extra_dirs:
            candidate = os.path.join(d, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanInvalidConfiguration(
            "juce/8.0.5 requires '{}' for OHOS ELF self-signing; "
            "not found in PATH or {}".format(name, ", ".join(extra_dirs)))

    def _append_rpath_to_pc(self, pc_names, view):
        """向生成的 .pc 的 Libs 行追加 DT_RPATH（--disable-new-dtags），
        使 pkg_check_modules 链接的构建期工具（juceaide）可运行。
        $ORIGIN 相对 juceaide 安装位置 bin/JUCE-<v>/ 回溯两级到包前缀。"""
        origin_flag = "-Wl,-rpath,$ORIGIN/../../{}".format(self._RUNTIME_VIEW_DIRNAME)
        for pc in pc_names:
            path = os.path.join(self.generators_folder, pc)
            if not os.path.isfile(path):
                continue
            content = load(self, path)
            if "--disable-new-dtags" in content:
                continue
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if line.startswith("Libs:"):
                    lines[i] = "{} -Wl,--disable-new-dtags -Wl,-rpath,{} {}".format(
                        line, view, origin_flag)
                    break
            save(self, path, "\n".join(lines) + "\n")

    def _patch_juceaide_libcxx(self, juceaide_cmakelists):
        """juceaide 引导构建的两处修复（均单行锚点）：
        1. bootstrap 分支：递归 CMake 不带 toolchain 文件，且上游会 unset
           CC/CXX 后按 PATH 探测——OHOS 真机上会误选 .harmonybrew/bin/CC
           （C 驱动）当 C++ 编译器，链接期缺 libc++ 全套符号。把外层已确认
           的编译器经 PASSTHROUGH 传入（OHOS 真机 build==host，语义等价于
           上游“host 工具用宿主编译器”的设计意图）。
        2. helper 分支：OHOS clang 编译期默认 libc++ 头但链接不自动链
           libc++，显式 -stdlib=libc++（OHOS clang 拒绝 -stdlib=c++ 拼写）。"""
        replace_in_file(
            self, juceaide_cmakelists,
            '    set(PASSTHROUGH_ARGS "")',
            '    set(PASSTHROUGH_ARGS "")\r\n'
            '    list(APPEND PASSTHROUGH_ARGS '
            '"-DCMAKE_C_COMPILER=${CMAKE_C_COMPILER}")\r\n'
            '    list(APPEND PASSTHROUGH_ARGS '
            '"-DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}")')
        replace_in_file(
            self, juceaide_cmakelists,
            "    target_link_libraries(juceaide PRIVATE",
            "    target_compile_options(juceaide PRIVATE -stdlib=libc++)\r\n"
            "    target_link_options(juceaide PRIVATE -stdlib=libc++)\r\n"
            "    target_link_libraries(juceaide PRIVATE")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # 默认目标 = juce_lv2_helper + juce_vst3_helper；juceaide 已在
        # configure 期由官方引导流程原生构建并自检（juceaide version）。
        cmake.build()
        cmake.install()

    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 官方 CMake config 安装于 lib/cmake/JUCE-<version>；消费方用原始
        # find_package(JUCE)（juce_add_module 机器），禁用 CMakeDeps 代生成。
        self.cpp_info.set_property("cmake_file_name", "JUCE")
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake",
                                                "JUCE-{}".format(self.version))]
