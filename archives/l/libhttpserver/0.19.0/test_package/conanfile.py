import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libhttpserver 的公共头 include <microhttpd.h>（传递依赖）——显式声明
        # 才能把 libmicrohttpd 的 include 带进头闭包。
        self.requires("libmicrohttpd/1.0.1")

    def build(self):
        dep = self.dependencies["libhttpserver"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libhttpserver.so")
        cxx = os.environ.get("CXX", "clang++")
        std_flag = "-std=gnu++17"
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        if os.path.isdir(sdk_lib):
            libdirs.append(sdk_lib)
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.libs]
                        + ["-Wl,-rpath," + p for p in libdirs] + ["-lc++", "-lpthread", "-ldl"])
        self.run(f"{cxx} {std_flag} test.cpp -o test_probe {inc} -DTARGET_SO='\"{so}\"' {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        export_ld = f"export LD_LIBRARY_PATH={sdk_lib}:$LD_LIBRARY_PATH; " if os.path.isdir(sdk_lib) else ""
        self.run(f"{bash} -c '{export_ld}./test_probe'", env="conanrun")
