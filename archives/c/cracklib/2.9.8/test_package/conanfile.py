import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 设备 /tmp 只读（SKILL §7 Gotchas / E002）：clang 编译临时文件
        # 需要可写 TMPDIR，指向 build 目录（HMDFS 权限受限时的标准恢复）
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        os.environ["TMP"] = _tmp
        os.environ["TEMP"] = _tmp
        # R33: 编译器从 conan conf 取
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        dep = self.dependencies["cracklib"].cpp_info
        inc = " ".join("-I" + p for p in dep.includedirs)
        libdir = dep.libdirs[0]
        self.run(
            f"{cc} test_cracklib.c -o test_cracklib {inc} "
            f"-L{libdir} -lcrack -Wl,-rpath,{libdir}"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        self.run("./test_cracklib", env="conanrun")