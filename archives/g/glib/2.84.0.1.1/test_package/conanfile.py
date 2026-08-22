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
        libdirs = []
        libs = []
        syslibs = []
        for _ref, _d in self.dependencies.items():
            for _comp in _d.cpp_info.components.values():
                for d in _comp.libdirs:
                    if d not in libdirs:
                        libdirs.append(d)
                for l in _comp.libs:
                    if l not in libs:
                        libs.append(l)
                for s in _comp.system_libs:
                    if s not in syslibs:
                        syslibs.append(s)
            for d in _d.cpp_info.libdirs:
                if d not in libdirs:
                    libdirs.append(d)
            for l in _d.cpp_info.libs:
                if l not in libs:
                    libs.append(l)
            for s in _d.cpp_info.system_libs:
                if s not in syslibs:
                    syslibs.append(s)
        if "glib-2.0" in dep.components and dep.components["glib-2.0"].libdirs:
            libdir = dep.components["glib-2.0"].libdirs[0]
        else:
            libdir = dep.libdirs[0] if dep.libdirs else (libdirs[0] if libdirs else "")
        glib_dep = self.dependencies["glib"]
        try:
            is_shared = bool(glib_dep.options.shared)
        except Exception:
            is_shared = os.path.isfile(os.path.join(libdir, "libglib-2.0.so"))
        so = os.path.join(libdir, "libglib-2.0.so")
        ld_libs = list(libs)
        if not is_shared and "intl" not in ld_libs:
            has_intl = any(os.path.isfile(os.path.join(d, "libintl.a")) or os.path.isfile(os.path.join(d, "libintl.so")) for d in libdirs)
            if has_intl:
                ld_libs.append("intl")
        ldflags = " ".join("-L" + d for d in libdirs)
        libs_str = " ".join("-l" + l for l in ld_libs) if ld_libs else ""
        if "-lglib-2.0" not in libs_str:
            libs_str = "-lglib-2.0 " + libs_str
        sys_str = " ".join("-l" + s for s in syslibs) if syslibs else ""
        defines = f"-DTARGET_SO='\"{so}\"'"
        if not is_shared:
            defines += " -DSTATIC_TEST"
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or "clang"
        self.run(f"{cc} test.c -o test_probe {inc} {defines} {ldflags} {libs_str} {sys_str} -ldl -lpthread")
    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
