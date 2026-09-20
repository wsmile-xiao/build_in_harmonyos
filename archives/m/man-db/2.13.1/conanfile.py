#!/usr/bin/env python3
"""Conan recipe for man-db 2.13.1 (Autotools: configure + make) — Manual page tools."""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, download
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MandbConan(ConanFile):
    name = "man-db"
    version = "2.13.1"
    description = "man-db is an implementation of the standard Unix documentation system"
    license = "GPL-2.0+"
    homepage = "https://www.nongnu.org/man-db/"
    url = "https://git.savannah.nongnu.org/cgit/man-db.git"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gdbm/1.24")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps: feed -I/-L/-l from gdbm/zlib into configure/make.
        # Without this, configure cannot find gdbm.h in the Conan cache and
        # dies with "Fatal: no supported database library/header found".
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-setuid",
            # Statically link man-db's internal libs (libman/libmandb). They
            # install to lib/man-db/ with an absolute RUNPATH of /lib/man-db,
            # which the OHOS loader cannot resolve from the Conan cache.
            "--disable-shared",
            "--enable-static",
            "--with-systemdtmpfilesdir=no",
            "--with-systemdsystemunitdir=no",
        ])
        tc.generate()
        # OHOS loader has no default search path for conan-cached shared libs
        # (libgdbm.so is shared-only). AutotoolsDeps puts -lgdbm into LIBS, so
        # configure's conftest programs link it and then fail to run unless
        # LD_LIBRARY_PATH points at the dependency lib dirs.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def _patch_config_status(self, cs_path):
        """Patch config.status to use umask 022 instead of 077 (HMDFS compatibility)."""
        if not os.path.exists(cs_path):
            return False
        with open(cs_path, "r") as f:
            content = f.read()
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            with open(cs_path, "w") as f:
                f.write(content)
            return True
        return False

    def build(self):
        apply_conandata_patches(self)

        # Build libpipeline from source (not available in conan registry)
        libpipeline_install = os.path.join(self.build_folder, "libpipeline-install")
        download(self, "https://deb.debian.org/debian/pool/main/libp/libpipeline/libpipeline_1.5.8.orig.tar.gz",
                 "libpipeline-1.5.8.tar.gz",
                 sha256="1b1203ca152ccd63983c3f2112f7fe6fa5afd453218ede5153d1b31e11bb8405")
        self.run("tar xzf libpipeline-1.5.8.tar.gz", env="conanbuild")

        # Copy config.guess/sub from man-db source for cross-compilation support
        lp_dir = os.path.join(self.build_folder, "libpipeline-1.5.8")
        dst_dir = os.path.join(lp_dir, "build-aux")
        os.makedirs(dst_dir, exist_ok=True)
        for sf in [os.path.join(self.source_folder, "build-aux", "config.guess"),
                   os.path.join(self.source_folder, "build-aux", "config.sub")]:
            if os.path.exists(sf):
                shutil.copy2(sf, os.path.join(dst_dir, os.path.basename(sf)))

        os.makedirs(libpipeline_install, exist_ok=True)
        self.run(f"cd {lp_dir} && ./configure --prefix={libpipeline_install} "
                 f"--disable-shared --enable-static --no-create", env="conanbuild")
        self._patch_config_status(os.path.join(lp_dir, "config.status"))
        self.run(f"cd {lp_dir} && ./config.status", env="conanbuild")
        self.run(f"cd {lp_dir} && make -j1 && make install", env="conanbuild")

        # Set libpipeline flags for man-db configure
        os.environ["libpipeline_CFLAGS"] = f"-I{libpipeline_install}/include"
        os.environ["libpipeline_LIBS"] = f"-L{libpipeline_install}/lib -lpipeline"

        # Create nroff wrapper only if groff is available
        groff_path = shutil.which("groff")
        if groff_path:
            nroff_wrapper = os.path.join(self.build_folder, "nroff")
            with open(nroff_wrapper, "w") as f:
                f.write("#!/bin/sh\nexec groff -Tascii -mandoc \"$@\"\n")
            os.chmod(nroff_wrapper, 0o755)
            cur_path = os.environ.get("PATH", "")
            os.environ["PATH"] = f"{self.build_folder}:{cur_path}"

        # Build man-db with configure --no-create then patch and run config.status
        autotools = Autotools(self)
        autotools.configure(args=["--no-create"])
        for pd in [self.build_folder, os.path.join(self.build_folder, "build-release")]:
            cs = os.path.join(pd, "config.status")
            if self._patch_config_status(cs):
                self.output.info(f"Patched config.status at {cs}")
                self.run(f"cd {pd} && ./config.status", env="conanbuild")
                break
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
