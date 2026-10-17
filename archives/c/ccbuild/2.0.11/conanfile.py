#!/usr/bin/env python3
"""Conan recipe for ccbuild 2.0.11 — C++ source scanning build utility。

ccbuild（bneijt/ccbuild）是 C++ 源码扫描构建工具（自动推导头文件依赖
并编译/链接），CMake 构建，唯一工具依赖 FLEX（源码扫描解析器生成——
本机/CI 均可用 flex 2.6.4，无 Conan 依赖）。

Upstream: bneijt/ccbuild release 2.0.11（2025-09-14 最新——清单
1.0.0 与上游不一致，按用户指示用真实版本 2.0.11）。

Build:   CMake + FLEX（find_package(FLEX) + FLEX_TARGET 生成 yylex.cc）。
Install: bin/ccbuild + share/man/man1。
Type:   application（CLI 工具——commands.json 软件级声明）

Deps:   FLEX 2.6.4（系统可用，非 Conan 依赖）；无编译期库依赖。

上游测试: test/（arguments.cc/argvtest.cc/attempt1.cc 等 13 文件）——
         compile+run 验证。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, copy
from conan.tools.build import cross_building


class CcbuildConan(ConanFile):
    name = "ccbuild"
    version = "2.0.11"
    description = "C++ source scanning build utility"
    license = "GPL-2.0"
    homepage = "https://github.com/bneijt/ccbuild"
    url = "https://github.com/bneijt/ccbuild"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # 依赖：boost（circular_buffer/lexical_cast/numeric——header-only
    # 完整头文件树版）+ openssl（MD5 计算——替代制品仓缺失的 gnutls）
    requires = "boost/1.90.0", "openssl/3.5.6"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload URL 含 /tar.gz/ 段——conan get() 误判为 zip 报
        # BadZipFile（batsignal/c4project/cct 同款）——显式 filename
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="ccbuild-2.0.11.tar.gz")
        # 系统 flex 未安装 C++ 头文件 FlexLexer.h（ccbuild 的
        # sourceScanner.hh include 它）——从 flex 源码取，复制进
        # ccbuild 源码树 src/（-I src 可搜到）
        flex_dir = os.path.join(self.source_folder, "_flex_src")
        get(self, **self.conan_data["flex_src"], strip_root=True,
            destination=flex_dir, filename="flex-2.6.4.tar.gz")
        flex_lexer = os.path.join(flex_dir, "src", "FlexLexer.h")
        if os.path.isfile(flex_lexer):
            import shutil
            shutil.copy(flex_lexer, os.path.join(self.source_folder, "src",
                                                 "FlexLexer.h"))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        # CMakeLists 无 find_package(boost/openssl)——依赖 include/lib
        # 路径经环境变量注入（CPLUS_INCLUDE_PATH 对 clang++ 生效，
        # LIBRARY_PATH 对链接生效）
        env = Environment()
        for dep in ("boost", "openssl"):
            pkg = self.dependencies[dep].package_folder
            inc = os.path.join(pkg, "include")
            lib = os.path.join(pkg, "lib")
            if os.path.isdir(inc):
                env.append_path("CPLUS_INCLUDE_PATH", inc)
            if os.path.isdir(lib):
                env.append_path("LIBRARY_PATH", lib)
        env.vars(self).save_script("conanbuild_dep_env")

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        # CMakeLists 适配：
        #   1. set (CMAKE_CXX_STANDARD 23) → 20（OHOS clang15 不支持
        #      -std=c++23，报 invalid value——c++2b 也不稳，保守用 20）
        #   2. link_libraries(gomp gnutls) → (gomp ssl crypto)（gnutls
        #      制品仓缺失，MD5 已改 openssl EVP——链接 ssl/crypto）
        cm = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cm, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s = s.replace("set (CMAKE_CXX_STANDARD 23)",
                      "set (CMAKE_CXX_STANDARD 20)\n"
                      "include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src)")
        s = s.replace("add_definitions(-fopenmp)",
                      "add_definitions(-fopenmp)\n"
                      "set(CMAKE_EXE_LINKER_FLAGS \"${CMAKE_EXE_LINKER_FLAGS} -fopenmp\")  # 链接器也需 -fopenmp 才自动链 libomp")
        s = s.replace("link_libraries(gomp gnutls)",
                      "link_libraries(ssl crypto)  # gomp 由 -fopenmp 自动链接（OHOS SDK libomp/libgomp），显式 -lgomp 链接器搜不到")
        with open(cm, "w", encoding="utf-8") as f:
            f.write(s)
        # OHOS 制品仓无 gnutls——MD5 计算改用 openssl EVP API（等价，
        # contentHash.cc 仅 gnutls_hash_init/hash/deinit 三处 + include）：
        #   MD5Info.ih:   <gnutls/gnutls.h>+<gnutls/crypto.h> → <openssl/evp.h>
        #   contentHash.cc: gnutls_hash_hd_t context; gnutls_hash_init
        #   (&context, GNUTLS_DIG_MD5); → EVP_MD_CTX_new() +
        #   EVP_DigestInit_ex(EVP_md5())；gnutls_hash(context, ...) →
        #   EVP_DigestUpdate；gnutls_hash_deinit(context, &md[0]) →
        #   EVP_DigestFinal_ex + EVP_MD_CTX_free。
        for fname in ("MD5Info/MD5Info.ih", "MD5Info/contentHash.cc"):
            p = os.path.join(self.source_folder, "src", fname)
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                s = f.read()
            if "MD5Info.ih" in fname:
                s = s.replace("#include <gnutls/gnutls.h>\n#include <gnutls/crypto.h>",
                              "#include <openssl/evp.h>")
            else:
                s = s.replace(
                    "        gnutls_hash_hd_t context;\n"
                    "        gnutls_hash_init (&context, GNUTLS_DIG_MD5);",
                    "        EVP_MD_CTX *context = EVP_MD_CTX_new();\n"
                    "        EVP_DigestInit_ex(context, EVP_md5(), nullptr);")
                s = s.replace("            gnutls_hash (context, buffer, ifile.gcount());",
                              "            EVP_DigestUpdate(context, buffer, ifile.gcount());")
                s = s.replace(
                    "        gnutls_hash_deinit (context, &md[0]);",
                    "        unsigned int md_len = 0;\n"
                    "        EVP_DigestFinal_ex(context, md, &md_len);\n"
                    "        EVP_MD_CTX_free(context);")
            with open(p, "w", encoding="utf-8") as f:
                f.write(s)
        # src/posix/wordexp.h 是 glibc 拷贝——用 __BEGIN_DECLS/__END_DECLS/
        # __THROW 宏（musl 无）——补兼容宏定义（OHOS musl libc）
        wp = os.path.join(self.source_folder, "src", "posix", "wordexp.h")
        with open(wp, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        macros = (
            "#ifndef __BEGIN_DECLS\n"
            "# ifdef __cplusplus\n"
            "#  define __BEGIN_DECLS extern \"C\" {\n"
            "#  define __END_DECLS }\n"
            "# else\n"
            "#  define __BEGIN_DECLS\n"
            "#  define __END_DECLS\n"
            "# endif\n"
            "#endif\n"
            "#ifndef __THROW\n"
            "# define __THROW __attribute__((__nothrow__))\n"
            "#endif\n"
        )
        if "__BEGIN_DECLS" not in s.split("\n")[0:3] and "#ifndef __BEGIN_DECLS" not in s:
            s = s.replace("#include <features.h>",
                          "#include <features.h>\n" + macros, 1)
        with open(wp, "w", encoding="utf-8") as f:
            f.write(s)
        # src/fileSystem/cwd.cc 的 _GNU_SOURCE 分支用 glibc 专有
        # get_current_dir_name（musl 无）——强制走 getcwd 分支
        # （OHOS musl 兼容）
        cp = os.path.join(self.source_folder, "src", "fileSystem", "cwd.cc")
        with open(cp, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s = s.replace("#ifdef _GNU_SOURCE", "#if 0  // _GNU_SOURCE (glibc get_current_dir_name 无——musl 走 getcwd)")
        with open(cp, "w", encoding="utf-8") as f:
            f.write(s)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.output.info("ccbuild 2.0.11: bin/ccbuild")
        # R38 — CLI 工具
        self.conf_info.define("user.tools.ccbuild:exe", "ccbuild")
