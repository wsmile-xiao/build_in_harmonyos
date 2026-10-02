import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building

HNP_BIN = "/data/service/hnp/bin"


def _tool(name: str) -> str:
    """探针编译器：优先 conanbuild 环境（profile buildenv 注入），否则
    依次回退 PATH 查找与鸿蒙 SDK 工具链绝对路径。"""
    found = shutil.which(name)
    if found:
        return found
    fallback = os.path.join(HNP_BIN, name)
    if os.path.isfile(fallback):
        return fallback
    return name


class GiftTestPackage(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        """编译运行时探针：链接包内全部 9 个共享库（NEEDED 同加载组，
        BIND_NOW 全量重定位，任一库加载失败即失败）+ 传递依赖
        expat（动态）/libuuid（静态）。"""
        gift = self.dependencies["gift"].cpp_info
        # gift 9 库在前（依赖序，与 recipe package_info 一致），
        # 传递依赖在后（libuuid 为静态 .a，须置于其消费者之后）。
        # 头文件路径取所有依赖的 includedirs（gift 为嵌套布局：
        # include/<lib>/include/*.h，由 recipe package_info 展开）。
        incs = []
        ldirs = list(gift.libdirs)
        libs = list(gift.libs)
        for _req, dep in self.dependencies.items():
            incs += ["-I" + p for p in dep.cpp_info.includedirs]
            if _req.ref.name == "gift":
                continue
            ldirs += dep.cpp_info.libdirs
            libs += dep.cpp_info.libs
        lflag = " ".join("-L" + p for p in ldirs)
        llibs = " ".join("-l" + n for n in libs)
        cxx = _tool(os.environ.get("CXX", "clang++"))
        iflag = " ".join(incs)
        self.run(
            f"{cxx} test_probe.cc -o test_probe {iflag} {lflag} {llibs} "
            f"-lm -lpthread -ldl -Wl,--allow-shlib-undefined"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # conanrun 环境提供传递依赖 libexpat.so 的搜索路径；gift 自身
        # libdir 若未被聚合则在此追加到头部（注意是追加而非覆盖，
        # musl exec 需要 NEEDED 搜索路径覆盖全部 9 库 + libexpat.so）。
        libdir = self.dependencies["gift"].cpp_info.libdirs[0]
        self.run(
            f"LD_LIBRARY_PATH='{libdir}'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}} ./test_probe",
            env="conanrun",
        )
