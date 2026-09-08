#!/usr/bin/env python3
"""Conan recipe for cconv 0.6.3 — Autotools project (configure + make).

cconv builds libcconv (libcconv.la) plus the `cconv` CLI tool; headers
install to $(includedir)/{cconv.h,unicode.h}.
The upstream 0.6.3 tarball ships configure.ac/Makefile.am only (no
pre-generated `configure` script), so build() bootstraps it from the
recipe's generated-build snapshot (see c-algorithms 1.0.0 precedent).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import shutil


class CconvConan(ConanFile):
    name = "cconv"
    version = "0.6.3"
    description = "Chinese character encoding conversion tool/library"
    license = "MIT"
    homepage = "https://github.com/xiaoyjy/cconv"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Upstream tarball has no generated configure; ship the autogen'd
    # snapshot (configure + OHOS-patched config.guess/config.sub + umask
    # 022 fix) so configure/make work without automake at build time.
    # Only top-level generated files are shipped: the m4/ subdirectory
    # (libtoolize bootstrap output) is NOT needed at build time because
    # Makefile.in bakes ACLOCAL/AUTOMAKE/AUTOCONF=true, so no aclocal
    # regeneration can ever run.  Keeping the recipe free of that
    # bootstrap-produced state makes it self-contained in a clean CI
    # export (see cconv-0.6.3-r02 CI first error).
    exports_sources = "generated-build/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cconv 0.6.3 has no forced third-party dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        # cconv 0.6.3 tarball ships configure.ac/Makefile.am only (no
        # generated configure); copy the recipe's generated-build snapshot
        # files into the source tree before configuring.  The tarball
        # ships an obsolete 2005 config.guess that lacks HarmonyOS
        # detection, so snapshot files (configure, config.guess,
        # config.sub, install-sh, missing, compile, aclocal.m4,
        # config.h.in, Makefile.in) must OVERWRITE their stale tarball
        # counterparts.
        #
        # Only explicit TOP-LEVEL files are copied (no subdirectory
        # walking): CI clean exports are only guaranteed for the listed
        # files, and the m4/ subdirectory (libtoolize bootstrap output)
        # is intentionally not shipped — it is unused because aclocal
        # regeneration never runs (ACLOCAL=true baked in Makefile.in).
        snapshot = os.path.join(self.export_sources_folder, "generated-build")
        required_files = (
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "compile", "aclocal.m4", "config.h.in",
            "Makefile.in", "ltmain.sh",
        )
        missing = [f for f in required_files
                   if not os.path.isfile(os.path.join(snapshot, f))]
        if missing:
            raise ConanException(
                "generated-build/ snapshot missing required files: "
                + ", ".join(missing)
                + ".  Upstream archive ships configure.ac only (no "
                "configure script); the recipe's generated-build snapshot "
                "must be complete."
            )
        for f in required_files:
            shutil.copy2(os.path.join(snapshot, f),
                         os.path.join(self.source_folder, f))
        # E490: ensure the autotools helper scripts carry the execute bit
        # (HMDFS path may drop POSIX mode bits during transfer).
        for helper in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "compile"):
            hp = os.path.join(self.source_folder, helper)
            if os.path.exists(hp):
                os.chmod(hp, 0o755)
        apply_conandata_patches(self)
        # Touch generated snapshot files so they are newer than
        # configure.ac/Makefile.am; prevents automake-generated Makefile
        # rules from re-running aclocal/automake/autoconf (which would
        # regenerate config.status and lose the OHOS patches).
        import time
        _now = time.time()
        for _gen in ("Makefile.in", "aclocal.m4", "config.h.in"):
            _gp = os.path.join(self.source_folder, _gen)
            if os.path.exists(_gp):
                os.utime(_gp, (_now, _now))
        cf = os.path.join(self.source_folder, "configure")
        if os.path.exists(cf):
            os.utime(cf, None)
        autotools = Autotools(self)
        autotools.configure()
        # AUTOMAKE/ACLOCAL=true: CI lacks automake; the shipped generated
        # Makefile.in must be used verbatim without regeneration (see
        # c-algorithms 1.0.0 precedent).
        self.run("AUTOMAKE=true ACLOCAL=true make -j1", env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # libcconv.la -> -lcconv
        self.cpp_info.libs = ["cconv"]
