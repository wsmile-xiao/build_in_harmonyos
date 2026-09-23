import os

# 与标准 C/C++ 头同名的文件名。含这些文件的目录**不得**进 -I 搜索路径，
# 否则会遮蔽标准库的同名头（fcl 的 fcl/common/time.h 遮蔽 <time.h> 实撞）。
_STD_HEADER_NAMES = {
    "time.h", "math.h", "string.h", "stdio.h", "stdlib.h", "assert.h", "errno.h",
    "signal.h", "limits.h", "float.h", "locale.h", "setjmp.h", "ctype.h", "wchar.h",
    "complex.h", "fenv.h", "inttypes.h", "stdint.h", "stddef.h", "stdarg.h",
    "memory", "list", "array", "vector", "string", "map", "set", "queue", "stack",
    "algorithm", "functional", "utility", "thread", "mutex", "atomic", "chrono",
}
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # 显式给 generators 会**替换**（而非追加）conan 的默认集，漏了 VirtualRunEnv
    # 就没有 conanrun 环境，test() 里 env="conanrun" 拿不到 LD_LIBRARY_PATH，
    # 表现为编译链接全过、跑起来报 `Error loading shared library ...`（实撞）。
    generators = "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 直连依赖头（minc2.h 引 hdf5.h/netcdf.h；直测 H5Fis_hdf5/ncopen）。
        # 传递依赖的头文件必须显式 requires：CMakeDeps/遍历都只保证直连
        # （hdf5/pcre/krb5 先例；版本与主配方一致以复用同一节点）。
        self.requires("hdf5/1.14.6")
        self.requires("netcdf/4.9.3")
        self.requires("zlib/1.3.1.1")

    def _collect_incs_libdirs(self):
        # ⚠️ 必须遍历**传递依赖**视图：self.dependencies.items() 默认只给直接依赖。
        # host 视图带 transitive；老 conan 没有该属性时退回直接依赖。
        # 两个视图**都要遍历**并去重（netcdf 先例）。
        _seen, _incs, _libdirs = set(), [], []
        for _view in ("host", None):
            try:
                _it = (self.dependencies.host if _view else self.dependencies).items()
            except AttributeError:
                continue
            for _r, _d in _it:
                _k = str(_r.ref) if hasattr(_r, "ref") else str(_r)
                if _k in _seen:
                    continue
                _seen.add(_k)
                _base = getattr(_d, "package_folder", None) or ""
                for _p in _d.cpp_info.includedirs:
                    if not os.path.isabs(_p) and _base:
                        _p = os.path.join(_base, _p)
                    if not os.path.isdir(_p):
                        continue
                    _incs.append("-I" + _p)
                    if not os.path.isdir(_p):
                        continue
                    for _name in sorted(os.listdir(_p)):
                        _sub = os.path.join(_p, _name)
                        if not os.path.isdir(_sub):
                            continue
                        _files = os.listdir(_sub)
                        if any(f in _STD_HEADER_NAMES for f in _files):
                            continue
                        if any(f.endswith((".h", ".hpp", ".hh", ".hxx")) for f in _files):
                            _incs.append("-I" + _sub)
                for _p in _d.cpp_info.libdirs:
                    if not os.path.isabs(_p) and _base:
                        _p = os.path.join(_base, _p)
                    if os.path.isdir(_p):
                        _libdirs.append(_p)
        return _incs, _libdirs

    def build(self):
        incs, libdirs = self._collect_incs_libdirs()
        inc = " ".join(dict.fromkeys(incs))
        cc = os.environ.get("CC", "clang")
        # C 测试不能收 C++ 标准开关；musl 上用 gnu 方言（_POSIX_C_SOURCE 声明）。
        std_flag = "-std=gnu99"
        # 主链路只 -lminc2（其余由 DT_NEEDED + rpath 解析）；
        # 直测 H5Fis_hdf5/ncopen 需要显式 -lhdf5 -lnetcdf。
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-lminc2", "-lhdf5", "-lnetcdf"]
                        + ["-Wl,-rpath," + p for p in libdirs])
        self.run(f"{cc} {std_flag} test.c -o test_probe {inc} {link}")
        self.output.info("test_package 编译完成：test_probe（minc2+minc1 双链路消费者）")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 显式拼 LD_LIBRARY_PATH：conanrunenv 的 libdirs 可能为空（shared=False 发布
        # 的包 conan 视为静态、不写 libdirs，但包里确实装了 .so；pango 实撞）。
        _seen, libdirs = set(), []
        for _view in ("host", None):
            try:
                _it = (self.dependencies.host if _view else self.dependencies).items()
            except AttributeError:
                continue
            for _r, _d in _it:
                _base = getattr(_d, "package_folder", None) or ""
                for _p in _d.cpp_info.libdirs:
                    if not os.path.isabs(_p) and _base:
                        _p = os.path.join(_base, _p)
                    if os.path.isdir(_p) and _p not in _seen:
                        _seen.add(_p)
                        libdirs.append(_p)
        ldpath = os.pathsep.join(libdirs)
        # 产物输出到 build_folder，断言写文件用 build_folder（不在包源目录留文件）。
        self.run(f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./test_probe .'",
                 env="conanrun")
