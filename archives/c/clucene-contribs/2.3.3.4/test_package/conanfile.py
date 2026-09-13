import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 变体无关消费者：链接参数取自各包 cpp_info（contribs .so + core 包
        # 的 core/shared 产物）；contribs/core/zlib 三包 include/lib 都要注入
        contribs = self.dependencies["clucene-contribs"].cpp_info
        core = self.dependencies["clucene-core"].cpp_info
        zlib = self.dependencies["zlib"].cpp_info
        inc = " ".join("-I" + p for p in contribs.includedirs + core.includedirs)
        ldirs = []
        for d in contribs.libdirs + core.libdirs + zlib.libdirs:
            if d not in ldirs:
                ldirs.append(d)
        ld = " ".join("-L" + d for d in ldirs)
        libs = " ".join("-l" + l for l in contribs.libs + core.libs)
        cxx = os.environ.get("CXX", "clang++")
        self.run(
            f"{cxx} smoke_contribs.cpp -o smoke_contribs_probe {inc} {ld} {libs} -lz")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # musl 加载器不消费 conanrunenv 的 LD_LIBRARY_PATH；contribs-lib 的
        # NEEDED(libclucene-core.so.1) 需两包 lib 目录都在路径上
        libpath = []
        for d in (self.dependencies["clucene-contribs"].cpp_info.libdirs
                  + self.dependencies["clucene-core"].cpp_info.libdirs):
            if d not in libpath:
                libpath.append(d)
        libpath = ":".join(libpath)
        self.run(
            f'LD_LIBRARY_PATH="{libpath}" {bash} -c "./smoke_contribs_probe"')
