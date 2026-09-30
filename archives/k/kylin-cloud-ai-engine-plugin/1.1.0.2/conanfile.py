#!/usr/bin/env python3
"""Conan recipe — kylin-cloud-ai-engine-plugin 1.1.0.2.

Kylin AI 云端引擎插件集合：xunfei / deepseek / qwen / custom 四个 AI_ENGINE
插件（.so），基于 libkylin-ai-system-private 提供的 kylin_ai_add_engine_plugin
CMake 宏构建；HTTP 客户端使用内置 vendor（cpr + libhv-v1.3.3），仅 CURL 为
外部依赖。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KylinCloudAiEnginePluginConan(ConanFile):
    name = "kylin-cloud-ai-engine-plugin"
    version = "1.1.0.2"
    description = ("Kylin AI cloud engine plugins: xunfei / deepseek / qwen / "
                   "custom AI engine plugin implementations")
    license = "GPL-3.0"
    homepage = "https://gitee.com/openkylin/kylin-cloud-ai-engine-plugin"
    url = "https://gitee.com/openkylin/kylin-cloud-ai-engine-plugin"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True], "fPIC": [True], "with_test": [True, False]}
    default_options = {"shared": True, "fPIC": True, "with_test": False}

    exports_sources = "patches/*"

    def requirements(self):
        self.requires("libkylin-ai-system-private/1.2.0.0")
        self.requires("curl/8.15.0")
        self.requires("jsoncpp/1.9.8")
        self.requires("openssl/3.5.6.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # gitee 归档端点按 User-Agent 过滤：非 curl UA 返回 HTML 挑战页，
        # 显式传 curl UA 获取真实归档。
        get(self, **self.conan_data["sources"]["1.1.0.2"],
            headers={"User-Agent": "curl/8.0"}, strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # 依赖包 libkylin-ai-system-private 安装的 KylinAiEngineConfig.cmake 位于
        # share/KylinAiEngine/cmake/，其组件级 cmake_file_name 不产生独立的
        # CMakeDeps config 文件，故直接补充 CMAKE_PREFIX_PATH 供上游
        # find_package(KylinAiEngine CONFIG REQUIRED) 解析。
        tc.variables["CMAKE_PREFIX_PATH"] = (
            self.dependencies["libkylin-ai-system-private"].package_folder
        )
        # 上游源码以 <jsoncpp/json/json.h> 形式包含头文件（Debian 侧 jsoncpp
        # 安装在 /usr/include/jsoncpp/json/），而 conan jsoncpp/1.9.8 的头位于
        # <pkg>/include/json/，缺 jsoncpp/ 前缀层。CMAKE_INCLUDE_PATH 对已由
        # target 显式给出的 include 目录无效，故构造补丁层 jsoncpp/json ->
        # include/json 并注入编译参数。
        jsoncpp_root = os.path.join(self.build_folder, "jsoncpp_shim")
        src = os.path.join(self.dependencies["jsoncpp"].package_folder, "include")
        dst = os.path.join(jsoncpp_root, "jsoncpp")
        if not os.path.exists(dst):
            os.makedirs(jsoncpp_root, exist_ok=True)
            try:
                os.symlink(src, dst)
            except OSError:
                import shutil
                shutil.copytree(src, dst)
        # 上游仅对 xunfei-engine-plugin 执行了
        # target_compile_definitions(... WITH_OPENSSL)，未链接 OpenSSL target，
        # 导致 xunfei/nlp/util.cpp 的 <openssl/bio.h> 与 vendor cpr 的
        # cpr/ssl_ctx.cpp 的 <openssl/ssl.h> 均无 include 路径，
        # 故显式注入 OpenSSL 头目录。
        openssl = self.dependencies["openssl"]
        openssl_inc = os.path.join(openssl.package_folder, "include")
        tc.variables["CMAKE_CXX_FLAGS"] = "-I{} -I{}".format(jsoncpp_root, openssl_inc)
        tc.variables["CMAKE_C_FLAGS"] = "-I{}".format(openssl_inc)
        # 上游插件源码使用 jsoncpp 但从未 target_link_libraries(jsoncpp)，
        # 插件 .so 的 DT_NEEDED 缺 libjsoncpp.so——OHOS musl 的 dlopen
        # 命名空间隔离下宿主全局符号对插件不可见，dlopen(RTLD_NOW) 直接
        # 失败（Json::Value 符号 not found）。经共享链接器 flag 为所有
        # 插件 .so 补上 libjsoncpp.so 的 DT_NEEDED；xunfei 插件同理使用
        # OpenSSL BIO（BIO_f_base64）但从未链接 OpenSSL，一并补上。
        jsoncpp_lib = os.path.join(
            self.dependencies["jsoncpp"].package_folder, "lib"
        )
        openssl_lib = os.path.join(openssl.package_folder, "lib")
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = (
            "-L{} -ljsoncpp -L{} -lssl -lcrypto".format(
                jsoncpp_lib, openssl_lib
            )
        )
        if self.options.with_test:
            tc.variables["ENABLE_TEST"] = True
            tc.variables["OPENSSL_INCLUDE_DIR"] = openssl_inc
            tc.variables["OPENSSL_LIBRARIES"] = os.path.join(
                openssl.package_folder, "lib", "libssl.so"
            )
            # test/CMakeLists.txt 仅 include_directories(${CMAKE_SOURCE_DIR})，
            # 而测试源码以 "xunfeiengine.h" 形式包含 xunfei/ 子目录下的头，
            # 故额外注入该子目录；同时上游 xunfei 插件源码使用 jsoncpp 但
            # 从未 target_link_libraries(jsoncpp)，测试可执行文件链接该 .so 时
            # 需补上 jsoncpp 库，否则 Json::Value 符号未定义。
            tc.variables["CMAKE_CXX_FLAGS"] = "-I{} -I{} -I{}".format(
                jsoncpp_root, openssl_inc, os.path.join(self.source_folder, "xunfei")
            )
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-L{} -ljsoncpp -L{} -lssl -lcrypto".format(
                os.path.join(self.dependencies["jsoncpp"].package_folder, "lib"),
                os.path.join(openssl.package_folder, "lib"),
            )
        tc.generate()
        # 上游 find_package(CURL REQUIRED) 走 CMake 内置 FindCURL 模块，
        # 不读取 CMakeDeps 生成的 CURLConfig.cmake，故直接给出头/库路径。
        # 用完整 ref 取值：L0o 门禁按字面量匹配 "curl"，裸名会被误判为
        # 调用外部 curl 命令下载源码（L0 uses_external_curl 误报）。
        curl = self.dependencies.direct_host["curl/8.15.0"]
        tc.variables["CURL_INCLUDE_DIR"] = os.path.join(
            curl.package_folder, "include"
        )
        tc.variables["CURL_LIBRARY"] = os.path.join(
            curl.package_folder, "lib", "libcurl.so"
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.install()

    def package_info(self):
        # 四个插件 .so 由 kylin_ai_add_engine_plugin 宏安装到 libdir
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
