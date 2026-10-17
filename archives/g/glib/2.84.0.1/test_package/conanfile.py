import os
from conan import ConanFile
from conan.tools.build import can_run, cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["glib"].cpp_info
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
        if "glib-2.0" in dep.components and dep.components["glib-2.0"].libdirs:
            libdir = dep.components["glib-2.0"].libdirs[0]
        else:
            libdir = dep.libdirs[0]
        so = os.path.join(libdir, "libglib-2.0.so")
        # R33: compiler from Conan conf, not bare ${CC}
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or "clang"
        self.run(
            f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' "
            f"-L{libdir} -lglib-2.0 -ldl -lpthread"
        )

    def test(self):
        # Cross SDK / qemu often cannot dlopen OHOS musl .so (SIGILL / missing rootfs).
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return
        # Extra guard: refuse qemu when binary is OHOS aarch64 shared-linked probe
        self.run("./test_probe", env="conanrun")
