#!/usr/bin/env python3
"""Conan recipe for easyflash 4.1.0 — no configure/make, direct source compile.

EasyFlash ships pure C sources (easyflash/src/*.c) without any build system;
the port layer (ef_port.c) is provided by the consumer. This recipe compiles
the core sources into a static library and installs the public headers.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class EasyflashConan(ConanFile):
    name = "easyflash"
    version = "4.1.0"
    description = "EasyFlash is an open source lightweight embedded flash memory library"
    license = "MIT"
    homepage = "https://github.com/armink/EasyFlash"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        env = VirtualBuildEnv(self)
        env.vars().apply()
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c") or os.environ.get("CC", "clang")
        src_dir = self.source_folder
        out_dir = self.build_folder
        objs = []
        srcs = [
            "easyflash.c", "ef_env.c", "ef_env_legacy.c",
            "ef_env_legacy_wl.c", "ef_iap.c", "ef_log.c", "ef_utils.c",
        ]
        flags = "-fPIC -O2 -I%s/easyflash/inc" % src_dir
        for s in srcs:
            obj = os.path.join(out_dir, s.replace(".c", ".o"))
            self.run("%s %s -c %s/easyflash/src/%s -o %s" % (cc, flags, src_dir, s, obj))
            objs.append(obj)
        archiver = os.environ.get("AR", "llvm-ar")
        self.run("%s rcs %s/libeasyflash.a %s" % (archiver, out_dir, " ".join(objs)))
        # Stage public headers next to the library so package() only reads
        # the build folder (self.source_folder is unavailable at package time).
        self.run("mkdir -p %s/include && cp %s/easyflash/inc/*.h %s/include/" % (out_dir, src_dir, out_dir))

    def package(self):
        inc_src = os.path.join(self.build_folder, "include")
        lib_src = os.path.join(self.build_folder, "libeasyflash.a")
        self.output.info("package(): build_folder=%s" % self.build_folder)
        self.output.info("package(): include exists=%s lib exists=%s" % (
            os.path.isdir(inc_src), os.path.isfile(lib_src)))
        self.run("mkdir -p %s/include" % self.package_folder)
        self.run("cp %s/*.h %s/include/" % (inc_src, self.package_folder))
        self.run("mkdir -p %s/lib" % self.package_folder)
        self.run("cp %s %s/lib/" % (lib_src, self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["easyflash"]
