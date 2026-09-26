import os
from conan import ConanFile
from conan.tools.build import cross_building


class LibnetfilterLogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs = []
        libdirs = []
        libs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            libdirs += _d.cpp_info.libdirs
            libs += ["-l" + l for l in _d.cpp_info.libs]
        cc = os.environ.get("CC", "clang")
        link = " ".join(["-L" + p for p in libdirs] + libs
                        + ["-Wl,-rpath," + p for p in libdirs])
        # OHOS：bionic 式 uapi 头与 musl 冲突，抑制内核 socket/nfnetlink 头
        # 并以 musl 侧等价定义补齐（与主配方 CPPFLAGS 同源）。
        ohos_defs = ("-D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t=sa_family_t "
                     "-D_UAPI_NFNETLINK_H") if self.settings.os == "OHOS" else ""
        self.run(f"{cc} {ohos_defs} test_consumer.c -o test_consumer "
                 f"{' '.join(sorted(set(incs)))} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # 直连执行：profile 的 CONFIG_SHELL(hnp bash) 在 HMDFS 下 getcwd 必挂（E386）
        self.run("./test_consumer", env="conanrun")
