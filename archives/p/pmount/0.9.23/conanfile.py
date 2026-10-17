import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches, get,
                         replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.errors import ConanInvalidConfiguration


class PmountConan(ConanFile):
    name = "pmount"
    version = "0.9.23"
    package_type = "application"

    description = ("pmount - mount removable devices as a normal user: it wraps mount(8) so a "
                   "user can mount hotplugged media without a matching fstab entry.")
    license = "GPL-2.0-or-later"
    homepage = "https://alioth-archive.debian.org/releases/pmount/pmount"
    url = ""
    topics = ("cli", "mount", "removable-devices", "linux")

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("pmount/%s is only built for OHOS armv8 here"
                                            % self.version)

    def requirements(self):
        # configure.ac:20-24 hard-fails without <blkid/blkid.h> and links -lblkid
        # through AC_CHECK_LIB.  The OHOS package ships a static libblkid.a.
        self.requires("libblkid/2.42.2")
        # Every source file includes <libintl.h> unconditionally and _() maps to
        # gettext(), so the NLS runtime is a link-time dependency even for
        # --disable-nls.  gettext/0.22.5.1 provides the header plus libintl.
        self.requires("gettext/0.22.5.1")

    def build_requirements(self):
        # configure:3899-3909 runs `intltool-update --version` unconditionally
        # (the AC_PROG_INTLTOOL version gate is not guarded by enable-nls), so
        # intltool must be on PATH already at configure time.
        self.tool_requires("intltool/0.51.0")
        # AM_GNU_GETTEXT/intltool.m4 probes `msgmerge` (and msgfmt/xgettext) at configure
        # time.  The device has them under brew, the CI worker does not, so configure
        # aborts with "GNU gettext tools not found; required for intltool" only in CI.
        # gettext is already a host requires() for <libintl.h>/libintl; declaring it as a
        # build tool too puts its bindirs on PATH through VirtualBuildEnv.
        self.tool_requires("gettext/0.22.5.1")

    # Conventional out-of-tree build: conan's default layout keeps src/ and
    # build/ apart, and automake 1.11 was already used to write these
    # Makefile.in files, so tests/Makefile.am's "../src/libpmount-util.a" and
    # "-I../src" resolve correctly under build/.  Regenerating that machinery is
    # the one thing that must not happen (see --disable-maintainer-mode).

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # AutotoolsToolchain only emits toolchain/compiler flags, so the -I/-L of
        # the host requirements have to be injected (configure otherwise dies on
        # "Missing /usr/include/blkid/blkid.h").  AutotoolsDeps is deliberately not
        # used: it flattens gettext/0.22.5.1's cpp_info.libs, which names
        # "asprintf" although that package ships no libasprintf (only intl,
        # gettextpo, gettextlib, gettextsrc, textstyle) =>
        # ld.lld: error: unable to find library -lasprintf.  Only -lintl and
        # -lblkid are actually required here, so the link line is built explicitly.
        tc = AutotoolsToolchain(self)
        # --disable-maintainer-mode: do not let make try to regenerate the
        # 2010-era Makefile.in files (automake >= 1.16 cannot read this
        # configure.ac at all -- AM_CONFIG_HEADER/AM_PROG_LIBTOOL/
        # AC_PROG_INTLTOOL/AC_HEADER_STDC were all removed since).
        tc.configure_args.extend([
            "--disable-maintainer-mode",
            "--disable-hal",                # hal is not packaged for OHOS
            "--disable-nls",                # po/ catalogs, not shipped
            "--disable-ruid-root-cryptsetup",
        ])
        if self.settings.os == "OHOS":
            # CI/conan passes no --build/--host when the build and host profiles
            # are the same device profile, so configure falls back to the bundled
            # config.guess (2008-01-23), which cannot classify UNAME_SYSTEM=HarmonyOS
            # and dies with "cannot guess build type; you must specify one".
            # The pair must also differ: with build == host autoconf assumes it can
            # execute probe binaries, and ./conftest then fails with
            # "Error loading shared library libintl.so.8" (create-07) because the
            # dependency lib dirs are not on the loader path during configure.
            # Declaring a real cross build skips those run tests; make check gets
            # the loader path explicitly instead (see _check_env in build()).
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        env = tc.environment()
        for ref, libs in (("libblkid", ("blkid",)), ("gettext", ("intl",))):
            agg = self.dependencies[ref].cpp_info.aggregated_components()
            for inc in agg.includedirs:
                env.append("CPPFLAGS", "-I%s" % os.path.join(
                    self.dependencies[ref].package_folder, inc))
            for lib in agg.libdirs:
                env.append("LDFLAGS", "-L%s" % os.path.join(
                    self.dependencies[ref].package_folder, lib))
            for name in libs:
                env.append("LIBS", "-l%s" % name)
        tc.generate(env=env)

    def _loader_env(self):
        dirs = []
        for ref in ("libblkid", "gettext"):
            dep = self.dependencies[ref]
            agg = dep.cpp_info.aggregated_components()
            dirs.extend(os.path.join(dep.package_folder, d) for d in agg.libdirs)
        return 'LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH"' % ":".join(dirs)

    def _write_fstab_fixture(self):
        """Recreate tests/check_fstab/, which upstream forgot to distribute.

        tests/Makefile.am has no EXTRA_DIST and the tarball has no check_fstab/
        directory, so test_policy cannot run as shipped: src/policy.c:406-409
        exits 100 when the fstab file cannot be opened.  Debian documents the
        same conclusion ("skipping tests (buggy in upstream tarball)" in its
        debian/rules).  The four assertions in tests/test_policy.c fully
        determine what the fixture must contain, so it is restored rather than
        dropped -- see notes.md for the case-by-case derivation.
        """
        d = os.path.join(self.build_folder, "tests", "check_fstab")
        os.makedirs(d, exist_ok=True)
        for name in ("a", "d"):
            with open(os.path.join(d, name), "w") as handle:
                handle.write("stub block device %s\n" % name)
        for link, target in (("b", "a"), ("c", "d"), ("e", "d")):
            path = os.path.join(d, link)
            if not os.path.islink(path):
                if os.path.exists(path):
                    os.remove(path)
                os.symlink(target, path)
        with open(os.path.join(d, "fstab"), "w") as handle:
            handle.write("check_fstab/a\t/mnt/a\ttmpfs\tdefaults\t0\t0\n"
                         "check_fstab/e\t/mnt/e\ttmpfs\tdefaults\t0\t0\n")

    def build(self):
        apply_conandata_patches(self)
        # E011/E114: config.status builds its helper dir with `(umask 077 &&
        # mktemp -d ./confXXXXXX)`, and on HMDFS the 0700 dir plus files created
        # without stored exec bits make the following `./confXXXXXX/subs1.awk`
        # invocation fail with "Permission denied" ->
        # "config.status: error: could not setup config files machinery".
        # Relaxing the mask keeps the real temp-directory creation intact (the
        # mktemp/mkdir fallbacks are untouched) instead of hiding it by swapping
        # environment.  One call covers both sites (configure:13279, :13284).
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 002", strict=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream suite: tests/Makefile.am registers TESTS = test_policy
        # (4 assertions inside).  test_sysfs is a check_PROGRAM only, upstream
        # marks it "not a real test" (it walks /sys for a live block device).
        self._write_fstab_fixture()
        # test_policy links gettext's shared libintl, so the loader has to be told
        # where the conan packages live -- CI's PATH/env is not the device shell's.
        self.run("%s make check -j1" % self._loader_env(), env="conanbuild",
                 cwd=self.build_folder)

    def package(self):
        # No autotools.install(): src/Makefile.am's install-data-hook copies the
        # binaries with `-o root -g root -m 4755`, which a non-root worker cannot
        # do, and pmount/pumount are noinst_PROGRAMS -- bin_PROGRAMS is only
        # non-empty when the hal frontend is enabled, which it is not.  Place the
        # two programs explicitly and keep their real permission bits: the
        # setuid escalation upstream relies on is not available on OHOS, so the
        # packaged tools are functional only on their unprivileged code paths.
        bindir = os.path.join(self.package_folder, "bin")
        for prog in ("pmount", "pumount"):
            copy(self, prog, src=os.path.join(self.build_folder, "src"), dst=bindir,
                 keep_path=False)
        copy(self, "pmount.allow", src=os.path.join(self.source_folder, "etc"),
             dst=os.path.join(self.package_folder, "res"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.set_property("cmake_find_mode", "none")
