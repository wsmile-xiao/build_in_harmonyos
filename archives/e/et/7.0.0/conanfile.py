#!/usr/bin/env python3
"""Conan recipe for et 7.0.0 (EternalTerminal).

EternalTerminal — a remote shell that reconnects without dropping the
session. CMake project, C++17, Apache-2.0. Built with -DDISABLE_VCPKG
so vendored deps in external_imported/ are used (Catch2, cxxopts,
cpp-httplib, json, simpleini, sole, …), while the heavy run-time deps
(zlib, openssl, libsodium, protobuf, absl, nlohmann_json) come from
conan requires.
"""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class EtConan(ConanFile):
    name = "et"
    version = "7.0.0"
    description = "EternalTerminal — reconnectable remote shell"
    license = "Apache-2.0"
    homepage = "https://github.com/MisterTea/EternalTerminal"
    url = "https://github.com/MisterTea/EternalTerminal"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = ("CMakeDeps",)

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_sentry": [True, False],
        "with_telemetry": [True, False],
        "build_testing": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_sentry": False,
        "with_telemetry": False,
        "build_testing": False,
    }

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def _sdk_llvm_libdir(self):
        """Derive the active OHOS SDK llvm/lib directory that contains
        the ABI-matched libxml2.so.16 the host lld links against."""
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            compiler = os.path.realpath(cxx)
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _build_environment(self):
        """Prepend the SDK llvm/lib to LD_LIBRARY_PATH so the host lld
        can load its ABI-matched libxml2.so.16 during CMake configure/build.
        CI shells prepend ~/usr/local/lib which can shadow the SDK's
        libxml2.so.16 and prevent lld from starting."""
        environment = Environment()
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_llvm_lib}"
            )
            environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanException(
                f"et supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("openssl/1.1.1w")
        self.requires("libsodium/1.0.22")
        # protobuf/33.6.1 is published in the ohpcd registry (PR #6251).
        # Its static libprotobuf.a references absl + utf8_range symbols,
        # so et must link abseil-cpp at build time.  utf8_range is shipped
        # inside the protobuf 33.6.1 package (lib/cmake/utf8_range/).
        self.requires("protobuf/33.6.1", transitive_headers=True)
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        self.requires("nlohmann_json/3.1.1")
        if self.options.with_sentry:
            self.requires("sentry-native/0.13.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        # ⭐ et 的 CMakeLists.txt 在 project() 之前检查 DISABLE_VCPKG,
        # 但 Conan 的 CMakeToolchain.variables 在 project() 之后才生效,
        # 所以 if(DISABLE_VCPKG) 永远 false，走 else 分支尝试 vcpkg
        # bootstrap（在鸿蒙无网络/git 时卡死）。
        # 修复：patch CMakeLists.txt 强制走 DISABLE_VCPKG 分支
        # （用 vendored external_imported/ 依赖）。
        if os.path.isfile(cmakelists):
            replace_in_file(
                self,
                cmakelists,
                "if(DISABLE_VCPKG)",
                "if(TRUE)",
                strict=False,
            )
            self.output.info("Patched CMakeLists.txt: if(DISABLE_VCPKG) -> if(TRUE)")
        # ⭐ protobuf 33.6.1 (≥4) triggers find_package(absl REQUIRED) +
        # find_package(utf8_range CONFIG REQUIRED). archives' abseil-cpp
        # uses cmake_file_name="abseil-cpp" (not "absl").  But
        # protobuf 33.6.1's static libprotobuf.a does NOT inline the
        # absl/utf8_range symbols — it still references them — so we
        # must keep the block and link those libs at build time.
        # Fix: replace target names with what conan CMakeDeps exposes.
        #   absl::log_internal_check_op -> abseil-cpp::abseil-cpp
        #   utf8_range::utf8_validity   -> keep (protobuf 33.6.1 ships
        #                                 lib/cmake/utf8_range/)
        #   utf8_range::utf8_range      -> keep
        if os.path.isfile(cmakelists):
            with open(cmakelists, "r", encoding="utf-8") as fh:
                txt = fh.read()
            # find_package(absl REQUIRED) -> find_package(abseil-cpp REQUIRED)
            txt = txt.replace(
                "find_package(absl REQUIRED)",
                "find_package(abseil-cpp REQUIRED)",
                1,
            )
            # absl::log_internal_check_op -> abseil-cpp::abseil-cpp
            txt = txt.replace(
                "absl::log_internal_check_op",
                "abseil-cpp::abseil-cpp",
                1,
            )
            with open(cmakelists, "w", encoding="utf-8") as fh:
                fh.write(txt)
            self.output.info("Patched CMakeLists.txt: absl/utf8_range block kept, target names fixed")
        # ⭐ protoc 在生成 ETerminal.pb.cc 时，ETerminal.proto 第 5 行
        # import "ET.proto"，但 protoc 的工作目录不对，找不到 ET.proto。
        # 修复：在 protobuf_generate_cpp 之前设 Protobuf_IMPORT_DIRS
        # 指向 proto/ 目录，让 protoc 能解析 import。
        if os.path.isfile(cmakelists):
            with open(cmakelists, "r", encoding="utf-8") as fh:
                txt = fh.read()
            old_gen = "protobuf_generate_cpp(ET_SRCS ET_HDRS proto/ET.proto)"
            new_gen = (
                "set(Protobuf_IMPORT_DIRS ${CMAKE_CURRENT_SOURCE_DIR}/proto)\n"
                "protobuf_generate_cpp(ET_SRCS ET_HDRS proto/ET.proto)"
            )
            if old_gen in txt:
                txt = txt.replace(old_gen, new_gen, 1)
                with open(cmakelists, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                self.output.info("Patched CMakeLists.txt: added Protobuf_IMPORT_DIRS for proto imports")
        # ⭐ et CMakeLists.txt 第 376 行 ${PROTOBUF_INCLUDE_DIRS} 是
        # CMake Module 模式变量（FindProtobuf.cmake 提供），但 conan
        # CMakeDeps 生成 Protobuf-config.cmake（Config 模式），不设
        # PROTOBUF_INCLUDE_DIRS。修复：替换为 ${Protobuf_INCLUDE_DIRS}
        # （CMakeDeps 生成的变量名），让 protobuf include 路径正确
        # 传递到 et-lib。
        if os.path.isfile(cmakelists):
            with open(cmakelists, "r", encoding="utf-8") as fh:
                txt = fh.read()
            if "${PROTOBUF_INCLUDE_DIRS}" in txt:
                txt = txt.replace(
                    "${PROTOBUF_INCLUDE_DIRS}",
                    "${Protobuf_INCLUDE_DIRS}",
                )
                with open(cmakelists, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                self.output.info("Patched CMakeLists.txt: PROTOBUF_INCLUDE_DIRS -> Protobuf_INCLUDE_DIRS")
        # ⭐ ${PROTOBUF_LIBS} 由 et CMakeLists.txt L264/L270 patch 后定义为
        #   protobuf::libprotobuf abseil-cpp::abseil-cpp
        #   utf8_range::utf8_validity utf8_range::utf8_range
        # et 的 et/etserver/etterminal/htm/htmd 各 target 通过
        # target_link_libraries(... ${PROTOBUF_LIBS}) 链接完整集合，
        # 这样 protobuf 静态库引用的 absl/utf8_range 符号才能解析。
        # 因此此处 NOT 替换 ${PROTOBUF_LIBS}：保留变量原样，让 et 上游
        # 的 target_link_libraries(${PROTOBUF_LIBS}) 正常展开。
        # ⭐ et 用全局 include_directories(${PROTOBUF_INCLUDE_DIRS})
        # 但 CMakeDeps 不设这个变量。protobuf::libprotobuf target 的
        # INTERFACE_INCLUDE_DIRECTORIES 会自动传递给链接它的 target。
        # 修复：把 include_directories 段里的 ${Protobuf_INCLUDE_DIRS}
        # 替换为 ${protobuf_INCLUDE_DIRS}（CMakeDeps 的命名规范），如果
        # 还是空，就直接删掉这行。
        if os.path.isfile(cmakelists):
            with open(cmakelists, "r", encoding="utf-8") as fh:
                txt = fh.read()
            # CMakeDeps 生成的变量名是 <pkg>_INCLUDE_DIRS（小写 pkg）
            old_inc = "${Protobuf_INCLUDE_DIRS}"
            new_inc = "${protobuf_INCLUDE_DIRS}"
            if old_inc in txt:
                txt = txt.replace(old_inc, new_inc, 1)
                with open(cmakelists, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                self.output.info("Patched CMakeLists.txt: Protobuf_INCLUDE_DIRS -> protobuf_INCLUDE_DIRS")
        # ⭐ et CMakeLists.txt 用 CMake 内置 FindOpenSSL.cmake 的
        # target 名 OpenSSL::SSL / OpenSSL::Crypto, 但 conan CMakeDeps
        # 对 openssl/1.1.1w (无显式 components) 生成的 target 是
        # openssl::openssl。同理 ZLIB::ZLIB → zlib::zlib。
        # ⭐ et 上游 CMakeLists.txt 用 ZLIB::ZLIB（大写）和
        # openssl::openssl（小写）。CMakeDeps 对 zlib/1.3.1 生成的
        # target 名因 recipe revision 不同而异：
        #   - CI 环境（zlib/1.3.1#2ee7c0ee）：zlib::zlib（小写）
        #   - 本地环境（zlib/1.3.1#ec22e0f2）：ZLIB::ZLIB（大写）
        # 单一替换无法兼容两种环境。修复：在 find_package(ZLIB) 之后
        # 插入双 target 兼容逻辑——无论 CMakeDeps 创建哪个大小写，
        # 都把缺失的那个作为 IMPORTED ALIAS 创建，让 ZLIB::ZLIB 和
        # zlib::zlib 都指向同一个库。OpenSSL 同理处理。
        if os.path.isfile(cmakelists):
            replace_in_file(self, cmakelists, "OpenSSL::SSL", "openssl::openssl", strict=False)
            replace_in_file(self, cmakelists, "OpenSSL::Crypto", "openssl::openssl", strict=False)
            # ⭐ CI 的 zlib/1.3.1#2ee7c0ee CMakeDeps 只创建小写 zlib::zlib，
            # 本地 zlib/1.3.1#ec22e0f2 只创建大写 ZLIB::ZLIB。et 上游 link
            # 的是 ZLIB::ZLIB。在 find_package(ZLIB) 之后插入双 target 兼容
            # 逻辑：无论 CMakeDeps 创建哪个大小写，都把缺失的那个作为
            # IMPORTED ALIAS 创建，让 ZLIB::ZLIB 和 zlib::zlib 都指向同一个库。
            replace_in_file(
                self,
                cmakelists,
                "find_package(ZLIB REQUIRED)",
                (
                    "find_package(ZLIB REQUIRED)\n"
                    "# Conan CMakeDeps target name varies by recipe revision:\n"
                    "#   CI  zlib/1.3.1#2ee7c0ee  -> zlib::zlib  (lowercase)\n"
                    "#   loc zlib/1.3.1#ec22e0f2 -> ZLIB::ZLIB  (uppercase)\n"
                    "# Create whichever alias is missing so both names resolve.\n"
                    "if(TARGET zlib::zlib AND NOT TARGET ZLIB::ZLIB)\n"
                    "    add_library(ZLIB::ZLIB ALIAS zlib::zlib)\n"
                    "elseif(TARGET ZLIB::ZLIB AND NOT TARGET zlib::zlib)\n"
                    "    add_library(zlib::zlib ALIAS ZLIB::ZLIB)\n"
                    "endif()"
                ),
                strict=False,
            )
            self.output.info("Patched CMakeLists.txt: OpenSSL::SSL/Crypto -> openssl::openssl, ZLIB double-target alias")
        # ⭐ et CMakeLists.txt 第 328-329 行链接 atomic + stdc++fs,
        # 这是 Linux GCC 的标准库。鸿蒙用 clang + libc++, 没这两个库。
        # 修复：删掉 atomic + stdc++fs 链接。
        if os.path.isfile(cmakelists):
            with open(cmakelists, "r", encoding="utf-8") as fh:
                txt = fh.read()
            old_link = "    atomic\n    stdc++fs\n"
            if old_link in txt:
                txt = txt.replace(old_link, "", 1)
                with open(cmakelists, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                self.output.info("Patched CMakeLists.txt: removed atomic + stdc++fs link")
        # ⭐ vendored cpp-httplib (external_imported/cpp-httplib/httplib.h)
        # 硬性要求 OpenSSL >= 3.0.0, 但 archives 用 OpenSSL 1.1.1w.
        # 修复：
        # 1. 把第 312-313 行 #elif OPENSSL_VERSION_NUMBER < 0x30000000L
        #    #error ... 改为 #define SSL_get1_peer_certificate
        #    SSL_get_peer_certificate（接受 1.1.1w，用旧 API 名）
        # 2. 这样 SSL_get1_peer_certificate (第 9765 行) 会映射到
        #    SSL_get_peer_certificate（OpenSSL 1.1.1 的 API 名）
        httplib = os.path.join(
            self.source_folder, "external_imported", "cpp-httplib", "httplib.h"
        )
        if os.path.isfile(httplib):
            with open(httplib, "r", encoding="utf-8") as fh:
                txt = fh.read()
            old_check = (
                '#elif OPENSSL_VERSION_NUMBER < 0x30000000L\n'
                '#error Sorry, OpenSSL versions prior to 3.0.0 are not supported\n'
                '#endif'
            )
            new_check = (
                '#elif OPENSSL_VERSION_NUMBER < 0x30000000L\n'
                '#define SSL_get1_peer_certificate SSL_get_peer_certificate\n'
                '#endif'
            )
            if old_check in txt:
                txt = txt.replace(old_check, new_check, 1)
                with open(httplib, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                self.output.info("Patched cpp-httplib: accept OpenSSL 1.1.1w (SSL_get_peer_certificate)")

    def generate(self):
        tc = CMakeToolchain(self)
        # Don't use vcpkg — vendored external_imported/ deps are used,
        # and heavy run-time deps come from conan requires.
        tc.variables["DISABLE_VCPKG"] = "ON"
        # Tell CMake we're on Linux/OHOS even when cross-compiling.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Disable optional pieces to shrink the dependency surface.
        tc.variables["BUILD_TESTING"] = "ON" if self.options.build_testing else "OFF"
        tc.variables["DISABLE_SENTRY"] = "ON" if not self.options.with_sentry else "OFF"
        tc.variables["DISABLE_TELEMETRY"] = "ON" if not self.options.with_telemetry else "OFF"
        tc.variables["CODE_COVERAGE"] = "OFF"
        tc.variables["FUZZING"] = "OFF"
        tc.variables["INSTALL_BASH_COMPLETION"] = "OFF"
        tc.variables["INSTALL_ZSH_COMPLETION"] = "OFF"
        # Protobuf: force static lib use so the link is self-contained.
        tc.variables["Protobuf_USE_STATIC_LIBS"] = "ON"
        # CMake's FindProtobuf.cmake needs the protoc executable path to
        # run protobuf_generate_cpp().  Conan's CMakeDeps exposes it via
        # the protobuf::protoc target's IMPORTED_LOCATION, but CMake's
        # built-in FindProtobuf.cmake looks for the Protobuf_PROTOC_EXECUTABLE
        # variable or protoc in PATH.  Set it explicitly.
        if "protobuf" in self.dependencies:
            pb = self.dependencies["protobuf"]
            protoc = os.path.join(pb.package_folder, "bin", "protoc")
            if os.path.isfile(protoc):
                tc.variables["Protobuf_PROTOC_EXECUTABLE"] = protoc
                self.output.info(f"Set Protobuf_PROTOC_EXECUTABLE={protoc}")
            # et CMakeLists.txt uses include_directories(${PROTOBUF_INCLUDE_DIRS})
            # which is set by CMake's built-in FindProtobuf.cmake (Module mode).
            # But the built-in FindProtobuf.cmake doesn't read conan CMakeDeps
            # config, so Protobuf_INCLUDE_DIRS may be empty/wrong.  Set it
            # explicitly to the conan protobuf package's include dir.
            # NOTE: source() patches ${PROTOBUF_INCLUDE_DIRS} ->
            # ${protobuf_INCLUDE_DIRS} (CMakeDeps naming), so the
            # tc.variables key must be protobuf_INCLUDE_DIRS (lowercase p).
            # protobuf 33.6.1 headers #include <absl/...>, so abseil-cpp's
            # include dir must be appended too.
            pb_include = os.path.join(pb.package_folder, "include")
            if os.path.isdir(pb_include):
                inc_dirs = pb_include
                if "abseil-cpp" in self.dependencies:
                    abs_inc = os.path.join(
                        self.dependencies["abseil-cpp"].package_folder, "include"
                    )
                    if os.path.isdir(abs_inc):
                        inc_dirs = inc_dirs + ";" + abs_inc
                tc.variables["protobuf_INCLUDE_DIRS"] = inc_dirs
                self.output.info(f"Set protobuf_INCLUDE_DIRS={inc_dirs}")
            # protobuf 33.6.1 ships lib/cmake/utf8_range/ inside its own
            # package folder.  CMakeDeps doesn't generate a utf8_range
            # config (utf8_range is not a separate conan package), so
            # point utf8_range_DIR at protobuf's lib/cmake/utf8_range/
            # to let find_package(utf8_range CONFIG REQUIRED) succeed.
            #
            # NOTE: do NOT use tc.variables["CMAKE_PREFIX_PATH"] for this.
            # Conan's CMakeToolchain emits
            #   set(CMAKE_PREFIX_PATH "<value>" CACHE STRING "...")
            # which *overrides* the earlier
            #   list(PREPEND CMAKE_PREFIX_PATH ${CMAKE_CURRENT_LIST_DIR})
            # that puts the generators/ folder on the search path.  The
            # net effect is that find_package(abseil-cpp REQUIRED) can no
            # longer see abseil-cpp-config.cmake in generators/ and fails
            # with "Could NOT find absl" / "Could not find a package
            # configuration file provided by abseil-cpp".
            #
            # Using <pkg>_DIR instead is robust: CMake's config-mode search
            # honours abseil-cpp_DIR / utf8_range_DIR directly, independent
            # of whatever CMAKE_PREFIX_PATH ends up being.
            pb_cmake = os.path.join(pb.package_folder, "lib", "cmake")
            utf8_cmake = os.path.join(pb_cmake, "utf8_range")
            if os.path.isdir(utf8_cmake):
                tc.variables["utf8_range_DIR"] = utf8_cmake
                self.output.info(f"Set utf8_range_DIR={utf8_cmake}")
            # abseil-cpp-config.cmake is generated by CMakeDeps into the
            # et build's generators/ folder.  Point abseil-cpp_DIR there
            # explicitly so find_package(abseil-cpp REQUIRED) succeeds
            # even if CMAKE_PREFIX_PATH was reset by the toolchain.
            if "abseil-cpp" in self.dependencies:
                gen_dir = os.path.join(
                    self.generators_folder
                    if hasattr(self, "generators_folder")
                    else os.path.join(self.build_folder, "generators"),
                )
                tc.variables["abseil-cpp_DIR"] = gen_dir
                self.output.info(f"Set abseil-cpp_DIR={gen_dir}")
                # protobuf 33.6.1 ships its own protobuf-config.cmake which
                # does `find_package(absl CONFIG)` internally.  abseil-cpp
                # packages its CMake config as lib/cmake/absl/abslConfig.cmake
                # (upstream name "absl"), so point absl_DIR there.
                absl_cmake = os.path.join(
                    self.dependencies["abseil-cpp"].package_folder,
                    "lib", "cmake", "absl",
                )
                if os.path.isdir(absl_cmake):
                    tc.variables["absl_DIR"] = absl_cmake
                    self.output.info(f"Set absl_DIR={absl_cmake}")
        # CMakeDeps generates <pkg>-config.cmake into the et build's
        # generators/ folder, but conan_toolchain.cmake resets
        # CMAKE_PREFIX_PATH, so find_package(zlib)/find_package(openssl)
        # can't locate zlib-config.cmake / openssl-config.cmake.  Point
        # <pkg>_DIR at the generators folder explicitly (same trick as
        # abseil-cpp_DIR above).
        gen_dir = os.path.join(
            self.generators_folder
            if hasattr(self, "generators_folder")
            else os.path.join(self.build_folder, "generators"),
        )
        for pkg in ("zlib", "openssl"):
            tc.variables[f"{pkg}_DIR"] = gen_dir
            self.output.info(f"Set {pkg}_DIR={gen_dir}")
        tc.generate()
        # CMakeDeps is declared in `generators` attribute, so Conan 2
        # auto-invokes it. Do NOT instantiate CMakeDeps(self).generate()
        # here — Conan 2 raises "declared in generators but instantiated
        # in generate() too".

    def build(self):
        # The OHOS SDK lld links libxml2.so.16 from its own llvm/lib.
        # CI shells prepend ~/usr/local/lib which can shadow that and
        # crash lld ("Error loading shared library libxml2.so.16").
        # Wrap configure/build in the SDK runtime path so lld starts;
        # the environment ends before package() to avoid leaking host
        # libs into the installed tree.
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.install()
        # Licenses
        for lic in ("LICENSE", "COPYING"):
            src = os.path.join(self.source_folder, lic)
            if os.path.isfile(src):
                copy(self, lic, src=src, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # et ships binaries (et, etserver, etterminal) + a few libs.
        # Consumers linking against et's libs will need these:
        self.cpp_info.libs = ["et_core", "terminal", "et_terminal_lib"]
        self.cpp_info.set_property("cmake_file_name", "et")
        self.cpp_info.set_property("cmake_target_name", "et::et")
