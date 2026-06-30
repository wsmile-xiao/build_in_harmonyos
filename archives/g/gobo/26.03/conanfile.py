#!/usr/bin/env python3
"""Conan recipe for Gobo Eiffel 26.03.

Gobo Eiffel is an Eiffel compiler and tools suite. The build uses a
bootstrap mechanism: pre-generated C sources are compiled with a C
compiler to create the Gobo Eiffel Compiler (gec), which is then used
to compile all other Eiffel tools.

R26: Binaries only depend on libc.so (system library) — effectively self-contained.
R27: No external Conan dependencies.
R28: test_package/ included.
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches


class GoboConan(ConanFile):
    name = "gobo"
    version = "26.03"
    description = "Gobo Eiffel: Eiffel compiler and tools (gec, geant, gelex, geyacc, etc.)"
    license = "MIT"
    homepage = "https://github.com/gobo-eiffel/gobo"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(self, "*", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R26: Static linking — Gobo binaries only depend on libc.so (system library)
        # BUILD_SHARED_LIBS=OFF equivalent: Eiffel bootstrap produces self-contained executables
        apply_conandata_patches(self)
        # Gobo uses a bootstrap mechanism, not autotools/cmake
        build_dir = Path(self.build_folder)
        gobo = str(build_dir)

        # Step 1: Create pthread stubs for HarmonyOS compatibility
        # HarmonyOS libc lacks pthread_setcancelstate and pthread_cancel
        stubs_c = build_dir / "pthread_stubs.c"
        stubs_c.write_text("""\
#include <pthread.h>
int pthread_setcancelstate(int state, int *oldstate) {
    if (oldstate) *oldstate = 0;
    return 0;
}
int pthread_cancel(pthread_t thread) {
    (void)thread;
    return 0;
}
""")
        stubs_o = build_dir / "pthread_stubs.o"
        self.run(f"clang -c -fPIC -O2 {stubs_c} -o {stubs_o}")

        # Step 2: Patch clang.cfg to include pthread stubs in link step
        clang_cfg = build_dir / "tool" / "gec" / "backend" / "c" / "config" / "clang.cfg"
        if clang_cfg.exists():
            content = clang_cfg.read_text()
            # Replace both libs_gc lines precisely to avoid double-stub
            content = content.replace(
                "libs_gc: -ldl\n",
                f"libs_gc: -ldl {stubs_o}\n"
            ).replace(
                "libs_gc:\n",
                f"libs_gc: {stubs_o}\n"
            )
            clang_cfg.write_text(content)

        # Step 3: Run bootstrap (compile gec from pre-generated C sources)
        # Modify bootstrap.sh in place to skip 'strip' (strip breaks HarmonyOS exec)
        bootstrap = build_dir / "tool" / "gec" / "bootstrap" / "bootstrap.sh"
        content = bootstrap.read_text()
        content = content.replace("STRIP=strip", "STRIP=echo")
        bootstrap.write_text(content)

        bin_dir = build_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)

        # Set environment variables directly (Conan 2.x env param has issues)
        os.environ["GOBO"] = gobo
        os.environ["PATH"] = f"{bin_dir}:{os.environ.get('PATH', '')}"

        self.run(f"sh {bootstrap} -v clang", cwd=str(bin_dir))

        # Step 4: Compile all Eiffel tools using gec
        tools = [
            ("gecc", "tool/gecc/src/system.ecf", ""),
            ("geant", "tool/geant/src/system.ecf", ""),
            ("gedoc", "tool/gedoc/src/system.ecf", ""),
            ("getest", "tool/getest/src/system.ecf", ""),
            ("gelint", "tool/gelint/src/system.ecf", ""),
            ("gecop", "tool/gecop/src/system.ecf", ""),
            ("gelsp", "tool/gelsp/src/system.ecf", "--gc=boehm"),
            ("geimage", "tool/geimage/src/system.ecf", ""),
            ("gelex", "tool/gelex/src/system.ecf", ""),
            ("geyacc", "tool/geyacc/src/system.ecf", ""),
            ("gepp", "tool/gepp/src/system.ecf", ""),
            ("gexslt", "tool/gexslt/src/system.ecf", ""),
        ]
        for tool_name, ecf_path, extra_flags in tools:
            ecf = build_dir / ecf_path
            self.run(
                f"{bin_dir}/gec --finalize {extra_flags} {ecf}",
                cwd=str(bin_dir)
            )

    def package(self):
        # Install compiled binaries
        bin_dir = Path(self.build_folder) / "bin"
        copy(self, "*", src=str(bin_dir), dst=os.path.join(self.package_folder, "bin"))
        # Install library and tool sources (needed by Eiffel projects using Gobo)
        for subdir in ["library", "tool"]:
            src = Path(self.build_folder) / subdir
            if src.exists():
                copy(self, "*", src=str(src),
                     dst=os.path.join(self.package_folder, "lib", "gobo", subdir))

    def package_info(self):
        self.cpp_info.libs = []
        # Gobo provides executables, not libraries
        self.cpp_info.bindirs = ["bin"]
        # Set GOBO environment variable for consumers
        self.cpp_info.set_property("gobo_root", os.path.join(self.package_folder, "lib", "gobo"))
