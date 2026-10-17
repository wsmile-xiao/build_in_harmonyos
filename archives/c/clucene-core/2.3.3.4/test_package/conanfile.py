import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 变体无关消费者：链接参数取自包 cpp_info（shared 变体链 .so，
        # static 变体链 -static .a），不硬编码库名
        dep = self.dependencies["clucene-core"].cpp_info
        inc = " ".join("-I" + p for p in dep.includedirs)
        libdir = dep.libdirs[0]
        libs = " ".join("-l" + l for l in dep.libs)
        cxx = os.environ.get("CXX", "clang++")
        # 真实消费者：编译 + 链接 clucene 并运行，
        # 覆盖 IndexWriter/IndexReader/QueryParser/IndexSearcher/Hits。
        self.run(f"{cxx} smoke.cpp -o smoke_probe {inc} -L{libdir} {libs} -lz")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 本机 musl 加载器不消费 conanrunenv 的 LD_LIBRARY_PATH，显式指向包 lib 目录
        libpath = ":".join(self.dependencies["clucene-core"].cpp_info.libdirs)
        self.run(f'LD_LIBRARY_PATH="{libpath}" {bash} -c "./smoke_probe"')
