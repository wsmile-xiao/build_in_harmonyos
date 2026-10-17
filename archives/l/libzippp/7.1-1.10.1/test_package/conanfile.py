import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libzippp"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（libzippp.h #include <zip.h>，须带上 libzip 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libzippp.so")
        cxx = os.environ.get("CXX", "clang++")
        std_flag = "-std=gnu++11"
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        # OHOS C++ 运行时：SDK llvm/lib 下有 libc++.so（链接器脚本）与 libc++_shared.so，
        # 默认搜索路径不含 SDK lib —— 链接与运行都要显式给路径（jinja2cpp 0.9 同款经验）。
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        if os.path.isdir(sdk_lib):
            libdirs.append(sdk_lib)
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.libs]
                        + ["-Wl,-rpath," + p for p in libdirs] + ["-lc++", "-ldl"])
        self.run(f"{cxx} {std_flag} test.cpp -o test_probe {inc} -DTARGET_SO='\"{so}\"' {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        if False:
            self.output.info("skip_test_run：GUI/app 库只验编译+链接")
            return
        # OHOS C++ 运行时：test_probe 与 libzippp.so 均 NEEDED libc++_shared.so，
        # 加载器默认搜索路径不含 SDK llvm/lib —— 运行时显式注入（jinja2cpp 0.9 同款经验）。
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        export_ld = f"export LD_LIBRARY_PATH={sdk_lib}:$LD_LIBRARY_PATH; " if os.path.isdir(sdk_lib) else ""
        self.run(f"{bash} -c '{export_ld}./test_probe'", env="conanrun")
