#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.build import can_run


class LibrrdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # 编译并运行 C 测试程序验证 librrd API 链通
            # 编译器从 Conan 工具链 conf（tools.build:compiler_executables）解析，
            # 而非宿主进程环境变量——避免用错编译器产生假测试结果
            import os
            cc_map = self.conf.get("tools.build:compiler_executables", default={}) or {}
            cc = cc_map.get("cpp") or cc_map.get("c") or os.environ.get(
                "CC", str(self.settings.compiler))
            src = os.path.join(self.source_folder, "src", "test_librrd.c")
            bin_path = os.path.join(self.build_folder, "test_librrd")
            # 从依赖的 cpp_info 获取 include 路径和库路径
            inc_dirs = self.dependencies["librrd"].cpp_info.includedirs
            lib_dirs = self.dependencies["librrd"].cpp_info.libdirs
            inc_flags = " ".join(f"-I{os.path.join(self.dependencies['librrd'].package_folder, d)}" for d in inc_dirs)
            lib_flags = " ".join(f"-L{os.path.join(self.dependencies['librrd'].package_folder, d)}" for d in lib_dirs)
            # librrd 静态库引用 pcre 符号（rrd_create 正则校验走 pcre 分支），
            # 需同时链接 pcre 库；librrd.a 依赖 librrdupd.a（rrd_seek/rrd_open
            # 等符号在其内），需补 -lrrdupd；系统库 -lm -lpthread -ldl 与配方
            # package_info 声明的 system_libs 保持一致
            pcre = self.dependencies["pcre"]
            pcre_inc = " ".join(
                f"-I{os.path.join(pcre.package_folder, d)}" for d in pcre.cpp_info.includedirs
            )
            pcre_lib = " ".join(
                f"-L{os.path.join(pcre.package_folder, d)}" for d in pcre.cpp_info.libdirs
            )
            self.run(f"{cc} -o {bin_path} {src} {inc_flags} {pcre_inc} {lib_flags} {pcre_lib} -lrrd -lrrdupd -lpcre -lm -lpthread -ldl", env="conanbuild")
            self.run(bin_path, env="conanrun")
