#!/usr/bin/env python3
"""Conan recipe for pioneers 15.6 — Settlers of Catan style board game.

pioneers (GNU/GPL, C, autotools + libtool) ships a GTK3 graphical client
(pioneers), a graphical map editor (pioneers-editor), a graphical server
(pioneers-server-gtk), a console game server (pioneers-server-console), a
metaserver directory daemon (pioneers-metaserver) and a headless computer
player / test bot (pioneersai).  This is an application package (R38):
only the six executables are published, and the headless trio is exercised
by the test package.

OHOS/arm64 adaptation notes (see notes.md):
- configure is shipped pre-generated in the upstream tarball, so build-time
  text edits inside build() reproduce the same environment the released
  configure expects.  The HarmonyOS target cannot run intltool/perl
  XML::Parser tooling, so --disable-nls plus neutralisation of the
  unconditional IT_PROG_INTLTOOL probes inside the shipped configure is used
  (same technique as libgsf/avahi-ui-tools/gnumeric).
- HMFS refuses the `(umask 077 && mktemp -d)` AS_TMPDIR temp dir used by
  autoconf (E011/E112/E118); the umask is stripped like the proven recipe.
- GUI programs parse --version/--help through GOption before gtk_init, so
  they exit cleanly on a display-less host; real play needs a display.
- glib ships a proxy libintl whose public libintl.h maps gettext() to
  g_libintl_*; consumers using <glib/gi18n.h> must link the glib-provided
  libintl.so (avahi-ui-tools precedent).  It is injected via configure's
  $LIBS (automake substitutes @LIBS@ into the generated Makefile).
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.gnu import PkgConfigDeps


class PioneersConan(ConanFile):
    name = "pioneers"
    version = "15.6"
    description = ("Settlers of Catan style board game: GTK3 client, "
                   "map editor, console/GTK servers, metaserver and AI player")
    license = "GPL-2.0-or-later"
    homepage = "https://pio.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # bin_PROGRAMS aggregated into the top-level Makefile by the included
    # *-Makefile.am fragments (client/gtk, client/ai, editor/gtk,
    # server, server/gtk, metaserver).
    _PROGRAMS = (
        "pioneers",
        "pioneersai",
        "pioneers-editor",
        "pioneers-server-console",
        "pioneers-server-gtk",
        "pioneers-metaserver",
    )

    # Console (headless) programs whose --version runs without a display.
    _HEADLESS = ("pioneers-server-console", "pioneers-metaserver", "pioneersai")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gtk/3.24.43's published OHOS binaries pin glib/2.84.0.1 (the gtk
        # recipe forces its dependency stack to shared=True); declaring the
        # same glib revision keeps the whole GTK closure on prebuilt binaries
        # (R36 — forcing glib/2.88.3 would conflict/recompile GTK from
        # source, ~hours, so glib/2.88.3 is intentionally not used here).
        self.requires(
            "gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires(
            "glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        PkgConfigDeps(self).generate()
        env = Environment()
        # Compiler + flags come from the Conan toolchain configuration, never
        # from bare ${CC}/${CFLAGS} shell variables (R33).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        for variable, key in (("CC", "c"), ("CXX", "cpp")):
            compiler = compilers.get(key)
            if not compiler:
                raise ConanException(
                    f"{variable} missing from tools.build:compiler_executables")
            env.define(variable, compiler)
        env.define("CFLAGS", "-fPIC -O2")
        env.define("CXXFLAGS", "-fPIC -O2")
        # HMFS bash starts with a failing getcwd; run configure/make through
        # the platform shell (avahi-ui-tools precedent).
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        # PkgConfigDeps writes glib-2.0/gio-2.0/gtk+-3.0.pc etc. here.
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # glib's proxy libintl provides the g_libintl_* symbols that the
        # <glib/gi18n.h> + libintl.h header chain maps gettext() to; it is
        # not reachable through glib-2.0.pc so it is appended to $LIBS
        # (avahi-ui-tools precedent).  @LIBS@ is baked into Makefile at
        # configure time, hence the injection through configure's $LIBS.
        glib = self.dependencies["glib"]
        intl_so = os.path.join(glib.package_folder, "lib", "libintl.so")
        if not os.path.isfile(intl_so):
            raise ConanException(
                f"glib package lacks proxy libintl: {intl_so}")
        # $LIBS is expanded by autoconf into the link command and baked into
        # Makefile as @LIBS@; the raw absolute path must not carry quotes
        # (quoted value makes configure treat the whole string as one path).
        env.define("LIBS", intl_so)
        env.vars(self).save_script("pioneers_env")

    def _configure_args(self):
        args = [
            # Explicit native triplet: the shipped config.guess (2018) cannot
            # guess HarmonyOS and the whole toolchain is native OHOS/arm64
            # (avahi-ui-tools / libgsf precedent).
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            # Optional runtime dependencies are intentionally disabled to keep
            # the dependency chain minimal (configure probes are best-effort
            # for these, but disable keeps the build deterministic).
            "--without-avahi",
            "--without-notify",
            "--without-sound",
            # Online help needs yelp-tools/itstool (not available for OHOS).
            "--disable-help",
            # Translations are built with intltool + gettext catalogs which
            # cannot run on OHOS; config.h then leaves ENABLE_NLS undefined
            # and common/gettext.c compiles to no-ops.
            "--disable-nls",
        ]
        return args

    def _patch_generated_configure(self, configure):
        """Apply the OHOS build-time edits to the shipped generated configure.

        The released tarball carries a generated configure; patching it in
        build() keeps every fix reproducible from the immutable upstream
        tarball without regenerating through autotools (proven approach used
        by libgsf/avahi-ui-tools for the same HMFS/NLS constraints).
        """
        if not os.path.isfile(configure):
            raise ConanException(f"configure script missing: {configure}")
        text = load(self, configure)
        original = text

        def repl(old, new, required=True, count_all=False):
            nonlocal text
            n = text.count(old) if count_all else (1 if old in text else 0)
            if n == 0:
                if required:
                    raise ConanException(
                        f"configure no longer contains expected snippet: {old[:60]}")
                return
            if count_all:
                text = text.replace(old, new)
            else:
                text = text.replace(old, new, 1)

        # 1) IT_PROG_INTLTOOL: freeze the version probe (intltool is absent
        #    and NLS is disabled).
        repl(
            'INTLTOOL_APPLIED_VERSION=`intltool-update --version | head -1 '
            '| cut -d" " -f3`',
            'INTLTOOL_APPLIED_VERSION=0.51.0  # OHOS: no intltool (nls disabled)')
        # 2) intltool scripts missing -> hard error: neutralised.
        repl(
            'if test -z "$INTLTOOL_UPDATE" -o -z "$INTLTOOL_MERGE" '
            '-o -z "$INTLTOOL_EXTRACT"; then',
            'if false; then  # OHOS: nls disabled, no intltool')
        # 3) GNU gettext tools presence + version hard errors: neutralised.
        repl(
            'if test -z "$XGETTEXT" -o -z "$MSGMERGE" -o -z "$MSGFMT"; then',
            'if false; then  # OHOS: nls disabled (no gettext)')
        repl(
            'if test -z "$xgversion" -o -z "$mmversion" -o -z "$mfversion"; then',
            'if false; then  # OHOS: nls disabled (no gettext ver)')
        # 4) perl requirement (XML::Parser XS cannot load on HMDFS): skip.
        repl(
            'if test -z "$INTLTOOL_PERL"; then',
            'if false; then  # OHOS: no perl needed (nls disabled)')
        repl(
            'if test "x" != "xno-xml"; then',
            'if test "x" = "xno-xml"; then  # OHOS: skip xml-parser check')
        # 5) HMFS AS_TMPDIR workaround: strip `umask 077 && ` so the temp
        #    dir is not created 2700+setgid (E011/E112/E118).
        text, n_mktemp = re.subn(
            r"um(?:ask|ash) 077 && mktemp -d", "mktemp -d", text)
        text, n_mkdir = re.subn(
            r"um(?:ask|ash) 077 && mkdir", "mkdir", text)
        if n_mktemp == 0 and n_mkdir == 0:
            self.output.warning(
                "generated configure has no AS_TMPDIR 'umask 077' pattern")
        if text != original:
            save(self, configure, text)
            self.output.info(
                "patched shipped configure: intltool/gettext checks "
                f"neutralised, umask 077 stripped (mktemp:{n_mktemp}, "
                f"mkdir:{n_mkdir})")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        configure = os.path.join(src, "configure")
        self._patch_generated_configure(configure)
        env = ["conanbuild", "conanrun", "pioneers_env"]
        # Run configure through the platform shell: HarmonyOS refuses to
        # execute scripts via shebang (avahi-ui-tools precedent).
        self.run(
            f"sh configure " + " ".join(self._configure_args()),
            cwd=src, env=env)
        # Build exactly the shipped programs.  This deliberately avoids the
        # po/ (translation catalogs) and intltool-merge data targets, which
        # have no OHOS tooling, and avoids regenerating gresource data.
        self.run(
            "make -j4 " + " ".join(self._PROGRAMS),
            cwd=src, env=env)
        missing = [p for p in self._PROGRAMS
                   if not (os.path.isfile(os.path.join(src, p))
                           or os.path.isfile(os.path.join(src, ".libs", p)))]
        if missing:
            raise ConanException(
                "built programs not found: " + ", ".join(missing))

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as binary:
                return binary.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_program_binary(self, src, name):
        # libtool may leave a wrapper script at the top level and the real
        # executable in .libs/; pick the ELF (avahi-ui-tools precedent).
        candidates = (
            os.path.join(src, ".libs", name),
            os.path.join(src, name),
        )
        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                return candidate
        raise ConanException(
            f"built program {name} not found under {src} "
            "(looked in .libs/ and top level)")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        src = self.source_folder
        for name in self._PROGRAMS:
            binary = self._find_program_binary(src, name)
            shutil.copy2(binary, os.path.join(bin_dir, name))
        copy(self, "COPYING", src,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "AUTHORS", src,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Application package: expose the bin directory for tool discovery
        # (R38 — commands.json is declared at the software level).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "pioneers")
        self.cpp_info.set_property("cmake_target_name", "pioneers::pioneers")
