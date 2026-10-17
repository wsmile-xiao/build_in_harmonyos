import os

from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    """手写编译行 + 显式带上 cpp_info.defines。

    为什么不用 CMakeDeps/find_package（试过，走不通）：
      · CMakeDeps 生成的 `pinocchio::pinocchio` 目标，其 INTERFACE_LINK_LIBRARIES
        的依赖段是**空的**（实测打印为
        `$<$<CONFIG:Release>:>;$<$<CONFIG:Release>:CONAN_LIB::pinocchio_*>`），
        即使在配方里声明了 `cpp_info.requires` 也没变
        —— 于是 boost/eigen 的 include 传不过来，报 `boost/next_prior.hpp` not found，
        而那个头在 boost 包里**确实存在**（逐个探测确认过）。

    两条路的短板正好互补，故取手写 + 显式 defines：
      · 手写编译行遍历 `self.dependencies` 的 includedirs → **include 齐全**；
      · 从 `cpp_info.defines` 取 `-D` → **编译定义齐全**
        （BOOST_MPL_LIMIT_LIST_SIZE=30 等，缺了必编不过，详见配方 package_info 的说明）。
    """

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["pinocchio"].cpp_info
        incs, libdirs = [], []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            libdirs += _d.cpp_info.libdirs
        inc = " ".join(incs)

        # 关键：把被测包导出的编译定义带上。conan 的 cpp_info.defines 就是为此存在的，
        # 但**手写编译行不会自动施加**，必须显式转成 -D。
        defs = " ".join("-D" + d for d in (dep.defines or []))

        _std = self.settings.get_safe("compiler.cppstd")
        std_flag = ("-std=c++%s" % str(_std).replace("gnu", "")) if _std else "-std=c++17"

        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.libs]
                        + ["-Wl,-rpath," + p for p in libdirs])
        cc = os.environ.get("CXX", "clang++")
        self.output.info("test 编译定义: %s" % defs)
        self.run(f"{cc} {std_flag} {defs} test.cpp -o test_probe {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        dirs = []
        for _ref, _d in self.dependencies.items():
            for d in (_d.cpp_info.libdirs or []):
                if d not in dirs:
                    dirs.append(d)
        old = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(dirs + ([old] if old else []))
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
