#!/usr/bin/env python3
"""Conan recipe for groonga 16.0.8 — embeddable fulltext search engine.

Groonga is a fast and accurate full text search engine based on
inverted indexes. Build system: CMake (upstream official, avoids
aclocal/autoreconf CI worker limitation).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GroongaConan(ConanFile):
    name = "groonga"
    version = "16.0.8"
    description = "An embeddable fulltext search engine"
    license = "LGPL-2.1-or-later"
    homepage = "https://groonga.org/"
    url = "https://github.com/groonga/groonga"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # CMakeDeps 生成器：为 lz4/zlib 依赖生成 *Config.cmake
    # groonga CMakeLists.txt:1341 find_package(lz4 CONFIG) 需 lz4Config.cmake
    # CMakeToolchain 由 generate() 内实例化（不能同时在 generators 和 generate() 里）
    # CI #15673: groonga CMakeLists.txt:646 find_package(ZLIB)+ZLIB::ZLIB（大写 target），
    # CMakeDeps 默认生成小写 zlib::zlib → target 不匹配 configure 失败。
    # → generate() 内实例化 CMakeDeps 并把 zlib 的 cmake_target_name 映射为 ZLIB::ZLIB。
    # （移除类级 generators="CMakeDeps"，改在 generate() 内显式实例化以支持 set_property）

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # 与 CMake -DGRN_WITH_* 配置参数保持一致，显式声明外部依赖
        # CI #16316: 链接 libgroonga.so 共享库报 "relocation R_AARCH64_ADR_PREL_PG_HI21
        # cannot be used against symbol 'z_errmsg'; recompile with -fPIC"——zlib/1.3.1
        # 静态 libz.a 非 PIC。仓库 zlib/1.3.1.1 是 -fPIC 鸿蒙版（CFLAGS=-fPIC 编静态库，
        # 对象可被共享库吸收，消费者 qpdf/cairo 同此依赖）→ 改用 1.3.1.1。
        self.requires("zlib/1.3.1.1")
        self.requires("lz4/1.10.0")
        # xxhash: groonga CMakeLists.txt:1271 find_package(xxHash CONFIG 0.8.0)
        # 项目 xxhash/0.8.3 包无 CMake config 文件，Conan CMakeDeps 生成器
        # 无法生成 xxHashConfig.cmake → 改用 groonga bundled xxhash
        # self.requires("xxhash/0.8.3")

    def validate(self):
        # R32: 平台兼容性检查
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"groonga {self.version} only supports Linux and OHOS, got os={self.settings.os}")

    def source(self):
        # R39: 仅用官方源（github.com/groonga），移除个人账户 mirror 回退
        # （aireview High: gitcode.com/aurawalker 非官方镜像 + sha256=None 跳过
        # 校验属供应链投毒风险）。CI 有内置 mirror fallback（gh-proxy 等）处理
        # GitHub 不可达场景。
        get(self, **self.conan_data["sources"], strip_root=True)
        # CI #15556: groonga release tarball 的 vendor/onigmo-source/ 是空目录
        # （onigmo 源码走 git submodule，GitHub tarball 不含），CMake 在
        # vendor/onigmo/CMakeLists.txt:140 找不到 regint.h 等源码。
        # 下载官方 onigmo 6.2.0 源码解包注入 vendor/onigmo-source/。
        onigmo = dict(self.conan_data.get("onigmo_source", {}))
        if onigmo:
            import shutil as _sh
            onigmo_tmp = os.path.join(self.source_folder, ".onigmo-src")
            get(self, **onigmo, destination=onigmo_tmp, strip_root=True)
            onigmo_dst = os.path.join(self.source_folder, "vendor", "onigmo-source")
            os.makedirs(onigmo_dst, exist_ok=True)
            for root, dirs, files in os.walk(onigmo_tmp):
                rel = os.path.relpath(root, onigmo_tmp)
                dst_dir = onigmo_dst if rel == "." else os.path.join(onigmo_dst, rel)
                os.makedirs(dst_dir, exist_ok=True)
                for fn in files:
                    src_f = os.path.join(root, fn)
                    dst_f = os.path.join(dst_dir, fn)
                    if not os.path.exists(dst_f):
                        _sh.copy2(src_f, dst_f)
            _sh.rmtree(onigmo_tmp, ignore_errors=True)
        # CI #16365: vendor/rapidjson-1.1.0/ 同 onigmo 是 git submodule 空目录
        # （GitHub tarball 不含），CMake 检测不到本地目录时走 ExternalProject 下载
        # github.com/Tencent/rapidjson（CI 网络受限 "timeout on name lookup" 失败，
        # 后续 cast.cpp 报 rapidjson/document.h not found）。
        # 下载官方 rapidjson 1.1.0 源码解包注入 vendor/rapidjson-1.1.0/，
        # 让 CMakeLists.txt:876 的 EXISTS 检查命中本地目录，ExternalProject 从本地复制。
        rapidjson_src = dict(self.conan_data.get("rapidjson_source", {}))
        if rapidjson_src:
            import shutil as _sh
            rapidjson_tmp = os.path.join(self.source_folder, ".rapidjson-src")
            get(self, **rapidjson_src, destination=rapidjson_tmp, strip_root=True)
            rapidjson_dst = os.path.join(self.source_folder, "vendor", "rapidjson-1.1.0")
            os.makedirs(rapidjson_dst, exist_ok=True)
            for root, dirs, files in os.walk(rapidjson_tmp):
                rel = os.path.relpath(root, rapidjson_tmp)
                dst_dir = rapidjson_dst if rel == "." else os.path.join(rapidjson_dst, rel)
                os.makedirs(dst_dir, exist_ok=True)
                for fn in files:
                    src_f = os.path.join(root, fn)
                    dst_f = os.path.join(dst_dir, fn)
                    if not os.path.exists(dst_f):
                        _sh.copy2(src_f, dst_f)
            _sh.rmtree(rapidjson_tmp, ignore_errors=True)

    def export_sources(self):
        # Conan 2.x G1 门禁要求 export_sources() 声明
        # aireview Medium: apply_conandata_patches 应在 source()/build() 阶段对源码打补丁，
        # export 阶段源码尚未下载展开 → 用 export_conandata_patches（复制补丁到 export 缓存），
        # 与仓库 flatcc/flac/frp/fzy/htslib 等配方约定一致
        export_conandata_patches(self)

    def generate(self):
        # CI #15673: groonga CMakeLists.txt:646 用 find_package(ZLIB)+ZLIB::ZLIB（大写），
        # CMakeDeps 默认生成小写 zlib::zlib → 映射 zlib 的 cmake_target_name 为 ZLIB::ZLIB
        # 使 find_package(ZLIB) 找到的 target 名与 groonga 引用一致（configure 不再报
        # "link interface of target grn_dependencies contains ZLIB::ZLIB but target not found"）。
        # lz4 同理：cmake/FindGroongalz4.cmake 检查 TARGET LZ4::lz4_shared 否则用
        # LZ4::lz4_static（静态构建）→ 映射 lz4 的 cmake_target_name 为 LZ4::lz4_static。
        deps = CMakeDeps(self)
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.set_property("lz4", "cmake_target_name", "LZ4::lz4_static")
        deps.generate()
        tc = CMakeToolchain(self)
        # CI #14499: CMake 4.1.2 不认识 OHOS 平台（"System is unknown to cmake"），
        # OHOS 基于 Linux 内核 → 显式声明 CMAKE_SYSTEM_NAME=Linux
        # （同 autotools --host=linux-gnu 处理，E090 变体：平台检测不匹配）
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # 禁用 bundled 依赖，使用项目已适配的外部库
        tc.variables["GRN_WITH_ZLIB"] = "yes"
        tc.variables["GRN_WITH_LZ4"] = "yes"
        # xxhash: groonga CMakeLists.txt:1271 find_package(xxHash CONFIG 0.8.0)
        # 项目 xxhash/0.8.3 包无 CMake config 文件 → 改用 groonga bundled xxhash
        tc.variables["GRN_WITH_XXHASH"] = "no"
        # rapidjson 用 groonga bundled 版本（vendor/rapidjson-1.1.0，CI #16365
        # source() 已注入源码）。必须显式 "bundled"：设 "yes" 时 CMake 走
        # find_package(GroongaRapidJSON) 误判 system（Headers 指向空
        # rapidjson-ep-install/include），ExternalProject 不执行 → cast.cpp
        # 报 rapidjson/document.h not found。
        tc.variables["GRN_WITH_RAPIDJSON"] = "bundled"
        # 禁用 groonga-httpd、groonga-normalizer-mysql 等可选组件（OHOS 无 apache/mysql）
        tc.variables["GRN_WITH_APACHE_ARROW"] = "no"
        # zstd：groonga CMakeLists.txt:747 用 FetchContent 下载 zstd-1.5.7
        # CI Worker 网络受限无法访问 github.com → 下载失败
        # zstd 是 groonga 可选依赖（压缩列存储），禁用避免网络依赖
        tc.variables["GRN_WITH_ZSTD"] = "no"
        # llama.cpp / ggml：groonga 16.0.8 新增可选 AI 嵌入依赖。
        # 正确变量名是 GRN_WITH_LLAMA_CPP（CMakeLists.txt:1757），
        # 之前误用 GRN_WITH_LLAMA 导致 llama.cpp 仍被 FetchContent 拉取
        # （CI #15436: _deps/llama_cpp-src/ggml 报 GGML_SYSTEM_ARCH: UNKNOWN）。
        # OHOS 不需要 AI 嵌入，禁用避免平台不兼容
        tc.variables["GRN_WITH_LLAMA_CPP"] = "no"
        # openzl：groonga 16.0.8 新增可选依赖，CMake 默认 FetchContent 下载
        # openzl 源码（CI #14729: _deps/openzl-src/CMakeLists.txt 报错），
        # CI Worker 网络受限无法访问 → 禁用（同 zstd 处理）
        tc.variables["GRN_WITH_OPENZL"] = "no"
        # msgpack-c：groonga CMakeLists.txt:1137/1152 grn_build_message_pack
        # 用 FetchContent 下载 msgpack-c-6.1.0（CI #15609: _deps 下载
        # "OpenSSL SSL_read: unexpected eof" 中断），CI Worker 网络受限
        # 无法访问 github.com → 禁用（同 zstd/openzl 处理）
        tc.variables["GRN_WITH_MESSAGE_PACK"] = "no"
        # simdjson：groonga CMakeLists.txt:778-804 GRN_WITH_SIMDJSON 默认 auto，
        # 找不到系统 simdjson 时 FetchContent 下载 simdjson-3.13.0（CI 网络受限
        # 无法访问 github.com，configure 报 "By not providing Findsimdjson.cmake"）
        # → 禁用（同 zstd/openzl/msgpack 处理）
        tc.variables["GRN_WITH_SIMDJSON"] = "no"
        # base64：groonga CMakeLists.txt:2170-2187 GRN_WITH_BASE64 默认 auto，
        # 找不到系统 base64 时 ExternalProject 下载 aklomp/base64（CI 网络受限
        # 无法访问 github.com，configure 报 "Could not find base64Config.cmake"）
        # → 禁用（同 simdjson/zstd 处理）
        tc.variables["GRN_WITH_BASE64"] = "no"
        # h3：groonga CMakeLists.txt:1667-1695 GRN_WITH_H3 默认 auto，找不到系统
        # h3 时 FetchContent 下载 uber/h3 v4.1.0（CI #16365: github.com 不可达，
        # "timeout on name lookup" 下载失败）→ 禁用（同 zstd/simdjson 处理）
        tc.variables["GRN_WITH_H3"] = "no"
        # 静态库构建
        tc.variables["GRN_SHARED_LIB"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # aarch64 little-endian，CMake 交叉编译无法探测 endianness
        tc.variables["CMAKE_C_BYTE_ORDER"] = "LITTLE_ENDIAN"
        tc.variables["CMAKE_CXX_BYTE_ORDER"] = "LITTLE_ENDIAN"
        # CMake 4.1.2 移除对 <3.5 的 cmake_minimum_required 兼容：rapidjson-ep
        # （ExternalProject 子 cmake）CMakeLists.txt:1 仍声明低版本（CI 报
        # "Compatibility with CMake < 3.5 has been removed"）。CMAKE_POLICY_VERSION_MINIMUM
        # 作为环境变量会被 ExternalProject 子进程继承 → 主/子 cmake 均按 3.5 策略配置。
        os.environ["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # P3: 许可证随包发布
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["groonga"]
        # groonga 头文件安装在 include/groonga/ 下（groonga.h 直接位于该层，
        # 消费者 #include <groonga.h>）→ includedirs 指向 include/groonga
        self.cpp_info.includedirs = ["include/groonga"]
        # aireview P2: groonga CMake 上游 find_package(groonga CONFIG) 需正确 target name，
        # Conan 2.x CMakeDeps 生成器靠 set_property 传播 cmake_target_name
        # CI #16365: 单段 "groonga" 使 CMakeDeps 生成裸 target `groonga`，
        # test_package 链接 groonga::groonga 找不到 → 用双段命名空间。
        self.cpp_info.set_property("cmake_target_name", "groonga::groonga")
        # 上游提供 groonga.pc（pkg-config 生态），同步声明供 PkgConfigDeps 消费方使用
        self.cpp_info.set_property("pkg_config_name", "groonga")
        # CI #16365: test_package 运行 test_groonga 需加载 libgroonga.so.0，
        # conanrun 环境缺 LD_LIBRARY_PATH → runenv_info 声明 lib 目录自动注入
        self.runenv_info.append_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
