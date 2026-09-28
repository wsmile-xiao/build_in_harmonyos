#!/usr/bin/env python3
"""Conan recipe for jigit 1.22 (JTE - Jigdo Template Export, Steve McIntyre).

Upstream layout (verified against jigit-1.22.tar.xz, 91 entries):
  * top level = plain hand-written Makefile with NO install target and NO
    configure script; it builds 7 C tools and reaches straight into
    libjte/libjte_libjte_la-*.o to link parallel-sums.
  * libjte/ = bundled autotools/libtool library (AC_INIT version 2.0.0,
    SONAME libjte.so.2) -- built IN SOURCE because the parent Makefile
    consumes its object files from the source tree.

Hard build dependencies (top-level Makefile links them unconditionally):
  -lz -lbz2  (Makefile:10/13/16) and -lpthread for parallel-sums (Makefile:28).
  libjte/configure.ac only *probes* bzlib.h/pthread.h (lines 129/141) and
  has no PKG_CHECK_MODULES at all -> no GTK/GLib/X11 anywhere in the tree.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

_TOOLS = ("jigdump", "jigit-mkimage", "jigsum", "jigsum-sha256",
          "parallel-sums", "extract-data", "rsyncsum")


class JigitConan(ConanFile):
    name = "jigit"
    version = "1.22"
    description = ("JTE (Jigdo Template Export): fast tools to create, inspect "
                   "and rebuild jigdo .jigdo/.template image files, plus the "
                   "libjte helper library")
    license = "GPL-2.0-or-later"
    homepage = "https://www.einval.com/~steve/software/JTE/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is supported on Linux and OHOS only, not {self.settings.os}")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")

    def layout(self):
        # Plain basic_layout: every build step below is issued with an explicit
        # cwd inside self.source_folder, because the parent Makefile links
        # libjte's *.o files straight out of the source tree and therefore
        # forbids an out-of-tree build.
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _configure_args(self, tc):
        prefix = self.package_folder.replace("\\", "/")
        # AutotoolsToolchain injects --disable-static whenever shared=True.  That
        # is fatal for this tree: libtool then swaps the libjte_libjte_la-*.o
        # files in libjte/ for dummy objects, and the parent Makefile links
        # parallel-sums against exactly those files.  Keep libtool's own default
        # (.a *and* .so, which is also what Debian's libjte-dev ships) and let
        # the shared=False flavour disable the shared object explicitly.
        tc.configure_args = [a for a in tc.configure_args
                             if str(a) != "--disable-static"]
        tc.configure_args.extend([
            f"--prefix={prefix}",
            f"--libdir={prefix}/lib",
            f"--includedir={prefix}/include",
            "--disable-maintainer-mode",
        ])
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
        return tc.configure_args

    def generate(self):
        tc = AutotoolsToolchain(self)
        self._configure_args(tc)
        tc.generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def _relax_hmdfs_scratch_dir(self, configure_path):
        """E129: swap the mktemp-based scratch dir for plain mkdir (see build())."""
        replace_in_file(
            self, configure_path,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
            '  test -d "$tmp"',
            'tmp=./conf$$-$RANDOM\n'
            '  mkdir "$tmp"')

    def build(self):
        apply_conandata_patches(self)
        libjte = os.path.join(self.source_folder, "libjte")

        # HMDFS hands out 0660 files, so every generated build script has to be
        # made executable again before autotools can run it.
        for relative in ("configure", "config.guess", "config.sub", "install-sh",
                         "missing", "compile", "ltmain.sh", "depcomp"):
            path = os.path.join(libjte, relative)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | 0o111)

        # E129 (HMDFS scratch dir): autoconf 2.69 creates config.status' private
        # temp dir with `(umask 077 && mktemp -d "./confXXXXXX")`.  Measured on
        # this device, toybox `mktemp -d` returns mode drwx--S--- (0700 from
        # mkdtemp plus the setgid bit HMDFS forces on every new directory), and
        # the kernel then refuses open(O_WRONLY) inside it -- so
        # `echo 'BEGIN {' >"$ac_tmp/subs1.awk"` dies with "can't create
        # ./confXXXXXX/subs1.awk: Permission denied" and configure aborts with
        # "config.status: error: could not setup config files machinery".
        # Relaxing the umask alone does NOT help: the same probe shows
        # `(umask 077 && mkdir "$tmp")` already yields a writable
        # drwxrws--x, i.e. the offending mode comes from mktemp itself, not from
        # the umask.  Plain mkdir is the variant that works (as in
        # archives/a/abnfgen/0.21), so drop the mktemp branch.  The string has a
        # single occurrence in this configure (grep count measured as 1), and it
        # sits inside the quoted here-doc that configure streams into
        # ./config.status -- so editing configure is what fixes the *generated*
        # config.status, which matters because configure runs it in one shot.
        self._relax_hmdfs_scratch_dir(os.path.join(libjte, "configure"))

        # OHOS has no /usr/bin/perl; the interpreter lives in the HNP toolchain
        # bin (/data/service/hnp/bin/perl) which is on PATH, so the absolute
        # shebang has to go through env(1). Same for the bundled example script.
        for script in ("mkjigsnap", "iso-image.pl"):
            replace_in_file(
                self, os.path.join(self.source_folder, script),
                "#!/usr/bin/perl -w", "#!/usr/bin/env perl", strict=False)

        tc = AutotoolsToolchain(self)
        args = " ".join(self._configure_args(tc))
        # The profile exports CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash, but
        # that binary is denied getcwd() everywhere except / on this device
        # (verified: `cd <anywhere> && /data/service/hnp/bin/bash -c pwd` prints
        # "shell-init: error retrieving current directory: getcwd: ... Permission
        # denied").  Autoconf 2.69's prologue re-execs configure with
        # $CONFIG_SHELL, so configure dies with
        # "configure: error: working directory cannot be determined".
        # Pin both variables to the platform /bin/sh (toybox ash) for the
        # configure run; the generated libtool/Makefile inherit SHELL from it.
        self.run(f'cd "{libjte}" && CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
                 f'sh ./configure {args}', env="conanbuild")
        self.run(f'cd "{libjte}" && make -j1', env="conanbuild")
        # Top level: `make` also drives `make -C libjte` through the `lib`
        # target, which is a no-op now that libjte/Makefile exists.
        self.run('cd "{}" && make -j1'.format(self.source_folder), env="conanbuild")

    def package(self):
        libjte = os.path.join(self.source_folder, "libjte")
        # libtool install creates the libjte.so -> .so.2 -> .so.2.0.0 chain
        # with real symlinks; a manual copy() would flatten them.
        self.run(f'cd "{libjte}" && make install', env="conanbuild")

        bin_dir = os.path.join(self.package_folder, "bin")
        for tool in _TOOLS:
            copy(self, tool, src=self.source_folder, dst=bin_dir, keep_path=False)
        # bin/jigdo-gen-checksum-list is only in EXTRA_DIST upstream, so
        # `make install` never ships it; Debian installs it by hand too.
        copy(self, "jigdo-gen-checksum-list", src=os.path.join(libjte, "bin"),
             dst=bin_dir, keep_path=False)
        # mkjigsnap is a Perl helper shipped in /usr/sbin by Debian.
        copy(self, "mkjigsnap", src=self.source_folder, dst=bin_dir, keep_path=False)
        # Upstream ships exactly one driver of the libjte template-creation API:
        # libjte/test/demo (a noinst_PROGRAMS binary). Without it the .jigdo /
        # .template round trip cannot be exercised on a device, so it is
        # installed under an unambiguous name.
        demo_src = os.path.join(libjte, "test", "demo")
        if os.path.isfile(demo_src):
            shutil.copyfile(demo_src, os.path.join(bin_dir, "jte-demo"))

        share = os.path.join(self.package_folder, "share")
        copy(self, "*.1", src=self.source_folder,
             dst=os.path.join(share, "man", "man1"), keep_path=False)
        copy(self, "*.8", src=self.source_folder,
             dst=os.path.join(share, "man", "man8"), keep_path=False)
        copy(self, "jigdo-gen-checksum-list.1", src=os.path.join(libjte, "doc"),
             dst=os.path.join(share, "man", "man1"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYRIGHT", src=libjte,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        for tool in _TOOLS + ("jigdo-gen-checksum-list", "mkjigsnap", "jte-demo"):
            path = os.path.join(bin_dir, tool)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | 0o111)

        # libtool wrappers reference the build tree and are useless here.
        for stale in os.walk(os.path.join(self.package_folder, "lib")):
            for filename in stale[2]:
                if filename.endswith(".la"):
                    os.remove(os.path.join(stale[0], filename))

    def package_info(self):
        self.cpp_info.libs = ["jte"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "libjte")]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["zlib::zlib", "bzip2::bzip2"]
        self.cpp_info.set_property("pkg_config_name", "libjte-2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
