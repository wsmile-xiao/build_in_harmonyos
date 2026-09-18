import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # P2 审查覆盖：消费者编译测试实际调用 kylin_ai_generate_gdbus_proto_code
        # 宏，宏执行 gdbus-codegen（由 glib 包提供）
        self.requires("glib/2.88.0.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # 显式 generate() 时 conan 不再自动注入 CMakeDeps——find_package
        # (libkylin-ai-system-private) 依赖其生成 config 文件
        CMakeDeps(self).generate()
        # 注入协议宏变量（消费者侧注入，与 libkysdk-coreai-speech 同模式）：
        #   KYLAI_GDBUS_CODEGEN      — gdbus-codegen 可执行（glib 包 bindir）
        #   KYLAI_GDBUS_PROTOCOL_DIR — gdbus XML 协议目录（本包 resdirs）
        #   KYLAI_PROTO_CMAKE_DIR    — KylinAiProtoFunctions.cmake 宏目录
        tc = CMakeToolchain(self)
        dep = self.dependencies["libkylin-ai-system-private"]
        glib = self.dependencies["glib"]
        tc.variables["KYLAI_GDBUS_CODEGEN"] = os.path.join(
            glib.package_folder, "bin", "gdbus-codegen")
        tc.variables["KYLAI_GDBUS_PROTOCOL_DIR"] = os.path.join(
            dep.package_folder, "share", "kylin-ai", "protocols", "gdbus")
        tc.variables["KYLAI_PROTO_CMAKE_DIR"] = os.path.join(
            dep.package_folder, "share", "KylinAiProto", "cmake")
        # gio/gio.h（glue.h 依赖）与 glib 链接库：收集全部依赖（含传递）的
        # include/lib 目录直接注入 CMake，绕开 pkg-config 的链式 Requires
        # 解析（glib-2.0.pc Requires: pcre2，在 CI/app 环境下易解析失败）
        inc_dirs, lib_dirs = [], []
        for dep in self.dependencies.values():
            # glib 布局：glib.h/gio.h 在 include/glib-2.0/，gio-unix 头在
            # include/gio-unix-2.0/，构建期生成的 glibconfig.h 在
            # lib/glib-2.0/include/（pkg-config 的 Cflags 会展开这些子目录）
            for rel in ("include", "include/glib-2.0", "include/gio-unix-2.0",
                        "lib/glib-2.0/include"):
                d = os.path.join(dep.package_folder, rel)
                if os.path.isdir(d) and d not in inc_dirs:
                    inc_dirs.append(d)
            for rel in ("lib",):
                d = os.path.join(dep.package_folder, rel)
                if os.path.isdir(d) and d not in lib_dirs:
                    lib_dirs.append(d)
        tc.variables["KYLAI_GLIB_INCLUDE_DIRS"] = ";".join(inc_dirs)
        tc.variables["KYLAI_GLIB_LIB_DIRS"] = ";".join(lib_dirs)
        # glib 为静态库：libintl/libffi 用绝对路径链接。CI 上 -lintl 库名可能
        # 被 OHOS 工具链的系统同名 libintl 抢占（其符号为 intl_* 而非 glib
        # 编译期使用的 g_libintl_*），导致 g_libintl_* 未定义；绝对路径直接
        # 定位 glib 包内 libintl.a / libffi.a，消除库名解析歧义
        def _find_lib(dirs, name):
            for d in dirs:
                p = os.path.join(d, name)
                if os.path.isfile(p):
                    return p
            return ""
        tc.variables["KYLAI_INTL_LIB"] = _find_lib(lib_dirs, "libintl.a")
        tc.variables["KYLAI_FFI_LIB"] = _find_lib(lib_dirs, "libffi.a")
        tc.generate()

    def build(self):
        # 构建阶段（构建 uid）编译两个消费者冒烟二进制，并经 cmake.test() 执行
        # ctest 真实运行（P2：实际执行宏生成链路产物；P3b：add_test 注册与实际
        # 执行一致）
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def test(self):
        # L0d 要求 test() 直接 self.run()。本阶段 python 以 app uid 运行，无法
        # exec 构建树产物（HMDFS 跨 app），探针做跨 app 可读的读取断言：
        # 头文件 API / 编译产物 / 协议文件（详见探针头注释）。
        # cmake_layout 下 run 的工作目录是 build folder，探针用源码绝对路径
        pkg = self.dependencies["libkylin-ai-system-private"].package_folder
        probe = os.path.join(self.source_folder, "test_kylin_ai_system_private.py")
        self.run(f"python3 {probe} {pkg} {self.build_folder}", env="conanrun")
