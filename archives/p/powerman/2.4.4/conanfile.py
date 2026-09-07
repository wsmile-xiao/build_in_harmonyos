#!/usr/bin/env python3
# -*- conanfile -*-
"""Conan recipe: powerman 2.4.4 — LLNL HPC cluster power management (C client/server).

OHOS adaptation notes (see also notes.md):
  * The GitHub release tarball ships NO pre-generated configure and only
    .l/.y parser sources (parse_lex.l / parse_tab.y), so build()
    bootstraps with libtoolize + autoreconf -fi (upstream autogen.sh
    equivalent).  The CI sandbox has the autoconf suite under
    /data/service/hnp/bin but lacks automake/aclocal/libtoolize/flex/bison,
    hence the four tool_requires (captagent 6.4.4 / acpica-unix precedent);
    they are resolved with the *build* profile, so both -pr:h and -pr:b
    must be passed to conan create.
  * The config.guess/config.sub that autoreconf installs into config/
    (AC_CONFIG_AUX_DIR([config]) — note the subdirectory, unlike posh)
    come from the conan automake/1.18 package — pristine GNU versions.
    On this platform they need the E007 HarmonyOS support set + E011
    umask relaxations, applied in build() right after autoreconf (both
    files are *generated* here, absent from the tarball, so they cannot
    ship as regular patches).
  * CONFIG_SHELL must be an absolute bash path: with a bare "bash" the
    generated libtool wrapper scripts for check programs get a
    "#! bash" shebang and the kernel does not PATH-search interpreters
    ("bad interpreter").  Not needed for the packaged binaries
    themselves (plain ELFs), kept for correctness/future tests.
  * Optional device daemons are disabled with upstream-official switches
    (--without-httppower/redfishpower/snmppower): they drag in
    libcurl/jansson/net-snmp, none of which the core
    powermand/powerman/plmpower/libpowerman needs.
  * E074: parallel make hits the HMDFS jobserver fifo EPERM -> -j1.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# E007: HarmonyOS uname branch for config.guess (same change set as the
# E007 knowledge entry / posh recipe; inserted before *:NetBSD:*:*).
_HARMONYOS_GUESS_BLOCK = """    *:HarmonyOS:*:*)
\tcase "$UNAME_MACHINE" in
\t    aarch64|arm64) MACHINE=aarch64 ;;
\t    armv7*|armv8*) MACHINE=arm ;;
\t    x86_64|amd64)  MACHINE=x86_64 ;;
\t    i?86)         MACHINE=i686 ;;
\t    *)            MACHINE="$UNAME_MACHINE" ;;
\tesac
\tGUESS=${MACHINE}-unknown-linux-ohos
\t;;

