import os
import shlex
import subprocess
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dependency = self.dependencies["expat"]
        dep = dependency.cpp_info
        # 头闭包自检要用「所有依赖」的 include（如 tk.h #include <tcl.h>，须带上 tcl 的 include）。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libexpat.so")
        configured = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = os.environ.get("CC") or configured.get("c")
        if not cc:
            if cross_building(self):
                raise ConanInvalidConfiguration("Cross consumer needs CC or tools.build:compiler_executables['c']")
            cc = "clang"
        args = [cc, "test.c", "-o", "test_probe", *incs]
        if dependency.options.shared:
            if not os.path.isfile(so):
                raise RuntimeError("Installed shared Expat library is missing: {}".format(so))
            # Compile a relocatable target consumer.  A Windows Conan cache path
            # is neither a valid C string literal nor a usable OHOS dlopen path.
            # Link the installed library as well as exercising dlopen at runtime.
            args += ["-L" + libdir, "-lexpat", "-ldl"]
        else:
            args += ["-DTEST_STATIC", "-L" + libdir, "-lexpat", "-ldl"]
        command = subprocess.list2cmdline(args) if os.name == "nt" else shlex.join(args)
        self.run(command)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        if False:
            self.output.info("skip_test_run：GUI/app 库只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
