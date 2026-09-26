import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir
from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class MmdbConan(ConanFile):
    name = "mmdb"
    version = "2.0.22"
    description = "Macromolecular coordinate library (CCP4 mmdb2)"
    license = "LGPL-3.0-or-later"
    url = "https://www.ccp4.ac.uk"
    homepage = "https://www.ccp4.ac.uk"
    topics = ("mmdb2", "ccp4", "mmcif", "pdb", "macromolecule", "coordinates")
    # Upstream configure.ac declares LT_INIT([disable-shared win32-dll]), so a
    # shared flavour cannot be built at all: the package is static-only and
    # therefore does not expose a "shared" option (Conan rejects a "library"
    # package type without one).
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    @property
    def _shell_guard(self):
        # Inline override for the shell that the ohos-aarch64 profile injects
        # (CONFIG_SHELL=SHELL=/data/service/hnp/bin/bash, a bash 5.3 whose
        # getcwd() fails in every directory on this device, which kills every
        # Autoconf script). See build() for the measurements.
        return "CONFIG_SHELL=/bin/sh SHELL=/bin/sh"

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        # No upstream patch is required for this port; the hook is kept so a
        # future patch set flows through the standard conandata pipeline.
        export_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        AutotoolsDeps(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _relax_autoconf_tmp_dir(self):
        """Point the autoconf scratch directory at a mode this tree accepts.

        Mechanism measured for this package inside the Conan build folder:
        "(umask 077 && mktemp -d ./confXXXXXX)" produces drwx--S--- and the
        next write into it fails ("touch: Permission denied"), while
        "(umask 000 && mkdir ...)" produces drwxrws--x and writes fine - a 0700
        directory is simply not writable by the effective uid on this HMDFS
        mount. config.status aborts with

            ./config.status[1035]: can't create ./confMuXnpa/subs1.awk
            config.status: error: could not setup config files machinery

        unless the scratch directory is created differently.
        configure/config.status are generated files shipped inside the release
        tarball, so they cannot go through the patches/ pipeline (R6); the
        substitution is therefore done in place at build time, the same shape
        the merged archives/c/cln/1.3.7 recipe uses (its mktemp variant is
        replaced by a umask-000 mkdir with a $$-$RANDOM unique name).
        """
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            self.output.warning("[tmp-dir] no configure script found, skipped")
            return
        with open(cfg, encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
        new = 'tmp=./conf$$-$RANDOM && (umask 000 && mkdir "$tmp") &&'
        if old not in text:
            self.output.warning(
                "[tmp-dir] autoconf mktemp pattern not found; upstream layout "
                "changed, re-check before trusting this recipe")
            return
        with open(cfg, "w", encoding="utf-8") as handle:
            handle.write(text.replace(old, new))
        self.output.info("[tmp-dir] replaced mktemp -d with a umask-000 mkdir")

    def build(self):
        apply_conandata_patches(self)
        # HarmonyOS/HMDFS shell fix (same family as knowledge entry E386 and
        # knowledge/drafts/DRAFT-6487-classads-configshell-hmdfs-getcwd): the
        # ohos-aarch64 profile exports CONFIG_SHELL=SHELL=/data/service/hnp/bin/bash.
        # That bash 5.3 cannot resolve its working directory anywhere on this
        # device - measured: "bash -c pwd" fails with
        # "getcwd: cannot access parent directories" in the Conan cache build
        # folder, in its src sibling and even in a freshly created directory
        # under ~/tmp, while "/bin/sh -c pwd" succeeds in all of them. Autoconf
        # re-execs configure and every config.* helper under CONFIG_SHELL, so
        # configure died at "working directory cannot be determined".
        # conanbuild.sh sources the profile buildenv last, so no
        # AutotoolsToolchain/VirtualBuildEnv assignment can beat it - the
        # override has to be inline, after conanbuild has been sourced.
        # Measured root cause differs from the draft above: the failing piece
        # is the bash binary, not the depth of the build directory.
        shell_guard = self._shell_guard
        src = self.source_folder
        # The scratch directory autoconf's config.status creates for its
        # generated awk/Makefile fragments is unusable on this device; the
        # substitution is explained in _relax_autoconf_tmp_dir().
        self._relax_autoconf_tmp_dir()
        # configure args mirror the Conan AutotoolsToolchain DESTDIR convention
        # (prefix=/ plus DESTDIR at install time) so the package stays
        # relocatable and nothing is written to a shared system prefix (R49).
        # The explicit --build/--host pair is required: the release tarball
        # ships a config.guess from 2013 which cannot map "uname -s =
        # HarmonyOS" to any system, and its GNU-probe fallback dies on this
        # device with "can't create $TMPDIR/cgXXXXXX/dummy.c: Permission
        # denied" (E007 family: GNU config scripts have no HarmonyOS branch).
        # Patching the generated scripts is not an option here (R6 forbids
        # editing generated files and the skill helper is only reachable when
        # OHC_SKILL_ROOT is exported), and the OHOS triplet itself is rejected
        # by that old config.sub (E072). build == host keeps autoconf on the
        # native path, so AC_RUN_IFELSE style probes still execute instead of
        # being skipped by a false cross-compile verdict.
        triplet = "aarch64-unknown-linux-musl"
        configure_args = (" --prefix=/ '--bindir=${prefix}/bin'"
                          " '--sbindir=${prefix}/bin'"
                          " '--libdir=${prefix}/lib'"
                          " '--includedir=${prefix}/include'"
                          " '--oldincludedir=${prefix}/include'"
                          " --build=" + triplet + " --host=" + triplet)
        self.run('cd "{}" && {} "./configure"{}'.format(src, shell_guard, configure_args),
                 env="conanbuild")
        self.run('cd "{}" && {} make -j4'.format(src, shell_guard), env="conanbuild")
        # Upstream registers no automated test suite at all: Makefile.am has
        # no TESTS / check_PROGRAMS and the tarball ships no tests directory
        # (inventory evidence in notes.md). The automake check target is still
        # invoked so the recipe never silently skips a suite that exists.
        self.run('cd "{}" && {} make -j4 check'.format(src, shell_guard), env="conanbuild")

    def package(self):
        shell_guard = self._shell_guard
        self.run('cd "{}" && {} make -j1 install DESTDIR="{}"'.format(
            self.source_folder, shell_guard, self.package_folder), env="conanbuild")
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LESSER", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mmdb")
        self.cpp_info.set_property("cmake_target_name", "mmdb::mmdb")
        self.cpp_info.set_property("pkg_config_name", "mmdb2")
        self.cpp_info.libs = ["mmdb2"]
        # pkginclude_HEADERS installs the public headers into include/mmdb2.
        self.cpp_info.includedirs = ["include", os.path.join("include", "mmdb2")]
        # AC_SEARCH_LIBS([cos],[m]): libm is a hard runtime requirement.
        self.cpp_info.system_libs = ["m"]
