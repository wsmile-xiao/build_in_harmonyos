import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        # Collect all dep libdirs (tiledb + its 9 mandatory deps) so the linker
        # resolves transitive symbols.
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        ldflags = []
        for ld in libdirs:
            ldflags += ["-L" + ld]
        rpath = ":".join([os.path.abspath(x) for x in libdirs])
        # C API lives in libtiledb.so (core); link it.
        # R33: 编译器必须来自 self.conf_info（tools.build:compiler_executables 由
        # VirtualBuildEnv/工具链注入），不得裸读未定义的 shell 环境变量 CC
        # （release worker 上为空会静默编译失败）。
        compilers = self.conf_info.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", "clang")
        self.run(
            f"{cc} test.c -o test_probe {inc} "
            f"{' '.join(ldflags)} -ltiledb "
            f"-Wl,-rpath,{rpath}"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile + link only (no OHOS runtime)")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
