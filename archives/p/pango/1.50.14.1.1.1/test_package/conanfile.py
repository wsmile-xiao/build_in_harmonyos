import os
from conan import ConanFile
from conan.tools.build import can_run, cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # pango 组件 requires 里挂的 transitive deps（glib/harfbuzz/cairo/fribidi/freetype/fontconfig）
        # 在 self.dependencies.items() 里默认不可见，build() 循环会漏掉这些 include 路径
        # （典型表现：找不到 <glib-object.h>）。显式 require 让循环拿到 headers。
        # 锁版本与 pango recipe 对齐，避免 option/graph 冲突。
        self.requires("glib/2.84.0.1", options={"shared": True})
        self.requires("harfbuzz/14.2.0.1.1.1")
        self.requires("cairo/1.18.4.1")
        self.requires("fribidi/1.0.16")
        self.requires("freetype/2.14.3")
        self.requires("fontconfig/2.18.1.1", force=True)

    def build(self):
        dep = self.dependencies["pango"].cpp_info
        incs = []
        libdirs = []
        libs = []
        for _ref, _d in self.dependencies.items():
            for _comp_name, comp in _d.cpp_info.components.items():
                incs += ["-I" + p for p in comp.includedirs]
                libdirs += list(comp.libdirs)
                libs += list(comp.libs)
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            libdirs += list(_d.cpp_info.libdirs)
            libs += list(_d.cpp_info.libs)

        seen_i, uniq_i = set(), []
        for flag in incs:
            if flag and flag not in seen_i:
                seen_i.add(flag)
                uniq_i.append(flag)
        inc = " ".join(uniq_i)

        seen_ld, uniq_ld = set(), []
        for d in libdirs:
            if d and d not in seen_ld:
                seen_ld.add(d)
                uniq_ld.append(d)
        ld = " ".join(f"-L{d}" for d in uniq_ld)

        # Prefer pangocairo + transitive link set from package_info.
        link_libs = []
        seen_l = set()
        for name in ("pangocairo-1.0", "pangoft2-1.0", "pango-1.0") + tuple(libs):
            if name and name not in seen_l:
                seen_l.add(name)
                link_libs.append(f"-l{name}")
        link = " ".join(link_libs)

        so = None
        for d in uniq_ld:
            cand = os.path.join(d, "libpangocairo-1.0.so")
            if os.path.isfile(cand):
                so = cand
                break
        if not so and "pangocairo" in dep.components and dep.components["pangocairo"].libdirs:
            so = os.path.join(dep.components["pangocairo"].libdirs[0], "libpangocairo-1.0.so")
        if not so:
            so = "libpangocairo-1.0.so"

        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or "clang"
        self.run(
            f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' "
            f"{ld} {link} -lgobject-2.0 -lglib-2.0 -lcairo -lharfbuzz "
            f"-lfreetype -lfontconfig -lfribidi -ldl -lm -lpthread"
        )

    def test(self):
        if cross_building(self) or not can_run(self):
            # oh_compile: qemu can run static OHOS bins, but shared libpango*.so → SIGILL.
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
