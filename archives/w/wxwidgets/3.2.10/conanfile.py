#!/usr/bin/env python3
"""Conan recipe for wxwidgets 3.2.10 — CMake-based cross-platform C++ framework.

wxWidgets is a mature open-source cross-platform C++ framework.
This recipe builds the base toolkit (non-GUI) for HarmonyOS with static linking.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file, copy
import os


class WxwidgetsConan(ConanFile):
    name = "wxwidgets"
    version = "3.2.10"
    description = "Cross-platform C++ framework for building desktop applications"
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
        # 与 manifest.yaml dependencies 保持一致，确保可复现构建
        # zlib/1.3.1.1: 与 curl/8.15.0 的 zlib 依赖保持一致，避免版本冲突
        self.requires("zlib/1.3.1.1")
        self.requires("expat/2.8.2")
        self.requires("curl/8.15.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 生成 Conan 依赖的 CMake config 文件，让 wxWidgets 的
        # find_package(ZLIB/expat/CURL) 能定位到 Conan 提供的包
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["wxBUILD_SHARED"] = self.options.shared
        tc.variables["wxBUILD_SAMPLES"] = "OFF"
        tc.variables["wxBUILD_TESTS"] = "OFF"
        tc.variables["wxUSE_GUI"] = "OFF"
        tc.variables["wxUSE_XLOCALE"] = "OFF"
        # lib_baseu 缺 wxThread/wxMutex/wxGetEnv 符号（实测链接 undefined——
        # thread/mutex/env 源未编入）——显式开启线程支持
        tc.variables["wxUSE_THREADS"] = "ON"
        # OHOS socket API 不兼容（WX_SOCKLEN_T int vs socklen_t*、
        # gethostbyname/getservbyname/inet_aton 不可用——实测编译错误）——
        # 关闭网络库（base toolkit 不需要 libwx_baseu_net——避免 socket 错误）
        tc.variables["wxUSE_SOCKETS"] = "OFF"
        tc.variables["wxUSE_NET"] = "OFF"
        # chkconf 检查：wxUSE_PROTOCOL_FTP/HTTP requires wxUSE_SOCKETS——
        # 同步关闭协议库（FTP/HTTP/WWW——base toolkit 不需要）
        tc.variables["wxUSE_PROTOCOL_FTP"] = "OFF"
        tc.variables["wxUSE_PROTOCOL_HTTP"] = "OFF"
        tc.variables["wxUSE_PROTOCOL_WWW"] = "OFF"
        # webrequest_curl.cpp 用 wxCloseSocket（wxUSE_SOCKETS=OFF 后未声明——
        # 实测编译错误）——关闭 webrequest 库
        tc.variables["wxUSE_WEBREQUEST"] = "OFF"
        # 平台检测（toolkit.cmake elseif 链）在 OHOS 下仍触发 Unsupported
        # platform（38 行 message FATAL_ERROR）——显式指定 wxBUILD_TOOLKIT
        # 跳过平台分支（wxUSE_GUI=OFF 时 toolkit 仅影响配置选择）
        tc.variables["wxBUILD_TOOLKIT"] = "gtk3"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        # 0001 补丁的 apply 在 copy-sources 后作用于 build 目录——实测 source
        # 的 toolkit.cmake 33 行仍 elseif(UNIX)（OHOS 不匹配 → Unsupported
        # platform）——apply 前 replace_in_file 确保平台分支生效
        replace_in_file(self,
                        os.path.join(self.source_folder, "build", "cmake", "toolkit.cmake"),
                        "elseif(UNIX)",
                        'elseif(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")')
        # OHOS 下 elseif 链仍走到 38 行的 message(FATAL_ERROR
        # "Unsupported platform")（wxUSE_GUI=OFF 仅 base toolkit——
        # toolkit 分支无关紧要）——把 Unsupported platform 分支替换为
        # 默认 gtk3（跳过 FATAL_ERROR）
        replace_in_file(self,
                        os.path.join(self.source_folder, "build", "cmake", "toolkit.cmake"),
                        'message(FATAL_ERROR "Unsupported platform")',
                        'set(wxDEFAULT_TOOLKIT gtk3)')
        # OHOS 的 getsockopt 声明 socklen_t*（unsigned int*）——wxwidgets 的
        # SOCKOPTLEN_T 在 OHOS 上为 int（实测 int* 无法转换）——改 len 类型
        # 为 socklen_t（socket.cpp 2 处 + sockunix.cpp 1 处）
        for f in ("src/common/socket.cpp", "src/unix/sockunix.cpp"):
            replace_in_file(self,
                            os.path.join(self.source_folder, f),
                            "SOCKOPTLEN_T len",
                            "socklen_t len")
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # wx/setup.h 是构建生成的头（cmake.install 装到 lib/wx/include/.../wx/）——
        # platform.h 的 #include "wx/setup.h" 从 include/wx-3.2/wx/ 找——实测
        # test_package 编译找不到——补打到 include/wx-3.2/wx/setup.h
        copy(self, "setup.h",
             src=os.path.join(self.package_folder, "lib", "wx", "include",
                              "base-unicode-static-3.2", "wx"),
             dst=os.path.join(self.package_folder, "include", "wx-3.2", "wx"))
        # wx/unix/ 子目录头（chkconf.h 等——chkconf.h 的 #include
        # "wx/unix/chkconf.h" 实测找不到——cmake.install 未装该子目录——
        # 从源码 include/wx/unix/ 补打（build 目录的 copy 未生效）
        copy(self, "*",
             src=os.path.join(self.source_folder, "include", "wx", "unix"),
             dst=os.path.join(self.package_folder, "include", "wx-3.2", "wx", "unix"))

    def package_info(self):
        # collect_libs 实测 AttributeError（该 conan 环境不支持）——手动声明
        # base toolkit 静态库（libwx_baseu-3.2.a / libwxregexu-3.2.a——
        # 构建产物，见 notes.md 交付物）；wxregexu 引用 wxThread/wxMutex/
        # wxGetEnv（libwx_baseu 的符号）——静态库链接顺序 regexu 在前
        self.cpp_info.libs = ["wxregexu-3.2", "wx_baseu-3.2"]
        # wxprec.h 等头文件在 include/wx-3.2/ 子目录（实测 test_package 的
        # #include <wx/wxprec.h> 找不到——include 路径缺 wx-3.2）
        self.cpp_info.includedirs = ["include/wx-3.2"]
        self.cpp_info.set_property("cmake_file_name", "wxwidgets")
        self.cpp_info.set_property("cmake_target_name", "wxwidgets::wxwidgets")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]
