#!/usr/bin/env python3
"""Conan recipe for analog (Homebrew version, upstream 6.0.18)

Analog is a web log file analyzer. This recipe uses the bundled
subdirectories (bzip2, libgd, libpng, pcre2, unzip, zlib) from the
upstream source, matching the upstream Makefile defaults.
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, rmdir
import os


class AnalogConan(ConanFile):
    name = "analog"
    version = "homebrew"
    license = "GPL-2.0-only"
    url = "https://github.com/c-amie/analog-ce"
    homepage = "https://www.c-amie.co.uk/software/analog/"
    description = "Analog is a fast logfile analyzer"
    topics = ("logfile", "analyzer", "web")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # All upstream dependencies (bzip2, libgd, libpng, pcre2, unzip, zlib)
        # are bundled in the source as subdirectories, matching the upstream
        # Makefile defaults (SUBDIRS = bzip2 libgd libpng pcre2 unzip zlib).
        # No external Conan packages needed.
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Analog only supports Linux and OHOS")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No external dependency generators needed — all deps are bundled.
        pass

    def build(self):
        install_prefix = self.package_folder

        # LANGDIR for runtime resource files
        langdir = os.path.join(install_prefix, "res", "analog", "lang").replace("\\", "/")

        # Write a config header to define LANGDIR as a C string literal.
        # This avoids shell quoting issues with -DLANGDIR="/path/" (the
        # shell strips the double quotes when make expands $(DEFS) in the
        # compiler recipe, causing the preprocessor to see bare slashes as
        # division operators).
        src_dir = os.path.join(self.source_folder, "src")
        config_h_path = os.path.join(src_dir, "ohos_langdir_config.h")
        with open(config_h_path, "w") as f:
            f.write(f'#define LANGDIR "{langdir}/"\n')

        # Use absolute path for -include so subdirectory makes (bzip2, etc.)
        # can find the config header when the working directory changes.
        abs_config_h = config_h_path.replace("\\", "/")
        cflags = "-O2 -fPIC -include {abs_config_h}".format(abs_config_h=abs_config_h)
        cc = self.settings.compiler or "gcc"
        os_name = "UNIX"

        # DEFS only needs -DUNIX now; LANGDIR is handled by -include.
        defs = "-DUNIX"

        # Patch pcre2 configure script to use umask 022 instead of 077.
        # The CI worker's HMDFS filesystem has UID mapping issues: when
        # config.status creates a temp directory with umask 077 (0700 perms),
        # the directory owner differs from the process UID, causing
        # "Permission denied" on temp files inside it (E011/E052).
        # See knowledge/doc/E011.md for details.
        pcre2_configure_path = os.path.join(src_dir, "pcre2", "configure")
        with open(pcre2_configure_path, "r") as f:
            configure_content = f.read()
        if "umask 077" in configure_content:
            configure_content = configure_content.replace("umask 077", "umask 022")
            with open(pcre2_configure_path, "w") as f:
                f.write(configure_content)

        # Patch pcre2's configure invocation in the Makefile to:
        # 1. Add --build=aarch64-unknown-linux-gnu to bypass config.guess
        #    tmp permission issue (CI worker's tmp dir is not writable).
        # 2. Pass DEFS='-DHAVE_CONFIG_H' to the recursive $(MAKE) so the
        #    autotools-generated Makefile's DEFS is not overridden by the
        #    parent DEFS='-DUNIX'. Without HAVE_CONFIG_H, pcre2grep.c
        #    skips including config.h, leaving PCRE2GREP_BUFSIZE etc.
        #    undeclared (error code:4e584c94d33a).
        # 3. Set PWD=${CURDIR}/pcre2 before ./configure: on HMDFS the
        #    parent build directory becomes inaccessible after conan
        #    creates the build tree, causing getcwd() → pwd to fail
        #    ("working directory cannot be determined").  Autoconf
        #    checks $PWD first as the working directory hint, so
        #    providing it explicitly works around the HMDFS limitation.
        makefile_path = os.path.join(src_dir, "Makefile")
        with open(makefile_path, "r") as f:
            makefile_content = f.read()
        makefile_content = makefile_content.replace(
            "cd pcre2 && ./configure && $(MAKE)",
            "cd pcre2 && PWD=${CURDIR}/pcre2 ./configure --build=aarch64-unknown-linux-gnu && $(MAKE) DEFS='-DHAVE_CONFIG_H'",
        )
        with open(makefile_path, "w") as f:
            f.write(makefile_content)

        # Build using the upstream Makefile with bundled subdirectories.
        # SUBDIRS and SUBDIROBJS are intentionally NOT overridden so the
        # upstream defaults (bzip2 libgd libpng pcre2 unzip zlib) are used.
        args = "CC={cc} CFLAGS=\"{cflags}\" DEFS='{defs}' LIBS=\"-lm\" OS={os_name}".format(
            cc=cc,
            cflags=cflags,
            defs=defs,
            os_name=os_name,
        )

        self.run("cd src && make {args}".format(args=args))

    def package(self):
        # Copy binary.
        # The build step runs "cd src && make ... -o ../analog", so the binary
        # ends up at {source_folder}/analog (one level above src/).
        copy(self, "analog", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Copy man page
        man_src = os.path.join(self.source_folder, "docs", "analog.man")
        if os.path.isfile(man_src):
            copy(self, "analog.man", src=os.path.join(self.source_folder, "docs"),
                 dst=os.path.join(self.package_folder, "man", "man1"))
        # Copy resource files
        for d in ("examples", "how-to", "images", "lang"):
            src_dir = os.path.join(self.source_folder, d)
            if os.path.isdir(src_dir):
                copy(self, "*", src=src_dir, dst=os.path.join(self.package_folder, "res", "analog", d))
        # Copy config sample
        cfg_src = os.path.join(self.source_folder, "analog.cfg-sample")
        if os.path.isfile(cfg_src):
            copy(self, "analog.cfg-sample", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "res", "analog"))
        # Copy example logfile
        log_src = os.path.join(self.source_folder, "examples", "logfile.log")
        if os.path.isfile(log_src):
            copy(self, "logfile.log", src=os.path.join(self.source_folder, "examples"),
                 dst=os.path.join(self.package_folder, "res", "analog", "examples"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []