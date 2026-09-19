#!/usr/bin/env python3
"""Conan recipe for libicns 0.9.0 (Apple icon format library).

Upstream: https://github.com/kornelski/libicns (kornelski's maintained
release line; 0.9.0 is the version declared by configure.ac on master).
The GitHub archive ships *no* generated Autotools files, so build()
bootstraps them (aclocal → autoconf → autoheader → libtoolize →
automake) before configure.

r02 fix (CI L1 "aclocal: inaccessible or not found", exit 127):
  - The OHOS CI build sandbox has no system automake/aclocal/libtool,
    so declare them as tool_requires (automake/1.18, libtool/2.5.4,
    autoconf/2.72, m4/1.4.19 — all verified consumable from ohpcd
    registry via `conan download --only-recipe`, RC=0).
  - Pass an explicit --build/--host=aarch64-unknown-linux-ohos triplet
    so configure never probes config.guess (uname -s = HarmonyOS has no
    match even in modern config.guess). automake/1.18's config.sub
    (2024-05-27) already accepts linux-ohos* / ohos*, so no config.sub
    patch is needed. Same approach as argp-standalone/1.4.1.
  - Keep the HMDFS umask 077 → 022 rewrite on the bootstrapped
    configure (E011 family: umask 077 mktemp dirs are unwritable on
    HMDFS), applied AFTER bootstrap since bootstrap regenerates it.

Other OHOS adaptations:
  - Every configure/make/check/install command runs with
    SHELL/CONFIG_SHELL=/system/bin/sh (avoids the HNP Bash getcwd
    failure inside HMDFS Conan build folders) and MKDIR_P bound to
    /system/bin/mkdir -p. TMPDIR is bound to a build-local .tmp dir.
  - configure's conftest programs link against the Conan-cached
    libpng16.so — LD_LIBRARY_PATH is prepended with every dependency
    libdir so the OHOS loader finds it.

The installed libicns.pc is rewritten to package-relative paths and the
obsolete non-relocatable libicns.la is deleted.
"""

