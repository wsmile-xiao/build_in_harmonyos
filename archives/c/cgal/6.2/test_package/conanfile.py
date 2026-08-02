import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["cgal"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        # header-only：没有 libcgal.so，不做 dlopen 探针（真断言在 test.cpp 里）
        cc = os.environ.get("CXX", "clang++")
        # 库本体按 profile 的 cppstd 编，测试标准必须跟上，
        # 否则库头里的 C++17 设施（std::void_t / is_arithmetic_v 等）全报找不到。
        _std = self.settings.get_safe("compiler.cppstd")
        std_flag = ("-std=c++%s" % str(_std).replace("gnu", "")) if _std else ""
        # -g0：clang-15 + lld 在 .debug_gdb_scripts 节上有已知问题——
        #   ld.lld: error: ...o:(.debug_gdb_scripts): string is not null terminated
        # 该节是调试用的 gdb pretty-printer 钩子，测试根本不需要调试信息。
        # 这与被测库无关（CGAL 包本身已构建成功），只是链接测试程序时才触发。
        std_flag += " -g0"
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        # CGAL 6.x 是 header-only，自身没有 .so；但它的**依赖**有：
        # 精确算术核（Exact_predicates_exact_constructions_kernel）在运行期要 gmp / mpfr。
        # 只链 dep.libs（cgal 的，空的）会漏掉它们 → 链接期 undefined symbol __gmpq_*。
        # 故把所有依赖的库名都收进来（有组件的取组件，没组件取聚合）。
        libnames = []
        for _ref, _d in self.dependencies.items():
            ci = _d.cpp_info
            libnames += list(ci.libs)
            for _cn, _c in (ci.components or {}).items():
                libnames += list(_c.libs)
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in libnames]
                        + ["-Wl,-rpath," + p for p in libdirs])
        # **必须分两步编译**：先 -c 出 .o，再单独链接。
        #
        # 一步式（编译+链接一条命令）时 clang 把临时目标文件写到 $TMPDIR，
        # 而设备上 $TMPDIR 在 HMDFS 上。大的 .o 会被写坏，lld 读它时报：
        #   ld.lld: error: /storage/.../tmp/test-XXXX.o:(.debug_gdb_scripts):
        #           string is not null terminated
        # 这个报错极具误导性——看着像某个头引入了畸形的调试节，
        # 实测逐层加头（<string>/<gmp.h>/<mpfr.h>/CGAL/version.h）产出的 .o
        # **都没有** .debug_gdb_scripts 节；-g0 也无效。真因是文件损坏。
        #
        # 同一类 HMDFS 问题本批次出现过两次：另一次是 hdc 推过来的 boost tarball
        # （101592940 字节）cp 进缓存只写了 16486400 字节。
        # CGAL 模板重、.o 大才中招；hdf5 的 C++ 测试 .o 小就没事。
        self.run(f"{cc} {std_flag} -c test.cpp -o test_probe.o {inc}")
        # 编完先剥掉 .debug_gdb_scripts 再链接。该节在设备上会被写成畸形，
        # lld 解析时报 `string is not null terminated`（见上方注释）。
        # 节不存在时 objcopy 是 no-op，所以这一步无条件做也安全。
        self.run("llvm-objcopy --remove-section=.debug_gdb_scripts "
                 "test_probe.o test_probe.o || true")
        self.run(f"{cc} test_probe.o -o test_probe {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        if False:
            self.output.info("skip_test_run：GUI/app 库只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
