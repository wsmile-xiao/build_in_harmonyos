#!/usr/bin/env python3
"""Conan recipe for OpenSLP 2.0.0 -- SLP (RFC 2608/2614) implementation.

Builds the static libslp library, the slpd service-agent daemon and the
slptool CLI for HarmonyOS PC (aarch64-linux-ohos).

The 2.0.0 release tarball ships a 2012-era configure whose generated
config.status is not POSIX-portable (it falls back to a ksh `print` builtin
that the OHOS /bin/sh lacks), and its make step regenerates the attribute
parser from common/slp_attr.{l,y} (flex/bison).  Following the repo pattern
for C autotools packages, this recipe therefore brings Autotools + flex/bison
as tool_requires and regenerates configure/Makefile.in from configure.ac with
modern Autotools, then patches config.sub for the `linux-ohos` OS.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OpenSlpConan(ConanFile):
    name = "openslp"
    version = "2.0.0"
    description = "OpenSLP: open-source implementation of the Service Location Protocol (RFC 2608/2614)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/openslp-org/openslp"
    url = "https://downloads.sourceforge.net/project/openslp/2.0.0/2.0.0%20Release/openslp-2.0.0.tar.gz"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("OpenSLP supports POSIX platforms only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # Regenerate configure/Makefile.in from configure.ac (the shipped
        # 2012 configure is not POSIX-safe on OHOS) and build the parser.
        self.tool_requires("m4/1.4.19")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def generate(self):
        VirtualBuildEnv(self).generate()
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--disable-dependency-tracking",
                "--disable-shared",
                "--enable-static",
            ]
        )
        if self.settings.os == "OHOS" and not cross_building(self):
            # Native OHOS workers cannot always execute config.guess; supplying
            # the canonical tuple avoids that probe.
            toolchain.configure_args.extend(
                ["--build=aarch64-linux-ohos", "--host=aarch64-linux-ohos"]
            )
        toolchain.generate()

    def _patch_config_sub(self):
        """Teach config.sub the `linux-ohos` OS (both 2012 and modern forms).

        Modern GNU config.sub (automake 1.18) already accepts the aarch64 CPU
        but not the OHOS OS name.  Two small edits make the tuple valid:
          - list `ohos` among valid OSes,
          - accept the `linux-ohos` kernel-OS combination.
        OpenSLP's source may keep the 2012 config.sub if autoreconf is skipped
        on some worker, so both spellings are handled.
        """
        path = os.path.join(self.source_folder, "config.sub")
        contents = load(self, path)
        if "linux-ohos" in contents:
            return  # already OHOS-aware

        old_style = (
            (
                "nto-qnx* | linux-gnu* | linux-android*",
                "nto-qnx* | linux-gnu* | linux-ohos* | linux-android*",
            ),
            (
                "| -mingw32* | -linux-gnu* | -linux-android* \\",
                "| -mingw32* | -linux-gnu* | -linux-ohos* | -linux-android* \\",
            ),
            (
                "\t-linux*)\n\t\tos=`echo $os | sed -e 's|linux|linux-gnu|'`",
                "\t-linux-ohos*)\n\t\t;;\n\t-linux*)\n\t\tos=`echo $os | sed -e 's|linux|linux-gnu|'`",
            ),
        )
        new_style = (
            ("| fiwix* )", "| fiwix* | ohos* )"),
            (
                "| linux-musl* | linux-relibc* | linux-uclibc* )",
                "| linux-musl* | linux-ohos* | linux-relibc* | linux-uclibc* )",
            ),
        )

        applied = 0
        candidates = (new_style, old_style)
        for style in candidates:
            matched = all(original in contents for original, _ in style)
            if not matched:
                continue
            for original, replacement in style:
                if replacement in contents:
                    continue
                replace_in_file(self, path, original, replacement)
            applied = len(style)
            break
        if applied == 0:
            raise ConanInvalidConfiguration(
                f"Cannot add OHOS support to unexpected config.sub: {path}"
            )

    def _automake_share(self):
        """Path to the tool_requires automake pure-perl modules directory."""
        try:
            pkg = self.dependencies.build["automake"]
        except KeyError:
            return ""
        share = os.path.join(pkg.package_folder, "share")
        if not os.path.isdir(share):
            return ""
        for name in sorted(os.listdir(share)):
            if name.startswith("automake-"):
                return os.path.join(share, name)
        return ""

    def build(self):
        apply_conandata_patches(self)

        # Regenerate configure/Makefile.in from configure.ac.  Conan's own
        # perl/5.42.2 package cannot load its XS Cwd module on HMDFS
        # (Permission denied), so run the bootstrap tools with the native OHOS
        # perl plus the automake package's pure-perl modules (ding-libs
        # pattern).  libtoolize runs first so aclocal finds the Libtool M4
        # macros.
        share = self._automake_share()
        perl = os.environ.get("PERL") or "/data/service/hnp/bin/perl"
        bootstrap_env = f'PERL="{perl}" PERL5LIB="{share}" ' if share else ""
        src = self.source_folder
        self.run(f"{bootstrap_env}libtoolize --copy --force", cwd=src, env="conanbuild")
        self.run(f"{bootstrap_env}aclocal --force -I m4", cwd=src, env="conanbuild")
        self.run(f"{bootstrap_env}autoconf --force", cwd=src, env="conanbuild")
        self.run(f"{bootstrap_env}automake --add-missing --copy", cwd=src, env="conanbuild")

        self._patch_config_sub()

        if self.settings.os == "OHOS":
            # musl provides fnmatch; skip the configure runtime probe that
            # cannot run under cross compilation.
            os.environ["ac_cv_func_fnmatch_works"] = "yes"
            # HMDFS: after Conan builds the tree, getcwd() may fail; publishing
            # the logical $PWD lets the configure re-exec resolve the directory.
            os.environ["PWD"] = self.build_folder

        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply():
            autotools.configure()
            autotools.make(
                args=[
                    "-j1",
                    "ACLOCAL=true",
                    "AUTOMAKE=true",
                    "AUTOCONF=true",
                    "AUTOHEADER=true",
                ]
            )

    def package(self):
        # Stage the four useful artifacts directly.  `make install` cannot be
        # used: etc/Makefile.am's install-data-hook runs `mkdir -p
        # $(localstatedir)/log` without $(DESTDIR), creating a real /var/log on
        # the read-only OHOS root during packaging.  The etc/ and doc/ outputs
        # are not needed by consumers anyway.
        import shutil
        pkg = self.package_folder
        bld = self.build_folder
        src = self.source_folder
        lib = os.path.join(pkg, "lib")
        inc = os.path.join(pkg, "include")
        bind = os.path.join(pkg, "bin")
        lic = os.path.join(pkg, "licenses")
        for d in (lib, inc, bind, lic):
            os.makedirs(d, exist_ok=True)

        def _locate(candidates):
            for c in candidates:
                if os.path.exists(c):
                    return c
            return None

        libslp_a = _locate(
            [
                os.path.join(bld, "libslp", ".libs", "libslp.a"),
                os.path.join(bld, "libslp", "libslp.a"),
            ]
        )
        if libslp_a is None:
            raise ConanInvalidConfiguration("libslp.a artifact not found")
        shutil.copy2(libslp_a, os.path.join(lib, "libslp.a"))
        shutil.copy2(os.path.join(src, "libslp", "slp.h"), os.path.join(inc, "slp.h"))
        for exe in ("slpd", "slptool"):
            artifact = _locate(
                [
                    os.path.join(bld, exe, exe),
                    os.path.join(bld, exe, ".libs", exe),
                ]
            )
            if artifact is None:
                raise ConanInvalidConfiguration(f"{exe} artifact not found")
            target = os.path.join(bind, exe)
            shutil.copy2(artifact, target)
            os.chmod(target, 0o755)
        shutil.copy2(os.path.join(src, "COPYING"), os.path.join(lic, "COPYING"))

    def package_info(self):
        self.cpp_info.libs = ["slp"]
        self.cpp_info.system_libs = ["pthread", "m"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "openslp")
        self.cpp_info.set_property("cmake_target_name", "openslp::openslp")
