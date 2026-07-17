#!/usr/bin/env python3
"""Conan recipe for ncurses 6.5 — OHOS static build."""

import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.5"
    description = "The ncurses (new curses) library"
    license = "X11"
    homepage = "https://www.gnu.org/software/ncurses"
    url = "https://www.gnu.org/software/ncurses"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def layout(self):
        # ncurses' config.status is fragile in out-of-source builds on OHOS/HMDFS:
        # it creates subdirectory Makefiles through temporary sed fragments and may
        # fail before the build tree mirrors the source tree. Build in-source so the
        # generated files land in the upstream directories that already exist.
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-shared")
        tc.configure_args.append("--without-debug")
        tc.configure_args.append("--without-ada")
        tc.configure_args.append("--without-manpages")
        tc.configure_args.append("--without-cxx-binding")
        tc.configure_args.append("--enable-widec")
        tc.configure_args.append("--enable-overwrite")
        # Generate config.status first, then patch its temporary-directory logic
        # before it creates Makefiles. This mirrors the proven HMDFS pattern used
        # by other autotools recipes in this repository.
        tc.configure_args.append("--no-create")
        tc.generate()

    def build(self):
        config_shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not config_shell:
            raise RuntimeError("bash is required to build ncurses on OHOS")
        tmpdir = os.path.join(self.build_folder, "_tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o700)
        os.environ["CONFIG_SHELL"] = config_shell
        os.environ["SHELL"] = config_shell
        os.environ["TMPDIR"] = tmpdir

        replace_in_file(
            self,
            os.path.join(self.source_folder, "config.guess"),
            """    *:Minix:*:*)
	GUESS=$UNAME_MACHINE-unknown-minix
	;;""",
            """    *:Minix:*:*)
	GUESS=$UNAME_MACHINE-unknown-minix
	;;
    *:HarmonyOS:*:*)
	case "$UNAME_MACHINE" in
	    aarch64|arm64)
		MACHINE=aarch64
		;;
	    armv7*|armv8*)
		MACHINE=arm
		;;
	    x86_64|amd64)
		MACHINE=x86_64
		;;
	    i?86)
		MACHINE=i686
		;;
	    *)
		MACHINE="$UNAME_MACHINE"
		;;
	esac
	GUESS=${MACHINE}-unknown-linux-ohos
	;;""",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "config.sub"),
            "| fiwix* | mlibc* | cos* | mbr* | ironclad* )",
            "| fiwix* | mlibc* | cos* | mbr* | ironclad* | ohos* )",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "config.sub"),
            "| linux-relibc*- | linux-uclibc*- )",
            "| linux-relibc*- | linux-uclibc*- | linux-ohos*- )",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "#! /bin/sh",
            f"#! {config_shell}\nTMPDIR='{tmpdir}'\nexport TMPDIR",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
            strict=False,
        )
        # With --no-create ncurses would still try make preinstall even though
        # Makefile has not been generated yet. Guard that ncurses-specific tail;
        # we run preinstall manually after the patched config.status succeeds.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            'fi\n${MAKE:-make} preinstall',
            'fi\nif test "$no_create" != yes; then\n  ${MAKE:-make} preinstall\nfi',
            strict=False,
        )

        autotools = Autotools(self)
        autotools.configure()
        self._patch_config_status_tmp(tmpdir)
        self.run(f'"{config_shell}" ./config.status', cwd=self.build_folder, env=["conanbuild"], ignore_errors=False)
        self._patch_generated_makefiles()
        self.run("make -j1 preinstall", cwd=self.build_folder, env=["conanbuild"], ignore_errors=False)
        autotools.make(args=["-j1"])
        self.run("make check -j1", cwd=self.build_folder, env=["conanbuild"], ignore_errors=False)

    def _patch_config_status_tmp(self, tmpdir):
        config_status = os.path.join(self.build_folder, "config.status")
        if not os.path.exists(config_status):
            config_status = os.path.join(self.source_folder, "config.status")
        if not os.path.exists(config_status):
            self.output.warning("config.status not found; skipping ncurses tmp patch")
            return

        fixed_tmp = os.path.join(tmpdir, "ncurses-config-status")
        os.makedirs(fixed_tmp, exist_ok=True)
        os.chmod(fixed_tmp, 0o700)
        with open(config_status, "r", encoding="utf-8") as file:
            content = file.read()

        content = content.replace("umask 077", "umask 022")
        # OHOS ships toybox expr, whose alternation handling corrupts the
        # autoconf config.status directory extraction used for sub-Makefiles.
        # When this happens, generated Makefiles point top_srcdir at mojibake
        # paths such as ".../����kk./Caps".  Force the existing sed fallback
        # for ac_dir extraction instead of executing the broken expr branch.
        content = content.replace(
            'ac_dir=`$as_expr X"$ac_file" :',
            'ac_dir=`false && $as_expr X"$ac_file" :',
            1,
        )
        for umask in ("077", "000", "022"):
            content = content.replace(
                f'tmp=`(umask {umask} && mktemp -d -q "$TMPDIR/csXXXXXX") 2>/dev/null` &&\n'
                '  test -n "$tmp" && test -d "$tmp"',
                f'tmp="{fixed_tmp}" &&\n'
                '  rm -rf "$tmp" && mkdir -p "$tmp" && chmod u+rwx "$tmp" && test -d "$tmp"',
            )
            content = content.replace(
                f'tmp=$TMPDIR/cs$$-$RANDOM\n  (umask {umask} && mkdir "$tmp")',
                f'tmp="{fixed_tmp}"\n  rm -rf "$tmp" && mkdir -p "$tmp" && chmod u+rwx "$tmp"',
            )

        with open(config_status, "w", encoding="utf-8") as file:
            file.write(content)

    def _patch_generated_makefiles(self):
        # On OHOS/HMDFS, ncurses' config.status can leak its temporary sed
        # directory into generated Makefiles as srcdir/top_srcdir.  The temp
        # directory name may contain non-portable bytes, so make later looks for
        # include/Caps under a garbage path.  We build in-source, therefore all
        # generated Makefiles can safely use relative source directories.
        top_makefiles = {"Makefile": "."}
        sub_makefiles = {
            "include/Makefile",
            "ncurses/Makefile",
            "progs/Makefile",
            "panel/Makefile",
            "menu/Makefile",
            "form/Makefile",
            "misc/Makefile",
        }
        makefiles = {**top_makefiles, **{rel: ".." for rel in sub_makefiles}}
        pattern = re.compile(r"^(\s*)(VPATH|top_srcdir|srcdir)(\s*=).*$")

        for rel_path, top_srcdir in makefiles.items():
            path = os.path.join(self.build_folder, *rel_path.split("/"))
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as file:
                lines = file.readlines()

            patched = []
            changed = False
            for line in lines:
                match = pattern.match(line.rstrip("\n"))
                if match:
                    value = top_srcdir if match.group(2) == "top_srcdir" else "."
                    # Avoid whitespace after '=': misc/install exports these
                    # make variables as shell assignments (top_srcdir=${...}).
                    # A leading value space becomes `top_srcdir= ..`, causing
                    # the shell to execute `..` as a command.
                    line = f"{match.group(1)}{match.group(2)}={value}\n"
                    changed = True
                patched.append(line)

            if changed:
                with open(path, "w", encoding="utf-8", errors="surrogateescape") as file:
                    file.writelines(patched)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ncursesw", "tinfow", "panelw", "menuw", "formw"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "ncursesw")
