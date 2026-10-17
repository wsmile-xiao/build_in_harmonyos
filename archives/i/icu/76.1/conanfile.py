#!/usr/bin/env python3
"""Conan recipe for ICU 76.1 — Unicode internationalization library.

HarmonyOS PC (aarch64) native adaptation. ICU source tarball extracts to a
directory containing a source/ subdirectory with configure.ac/configure.

Three issues resolved:
  1. SIGSEGV (Error -11): Sourcing Conan's conanbuild.sh causes /bin/sh to
     crash on OHOS when configure runs conftest probes.  Fix: set CC/CXX/AR/
     RANLIB directly and skip conanbuild.sh.  (Knowledge E064)
  2. Cross-compilation: ICU requires --with-cross-build when build != host.
     Create a minimal cross-build stub with icucross.mk so configure accepts
     the --with-cross-build argument.  (DRAFT-gnustep-gui-ohos-autoconf-cross-probe)
  3. E011 umask: config.status uses `umask 077` which fails on HMDFS.
     Fix: sed config.status after configure generates it.  (Knowledge E011)

References:
  - Upstream: https://github.com/unicode-org/icu
  - Tag: release-76-1
"""

import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class IcuConan(ConanFile):
    name = "icu"
    version = "76.1"
    description = "ICU — International Components for Unicode"
    license = "Unicode-3.0"
    homepage = "https://icu.unicode.org/"
    url = "https://github.com/unicode-org/icu"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Do NOT use Conan's conanbuild.sh — sourcing it crashes /bin/sh on
        # OHOS (SIGSEGV / Error -11).  Instead we set compiler vars directly
        # in the shell command that runs configure (see build()).
        pass

    def build(self):
        apply_conandata_patches(self)

        # ICU source is in source/ subdirectory after strip_root extraction
        src = os.path.join(self.source_folder, "source")

        # Ensure configure scripts are executable
        for script in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "mkinstalldirs"):
            path = os.path.join(src, script)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

        # ── Cross-compilation setup ──
        # OHOS CI blocks unsigned conftest binaries (SIGSEGV/Error -11).
        # Use different triples so configure enters cross_compiling=yes mode,
        # skipping AC_RUN_IFELSE probes.  ICU then requires --with-cross-build,
        # so we create a minimal stub directory with icucross.mk.
        host = "aarch64-unknown-linux-ohos"
        build = "x86_64-unknown-linux-gnu"

        cross_build = os.path.join(self.build_folder, "icu-cross-stub", "config")
        os.makedirs(cross_build, exist_ok=True)
        cross_build_root = os.path.join(self.build_folder, "icu-cross-stub")

        icucross_mk = os.path.join(cross_build, "icucross.mk")
        if not os.path.exists(icucross_mk):
            with open(icucross_mk, "w") as f:
                f.write("# Minimal icucross.mk stub for same-arch OHOS build\n")
                f.write(f"ICU_CROSS_BUILDROOT = {cross_build_root}\n")
                f.write("U_IS_BIG_ENDIAN = 0\n")
                f.write("U_HAVE_ATOMIC = 1\n")
                f.write("U_HAVE_STRTOD_L = 0\n")
                f.write("U_HAVE_XLOCALE_H = 0\n")

        # icucross.inc: platform make fragment (mh-linux) + genccode assembly
        icucross_inc = os.path.join(cross_build, "icucross.inc")
        if not os.path.exists(icucross_inc):
            mh_linux = os.path.join(src, "config", "mh-linux")
            import shutil
            if os.path.isfile(mh_linux):
                shutil.copy2(mh_linux, icucross_inc)
            else:
                # Fallback: write minimal content
                with open(icucross_inc, "w") as f:
                    f.write("# Minimal icucross.inc stub\n")
            with open(icucross_inc, "a") as f:
                f.write("\n# Cross-compilation overrides\n")
                f.write("GENCCODE_ASSEMBLY_TYPE = -a gcc\n")
                f.write("SO_TARGET_VERSION_SUFFIX =\n")

        configure_args = [
            f"--host={host}",
            f"--build={build}",
            f"--with-cross-build={cross_build_root}",
            "ac_cv_prog_cc_works=yes",
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--disable-shared",
            "--enable-static",
            "--disable-extras",
            "--disable-icuio",
            "--disable-layout",
            "--disable-layoutex",
            "--disable-tests",
            "--disable-samples",
            "--with-data-packaging=static",
            "--enable-renaming",
            "--disable-strict",
            "--without-html-doc",
        ]

        if self.options.shared:
            configure_args = [a for a in configure_args
                              if a not in ("--disable-shared", "--enable-static")]
            configure_args.append("--enable-shared")
            configure_args.append("--disable-static")

        # Set compiler env vars directly (no conanbuild.sh) to avoid SIGSEGV.
        env_prefix = "CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib"

        # ── Step 1: Run configure --no-create (generates config.status only) ──
        self.output.info(f"Running configure --host={host} --build={build} ...")
        self.run(
            f"{env_prefix} bash ./configure --no-create {' '.join(configure_args)}",
            cwd=src,
        )

        # ── Step 2: E011 fix — patch config.status umask 077 → 022 ──
        # HMDFS: umask 077 creates dirs that the current UID can't write to.
        config_status = os.path.join(src, "config.status")
        if os.path.isfile(config_status):
            with open(config_status, "r") as f:
                content = f.read()
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(config_status, "w") as f:
                    f.write(content)
                self.output.info("E011: Patched config.status umask 077 → 022")

        # ── Step 3: Run config.status to generate Makefiles ──
        self.output.info("Running config.status ...")
        self.run(f"{env_prefix} bash ./config.status", cwd=src)

        self.output.info("Building ICU ...")
        self.run("make -j1", cwd=src)

    def package(self):
        src = os.path.join(self.source_folder, "source")

        self.run(f"make DESTDIR={self.package_folder} install", cwd=src)

        # ICU installs to DESTDIR/usr/local by default; move to DESTDIR directly
        usr_local = os.path.join(self.package_folder, "usr", "local")
        if os.path.isdir(usr_local):
            import shutil
            for item in os.listdir(usr_local):
                src_path = os.path.join(usr_local, item)
                dst_path = os.path.join(self.package_folder, item)
                if os.path.exists(dst_path):
                    if os.path.isdir(dst_path):
                        shutil.rmtree(dst_path)
                    else:
                        os.remove(dst_path)
                shutil.move(src_path, dst_path)
            shutil.rmtree(os.path.join(self.package_folder, "usr"),
                          ignore_errors=True)

    def package_info(self):
        self.cpp_info.libs = [
            "icuuc", "icui18n", "icudata",
        ]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
