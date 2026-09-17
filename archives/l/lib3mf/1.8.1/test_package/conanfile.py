import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["lib3mf"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（lib3mf 头会 #include <zip.h>，
        # 需带上 libzip/zlib/ossp-uuid 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        # lib3mf 是 C++ 库但对外导出 C 接口（NMR_DLLInterfaces.h），测试用 C++ 编译器
        # 链接以带上 libc++_shared 运行时。
        cxx = os.environ.get("CXX", "clang++")
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l3MF"]
                        + ["-Wl,-rpath," + p for p in libdirs])
        so = ""
        for p in libdirs:
            cand = os.path.join(p, "lib3MF.so")
            if os.path.exists(cand):
                so = cand
                break
        self.run(f"{cxx} -std=c++11 test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # OHOS PC 本机执行需要系统 libc++_shared.so（/system/lib64）；
        # env="conanrun" 会重建环境变量，须在命令内显式前置路径。
        import os
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'LD_LIBRARY_PATH=/system/lib64:$LD_LIBRARY_PATH {bash} -c "./test_probe"',
                 env="conanrun")
