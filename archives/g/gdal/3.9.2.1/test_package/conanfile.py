import os
from conan import ConanFile
from conan.tools.build import can_run, cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs = []
        libdirs = []
        for _ref, _d in self.dependencies.host.items():
            pf = _d.package_folder or ""
            for p in list(_d.cpp_info.includedirs):
                ap = p if os.path.isabs(p) else os.path.join(pf, p)
                if ap and os.path.isdir(ap):
                    incs.append(ap)
            for d in list(_d.cpp_info.libdirs):
                ad = d if os.path.isabs(d) else os.path.join(pf, d)
                if ad and os.path.isdir(ad):
                    libdirs.append(ad)

        seen, uniq_i = set(), []
        for p in incs:
            flag = "-I" + p
            if flag not in seen:
                seen.add(flag)
                uniq_i.append(flag)
        inc = " ".join(uniq_i)

        seen_ld, uniq_ld = set(), []
        for d in libdirs:
            if d and d not in seen_ld:
                seen_ld.add(d)
                uniq_ld.append(d)
        ld = " ".join(f"-L{d}" for d in uniq_ld)

        so = None
        for d in uniq_ld:
            cand = os.path.join(d, "libgdal.so")
            if os.path.isfile(cand):
                so = cand
                break
        if not so:
            so = "libgdal.so"

        # Prefer shared gdal only; transitive statics already inside .so when linked at package time.
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or "clang"
        self.run(
            f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' "
            f"{ld} -lgdal -ldl -lm -lpthread"
        )

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
