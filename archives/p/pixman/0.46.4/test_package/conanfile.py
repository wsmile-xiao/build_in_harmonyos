import os
import shlex
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["pixman"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        libdir = dep.libdirs[0]
        so_candidates = [
            os.path.join(libdir, "libpixman-1.so"),
            os.path.join(libdir, "libpixman-1.so.0"),
            os.path.join(libdir, "libpixman-1.so.0.46.4"),
        ]
        so = next((path for path in so_candidates if os.path.exists(path)), so_candidates[0])
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = os.environ.get("CC") or executables.get("c") or "clang"
        args = [cc, "test.c", "-o", "test_probe"]
        args.extend(incs)
        args.extend([f"-DTARGET_SO=\"{so}\"", "-ldl"])
        self.run(" ".join(shlex.quote(arg) for arg in args))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
