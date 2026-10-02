from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, mkdir
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
import os


class SemsOpusConan(ConanFile):
    name = "sems-opus"
    version = "2.1.0"
    description = "SEMS Opus codec plug-in (sems-server/sems 2.1.0, core + opus module)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/sems-server/sems"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("opus/1.5.2")
        self.requires("libevent/2.1.12")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 FindOpus.cmake / FindLibevent2.cmake 用变量探测，注入 conan 依赖路径
        opus = self.dependencies["opus"]
        lev = self.dependencies["libevent"]
        tc.variables["OPUS_INCLUDE_DIR"] = opus.cpp_info.includedirs[0]
        opus_lib = os.path.join(opus.cpp_info.libdirs[0], "libopus.so")
        if not os.path.exists(opus_lib):
            opus_lib = os.path.join(opus.cpp_info.libdirs[0], "libopus.a")
        tc.variables["OPUS_LIBRARIES"] = opus_lib
        tc.variables["OPUS_FOUND"] = True
        tc.variables["LIBEVENT2_INCLUDE_DIR"] = lev.cpp_info.includedirs[0]
        tc.variables["LIBEVENT2_LIB_DIR"] = lev.cpp_info.libdirs[0]
        lev_lib = os.path.join(lev.cpp_info.libdirs[0], "libevent.a")
        if not os.path.exists(lev_lib):
            lev_lib = os.path.join(lev.cpp_info.libdirs[0], "libevent.so")
        tc.variables["LIBEVENT2_LIBRARIES"] = lev_lib
        tc.variables["LIBEVENT2_FOUND"] = True
        # 仅构建 core + opus 插件；禁用其余可选组件
        tc.variables["SEMS_USE_OPUS"] = "ON"
        tc.variables["SEMS_USE_ILBC"] = "OFF"
        tc.variables["SEMS_USE_MONITORING"] = "OFF"
        tc.variables["SEMS_USE_PYTHON"] = "OFF"
        tc.variables["SEMS_USE_IPV6"] = "ON"
        # 裁剪全部 app 模块：opus 是 core plug-in，apps 层不需要
        tc.variables["EXCLUDE_APP_MODULES"] = ("ann_b2b announce_transfer announcement annrecorder "
            "callback click2dial conference db_reg_agent diameter_client dsm early_announce "
            "early_dbprompt jsonrpc mobile_push monitoring mp3 msg_storage mwi precoded_announce "
            "reg_agent registrar_client sbc siprec_srs voicebox voicemail webconference "
            "xmlrpc2di conf_auth ivr mailbox pin_collect")
        # R26/OHOS: 静态 core
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # core/sip 静态库一并构建：dlopen 插件的宿主进程需要 whole-archive
        # 链接它们以提供 run_log_hooks 等 core 符号
        cmake.build(target="sems_core")
        cmake.build(target="sems_sip")
        cmake.build(target="sems_opus")
        # 上游测试（R51 rule4 硬性要求真实执行）：sems_tests 为 fct.h 单体
        # 测试程序（10 个测试源文件），依赖 sems_core/sems_sip + sbc 应用源码
        cmake.build(target="sems_tests")

    def package(self):
        # 安装 opus 插件动态模块（上游 OUTPUT_NAME=opus，无前缀）与 SEMS core 插件接口头文件
        copy(self, "opus.so",
             src=os.path.join(self.build_folder, "core", "plug-in", "opus"),
             dst=os.path.join(self.package_folder, "lib", "sems", "plug-in"), keep_path=False)
        # core/sip 静态库：dlopen 插件的宿主进程需要 whole-archive 链接
        # （位于 build/Release/core|sip/ 下，**/ 递归匹配）
        copy(self, "**/libsems_core.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "**/libsems_sip.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # 上游测试可执行文件（R51 rule4：随包分发供消费者真实执行）
        # 位于 build/Release/core/ 下，**/ 递归匹配
        copy(self, "**/sems_tests",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "core", "ampi"),
             dst=os.path.join(self.package_folder, "include", "sems", "ampi"))
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "core", "amci"),
             dst=os.path.join(self.package_folder, "include", "sems", "amci"))
        mkdir(self, os.path.join(self.package_folder, "lib", "sems", "plug-in"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # core/sip 静态库：dlopen 插件的宿主进程需 whole-archive 链接它们，
        # 提供 run_log_hooks 等插件引用的 core 符号（SEMS 插件加载模型）
        self.cpp_info.libs = ["sems_core", "sems_sip"]
        self.cpp_info.system_libs = ["dl"]
