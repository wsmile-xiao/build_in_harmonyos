import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 头闭包用「所有依赖」的 include（coin 的 Inventor/*.h + gl4es 的 GL 头）。
        incs = []
        libs = []
        libdirs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            libs += ["-l" + l for l in _d.cpp_info.libs]
            libdirs += _d.cpp_info.libdirs
        inc = " ".join(incs)
        # rpath 兜底：coin（libCoin.so.80）与 gl4es（libGL.so.1）两个包内 lib 目录
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-Wl,-rpath," + p for p in libdirs]
                        + libs)
        cc = os.environ.get("CXX", "clang++")
        self.run(f"{cc} test.cpp -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += [os.path.join(_d.package_folder, d) for d in _d.cpp_info.libdirs]
        ld = ":".join(libdirs + ["/system/lib64"])
        # LIBGL_* 是 gl4es 运行时接线（OHOS 无 libGLESv2/libGL，GLES 走 libGLESv3.so，
        # EGL 走 libEGL.so）——SoDB::init() 内 glue 层会经 gl4es 探测 GL 能力。
        # test.cpp 不创建 GL 上下文、不做离屏渲染（纯 CPU 解析+字段断言路径）。
        self.run(f"LD_LIBRARY_PATH={ld} "
                 f"LIBGL_GLES=/system/lib64/libGLESv3.so "
                 f"LIBGL_EGL=/system/lib64/libEGL.so ./test_probe")
