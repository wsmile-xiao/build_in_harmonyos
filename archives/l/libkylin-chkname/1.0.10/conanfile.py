#!/usr/bin/env python3
"""Conan Autotools recipe for libkylin-chkname 1.0.10."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _patch_generated_config_guess(conanfile):
    """Teach Automake's generated config.guess to identify HarmonyOS.

    automake/1.18 already accepts ``aarch64-unknown-linux-ohos`` in
    config.sub, but its config.guess cannot derive that triplet from the
    native worker's ``uname -s = HarmonyOS``.  Patch the freshly generated
    helper instead of passing --build/--host, which would incorrectly turn a
    native build into a cross build and skip runtime feature checks.
    """
    config_guess = os.path.join(
        conanfile.source_folder, "build-aux", "config.guess"
    )
    if not os.path.isfile(config_guess):
        raise ConanInvalidConfiguration(
            "autoreconf did not generate build-aux/config.guess"
        )

    with open(config_guess, "r", encoding="utf-8") as handle:
        content = handle.read()
    if "*:HarmonyOS:*:*)" not in content:
        marker = (
            "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:"
            "$UNAME_VERSION in\n"
        )
        if marker not in content:
            raise ConanInvalidConfiguration(
                "unsupported config.guess layout: platform case not found"
            )
        harmonyos_case = (
            "    *:HarmonyOS:*:*)\n"
            "\tcase \"$UNAME_MACHINE\" in\n"
            "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
            "\t    x86_64|amd64) MACHINE=x86_64 ;;\n"
            "\t    *) MACHINE=\"$UNAME_MACHINE\" ;;\n"
            "\tesac\n"
            "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
            "\t;;\n\n"
        )
        content = content.replace(marker, marker + harmonyos_case, 1)
        with open(config_guess, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(config_guess, 0o755)
        conanfile.output.info(
            "config.guess: added native HarmonyOS platform detection"
        )


def _patch_generated_configure_umask(conanfile):
    """Keep Autoconf's config.status temporary directory writable on HMDFS.

    HarmonyOS HMDFS remaps directory ownership.  Autoconf's ``umask 077``
    then leaves the active worker unable to create ``subs1.awk`` below the
    generated ``confXXXXXX`` directory.  The established E011 workaround
    uses a 022 mask so HMDFS does not leave that directory owner-only under
    the mapped identity.
    """
    configure = os.path.join(conanfile.source_folder, "configure")
    if not os.path.isfile(configure):
        raise ConanInvalidConfiguration(
            "autoreconf did not generate configure"
        )

    with open(configure, "r", encoding="utf-8") as handle:
        content = handle.read()
    occurrences = content.count("umask 077")
    if occurrences == 0:
        raise ConanInvalidConfiguration(
            "unsupported configure layout: Autoconf temporary-directory "
            "umask not found"
        )

    content = content.replace("umask 077", "umask 022")
    with open(configure, "w", encoding="utf-8") as handle:
        handle.write(content)
    conanfile.output.info(
        "configure: relaxed {} HMDFS temporary-directory umask(s)".format(
            occurrences
        )
    )


class LibkylinChknameConan(ConanFile):
    name = "libkylin-chkname"
    version = "1.0.10"
    description = "Library for validating openKylin user and group names"
    license = "MulanPSL-2.0"
    homepage = "https://gitee.com/openkylin/libkylin-chkname"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libintl is part of the public API implementation: strerror strings
        # are translated at runtime.  Propagate its link information even for
        # the shared build: OHOS lld uses --no-allow-shlib-undefined and must
        # be able to locate libintl.so while linking each downstream binary.
        # gettext is packaged as an application, so Conan propagates its lib
        # directory without adding library names.  package_info() explicitly
        # adds only intl, which is also required by static consumers.
        self.requires(
            "gettext/0.22.5.1",
            transitive_headers=False,
            transitive_libs=True,
        )

    def build_requirements(self):
        # The release archive must be bootstrapped from configure.ac.  CI only
        # preinstalls autoconf, so supply the architecture-neutral aclocal,
        # automake and libtoolize scripts through the approved tool packages.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libkylin-chkname supports Linux and OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        # gettext/0.22.5.1 currently advertises an absent libasprintf in its
        # aggregate cpp_info.  This library only uses libintl, so expose only
        # its headers and library search path.  Do not put -lintl in global
        # LIBS: AC_PROG_CC would then link its earliest runnable conftest to a
        # target shared library, and native HarmonyOS workers whose loader
        # path does not include the Conan cache report error 77.  Patch 0003
        # attaches -lintl only to the real library and tells Libtool that the
        # shared target must not retain unresolved symbols.  Using $(LIBINTL)
        # here is insufficient: Libtool reduces its absolute .so path to -L
        # and omits libintl from the target's DT_NEEDED entries on OHOS.
        gettext = self.dependencies["gettext"]
        dependency_env = Environment()
        # Keep the matching Conan libintl header/library pair ahead of the
        # worker's shared /usr/local prefix.  That prefix can contain GLib's
        # proxy libintl.h (which redirects to g_libintl_*), while the Conan
        # gettext library exports the standard libintl_* ABI.
        dependency_env.prepend(
            "CPPFLAGS", "-I{}".format(os.path.join(gettext.package_folder, "include"))
        )
        dependency_env.prepend(
            "LDFLAGS", "-L{}".format(os.path.join(gettext.package_folder, "lib"))
        )
        # The OHOS CI image keeps the native gettext bootstrap tools outside
        # PATH.  autoreconf needs both autopoint and its architecture-neutral
        # archive data; the Conan gettext requirement itself is target code
        # and therefore must not be executed on the build host.
        native_gettext = "/data/service/hnp/gettext.org/gettext_0.26"
        native_autopoint = os.path.join(native_gettext, "bin", "autopoint")
        if not os.path.isfile(native_autopoint):
            native_autopoint = shutil.which("autopoint")
            if native_autopoint:
                native_gettext = os.path.dirname(os.path.dirname(native_autopoint))
        if not native_autopoint:
            raise ConanInvalidConfiguration(
                "native autopoint is required to bootstrap the release archive"
            )
        dependency_env.define("AUTOPOINT", native_autopoint)
        dependency_env.define(
            "gettext_datadir", os.path.join(native_gettext, "share", "gettext")
        )
        # The worker only exposes msgfmt/xgettext in its default HNP PATH;
        # msgmerge remains in gettext.org/<version>/bin.  The generated po
        # rules require a real host msgmerge to create each intermediate
        # *.1po file, even though configure otherwise accepts MSGMERGE=:.
        native_msgmerge = os.path.join(native_gettext, "bin", "msgmerge")
        if not os.path.isfile(native_msgmerge):
            native_msgmerge = shutil.which("msgmerge")
        if not native_msgmerge:
            raise ConanInvalidConfiguration(
                "native msgmerge is required to build translation catalogs"
            )
        dependency_env.prepend_path("PATH", os.path.dirname(native_msgmerge))
        dependency_env.define_path("MSGMERGE", native_msgmerge)

        # Run the packaged Automake Perl scripts explicitly.  Their shebang
        # names the OHOS worker's Perl path, which is not portable to local
        # verification hosts even though the scripts are architecture-neutral.
        bootstrap_env = Environment()
        automake = self.dependencies.build["automake"]
        automake_bin = os.path.join(automake.package_folder, "bin")
        automake_data = os.path.join(
            automake.package_folder, "share", "automake-1.18"
        )
        aclocal_data = os.path.join(
            automake.package_folder, "share", "aclocal"
        )
        aclocal_versioned = os.path.join(
            automake.package_folder, "share", "aclocal-1.18"
        )
        native_perl = "/data/service/hnp/bin/perl"
        if not os.path.isfile(native_perl):
            native_perl = shutil.which("perl")
        if not native_perl:
            raise ConanInvalidConfiguration(
                "native Perl is required to run the Automake tools"
            )
        bootstrap_env.define(
            "ACLOCAL",
            shlex.join(
                [
                    native_perl,
                    os.path.join(automake_bin, ".aclocal-real"),
                    "--automake-acdir=" + aclocal_versioned,
                    "--system-acdir=" + aclocal_data,
                ]
            ),
        )
        bootstrap_env.define(
            "AUTOMAKE",
            shlex.join(
                [
                    native_perl,
                    os.path.join(automake_bin, ".automake-real"),
                    "--libdir=" + automake_data,
                ]
            ),
        )
        bootstrap_env.prepend_path("PERL5LIB", automake_data)
        native_autom4te = "/data/service/hnp/bin/autom4te"
        if not os.path.isfile(native_autom4te):
            native_autom4te = shutil.which("autom4te")
        if not native_autom4te:
            raise ConanInvalidConfiguration(
                "native autom4te is required to run aclocal"
            )
        bootstrap_env.define("AUTOM4TE", native_autom4te)
        no_op = shutil.which("true")
        if not no_op:
            raise ConanInvalidConfiguration(
                "native true command is required to bootstrap Libtool"
            )
        bootstrap_env.define("LIBTOOLIZE", no_op)
        bootstrap_env.vars(self).save_script("libkylin_chkname_bootstrap")
        dependency_env.vars(self).save_script("libkylin_chkname_gettext")
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # libtoolize in the registry package embeds OHOS system-tool paths.
        # Seed its unmodified generated inputs directly, which also avoids
        # executing that wrapper on non-OHOS verification hosts.
        libtool = self.dependencies.build["libtool"]
        copy(
            self,
            "*.m4",
            src=os.path.join(libtool.package_folder, "share", "aclocal"),
            dst=os.path.join(self.source_folder, "m4"),
        )
        copy(
            self,
            "ltmain.sh",
            src=os.path.join(
                libtool.package_folder, "share", "libtool", "build-aux"
            ),
            dst=os.path.join(self.source_folder, "build-aux"),
        )
        # The release archive intentionally contains configure.ac/Makefile.am,
        # not generated build files.  Host Autotools/gettext generate them;
        # the target compiler itself still comes exclusively from the profile.
        self.run(
            "autoreconf --force --install",
            cwd=self.source_folder,
            env=["conanbuild", "libkylin_chkname_bootstrap"],
        )
        # E007: Automake's generated config.guess does not recognize the
        # HarmonyOS uname.  Patch native platform detection before configure;
        # config.sub from automake/1.18 already accepts linux-ohos.
        _patch_generated_config_guess(self)
        # E011: Autoconf embeds config.status temporary-directory creation in
        # configure.  HMDFS ownership mapping makes its default umask 077
        # directory unwritable by the active worker, so relax it before
        # configure emits and runs config.status.
        if str(self.settings.os) == "OHOS":
            _patch_generated_configure_umask(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Automake supplies a no-op check target.  Run it to retain direct
        # evidence that zero upstream tests were registered; the complete
        # source-tree audit is declared in test_package/MANIFEST.yml.
        autotools.make(target="check")

    def package(self):
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["kylin_chkname"]
        # gettext/0.22.5.1 has package_type=application, so its aggregate
        # CMake target intentionally contributes no library names.  Its
        # transitive libdir above supplies libintl.so; name only that direct
        # ABI dependency here so static consumers resolve the same symbols.
        self.cpp_info.system_libs = ["intl"]
        self.cpp_info.set_property("cmake_file_name", "libkylin-chkname")
        self.cpp_info.set_property(
            "cmake_target_name", "libkylin-chkname::libkylin-chkname"
        )
        self.runenv_info.define_path(
            "KYLIN_CHKNAME_RESERVED_NAMES",
            os.path.join(
                self.package_folder, "share", "kylin-chkname", "reserved-names"
            ),
        )
        self.runenv_info.define_path(
            "KYLIN_CHKNAME_LOCALEDIR",
            os.path.join(self.package_folder, "share", "locale"),
        )
