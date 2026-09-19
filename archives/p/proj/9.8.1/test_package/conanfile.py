import os
from conan import ConanFile
from conan.tools.build import can_run, cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["proj"].cpp_info
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
            for comp in _d.cpp_info.components.values():
                for p in list(comp.includedirs):
                    ap = p if os.path.isabs(p) else os.path.join(pf, p)
                    if ap and os.path.isdir(ap):
                        incs.append(ap)
                for d in list(comp.libdirs):
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
            cand = os.path.join(d, "libproj.so")
            if os.path.isfile(cand):
                so = cand
                break
        if not so and dep.libdirs:
            so = os.path.join(dep.libdirs[0], "libproj.so")
        if not so:
            so = "libproj.so"

        # sqlite3 is statically linked into libproj.so (Conan sqlite3 is .a);
        # do not pass -lsqlite3 (host graph may skip that binary's -L path).
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or "clang"
        # Conan 2.x build() 从 build_folder 执行，test.c 在 source_folder，
        # 必须用绝对路径避免 "file not found" 编译失败。
        test_src = os.path.join(self.source_folder, "test.c")
        self.run(
            f"{cc} {test_src} -o test_probe {inc} -DTARGET_SO='\"{so}\"' "
            f"{ld} -lproj -ldl -lm -lpthread"
        )

    def test(self):
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return
        self.run("./test_probe", env="conanrun")