import os
import re
import shlex
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibicnsConan(ConanFile):
    name = "libicns"
    version = "0.9.0"
    description = "Library for manipulating Apple ICNS icon files"
    license = "LGPL-2.1-or-later"  # library; bundled icnsutils tools are GPL-2.0
    homepage = "https://github.com/kornelski/libicns"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58", transitive_headers=True)

    def build_requirements(self):
        # r02: OHOS CI sandbox lacks system autotools; pull them in as
        # tool_requires (resolved with the *build* profile, so conan
        # create must pass both -pr:h and -pr:b — CI does).
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("m4/1.4.19")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libicns supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._autotools_toolchain().generate()
        # OHOS loader has no default search path for conan-cached shared libs;
        # configure's conftest runs compiled programs and would fail with
        # "Error loading shared library libpng16.so.16" otherwise.
        environment = Environment()
        for dependency in self.dependencies.values():
            for libdir in dependency.cpp_info.libdirs:
                environment.prepend_path("LD_LIBRARY_PATH", libdir)
        environment.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._bootstrap_autotools()
                self._fix_configure_umask()
                self._configure_ohos()
                self._run_ohos("make -j1")
                self._run_ohos("make -j1 check")
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])
                autotools.make(target="check", args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                Autotools(self).install(args=["-j1"])
        self._relocate_metadata()
        self._copy_licenses()

    def package_info(self):
        self.cpp_info.libs = ["icns"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["libpng::libpng"]
        self.cpp_info.set_property("cmake_file_name", "libicns")
        self.cpp_info.set_property("cmake_target_name", "libicns::libicns")
        self.cpp_info.set_property("pkg_config_name", "libicns")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        return environment

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # r02: explicit native triplet — configure never probes
            # config.guess (HarmonyOS uname has no match) and automake
            # 1.18's config.sub already accepts linux-ohos.
            toolchain.configure_args.append("--build=aarch64-unknown-linux-ohos")
            toolchain.configure_args.append("--host=aarch64-unknown-linux-ohos")
        return toolchain

    def _bootstrap_autotools(self):
        """0.9.0 GitHub archive ships no generated Autotools files.

        The OHOS CI sandbox has no system autotools, and some devices keep
        a shadowing system automake under $HOME/usr/local/bin. The
        autoconf/automake/libtool/m4 tool_requires export their own
        *tool env vars (ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER/AUTOM4TE/
        LIBTOOLIZE/M4) into the conanbuild env, so reference those vars
        (falling back to the plain command name) — this resolves to the
        Conan packages regardless of ambient PATH order.

        PERL5LIB/interpreter hazard: the automake payloads
        (.aclocal-real/.automake-real) carry a device-perl shebang
        (e.g. /data/service/hnp/bin/perl, v5.42.0) while the autoconf
        payload (.autom4te-real etc.) and the perl tool_require use the
        conan perl (5.42.2 aarch64-linux-thread-multi). Running the
        device perl with the conan perl's thread-multi XS dirs on
        PERL5LIB fails with "Perl_my_cxt_init: symbol not found";
        dropping the conan perl lib dirs breaks autom4te ("can't locate
        strict.pm"). Fix (verified): invoke the aclocal/automake
        payloads DIRECTLY under $PERL (the conan perl) and keep the
        existing PERL5LIB (conan perl lib dirs) while APPENDING the
        automake/autoconf share dirs.
        """
        source = self.source_folder
        env_prefix = (
            '_am_root="$(cd "$(dirname "$(dirname "${ACLOCAL:-.}")")" 2>/dev/null && pwd)"; '
            '_ac_root="$(cd "$(dirname "$(dirname "${AUTOCONF:-.}")")" 2>/dev/null && pwd)"; '
            'export PERL5LIB="${PERL5LIB:+$PERL5LIB:}'
            '${_am_root:+$_am_root/share/automake-1.18}'
            '${_am_root:+:$_am_root/share/aclocal-1.18}'
            '${_ac_root:+:$_ac_root/share/autoconf}"; '
        )

        # aclocal: bypass the device-perl shebang by running the payload
        # with the conan perl ($PERL) and the wrapper's acdir flags.
        self.run(
            env_prefix
            + '"${PERL:-perl}" "$_am_root/bin/.aclocal-real"'
            ' --automake-acdir="$_am_root/share/aclocal-1.18"'
            ' --system-acdir="$_am_root/share/aclocal" --force',
            cwd=source,
            env="conanbuild",
        )
        self.run(
            env_prefix + "${AUTOCONF:-autoconf} -o configure configure.ac",
            cwd=source,
            env="conanbuild",
        )
        configure = Path(source, "configure")
        if not configure.is_file():
            raise ConanException("autoconf failed to generate configure")
        self.run(
            env_prefix + "${AUTOHEADER:-autoheader}",
            cwd=source,
            env="conanbuild",
        )
        config_h_in = Path(source, "config.h.in")
        if not config_h_in.is_file():
            config_h_in.write_text("", encoding="utf-8")
        # libtoolize before automake: automake needs ltmain.sh
        if not Path(source, "ltmain.sh").exists():
            self.run(
                env_prefix + "${LIBTOOLIZE:-libtoolize} --copy --force",
                cwd=source,
                env="conanbuild",
                ignore_errors=True,
            )
        if not Path(source, "ltmain.sh").exists():
            _lt_pkg = None
            try:
                _lt_pkg = self.dependencies["libtool"].package_folder
            except Exception:
                pass
            if _lt_pkg:
                _cand = Path(_lt_pkg, "share", "libtool", "build-aux", "ltmain.sh")
                if _cand.is_file():
                    import shutil
                    shutil.copy(_cand, Path(source, "ltmain.sh"))
        # automake: same direct-payload invocation as aclocal.
        self.run(
            env_prefix
            + '"${PERL:-perl}" "$_am_root/bin/.automake-real"'
            ' --libdir="$_am_root/share/automake-1.18"'
            ' --add-missing --copy --force-missing',
            cwd=source,
            env="conanbuild",
        )

    def _fix_configure_umask(self):
        """HMDFS: bootstrapped configure uses `umask 077 && mktemp -d`
        which creates 0700 dirs the effective user cannot write into
        (E011 family). Rewrite every `umask 077` to `umask 022`.

        The number of sites depends on the autoconf generation (2 with
        the device autoconf, 3 with the conan autoconf tool_require), so
        no fixed-count contract — replace all occurrences, fail only if
        the file is missing."""
        path = Path(self.source_folder, "configure")
        if not path.is_file():
            raise ConanException("configure script is missing for umask fix")
        content = path.read_text(encoding="utf-8")
        needle = "umask 077"
        count = content.count(needle)
        if count:
            path.write_text(
                content.replace(needle, "umask 022"), encoding="utf-8"
            )
        self.output.info(f"configure: umask 077 -> 022 ({count} sites)")

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        configure = Path(self.source_folder, "configure")
        if not configure.is_file():
            raise ConanException(f"configure script is missing: {configure}")
        arguments = " ".join(
            shlex.quote(argument)
            for argument in self._autotools_toolchain().configure_args
        )
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "libicns.pc")
        if not pc_path.is_file():
            raise ConanException("installed libicns.pc is missing")
        pc_content = pc_path.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("libicns.pc has no unique prefix field")
        pc_path.write_text(pc_content, encoding="utf-8")

        la_path = Path(self.package_folder, "lib", "libicns.la")
        if la_path.is_file():
            la_path.unlink()

    def _copy_licenses(self):
        for name in ("COPYING.LGPL-2.1", "COPYING"):
            source = Path(self.source_folder, name)
            if source.is_file():
                copy(
                    self,
                    name,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                    keep_path=False,
                )
