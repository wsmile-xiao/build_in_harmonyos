#!/usr/bin/env python3
"""
Conan recipe for authselect v1.7.1 — OHOS (OpenHarmony) aarch64 adaptation.

Build system: autotools (configure + make).
Dependencies: popt (CLI parsing), libselinux (SELinux policy), gettext (i18n, build), cmocka (test, build).
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AuthselectConan(ConanFile):
    name = "authselect"
    version = "1.7.1"
    description = "Tool to select system authentication and identity sources from supported profiles"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/authselect/authselect"
    url = "https://github.com/authselect/authselect"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("popt/1.16")
        self.requires("libselinux/3.10.1")

    def build_requirements(self):
        # Git tag archive ships no configure; bootstrap with autoreconf in
        # build().  CI host has the autoconf suite under /data/service/hnp/bin
        # but lacks aclocal/automake/libtoolize, so pull them in as
        # tool_requires (same approach as afuse/adcli).  gettext provides
        # autopoint + gettext.m4 for AM_GNU_GETTEXT in configure.ac.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("gettext/0.22.5.1")
        self.test_requires("cmocka/2.0.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-nls")
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        # REQUIRE_SELINUX in configure.ac uses AC_CHECK_HEADERS (not
        # PKG_CHECK_MODULES), so CPPFLAGS must include the selinux
        # include dir.  Set it in the toolchain environment BEFORE
        # tc.generate() writes conanbuild.sh.
        libselinux = self.dependencies.get("libselinux")
        if libselinux is not None:
            self.buildenv.define("CPPFLAGS",
                f"-I{libselinux.package_folder}/include")
            self.buildenv.define("LDFLAGS",
                f"-L{libselinux.package_folder}/lib")
        # pcre2/10.47 is a transitive dependency of libselinux/3.10.1.
        # libauthselect.so references pcre2_get_error_message_8, and the
        # linker (--no-allow-shlib-undefined) requires the symbol to be
        # resolvable at link time.  Add -lpcre2-8 explicitly.
        pcre2 = self.dependencies.get("pcre2")
        if pcre2 is not None:
            self.buildenv.append("LDFLAGS",
                f"-L{pcre2.package_folder}/lib -lpcre2-8")
        # config.status creates temp files via mktemp; ensure TMPDIR
        # points to a writable location (HMDFS setgid + bad uid).
        self.buildenv.define("TMPDIR", os.path.expanduser("~/tmp"))
        tc.generate()
        # PkgConfigDeps generates .pc files for popt/cmocka etc. so
        # configure's PKG_CHECK_MODULES (POPT, CMOCKA) succeeds.
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # Upstream GitHub tag tarball does not ship pre-generated configure;
        # bootstrap with autoreconf.  The gettext tool package does not export
        # ACLOCAL_PATH/GETTEXTDATADIR, so locate its share dirs dynamically
        # and provide them so aclocal finds gettext.m4 (AM_GNU_GETTEXT) and
        # autopoint finds its archive data.
        self.run(
            'GETTEXT_PREFIX=$(dirname "$(dirname "$(command -v autopoint)")") && '
            'mkdir -p build && '
            'cp "$GETTEXT_PREFIX/share/gettext/config.rpath" build/ 2>/dev/null && '
            'ACLOCAL_PATH="$GETTEXT_PREFIX/share/aclocal${ACLOCAL_PATH:+:$ACLOCAL_PATH}" '
            'AUTOPOINT=true autoreconf -fi',
            cwd=self.source_folder, env="conanbuild")
        # E114/E011: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
        # yields a drwx--S--- temp dir config.status cannot write into.
        # Relax umask in the generated configure (same as afuse/adcli).
        self.run("sed -i 's/umask 077/umask 022/g' configure",
                 cwd=self.source_folder)
        # autopoint is skipped (AUTOPOINT=true) so po/Makefile.in.in
        # (normally installed by gettext) is missing.  Create a minimal
        # placeholder since we use --disable-nls.
        self.run("mkdir -p po && touch po/Makefile.in.in",
                 cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        # NLS is disabled, so the po/ subdirectory has no build targets.
        # Remove it from SUBDIRS in the generated Makefile so make
        # doesn't fail trying to build po/.
        self.run("sed -i '/^SUBDIRS/s/ po / /' Makefile")
        # OHOS Clang's <regex.h> does not define REG_NOERROR (POSIX
        # constant for regexec success).  Replace it everywhere with the
        # literal value 0 (nsswitch.c, template.c, ...).
        self.run(
            "grep -rl 'REG_NOERROR' src/ | xargs sed -i 's/REG_NOERROR/0/g'",
            cwd=os.path.join(self.build_folder, ".."))
        # OHOS glibc-compat lacks BSD permission macros ALLPERMS/
        # ACCESSPERMS.  Replace them with their literal values.
        self.run(
            "sed -i 's/ALLPERMS/07777/g; s/ACCESSPERMS/07777/g' "
            "src/lib/files/symlinks.c src/lib/files/nsswitch.c "
            "src/lib/util/file.c src/lib/util/template.c "
            "src/lib/util/textfile.c",
            cwd=os.path.join(self.build_folder, ".."))
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["authselect"]