"""


class PowermanConan(ConanFile):
    name = "powerman"
    version = "2.4.4"
    description = "PowerMan — LLNL remote power management for HPC clusters: powermand daemon, powerman client, plmpower, libpowerman"
    topics = ("power", "hpc", "cluster", "remote-power-management")
    homepage = "https://github.com/chaos/powerman"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "GPL-2.0-or-later"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # tarball ships no configure (autoreconf needed, via tool chain);
        # parse_tab.y/parse_lex.l need bison/flex.  CI sandbox has none of
        # these, so all four are tool_requires (captagent precedent).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos"):
            raise ConanException("Only Linux/OHOS-family supported")

    def generate(self):
        # R33: compiler/flags come from the Conan toolchain
        # (AutotoolsToolchain reads the profile conf), never from bare
        # CC/CFLAGS shell variables.
        tc = AutotoolsToolchain(self)
        # Upstream-official switches: optional device daemons off.
        # httppower -> libcurl; redfishpower -> libcurl+jansson;
        # snmppower -> net-snmp.  None are needed by the core
        # powermand/powerman/plmpower/libpowerman.
        tc.configure_args.extend([
            "--without-httppower",
            "--without-redfishpower",
            "--without-snmppower",
        ])
        tc.generate()
        AutotoolsDeps(self).generate()
        # Upstream builds never define NDEBUG: powerman's code style uses
        # assert() as the sole consumer of many locals (TcpDev *tcp etc.),
        # so the conan Release default -DNDEBUG turns them into
        # -Wunused-variable/-Wunused-but-set-variable errors under -Werror.
        # Strip it to keep upstream build semantics (asserts stay active).
        toolchain_sh = None
        for cand in (os.path.join(self.generators_folder,
                                  "conanautotoolstoolchain.sh"),
                     os.path.join(self.generators_folder, "conan",
                                  "conanautotoolstoolchain.sh")):
            if os.path.isfile(cand):
                toolchain_sh = cand
                break
        if toolchain_sh is None:
            raise ConanException(
                "conanautotoolstoolchain.sh not found under "
                f"{self.generators_folder} — conan generators layout "
                "changed, update the recipe")
        with open(toolchain_sh, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # conan writes a dedicated line: export CPPFLAGS="...${CPPFLAGS:+ }-DNDEBUG"
        kept = [l for l in lines if "-DNDEBUG" not in l]
        if len(kept) != len(lines):
            with open(toolchain_sh, "w", encoding="utf-8") as f:
                f.writelines(kept)
            self.output.info(
                f"stripped -DNDEBUG line from the toolchain ({len(lines) - len(kept)} line(s); "
                "upstream never builds with NDEBUG — assert()-consumed locals "
                "would become -Wunused-variable errors under -Werror)")

    # ---- generated-autotools-scripts portability fixes -----------------

    @staticmethod
    def _relax_umask_077(path, to, what):
        """E011/E114: umask 077 temp dirs are unwritable on HMDFS (UID-mapped
        setgid).  Relax every occurrence, return how many (fail loudly on 0
        so a silent upstream change is caught)."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = f.read()
        n = data.count("umask 077")
        if n:
            data = data.replace("umask 077", "umask %s" % to)
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
        if n == 0:
            raise ConanException(
                f"{what}: no 'umask 077' found in {path} — upstream file "
                "layout changed, update the recipe")
        return n

    def _fix_configure(self, configure):
        # E011/E114: config.status cannot write into 0700 temp dirs on
        # HMDFS ("could not setup config files machinery").
        n = self._relax_umask_077(configure, "022", "configure umask fix")
        self.output.info(
            f"relaxed umask 077 -> 022 in generated configure "
            f"({n} occurrence(s), E011/E114)")

    def _fix_config_guess_sub(self, auxdir):
        """E007 + E011 fixes for the config.guess/config.sub that autoreconf
        just installed (into config/ — AC_CONFIG_AUX_DIR([config])) from the
        conan automake package.  Same change set as the E007 knowledge
        entry / posh recipe: __OHOS__ LIBC probe, *:HarmonyOS:* uname
        branch, ohos-linux triplet and ohos* OS entry in config.sub;
        config.guess umask 077 -> 000 (the value upstream used before the
        2024-07-27 hardening)."""
        guess = os.path.join(auxdir, "config.guess")
        sub = os.path.join(auxdir, "config.sub")
        for p in (guess, sub):
            if not os.path.isfile(p):
                raise ConanException(
                    f"config fix: {p} not found — autoreconf/aux-dir "
                    "layout changed, update the recipe")

        # --- config.guess ---
        with open(guess, "r", encoding="utf-8", errors="replace") as f:
            data = f.read()
        n = data.count("umask 077")
        if n:
            data = data.replace("umask 077", "umask 000")
        if "__OHOS__" not in data:
            data = re.sub(
                r"(^\s*#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)",
                "\\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                data, count=1, flags=re.MULTILINE)
        if "HarmonyOS" not in data:
            data = re.sub(
                r"(^[ \t]+\*\:NetBSD\:\*\:\*\)[ \t]*\n)",
                lambda m: _HARMONYOS_GUESS_BLOCK + m.group(1),
                data, count=1, flags=re.MULTILINE)
        with open(guess, "w", encoding="utf-8") as f:
            f.write(data)
        self.output.info(
            f"config.guess: umask fixes={n}, "
            f"__OHOS__={'__OHOS__' in data}, "
            f"HarmonyOS={'HarmonyOS' in data}")

        # --- config.sub ---
        with open(sub, "r", encoding="utf-8", errors="replace") as f:
            data = f.read()
        if "ohos-linux)" not in data:
            data = re.sub(
                r"(\s*android-linux\)\s*\n)((\s*)basic_machine=\$field1-unknown\s*\n)((\s*)basic_os=linux-android\s*\n)(\s*;;\s*\n)",
                lambda m: (m.group(1) + m.group(2) + m.group(4)
                           + m.group(6) + "\tohos-linux)\n"
                           + m.group(3) + "basic_machine=$field1-unknown\n"
                           + m.group(5) + "basic_os=linux-ohos\n"
                           + m.group(6)),
                data, count=1)
        if "ohos*" not in data:
            data = re.sub(r"(gnu\*\s*\|\s*android\*)",
                          lambda m: m.group(1) + " | ohos*",
                          data, count=1)
        with open(sub, "w", encoding="utf-8") as f:
            f.write(data)
        self.output.info(
            f"config.sub: ohos-linux={'ohos-linux)' in data}, "
            f"ohos*={'ohos*' in data}")

        # Fail loudly if the essential E007 markers did not land: a silent
        # miss would resurface as "cannot guess build type".
        for path, marker in ((guess, "HarmonyOS"), (sub, "ohos-linux)")):
            with open(path, "r", encoding="utf-8") as f:
                if marker not in f.read():
                    raise ConanException(
                        f"E007 fix did not land in {path} "
                        f"(marker {marker!r} missing) — aborting before "
                        "configure fails obscurely")

    def _bash_path(self):
        # OhosPC: CONFIG_SHELL must be absolute (see class docstring).
        # CI sandbox and local dev box both have bash here.
        for cand in ("/data/service/hnp/bin/bash",):
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        w = shutil.which("bash")
        if w:
            return w
        raise ConanException("bash not found — required as CONFIG_SHELL")

    def build(self):
        apply_conandata_patches(self)

        # Bootstrap (upstream autogen.sh equivalent): libtoolize first so
        # LT_INIT macros are in place, then full autoreconf.
        self.run("libtoolize --automake --copy", cwd=self.source_folder,
                 env="conanbuild")
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")

        # Portability fixes on the freshly generated autotools scripts.
        self._fix_configure(os.path.join(self.source_folder, "configure"))
        self._fix_config_guess_sub(
            os.path.join(self.source_folder, "config"))  # AC_CONFIG_AUX_DIR

        # CONFIG_SHELL absolute: keeps libtool wrapper shebangs executable.
        os.environ["CONFIG_SHELL"] = self._bash_path()

        autotools = Autotools(self)
        # No --build/--host: config.guess (E007-fixed above) detects
        # aarch64-unknown-linux-ohos natively.
        autotools.configure()
        # E074 avoidance: parallel make can hit the HMDFS jobserver fifo
        # EPERM (abiword-plugin precedent); powerman is small, -j1 is cheap.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # conan does not track libtool .la files
        rm(self, "*.la", os.path.join(self.package_folder, "lib"),
           recursive=True)

    def package_info(self):
        # Application package with an incidental client library:
        # bin/  = powerman, pm        sbin/ = powermand, plmpower
        # lib/  = libpowerman(.so/.a) include/ = libpowerman.h
        # etc/powerman/ = device specification scripts (*.dev)
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["powerman"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.resdirs = ["etc"]
