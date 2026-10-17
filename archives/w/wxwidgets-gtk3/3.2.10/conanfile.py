#!/usr/bin/env python3
"""Conan recipe for wxwidgets-gtk3 3.2.10 — wxGTK3 GUI toolkit for HarmonyOS PC.

GUI variant of wxWidgets built with wxUSE_GUI=ON against the published
gtk/3.24.43 (broadway backend, X11/Wayland disabled). All X11-specific code
in the wx GTK port is guarded by GDK_WINDOWING_X11 and compiles out with
this backend, so no X11 client libraries are needed (toolkit.cmake only
requires find_package(X11) when wxHAVE_GDK_X11 is set by FindGTK3.cmake).

Image support uses the wx-bundled copies of libpng/libjpeg (wxUSE_LIBPNG/
wxUSE_LIBJPEG=builtin) to avoid mixing libjpeg and libjpeg-turbo in one
dependency graph; TIFF is disabled.

Sockets stay ON (codeblocks consumers may use wx net APIs); the OHOS
socklen_t incompatibility is fixed in build() by pointing the WX_SOCKLEN_T/
SOCKOPTLEN_T fallbacks at socklen_t (the base-variant recipe had disabled
sockets instead).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import PkgConfigDeps


class WxwidgetsGtk3Conan(ConanFile):
    name = "wxwidgets-gtk3"
    version = "3.2.10"
    description = "Cross-platform C++ GUI framework, wxGTK3 variant (broadway backend)"
    license = "wxWindows Library Licence"
    homepage = "https://www.wxwidgets.org"
    url = "https://github.com/wxWidgets/wxWidgets"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 与 manifest.yaml dependencies 保持一致（可复现构建）
        # zlib/1.3.1.1 与 gtk 树（cairo/curl 系列）一致
        self.requires("gtk/3.24.43")
        self.requires("zlib/1.3.1.1")
        # expat 用 wx 内置（wxxml 经 FindEXPAT 模块变量取 sys expat，
        # 与 conan CMakeDeps 的小写 expat 配置文件名接不上——builtin 规避）

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # FindGTK3.cmake 通过 pkg_check_modules(gtk+-3.0) 探测 GTK，
        # 需要 PkgConfigDeps 生成 .pc 文件
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        # 静态库统一 PIC：codeblocks 等「共享库+插件」架构的应用需要把
        # 静态 wx 链进 shared lib——CI profile 不带全局 -fPIC，显式开启
        # 保证产物在任何环境可作 PIC 使用
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["wxBUILD_SHARED"] = self.options.shared
        tc.variables["wxBUILD_SAMPLES"] = "OFF"
        tc.variables["wxBUILD_DEMOS"] = False
        tc.variables["wxBUILD_BENCHMARKS"] = False
        tc.variables["wxBUILD_TESTS"] = "OFF"
        tc.variables["wxBUILD_PRECOMP"] = "OFF"
        # locale 目录跳过：CI worker（#40577/CI-011）上存在运行时损坏的
        # msgfmt（缺 libintl.so.8），FindGettext 只探测二进制存在性不验证
        # 可运行，AUTO 模式下构建期 .gmo 全部 Error 127——显式 OFF 使构建
        # 不依赖 worker gettext 状态；wxstd 消息翻译目录非本包消费必需
        tc.variables["wxBUILD_LOCALES"] = "OFF"
        tc.variables["wxUSE_GUI"] = "ON"
        tc.variables["wxBUILD_TOOLKIT"] = "gtk3"
        # 线程支持必须显式开启（base 变体实测缺 wxThread/wxMutex 符号）
        tc.variables["wxUSE_THREADS"] = "ON"
        # sockets 保持开启：wxUSE_SOCKETS=OFF 时 include/wx/protocol/protocol.h
        # 的 SetTimeout override 无基类可覆盖（htmlpars.cpp 无条件含 url.h），
        # 上游对 sockets-off 未做干净——改为修复 socklen_t 差异（build()）
        tc.variables["wxUSE_WEBREQUEST"] = "OFF"
        # 图像库：内置 png/jpeg（避免 libjpeg 与 libtiff 引入的 libjpeg-turbo
        # 在同一依赖图中共存）；TIFF 关闭
        tc.variables["wxUSE_LIBPNG"] = "builtin"
        tc.variables["wxUSE_LIBJPEG"] = "builtin"
        tc.variables["wxUSE_LIBTIFF"] = "OFF"
        # expat 内置（同上：FindEXPAT 模块与 CMakeDeps 文件名不兼容）
        tc.variables["wxUSE_EXPAT"] = "builtin"
        # broadway 后端无 GLX/EGL 呈现路径——关闭 GL 相关
        tc.variables["wxUSE_OPENGL"] = "OFF"
        tc.variables["wxUSE_GLCANVAS"] = "OFF"
        # 设备侧缺失的可选特性
        tc.variables["wxUSE_MEDIACTRL"] = "OFF"
        tc.variables["wxUSE_JOYSTICK"] = "OFF"
        tc.variables["wxUSE_SOUND"] = "OFF"
        tc.variables["wxUSE_LIBNOTIFY"] = "OFF"
        tc.variables["wxUSE_SPELLCHECK"] = "OFF"
        tc.variables["wxUSE_WEBVIEW"] = "OFF"
        tc.variables["wxUSE_PRIVATE_FONTS"] = "OFF"
        # musl 无 xlocale 扩展（base 变体经验）
        tc.variables["wxUSE_XLOCALE"] = "OFF"
        # 显式声明平台名：适配版 conan 映射 HarmonyOS、原版 conan 走 uname
        # 探测（也是 HarmonyOS）——两者 UNIX 均不成立，toolkit.cmake 的
        # 0001 补丁匹配 STREQUAL "OHOS"——用 cache 变量统一为 OHOS
        # （与 wxwidgets base 变体历史验证配置一致）
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        # OHOS getsockopt/setsockopt 接受 socklen_t*（unsigned int*），而
        # include/wx/private/socket.h 在无 configure 宏时把 WX_SOCKLEN_T/
        # SOCKOPTLEN_T 兜底定义为 int——C++ 下 int* 与 socklen_t* 不兼容
        # （socket.cpp 3 处 + sockunix.cpp 1 处 getsockopt 调用全部报错）。
        # POSIX 分支兜底改用 socklen_t，并引入其定义头 <sys/socket.h>
        sockh = os.path.join(self.source_folder, "include", "wx", "private",
                             "socket.h")
        replace_in_file(
            self, sockh,
            "    #include <sys/time.h>   // for timeval",
            "    #include <sys/time.h>   // for timeval\n"
            "    #include <sys/socket.h>  // for socklen_t")
        for macro in ("WX_SOCKLEN_T", "SOCKOPTLEN_T"):
            replace_in_file(
                self, sockh,
                f"#ifndef {macro}\n"
                f"    #define {macro} int\n"
                f"#endif",
                f"#ifndef {macro}\n"
                f"    #if defined(__WINDOWS__)\n"
                f"        #define {macro} int\n"
                f"    #else\n"
                f"        #define {macro} socklen_t\n"
                f"    #endif\n"
                f"#endif")
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        if self.settings.os == "OHOS":
            # 设备内存受限时并行链接易 OOM——串行构建保守处理
            cmake.build(cli_args=["-j2"])
        else:
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # wx-config 生成时把 CMake 目标名 ZLIB::ZLIB 当库名嵌入 --libs 输出
        # （实测消费者拿到 -lZLIB::ZLIB 链接失败；正确的 -lz 已在列表中）——
        # 安装后清洗该坏 token，wx-config 消费者（codeblocks 等）才能用
        wx_config = os.path.join(self.package_folder, "bin", "wx-config")
        if os.path.isfile(wx_config):
            # 实际字面量：ldlibs_base="-lZLIB::ZLIB -lwxregexu..."（带尾随空格）
            replace_in_file(self, wx_config, "-lZLIB::ZLIB ", "")
        # wx/setup.h 是构建生成头，装在 lib/wx/include/<toolkit>-unicode-static-3.2/
        # 下——消费者从 include/wx-3.2/wx/ 找（base 变体实测找不到——补打）
        for setup_dir in os.listdir(os.path.join(self.package_folder, "lib",
                                                 "wx", "include")):
            copy(self, "setup.h",
                 src=os.path.join(self.package_folder, "lib", "wx", "include",
                                  setup_dir, "wx"),
                 dst=os.path.join(self.package_folder, "include", "wx-3.2", "wx"))
        # wx/unix/ 与 wx/gtk/ 子目录头（chkconf.h 等）cmake.install 未完整
        # 安装——从源码补打（base 变体对 unix/ 的处理 + GUI 需要 gtk/）
        copy(self, "*",
             src=os.path.join(self.source_folder, "include", "wx", "unix"),
             dst=os.path.join(self.package_folder, "include", "wx-3.2", "wx", "unix"))
        copy(self, "*",
             src=os.path.join(self.source_folder, "include", "wx", "gtk"),
             dst=os.path.join(self.package_folder, "include", "wx-3.2", "wx", "gtk"))
        copy(self, "*",
             src=os.path.join(self.source_folder, "include", "wx", "generic"),
             dst=os.path.join(self.package_folder, "include", "wx-3.2", "wx", "generic"))

    def package_info(self):
        # 静态链接顺序：上层 GUI 库在前，base 在后；内置 3rdparty 库
        # （expat/regex/jpeg/png/scintilla，无 -OHOS 后缀）紧随其使用者
        # 注意：wx 主库带 -OHOS 后缀（显式 CMAKE_SYSTEM_NAME=OHOS 使 CMake
        # 判定交叉编译，functions.cmake cross_target 追加），CI/设备行为一致
        self.cpp_info.libs = [
            "wx_gtk3u_stc-3.2-OHOS",
            "wxscintilla-3.2",
            "wx_gtk3u_ribbon-3.2-OHOS",
            "wx_gtk3u_richtext-3.2-OHOS",
            "wx_gtk3u_propgrid-3.2-OHOS",
            "wx_gtk3u_xrc-3.2-OHOS",
            "wx_gtk3u_aui-3.2-OHOS",
            "wx_gtk3u_html-3.2-OHOS",
            "wx_gtk3u_qa-3.2-OHOS",
            "wx_gtk3u_adv-3.2-OHOS",
            "wx_gtk3u_core-3.2-OHOS",
            "wx_baseu_xml-3.2-OHOS",
            "wxexpat-3.2",
            "wx_baseu_net-3.2-OHOS",
            "wx_baseu-3.2-OHOS",
            "wxregexu-3.2",
            "wxjpeg-3.2",
            "wxpng-3.2",
        ]
        self.cpp_info.includedirs = ["include/wx-3.2"]
        # wx 头文件要求预定义端口宏（defs.h 无端口宏时 #error "No Target!"，
        # wx/gtk/colour.h 等引用的 GdkColor/GtkWidget 类型也依赖 gtk 头被
        # platform.h 按 __WXGTK__ 引入）——wx-config 会自动加，CMakeDeps
        # 消费路径由 defines 提供
        self.cpp_info.defines = ["__WXGTK__"]
        self.cpp_info.set_property("cmake_file_name", "wxwidgets-gtk3")
        self.cpp_info.set_property("cmake_target_name", "wxwidgets-gtk3::wxwidgets-gtk3")
        # 消费者静态链接 wx 时需要 GTK 全链与 zlib（transitive 由 gtk 配方声明）
        self.cpp_info.requires = ["gtk::gtk", "zlib::zlib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m", "dl"]
