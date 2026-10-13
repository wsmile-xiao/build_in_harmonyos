#!/usr/bin/env python3
"""conan test_package 鈥?librepo 1.18.0.

Compiles a real C consumer against the packaged librepo (metalink parsing +
version macros) and runs it on a local XML fixture; no network access is
required.
"""
import os
import shutil

from conan import ConanFile


class LibrepoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        includes = []
        libdirs = []
        seen = set()
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for d in dep.cpp_info.includedirs or ["include"]:
                p = os.path.join(dep.package_folder, d)
                if p not in seen:
                    seen.add(p)
                    includes.append(p)
            for comp in dep.cpp_info.components.values():
                for d in comp.includedirs:
                    p = os.path.join(dep.package_folder, d)
                    if p not in seen:
                        seen.add(p)
                        includes.append(p)
            for d in dep.cpp_info.libdirs or ["lib"]:
                p = os.path.join(dep.package_folder, d)
                if p not in seen:
                    seen.add(p)
                    libdirs.append(p)
            for comp in dep.cpp_info.components.values():
                for d in comp.libdirs:
                    p = os.path.join(dep.package_folder, d)
                    if p not in seen:
                        seen.add(p)
                        libdirs.append(p)

        cc = shutil.which("clang") or "clang"
        src = os.path.join(self.recipe_folder, "test_consumer.c")
        fixture = os.path.join(self.recipe_folder, "metalink_fixture.xml")
        exe = os.path.join(self.build_folder, "test_consumer")

        flags = " ".join(f"-I{p}" for p in includes)
        lflags = " ".join(f"-L{p}" for p in libdirs)
        # The consumer only calls librepo and glib APIs directly; the rest of
        # the dependency closure is pulled in via librepo.so's DT_NEEDED
        # (lld resolves the remaining symbols through the -L dirs above).
        self.run(
            f'{cc} -O2 {flags} "{src}" -o "{exe}" {lflags} -lrepo -lglib-2.0',
            cwd=self.build_folder,
            env="conanbuild",
        )
        self.run(f'"{exe}" "{fixture}"', cwd=self.build_folder,
                 env=["conanbuild", "conanrun"])
