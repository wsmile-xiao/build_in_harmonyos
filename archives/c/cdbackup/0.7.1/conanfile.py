"""Conan recipe — cdbackup 0.7.1 (CD-R(W) backup utility, plain Makefile)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy


class CdbackupConan(ConanFile):
    name = "cdbackup"
    version = "0.7.1"
    package_type = "application"
    license = "BSD"
    description = "CD-R(W) backup utility: streaming backup to CD/DVD media"
    homepage = "https://www.muempf.de/cdbackup.html"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_execs.get("c", "cc")
        # OHOS/musl: u_char is not auto-exported, add <sys/types.h> to headers
        self.run("sed -i '1i#include <sys/types.h>' virtual.h",
                 cwd=self.source_folder)
        # musl/OHOS: rindex not in libc, use strrchr instead
        self.run("sed -i 's/rindex/strrchr/g' virtual.c",
                 cwd=self.source_folder)
        self.run(f"make CC={cc} CFLAGS='-O2 -fPIC'", cwd=self.source_folder)

    def package(self):
        copy(self, "cdbackup", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "cdrestore", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
