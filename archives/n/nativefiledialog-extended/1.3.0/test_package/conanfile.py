#!/usr/bin/env python3
"""Conan test_package — nativefiledialog-extended 1.3.0.

Direct compile+run (agg precedent, no CMake/find_package): test.cpp links
against the installed libnfd.a plus the full GTK3 dependency chain collected
from the dependency graph (glib keeps lib dirs in components — abiword
precedent), wrapped in --start-group to avoid link-order sensitivity.

The upstream test/ suite needs SDL2 and a GUI environment and cannot run
headless; see test_package/MANIFEST.yml for the rule4 attribution.
"""
import os

from conan import ConanFile


class NfdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # Explicit env generators: conanbuild provides the OHOS clang++ PATH,
    # conanrun provides LD_LIBRARY_PATH for the shared GTK chain at runtime.
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        nfd = self.dependencies["nativefiledialog-extended"]
        incs = []
        lds = []
        libs = []
        seen_inc = set()
        seen_ld = set()
        seen_lib = set()

        def collect(info, pkg_folder):
            for i in info.includedirs:
                a = i if (os.path.isabs(i) or not pkg_folder) else os.path.join(pkg_folder, i)
                if a not in seen_inc:
                    seen_inc.add(a)
                    incs.append(a)
            for d in info.libdirs:
                a = d if (os.path.isabs(d) or not pkg_folder) else os.path.join(pkg_folder, d)
                if a not in seen_ld:
                    seen_ld.add(a)
                    lds.append(a)
            for l in list(info.libs) + list(info.system_libs):
                flag = "-l" + l
                if flag not in seen_lib:
                    seen_lib.add(flag)
                    libs.append(flag)

        # Headers only need nfd itself; lib dirs/libs come from the whole
        # transitive chain (static libnfd.a references GTK symbols).
        collect(nfd.cpp_info, getattr(nfd, "package_folder", None) or "")
        for dep in self.dependencies.host.values():
            if dep.ref.name == "nativefiledialog-extended":
                continue
            pf = getattr(dep, "package_folder", None) or ""
            collect(dep.cpp_info, pf)
            # glib/cairo etc. keep lib dirs in components (abiword precedent)
            for comp in getattr(dep.cpp_info, "components", {}).values():
                collect(comp, pf)

        inc_flags = " ".join("-I" + i for i in incs)
        ld_flags = " ".join("-L" + d for d in lds)
        lib_flags = "-Wl,--start-group " + " ".join(libs) + " -Wl,--end-group"
        self.run(
            f"clang++ -std=c++17 -O2 {inc_flags} test.cpp {ld_flags} {lib_flags} -o test_nfd",
            cwd=self.build_folder,
            env="conanbuild",
        )

    def test(self):
        # GTK chain is shared libs → runtime needs conanrun (LD_LIBRARY_PATH).
        # Headless-safe: NFD_Init may legitimately fail without a display;
        # test.cpp validates both outcomes (see test.cpp comments).
        self.run("./test_nfd", cwd=self.build_folder, env="conanrun")
