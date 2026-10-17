import glob
import os

from conan import ConanFile
from conan.tools.build import can_run


class GdcmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(getattr(self, "tested_reference_str", None) or "gdcm/3.2.11")

    def build(self):
        # 与主配方一致的裸编译路线（os=OHOS 下 CMakeToolchain 的 CMAKE_SYSTEM_NAME 映射问题 ML-0035）
        dep = self.dependencies["gdcm"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            for p in _d.cpp_info.aggregated_components().includedirs:
                incs.append("-I" + p)
                # gdcm 头文件装在 include/gdcm-<ver>/ 子目录
                sub = os.path.join(p, "gdcm-3.2")
                if os.path.isdir(sub):
                    incs.append("-I" + sub)
        inc = " ".join(incs)
        libdir = dep.aggregated_components().libdirs[0]
        # 动态发现包内 .a（上游库集随 USE_SYSTEM 开关变化：gdcmrle 不独立成库等）
        archives = sorted(glob.glob(os.path.join(libdir, "*.a")))
        # conan 依赖（zlib/expat）的库也要链接——从各依赖包 libdirs 动态取
        dep_libs = []
        for _ref, _d in self.dependencies.items():
            if str(_d.ref.name) == "gdcm":
                continue
            for d in _d.cpp_info.aggregated_components().libdirs:
                for l in sorted(glob.glob(os.path.join(d, "*.a")) + glob.glob(os.path.join(d, "*.so*"))):
                    if os.path.isfile(l) and not os.path.islink(l):
                        dep_libs.append(l)
        libs = " ".join(archives + dep_libs)
        cxx = os.environ.get("CXX", "clang++")
        self.run(
            f"{cxx} -std=c++11 -O1 test_gdcm.cpp -o test_gdcm {inc} "
            f"-L{libdir} {libs} -Wl,--allow-shlib-undefined"
        )

    def test(self):
        if can_run(self):
            # 运行时依赖（实测 NEEDED）：libexpat.so（conan 依赖）+ libc++_shared.so（SDK
            # llvm/lib/aarch64-linux-ohos）。不 source conanrun.sh——其继承的系统默认
            # LD_LIBRARY_PATH 含缺符号的 libc++ 变体，实测最小路径集即可正确运行。
            import os as _os
            parts = []
            for dep in ("expat", "zlib"):
                if dep in self.dependencies:
                    for d in self.dependencies[dep].cpp_info.aggregated_components().libdirs:
                        parts.append(d)
            for sdk_lib in (
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
                "/data/service/hnp/lib",
            ):
                if _os.path.isdir(sdk_lib):
                    parts.append(sdk_lib)
            ld = ":".join(parts)
            self.run('LD_LIBRARY_PATH="{}" ./test_gdcm'.format(ld))
        else:
            self.output.info("Cross-building: skip running test executable")
