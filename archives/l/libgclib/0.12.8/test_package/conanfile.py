#!/usr/bin/env python3
"""Compile and run the libgclib consumers against the OHOS package.

消费者视角：只用 `-I<include>` + `-L<lib> -lgclib` 以及**依赖方发布的
`cpp_info.cxxflags`**，不碰源码树。

三个二进制：
  test_libgclib_cxx11 / test_libgclib_cxx17 —— 同一份消费者源码分别按
      -std=c++11（上游 Makefile 的 BASEFLAGS）与 -std=c++17（OHOS profile 的
      compiler.cppstd）编译，两次都必须链接成功、运行结果逐条相同。gclib
      全库零 throw、零 RTTI，因此 c++11 编的 .so 必须能被 c++17 的消费者
      链接；反过来，上游只在 c++11 下编过，c++17 这一趟是"消费者视角"
      的实测 —— `GList.hh` 声明/定义异常规格不一致就只在这里暴露（见
      conanfile.py 的 source()：该问题已用补丁修掉，本测试是它的回归防护）。
      每个可执行文件都由两个 TU 链接：test_libgclib.cpp（GHashMap 簇 22 头）
      + test_hdr_cluster_b.cpp（GHash 簇 2 头）—— 两簇同名不同签名的
      `class GHash` 使它们无法共处一个 TU，见两个源文件的头部注释。
      编译开关取自 `libgclib` 的 `cpp_info.cxxflags`（-fno-exceptions /
      -fno-rtti，接口级要求），这条断言本身也验证了依赖方真的发布了它们。
  test_ohos_gclib —— 不链接 libgclib，纯靠 dlopen+dlsym 验证 .so 的平台 ABI、
      导出符号与“加载即完成静态初始化”的运行时契约。

不给 -rpath：运行时靠 conanrun 环境的 LD_LIBRARY_PATH 找 libgclib.so，
避免把 worker 上的绝对路径烘进二进制。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class LibGclibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("cpp", "clang++")

    def _libname(self):
        pkg = self.dependencies["libgclib"]
        for candidate in ("libgclib.so", "libgclib.a"):
            if os.path.isfile(os.path.join(pkg.package_folder, "lib", candidate)):
                return candidate
        return "libgclib.so"

    def test(self):
        pkg = self.dependencies["libgclib"]
        cxx = self._compiler()
        include_dir = os.path.join(pkg.package_folder, "include")
        lib_dir = os.path.join(pkg.package_folder, "lib")
        libname = self._libname()

        if not can_run(self):
            self.output.info("cross-building: libgclib consumer execution skipped")
            return

        # ── 消费者契约：同一份源码，两种 C++ 标准各编一次 ──
        # 编译开关一律取自 libgclib 自己发布的 cpp_info.cxxflags（见
        # conanfile.py 的 package_info），不在 test_package 里另写一套 ——
        # 这样「依赖方到底有没有把接口级开关发布出来」本身也被测到。
        # 之所以必须继承：GList/GVec/GHash 这些模板在库的 TU 和消费者的
        # TU 里都会实例化，两侧的开关不一致就是同实体的两份不同定义。
        flags = " ".join(pkg.cpp_info.cxxflags)
        self.output.info("libgclib usage cxxflags: {}".format(flags or "(none)"))

        sources = " ".join(
            '"{}"'.format(os.path.join(self.source_folder, name))
            for name in ("test_libgclib.cpp", "test_hdr_cluster_b.cpp")
        )
        for std in ("c++11", "c++17"):
            tag = std.replace("+", "")
            executable = os.path.join(self.build_folder, "test_libgclib_" + tag)
            self.run(
                '"{}" -std={} -O1 {} -I"{}" {} -L"{}" -lgclib -pthread -o "{}"'.format(
                    cxx, std, flags, include_dir, sources, lib_dir, executable
                ),
                env="conanbuild",
            )
            self.run('"{}"'.format(executable), env="conanrun")

        # ── 鸿蒙特有：平台 ABI / 导出符号 / 运行时静态初始化 ──
        if libname.endswith(".so"):
            ohos_exe = os.path.join(self.build_folder, "test_ohos_gclib")
            self.run(
                '"{}" -std=c++11 -O1 {} -I"{}" "{}" -ldl -o "{}"'.format(
                    cxx,
                    flags,
                    include_dir,
                    os.path.join(self.source_folder, "test_ohos_gclib.cpp"),
                    ohos_exe,
                ),
                env="conanbuild",
            )
            self.run(
                '"{}" "{}"'.format(ohos_exe, os.path.join(lib_dir, libname)),
                env="conanrun",
            )
        else:
            self.output.info(
                "static build: OHOS platform-ABI test needs a shared object, skipped"
            )
