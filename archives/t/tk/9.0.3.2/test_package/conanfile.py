import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # C 级用户测试：编译 test.c 链接 libtcl9tk9.0 + libtcl9.0
        tk_cpp = self.dependencies["tk"].cpp_info
        tcl_cpp = self.dependencies["tcl"].cpp_info
        inc = " ".join("-I" + d for d in tk_cpp.includedirs + tcl_cpp.includedirs)
        lib = " ".join("-L" + d for d in tk_cpp.libdirs + tcl_cpp.libdirs)
        libs = " ".join("-l" + l for l in tk_cpp.libs + tcl_cpp.libs)
        cc = os.environ.get("CC", "clang")
        self.run(f"{cc} test.c -o test_probe {inc} {lib} {libs} -w")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip")
            return
        # 设置 Tcl/Tk 脚本库路径
        tcl_dep = self.dependencies["tcl"]
        tk_dep = self.dependencies["tk"]
        tcl_lib = os.path.join(tcl_dep.package_folder, "lib", "tcl9.0")
        tk_lib = os.path.join(tk_dep.package_folder, "lib", "tk9.0")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # R34: 执行 test_probe — 调用 Tcl/Tk C API 验证库可加载且运行时可初始化
        self.run(
            f'{bash} -c \'TCL_LIBRARY="{tcl_lib}" TK_LIBRARY="{tk_lib}" ./test_probe\'',
            env="conanrun",
        )
