"""Conan recipe — cdde 0.3.1 (CD Detect & Execute, autotools + libxml2)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy


class CddeConan(ConanFile):
    name = "cdde"
    version = "0.3.1"
    package_type = "application"
    license = "GPL-2.0"
    description = "CD Detect & Execute: detects CD/DVD and runs configured commands"
    homepage = "https://cdde.sourceforge.net/"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("libxml2/2.15.3")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_execs.get("c", "cc")
        # libxml2 headers are under include/libxml2/, but code does
        # #include <libxml/parser.h> so we need -I.../include/libxml2
        dep_libs = []
        dep_incs = []
        libxml2_inc = None
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf:
                dep_libs.append(os.path.join(pf, "lib"))
                if os.path.isdir(os.path.join(pf, "include", "libxml2")):
                    libxml2_inc = os.path.join(pf, "include", "libxml2")
                dep_incs.append(os.path.join(pf, "include"))
        ldflags = " ".join(f"-L{d}" for d in dep_libs)
        # cppflags must include libxml2's include/libxml2/ dir since code
        # does #include <libxml/parser.h>
        all_incs = list(dep_incs)
        if libxml2_inc and libxml2_inc not in all_incs:
            all_incs.append(libxml2_inc)
        cppflags = " ".join(f"-I{d}" for d in all_incs)
        # Find pkgconfig dirs for Conan dependencies
        pkg_paths = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf:
                pc = os.path.join(pf, "lib", "pkgconfig")
                if os.path.isdir(pc):
                    pkg_paths.append(pc)
        pkg_config = ":".join(pkg_paths) if pkg_paths else ""
        # E114: config.status uses `umask 077 && mktemp -d` which fails on HMDFS.
        # Patch umask to 022 in the configure script BEFORE running it.
        self.run("sed -i 's/umask 077/umask 022/' configure",
                 cwd=self.source_folder)
        # OHOS/musl: fstab.h not available. Write a patch header and include it.
        stub_h = os.path.join(self.source_folder, "src", "ohos_fstab_stub.h")
        with open(stub_h, "w") as f:
            f.write("#ifndef OHOS_FSTAB_STUB_H\n#define OHOS_FSTAB_STUB_H\n")
            f.write("struct fstab { char *fs_file; char *fs_type; };\n")
            f.write("static struct fstab _stub_fstab = {0};\n")
            f.write("static struct fstab *getfsspec(const char *s) { return &_stub_fstab; }\n")
            f.write("#define _PATH_FSTAB \"/etc/fstab\"\n")
            f.write("#endif\n")
        self.run(
            "sed -i 's|#include <fstab.h>|"
            "#ifdef __OHOS__\\n#include \"ohos_fstab_stub.h\"\\n"
            "#else\\n#include <fstab.h>\\n#endif|' src/cdde.c",
            cwd=self.source_folder)
        # OHOS/musl: add missing unistd.h for close/usleep
        self.run("sed -i '1i#include <unistd.h>' src/cdde.c",
                 cwd=self.source_folder)
        self.run(
            f"CC={cc} CFLAGS='-O2 -fPIC' "
            f"CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}' "
            f"PKG_CONFIG_PATH='{pkg_config}' ./configure",
            cwd=self.source_folder)
        # Sub-Makefile doesn't inherit CPPFLAGS from make invocation;
        # append include/lib flags to src/Makefile after configure generates it.
        self.run(
            f"echo 'CPPFLAGS += {cppflags}' >> src/Makefile && "
            f"echo 'LDFLAGS += {ldflags}' >> src/Makefile",
            cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        copy(self, "cdde", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
