import os

from conan import ConanFile


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直呼 CC 编译（仓库惯例，同 freetype）：ohos-aarch64 profile 会经
        # 环境注入 CC；这里再兜底取依赖解析后的编译器路径。
        dep = self.dependencies["libdrawtext"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "clang")

        # 主用例：直接链接消费者 —— 上层应用视角，仅用包内 drawtext.h 与
        # libdrawtext.so（-L<package-libdir> -ldrawtext），不引用源码目录。
        self.run(f"{cc} test.c -o test_consumer {inc} -L{libdir} -ldrawtext")

        # 补充用例：dlopen SONAME 库 + 14 个核心符号 dlsym 解析（R40）。
        so = os.path.join(libdir, "libdrawtext.so")
        self.run(f"{cc} test.c -o test_probe -DSYMBOL_PROBE {inc} -DTARGET_SO='\"{so}\"'")

    def test(self):
        # 本机即目标机（OHOS PC 上原生构建运行），真实执行渲染测试。
        # OHOS 运行时无系统 libfreetype：E505 —— 手动收集全部依赖（含
        # 传递依赖 freetype）的 lib 目录到 LD_LIBRARY_PATH，再运行。
        # 注：d.cpp_info.libdirs 若为相对路径则相对 d.package_folder。
        library_paths = []
        for d in self.dependencies.values():
            if d.cpp_info.libdirs:
                ld = d.cpp_info.libdirs[0]
                if not os.path.isabs(ld):
                    ld = os.path.join(d.package_folder, ld)
                if os.path.isdir(ld):
                    library_paths.append(ld)
        existing = os.environ.get("LD_LIBRARY_PATH")
        if existing:
            library_paths.append(existing)
        ld_path = ":".join(library_paths)
        # 消费者可执行文件 NEEDED libdrawtext.so.0（SONAME），运行时同样
        # 由上述 LD_LIBRARY_PATH 提供解析路径。
        self.run(f"LD_LIBRARY_PATH='{ld_path}' ./test_consumer", env="conanrun")
        libdir = self.dependencies["libdrawtext"].cpp_info.libdirs[0]
        so = os.path.join(libdir, "libdrawtext.so")
        self.run(f"LD_LIBRARY_PATH='{ld_path}' ./test_probe '{so}'", env="conanrun")
        # 鸿蒙特有测试（独立统计）：ELF/SONAME/NEEDED/.codesign/软件 raster
        # 运行，全部针对 Conan 包内安装产物（E212 + NO_OPENGL 验证）。
        pkg = self.dependencies["libdrawtext"].package_folder
        self.run(f"LD_LIBRARY_PATH='{ld_path}' sh ./test_ohos.sh '{pkg}' ./test_consumer", env="conanrun")
        self.output.info("libdrawtext: consumer + OHOS-specific + symbol probe tests passed")
