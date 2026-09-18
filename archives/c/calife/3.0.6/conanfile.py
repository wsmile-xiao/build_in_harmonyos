"""Conan recipe — calife 3.0.6 (lightweight sudo alternative, autotools + PAM)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CalifeConan(ConanFile):
    name = "calife"
    version = "3.0.6"
    package_type = "application"
    license = "BSD-2-Clause"
    description = "Lightweight sudo alternative"
    homepage = "https://www.keltia.net/programs/calife/"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("linux-pam/1.7.2")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_execs.get("c", "gcc")
        # Pass Conan dependency paths so configure can find PAM
        dep_libs = []
        dep_incs = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf:
                dep_libs.append(os.path.join(pf, "lib"))
                dep_incs.append(os.path.join(pf, "include"))
        ldflags = " ".join(f"-L{d}" for d in dep_libs)
        cppflags = " ".join(f"-I{d}" for d in dep_incs)
        # E114 (bypass-mktemp): on HMDFS, the `umask 077 && mktemp -d ./confXXXXXX`
        # temp dir that config.status uses for ac_tmp cannot hold newly created
        # files -> "./confXXXX/subs1.awk: Permission denied" / "could not setup
        # config files machinery". Pre-create a plain (umask-inherited) dir in the
        # source tree and pin ac_tmp to it. The tarball ships no config.status, so
        # sed only configure: its config.status generation here-doc is single-quoted,
        # so the literal replacement ends up in the generated config.status.
        self.run("rm -rf cs-tmpdir && mkdir cs-tmpdir", cwd=self.source_folder)
        self.run("sed -i 's|ac_tmp=\\$tmp|ac_tmp=./cs-tmpdir|' configure",
                 cwd=self.source_folder)
        self.run(
            f"CC={cc} CFLAGS='-O2 -fPIC' "
            f"CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}' "
            f"./configure --build=aarch64-unknown-linux-gnu "
            f"--host=aarch64-linux-gnu",
            cwd=self.source_folder)
        self.run("make", cwd=self.source_folder)

    def package(self):
        copy(self, "calife", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
