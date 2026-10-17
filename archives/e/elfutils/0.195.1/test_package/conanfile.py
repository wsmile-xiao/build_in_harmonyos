import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    """消费者侧验证：编译 test.cpp 并**真实执行**，共 27 条断言。

    0.195 的 test_package 只有 1 条 dlopen 断言（且加载的是实体名
    `libelf.so`）；本次扩到 27 条并改为直接链 libelf/libdw/libdebuginfod，
    断言全部走真实 API 调用（见 test.cpp 顶部注释）。
    """
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["elfutils"].cpp_info
        # 头/库闭包要用「所有依赖」（含传递依赖）的 include/lib 目录：
        # elfutils 的公开头会连带引到 musl-fts / musl-obstack 的头，
        # 而 -lelf/-ldw/-ldebuginfod 在链接期还要找到 curl/json-c/zstd 等。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        cc = os.environ.get("CXX", "clang++")
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.libs]
                        + ["-Wl,-rpath," + p for p in libdirs])
        self.run(f"{cc} test.cpp -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # test.cpp 自己会 unset DEBUGINFOD_URLS（离线确定性），并把
        # DEBUGINFOD_CACHE_PATH 指向 argv[1] 这个可写目录，避免测试进程写
        # 调用者的 HOME
        cache_dir = os.path.join(self.build_folder, "debuginfod-cache")
        os.makedirs(cache_dir, exist_ok=True)
        self.run(f"{bash} -c './test_probe \"{cache_dir}\"'", env="conanrun")
