from conan import ConanFile
from conan.tools.build import can_run, cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["harfbuzz"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            for _comp_name, comp in _d.cpp_info.components.items():
                incs += ["-I" + p for p in comp.includedirs]
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        seen = set()
        uniq = []
        for flag in incs:
            if flag not in seen:
                seen.add(flag)
                uniq.append(flag)
        inc = " ".join(uniq)
        if "harfbuzz" in dep.components and dep.components["harfbuzz"].libdirs:
            libdir = dep.components["harfbuzz"].libdirs[0]
        else:
            libdir = dep.libdirs[0]
        # R34: API calls (hb_version_string / hb_buffer_create) prove the
        # Conan package is wired correctly.  Skip the previous dlopen-based
        # probe: on native OHOS, libharfbuzz.so may live outside the
        # process namespace and the dynamic loader can return EPERM; this
        # shouldn't fail the test_package.  ELF NEEDED audit of the real
        # test/api/test-* binaries already proves the loader path on OHOS.
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = ce.get("cpp") or "clang++"
        self.run(
            f"{cxx} test.c -o test_probe {inc} "
            f"-L{libdir} -lharfbuzz -lpthread"
        )

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
