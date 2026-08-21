"""simavr is a lean, mean and hackable AVR simulator for linux & OSX."""
import os
import shutil
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, get


class SimavrConan(ConanFile):
    name = "simavr"
    version = "1.6"
    package_type = "static-library"
    license = "GPL-3.0"
    homepage = "https://github.com/buserror/simavr"
    url = "https://github.com/buserror/simavr"
    description = "AVR simulator (libsimavr + run_avr CLI)"
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"

    def requirements(self):
        # simavr's sim_elf.c needs libelf (ELF firmware parsing)
        self.requires("libelf/0.8.13")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def build(self):
        # build static libsimavr only (skip run_avr CLI — Makefile.common's
        # .elf link rule `${filter %.o,$^}` drops libsimavr.a and relies on
        # libsimavr.so + rpath-link, which breaks on OHOS); RELEASE=1
        # ensures installable layout
        elf = self.dependencies["libelf"]
        cppflags = (f"-I{elf.package_folder}/include "
                    f"-I{elf.package_folder}/include/libelf")
        ldflags = f"-L{elf.package_folder}/lib -lelf"
        self.run(
            f"make -j1 -C simavr RELEASE=1 libsimavr "
            f"CFLAGS+='{cppflags}' LDFLAGS+='{ldflags}'",
            cwd=self.source_folder)

    def package(self):
        src = os.path.join(self.source_folder, "simavr")
        obj = os.path.join(src, "obj-aarch64-unknown-linux-ohos")
        if not os.path.isdir(obj):
            obj = os.path.join(src, "obj")
        copy(self, "*.h", src=os.path.join(src, "sim"),
             dst=os.path.join(self.package_folder, "include", "simavr"))
        copy(self, "*.h", src=src,
             dst=os.path.join(self.package_folder, "include", "simavr"))
        copy(self, "*.h", src=os.path.join(src, "sim", "avr"),
             dst=os.path.join(self.package_folder, "include", "simavr", "avr"))
        copy(self, "*.h", src=os.path.join(self.source_folder,
                                           "examples", "parts"),
             dst=os.path.join(self.package_folder, "include", "simavr", "parts"))
        copy(self, "libsimavr.a", src=obj,
             dst=os.path.join(self.package_folder, "lib"))
        # pkgconfig files (fix PREFIX/VERSION placeholders)
        for pc in ("simavr.pc", "simavr-avr.pc", "simavrparts.pc"):
            p = os.path.join(src, pc)
            if os.path.isfile(p):
                s = open(p).read()
                s = s.replace("PREFIX",
                              self.package_folder).replace("VERSION", "1.6")
                os.makedirs(os.path.join(self.package_folder, "lib",
                                         "pkgconfig"), exist_ok=True)
                with open(os.path.join(self.package_folder, "lib",
                                       "pkgconfig", pc), "w") as f:
                    f.write(s)

    def package_info(self):
        self.cpp_info.libs = ["simavr"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "simavr")

    def deploy(self):
        self.copy("*.a", dst="lib", src="lib")
