import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibMatioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 回归前提：TMPDIR 必须指向【长于上游旧 21 字节缓冲区】的可写路径，
        # Mat_VarDelete 的 mkdtemp 才会走补丁的 TMPDIR 分支（test_libmatio.c
        # 的 verify_long_tmpdir_delete 同时断言路径长度 > 21）。
        # 本次 OHOS 实测：不加 LD_LIBRARY_PATH 时加载器找不到 libmatio.so.14
        # 及其 hdf5/zlib 依赖，被测包与依赖的 lib 目录须显式给出；
        # conan 2.29 的 CMake.test(env=) 只接受环境名列表，不接受 "VAR=val"，
        # 故用 self.run() 直接驱动 ctest（与 cmake.test() 的 make test 完全等价）。
        import os
        test_dir = os.path.join(self.build_folder, "run")
        os.makedirs(test_dir, exist_ok=True)
        long_tmpdir = os.path.join(
            test_dir, "long_tmpdir_regression_directory_exceeding_legacy_21_byte_buffer")
        os.makedirs(long_tmpdir, exist_ok=True)

        libpaths = self._run_lib_paths()
        self.output.info("LD_LIBRARY_PATH={}".format(libpaths))
        self.output.info("TMPDIR={}".format(long_tmpdir))

        exe = os.path.join(self.build_folder, "test_libmatio")
        env = "LD_LIBRARY_PATH=\"{libs}\" TMPDIR=\"{tmp}\"".format(
            libs=libpaths, tmp=long_tmpdir)
        self.run("{env} \"{exe}\"".format(env=env, exe=exe), env=["conanbuild"])
        self.output.info("test_libmatio PASSED (exit 0, assertions inside)")

    def _run_lib_paths(self):
        """运行 test 可执行文件所需的共享库目录：被测包 + 依赖。
        从 CMakeDeps 生成器目录的 matio-Target-*.cmake 解析 IMPORTED_LOCATION；
        依赖的 lib 目录直接用其 package folder。"""
        import os
        import re
        import glob
        paths = []
        gen = os.path.join(self.generators_folder)
        for f in glob.glob(os.path.join(gen, "matio-Target-*.cmake")):
            content = open(f).read()
            for m in re.finditer(r'IMPORTED_LOCATION_[A-Z]+\s+"([^"]+)"', content):
                libfile = m.group(1)
                libdir = os.path.dirname(libfile)
                if libdir not in paths:
                    paths.append(libdir)
        for _, dep in self.dependencies.items():
            for libdir in dep.cpp_info.libdirs:
                if libdir not in paths:
                    paths.append(libdir)
        return ":".join(paths)
