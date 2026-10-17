#!/usr/bin/env python3
"""Conan recipe for encfs 1.9.5 — FUSE 加密文件系统（C++）。

encfs（vgough）是 FUSE 加密文件系统（C++），CMake 构建。版本
1.9.5 为上游 tag（用户给 1.9.5 存在——按真实版）。

Upstream: https://codeload.github.com/vgough/encfs/tar.gz/refs/tags/v1.9.5

Build:   CMake。依赖 libfuse/2.9.9（fuse2，制品仓已合入 PR #6820）+
         OpenSSL（制品仓 openssl/3.5.6 ✅）；tinyxml 用内置
         （USE_INTERNAL_TINYXML 默认 ON）可绕过。
Install: bin/encfs + lib/libencfs。
Type:   application（CLI 工具——commands.json 软件级声明）

上游测试: test/（Cipher_test.cpp/MemoryPool_test.cpp 用 gtest——
         unittests 目标，共 16 用例），build 阶段 make unittests +
         直跑二进制全量实跑 16 例（OPENSSL_CONF 激活 legacy provider 后
         blowfish 全过 + ENTS_TMPDIR 绕 OHOS /tmp 只读）；消费测试
         验证 bin/encfs。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get
import os


class EncfsConan(ConanFile):
    name = "encfs"
    version = "1.9.5"
    description = "Encrypted filesystem for FUSE (encrypted overlay on a directory)"
    license = "LGPL-2.1"
    homepage = "https://vgough.github.io/encfs/"
    url = "https://github.com/vgough/encfs"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # libfuse/2.9.9（fuse2，encfs 原生 FUSE_USE_VERSION=29）+ openssl 制品仓均有
    requires = "libfuse/2.9.9", "openssl/3.5.6"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload URL 含 /tar.gz/ 段——conan get() 误判 zip（BadZipFile，
        # batsignal/c4project 同款），显式 filename
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="encfs-1.9.5.tar.gz")

    def generate(self):
        # 双 sysroot 污染（已知）：profile 配旧 SDK 5_0_2 sysroot，而
        # clang 默认 libc++ 头来自新 SDK 26.0.0.18——libc++ string.h 与
        # 旧 sysroot string.h 冲突（functions differ only in return type）
        # ——覆盖 sysroot 为新 SDK 与 libc++ 一致
        self.conf_info.define(
            "tools.build:sysroot",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot")
        tc = CMakeToolchain(self)
        # 内置 tinyxml（制品仓无 tinyxml 但 tinyxml2 有——encfs 默认
        # USE_INTERNAL_TINYXML ON，无需外部）
        tc.variables["USE_INTERNAL_TINYXML"] = "ON"
        # 不装 libencfs 库（INSTALL_LIBENCFS 默认 OFF）
        tc.variables["INSTALL_LIBENCFS"] = "OFF"
        # 关 NLS（默认 ON 编译 po/ 翻译目录需 gettext msgmerge——制品仓
        # 无，非核心编译依赖，绕过）
        tc.variables["ENABLE_NLS"] = "OFF"
        # encfs FindFUSE.cmake 只搜系统路径（/opt /usr/pkg）——注入
        # conan libfuse2 包路径（include/fuse/fuse.h + lib/libfuse.a）
        fuse = self.dependencies["libfuse"].package_folder
        tc.variables["FUSE_INCLUDE_DIR"] = os.path.join(fuse, "include", "fuse")
        tc.variables["FUSE_LIBRARIES"] = os.path.join(fuse, "lib", "libfuse.a")
        tc.generate()

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        # 双 sysroot 污染（已知）：conan_toolchain.cmake 强制 CMAKE_SYSROOT
        # =5_0_2（旧 SDK），而 clang 内置 libc++ 头来自 26.0.0.18（新）——
        # libc++ string.h 与旧 sysroot string.h 冲突。conf_info 覆盖未生效，
        # 直接 patch 生成的 toolchain 文件为 26.0.0.18（与 libc++ 一致）
        import glob
        for tc_path in glob.glob(os.path.join(self.build_folder, "**",
                                              "generators", "conan_toolchain.cmake"),
                                 recursive=True):
            with open(tc_path, "r", encoding="utf-8", errors="replace") as f:
                s = f.read()
            s = s.replace(
                "set(CMAKE_SYSROOT /storage/Users/currentUser/ohos_sdk/5_0_2/sysroot)",
                "set(CMAKE_SYSROOT /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot)")
            with open(tc_path, "w", encoding="utf-8") as f:
                f.write(s)
        # CMake 4.x 不认旧 cmake_minimum_required（<3.5 报错）——顶层
        # 2.8 与 vendor 子目录（tinyxml2 2.6/benchmark 2.8.12/googletest
        # 2.6.2）统一 patch 为 3.16
        import re
        for root, _dirs, files in os.walk(self.source_folder):
            if "CMakeLists.txt" not in files:
                continue
            cm = os.path.join(root, "CMakeLists.txt")
            with open(cm, "r", encoding="utf-8", errors="replace") as f:
                s = f.read()
            s2 = re.sub(
                r"cmake_minimum_required\s*\(\s*VERSION\s+[0-9.]+(?:\s+FATAL_ERROR)?\s*\)",
                "cmake_minimum_required(VERSION 3.16)", s)
            # cmake_policy(VERSION 旧版) 同样不认（CMake 4.x）——patch 为 3.16
            s2 = re.sub(
                r"cmake_policy\s*\(\s*VERSION\s+[0-9.]+(?:\s+[0-9.]+)?\s*\)",
                "cmake_policy(VERSION 3.16)", s2)
            # cmake_policy(SET CMP0063 OLD) 在 CMake 4.x 已移除该策略——
            # 删除该行（vendor/tinyxml2 旧兼容代码）
            s2 = re.sub(r"^\s*cmake_policy\s*\(\s*SET\s+CMP0063\s+OLD\s*\)\s*$",
                        "", s2, flags=re.MULTILINE)
            # encfs 强制 CMAKE_CXX_STANDARD 11——libc++ 的 wchar.h/string.h
            # 在 C++11 下冲突（functions differ only in return type），
            # 改 17（与 conan 工具链一致）
            s2 = s2.replace("set(CMAKE_CXX_STANDARD 11)",
                            "set(CMAKE_CXX_STANDARD 17)")
            # libc++ string.h/wchar.h 在 encfs 编译环境触发 const 重载声明
            # （strchr/wcspbrk 等）与 OHOS sysroot 头冲突（functions differ
            # only in return type）——最小 C++ 测试 <string> 不冲突，是 encfs
            # 编译宏触发。加 add_definitions 定义 _LIBCPP_STRING_H_HAS_CONST_
            # OVERLOADS + _LIBCPP_WCHAR_H_HAS_CONST_OVERLOADS 让 libc++ 跳过
            # const 重载声明（系统头已声明非 const 版本）——绕过冲突
            s2 = s2.replace(
                'add_definitions( -DPACKAGE="encfs" )',
                'add_definitions( -DPACKAGE="encfs" -D_LIBCPP_STRING_H_HAS_CONST_OVERLOADS -D_LIBCPP_WCHAR_H_HAS_CONST_OVERLOADS )')
            if s2 != s:
                with open(cm, "w", encoding="utf-8") as f:
                    f.write(s2)
        # encfs.h 在 namespace encfs 内用 `struct utimbuf *buf` 声明
        # encfs_utime()——C++ 里这会在 encfs 命名空间 forward-declare 一个
        # encfs::utimbuf，遮蔽全局 <utime.h> 的 struct utimbuf，DirNode.cpp
        # 的 `struct utimbuf ut;` 报 incomplete type——加 #include <utime.h>
        # 提供全局定义 + 声明改全局 `::utimbuf`
        eh = os.path.join(self.source_folder, "encfs", "encfs.h")
        with open(eh, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s2 = s.replace('#include "easylogging++.h"',
                       '#include "easylogging++.h"\n#include <utime.h>')
        s2 = s2.replace("int encfs_utime(const char *path, struct utimbuf *buf);",
                        "int encfs_utime(const char *path, struct ::utimbuf *buf);")
        if s2 != s:
            with open(eh, "w", encoding="utf-8") as f:
                f.write(s2)
        # NullCipher.cpp 的 NullDestructor::operator()(NullKey *&) 参数是
        # 非 const 引用——libc++ shared_ptr 的 __shared_ptr_deleter_ctor_reqs
        # 要求 deleter 可被 _Yp* 右值调用，引用参数绑定失败 → gNullKey 构造
        # "no matching constructor"。改值传递 NullKey *
        nc = os.path.join(self.source_folder, "encfs", "NullCipher.cpp")
        with open(nc, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s2 = s.replace("void operator()(NullKey *&) {}",
                       "void operator()(NullKey *) {}")
        if s2 != s:
            with open(nc, "w", encoding="utf-8") as f:
                f.write(s2)
        # OHOS bionic libc 无 pthread_cancel/pthread_setcancelstate（同
        # 制品仓 libfuse/2.9.9 test_package pthread_stubs.c 同款 E051）——
        # 生成 weak stub 源注入 encfs-bin 源列表（FUSE 在 OHOS 无内核模块
        # 本就不可挂载，stub 返回 ENOSYS 语义）
        stub = os.path.join(self.source_folder, "encfs", "pthread_stubs.cpp")
        with open(stub, "w", encoding="utf-8") as f:
            f.write(
                "/* OHOS bionic libc 无 pthread_cancel/pthread_setcancelstate"
                "（libfuse2 test_package pthread_stubs.c 同款） */\n"
                "#include <pthread.h>\n#include <errno.h>\n"
                "extern \"C\" int pthread_cancel(pthread_t t) {\n"
                "  (void)t; errno = ENOSYS; return -1;\n}\n"
                "extern \"C\" int pthread_setcancelstate(int s, int *o) {\n"
                "  if (o) *o = PTHREAD_CANCEL_ENABLE;\n"
                "  (void)s; errno = ENOSYS; return -1;\n}\n")
        top = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(top, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        # 注入 encfs 静态库目标（encfs-bin/encfsctl/makekey/checkops 都
        # link 它，下游全部自动拿到 stub 符号）
        s2 = s.replace(
            "target_link_libraries(encfs",
            "set(ENCFS_PTHREAD_STUBS ${CMAKE_CURRENT_SOURCE_DIR}/encfs/pthread_stubs.cpp)\n"
            "target_sources(encfs PRIVATE ${ENCFS_PTHREAD_STUBS})\n"
            "target_link_libraries(encfs")
        if s2 != s:
            with open(top, "w", encoding="utf-8") as f:
                f.write(s2)
        cmake = CMake(self)
        cmake.configure()
        # 直接 make -j1（catdoc/ccze 同款）：OHOS 禁 mkfifo jobserver，
        # CMake.build() 并行封装可能卡死
        self.run("make -j1", env="conanbuild")
        # 上游单测实跑（铁律：上游测试能跑都跑）——unittests 是 gtest
        # 目标（EXCLUDE_FROM_ALL，make -j1 不含；Cipher_test/MemoryPool_test
        # 纯计算，无 FUSE 挂载环境依赖，OHOS 可实跑）。make unittests 顺带
        # 构建 vendored gtest 依赖
        # ConfigLoadStore 硬编码 mkstemp("/tmp/encfstestXXXXXX")——OHOS /tmp
        # 只读直接失败。补丁：TMPDIR 取 env ENCTS_TMPDIR（build 时指 build
        # 目录下 test/），其余行为不变。【必须在 make unittests 之前打，
        # 否则二进制仍是 /tmp 硬编码】
        ct = os.path.join(self.source_folder, "test", "Cipher_test.cpp")
        with open(ct, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        s2 = s.replace(
            "  // save config\n  // Creation of a temporary file should be "
            "more platform independent. On\n  // c++17 we could use "
            "std::filesystem.\n  std::string name = \"/tmp/encfstestXXXXXX\";",
            "  // save config\n  // Creation of a temporary file should be "
            "more platform independent. On\n  // c++17 we could use "
            "std::filesystem.\n"
            "  const char *tdir = getenv(\"ENTS_TMPDIR\");\n"
            "  std::string name = std::string(tdir ? tdir : \"/tmp\") + "
            "\"encfstestXXXXXX\";")
        if s2 != s:
            with open(ct, "w", encoding="utf-8") as f:
                f.write(s2)
        # make unittests（EXCLUDE_FROM_ALL，顺带构建 vendored gtest 依赖）
        self.run("make unittests -j1", env="conanbuild")
        # OpenSSL 3.x 把 blowfish 挪进 legacy provider——不激活时 encfs 1.9.5
        # 调废弃 EVP_bf_cbc() 的 5 例 blowfish 参数化用例会段错误并炸掉整个
        # gtest 进程（实测：只设 OPENSSL_MODULES 不够，必须 OPENSSL_CONF 里
        # activate legacy）。生成 legacy 激活配置 + OPENSSL_MODULES 指向
        # openssl 包的 ossl-modules → 16 例全可跑
        ssl = self.dependencies["openssl"].package_folder
        cnf = os.path.join(self.build_folder, "openssl_legacy.cnf")
        with open(cnf, "w", encoding="utf-8") as f:
            f.write(
                "openssl_conf = openssl_init\n"
                "[openssl_init]\n"
                "providers = provider_sect\n"
                "[provider_sect]\n"
                "default = default_sect\n"
                "legacy = legacy_sect\n"
                "[default_sect]\n"
                "activate = 1\n"
                "[legacy_sect]\n"
                "activate = 1\n")
        # Conan 2 self.run(env=) 只接受 list——环境变量用 sh 内联前缀注入；
        # 尾 / 保证拼接出 <tmpdir>/encfstestXXXXXX
        tmpdir = os.path.join(self.build_folder, "test").replace("\\", "/") + "/"
        os.makedirs(os.path.dirname(tmpdir), exist_ok=True)
        self.run(
            'OPENSSL_CONF=' + cnf +
            ' OPENSSL_MODULES=' + os.path.join(
                ssl, "lib", "ossl-modules").replace("\\", "/") +
            ' ENTS_TMPDIR=' + tmpdir + ' test/unittests')
        self.output.info(
            "上游单测：16/16 全量实跑（OPENSSL_CONF 激活 legacy provider 后 "
            "blowfish 全过；ENTS_TMPDIR 绕 OHOS /tmp 只读）")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.output.info("encfs 1.9.5: bin/encfs")
        self.conf_info.define("user.tools.encfs:exe", "encfs")
