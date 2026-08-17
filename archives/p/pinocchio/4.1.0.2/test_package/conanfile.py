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
        # eigen 是 pinocchio 公开头文件的直接依赖（pinocchio/multibody.hpp include <Eigen/Core>）。
        # 手写编译行场景下，把 eigen 声明为 test_package 的直接依赖以拿到它的真实 include 路径：
        # 实测 conan create 的 test 上下文中，header-only 传递依赖（eigen）的
        # cpp_info.package_folder 为 None、includedirs 退化成默认 ['include']，
        # 拿不到 <pkg>/include/eigen3；声明为直接依赖后与普通消费者解析一致。
        self.requires("eigen/3.4.0")

    def build(self):
        dep = self.dependencies["pinocchio"].cpp_info
        incs, libdirs = [], []
        for _ref, _d in self.dependencies.items():
            pkg = _d.package_folder or ""
            for p in _d.cpp_info.includedirs:
                # 实测（4.1.0.1 适配时）：header-only 传递依赖（eigen/3.4.0、zlib）在
                # conan create 的 test 上下文里 cpp_info.includedirs 会退化成默认
                # 相对值 ['include']（不走绝对化），直接 -I 会编不过。必须解析到
                # package_folder 下再拼。
                incs.append("-I" + (p if os.path.isabs(p) else os.path.join(pkg, p)))
            libdirs += _d.cpp_info.libdirs
        # 上面解析后 eigen 拿到 <pkg>/include，但它的头文件实际在 <pkg>/include/eigen3
        # （recipe package_info 声明的是 include/eigen3，create 上下文却只给了 include）。
        # 对无 lib 的 header-only 依赖，探测 package 真实 include 布局补上子目录。
        for _ref, _d in self.dependencies.items():
            if _d.cpp_info.libs:
                continue
            base = os.path.join(_d.package_folder or "", "include")
            if not os.path.isdir(base):
                continue
            for name in sorted(os.listdir(base)):
                sub = os.path.join(base, name)
                if os.path.isdir(sub) and "-I" + sub not in incs:
                    incs.append("-I" + sub)
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
