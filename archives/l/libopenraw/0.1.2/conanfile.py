#!/usr/bin/env python3
"""Conan recipe — libopenraw 0.1.2 (Autotools, C++11)

libopenraw is a library for decoding camera RAW files.

OHOS adaptations:
  - Patch 001: disable gnome/curl/testsuite, prune SUBDIRS to lib/doc/include.
  - autoreconf at build time (automake/libtool as build_requires), so no
    generated files need to be shipped in this PR.
  - OHOS autotools toolchain fix: the conan perl 5.42.2 binary is a PIE
    executable with BIND_NOW and no exported symbols, so it cannot load the
    XS modules its own automake scripts need — aclocal dies with
        Can't load .../Cwd/Cwd.so: Perl_my_cxt_init: symbol not found
    The scripts themselves are installed with a hardcoded
    ``#!/data/service/hnp/bin/perl`` (worker perl 5.42.0, which does load
    Cwd), so the only problem left is PERL5LIB: conanbuildenv points it at
    the conan 5.42.2 module tree, which that 5.42.0 interpreter then fails
    to load. Narrow PERL5LIB to the automake module dir, add the libtool and
    hnp pkg-config m4 dirs to ACLOCAL_PATH, and keep conan's
    aclocal/automake/libtoolize ahead on PATH (the worker has no copies).
  - configure: umask 077 -> 022 (HMDFS forces setgid, so mktemp dirs
    created with umask 077 are unwritable).
  - make -j1: parallel make hits HMDFS jobserver fifo EPERM.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibopenrawConan(ConanFile):
    name = "libopenraw"
    version = "0.1.2"
    description = "Library for easy decoding of camera RAW files"
    license = "LGPL-3.0-or-later"
    homepage = "https://libopenraw.freedesktop.org/"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libopenraw is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("boost/1.84.0")
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        # aclocal/automake/libtoolize are absent from the OHOS worker's hnp
        # tooling (hnp ships only m4/autoconf/autoheader/autoreconf), so these
        # three come from conan. They are also the only build tools needed:
        # autoreconf resolves m4/autoconf/autoheader from PATH, which hnp
        # provides, and from the AUTOCONF/AUTOHEADER/AUTOM4TE variables that
        # conanbuildenv points at the hnp copies.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def generate(self):
        # Emit libxml2's libxml-2.0.pc (plus boost/jpeg pc files) and put the
        # generator dir on PKG_CONFIG_PATH so configure's PKG_CHECK_MODULES
        # (LIBXML) resolves the dependency.
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-gnome")
        tc.configure_args.append("--disable-curl")
        boost_folder = self.dependencies["boost"].package_folder
        tc.configure_args.append(f"--with-boost={boost_folder}/include")
        jpeg_folder = self.dependencies["libjpeg-turbo"].package_folder
        tc.extra_cflags.append(f"-I{jpeg_folder}/include")
        tc.extra_cxxflags.append(f"-I{jpeg_folder}/include")
        tc.extra_cxxflags.append("-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE")
        tc.extra_ldflags.append(f"-L{jpeg_folder}/lib")
        # libxml2 is consumed via pkg-config by configure (PKG_CHECK_MODULES
        # in configure.ac), so its .pc dir must be on PKG_CONFIG_PATH.
        xml_folder = self.dependencies["libxml2"].package_folder
        tc.extra_cflags.append(f"-I{xml_folder}/include/libxml2")
        tc.extra_cflags.append(f"-I{xml_folder}/include")
        tc.extra_ldflags.append(f"-L{xml_folder}/lib")
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def _run_autoreconf(self):
        """Run autoreconf with a working perl on OHOS.

        conanbuildenv exports PERL5LIB as the conan perl 5.42.2 module tree.
        aclocal/automake/libtoolize are shell shims here, but the perl behind
        them is the worker's hnp perl 5.42.0 (``#!/data/service/hnp/bin/perl``
        in the installed scripts). If PERL5LIB still lists the 5.42.2 tree,
        that 5.42.0 interpreter goes looking for modules under 5.42.2 paths
        and aclocal dies before doing any work.

        So narrow PERL5LIB to the automake perl module dir, add the libtool
        and hnp pkg-config m4 dirs to ACLOCAL_PATH (PKG_INSTALLDIR), and keep
        conan's aclocal/automake/libtoolize ahead on PATH — the worker ships
        no copies of those three. m4/autoconf/autoheader are still resolved
        from the worker PATH, which is what hnp installs.
        """
        env = {}
        ac = next((d for d in self.dependencies.build.values()
                   if d.ref.name == "automake"), None)
        lt = next((d for d in self.dependencies.build.values()
                   if d.ref.name == "libtool"), None)
        if ac and lt:
            env["PERL5LIB"] = os.path.join(ac.package_folder, "share", "automake-1.18")
            env["ACLOCAL_PATH"] = ":".join([
                os.path.join(ac.package_folder, "share", "aclocal-1.18"),
                os.path.join(lt.package_folder, "share", "aclocal"),
                "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal",
            ])
            # Prepended, not replaced: dirname/sed live in /system/bin.
            env["PATH"] = ":".join([
                os.path.join(ac.package_folder, "bin"),
                os.path.join(lt.package_folder, "bin"),
            ]) + ":$PATH"
        if str(self.settings_build.os) == "OHOS":
            # /tmp is read-only on these workers and m4 needs a scratch dir.
            env["TMPDIR"] = self._scratch_dir()
        # PATH is double-quoted so the trailing $PATH expands; the rest are
        # single-quoted (conan paths contain no spaces).
        prefix = " ".join(
            f'PATH="{v}"' if k == "PATH" else f"{k}='{v}'"
            for k, v in env.items())
        self.run(f"{prefix} autoreconf -f -i", cwd=self.source_folder)

    def _scratch_dir(self):
        """A writable scratch dir: /tmp is read-only on OHOS workers."""
        if self.build_folder:
            d = os.path.join(self.build_folder, "tmp")
            os.makedirs(d, exist_ok=True)
            return d
        return os.environ.get("TMPDIR", "/tmp")

    def _fix_configure_umask(self):
        """autoreconf regenerates configure, so this must run AFTER it."""
        for cfg in glob.glob(os.path.join(self.source_folder, "configure")):
            with open(cfg, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "umask 077" not in text:
                continue
            text = text.replace("umask 077", "umask 022")
            with open(cfg, "w", encoding="utf-8") as f:
                f.write(text)
            self.output.info("patched configure: umask 077 -> umask 022")

    def build(self):
        apply_conandata_patches(self)
        self._run_autoreconf()
        self._fix_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # The upstream testsuite compiles the TESTS (test_xmlhandler + testsuite)
        # and runs them. It requires libxml2 and, for the raw-file tests, the
        # actual camera RAW files that are fetched via CURL bootstrap. The raw
        # files are not present on the build machine, so only the self-contained
        # unit test (test_xmlhandler) actually passes; the file-backed tests are
        # expected to be skipped/failed without their data.
        # Run the testsuite tests in two steps, only inside the testsuite/ subdir
        # (running from the build root also recurses into lib/ where
        # TESTS=teststream links against the uninstalled libopenraw.la and fails
        # to resolve libxml2.so at link time in the OHOS CI).
        #   1) "make check_PROGRAMS" with env="conanbuild": compiling/linking the
        #      check programs needs the linker to find the system libxml2
        #      (LD_LIBRARY_PATH must NOT be clobbered by conanrun's override).
        #   2) "make check-TESTS" with env="conanrun": running the binaries needs
        #      the dependencies (libopenraw.so, libxml2, ...) on the loader path.
        # Guard with can_run() so the tests only execute when host==build (e.g.
        # the OHOS worker).
        if can_run(self):
            tsuite = os.path.join(self.build_folder, "testsuite")
            # check_PROGRAMS is a variable (test_xmlhandler) not a make target;
            # compile the real program targets so the linker runs under conanbuild
            # (LD_LIBRARY_PATH keeps the system libxml2 for the OHOS lld).
            self.run('make -C "%s" test_xmlhandler testsuite -j1' % tsuite, env="conanbuild")
            # check-TESTS is the target that runs the TESTS; run it under conanrun
            # so the binaries find libopenraw.so / libxml2 on the loader path.
            self.run('make -C "%s" check-TESTS -j1' % tsuite, env="conanrun")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["openraw"]
        self.cpp_info.set_property("cmake_file_name", "libopenraw")
        self.cpp_info.set_property("cmake_target_name", "libopenraw::libopenraw")
        self.cpp_info.set_property("pkg_config_name", "libopenraw-0.1")
        self.cpp_info.includedirs = ["include", "include/libopenraw-0.1"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
