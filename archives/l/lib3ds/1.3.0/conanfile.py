#!/usr/bin/env python3
"""Conan recipe — lib3ds 1.3.0 (Autotools).

Upstream lib3ds is the free ANSI-C library for 3D-Studio (.3DS) model files.
The 1.3.0 release ships a pre-generated autotools `configure` (2006 vintage)
plus `Makefile.am`; every Linux distribution builds it with that autotools
chain (Debian, Fedora, Gentoo, FreeBSD). We follow the same path — no CMake
exists in this release.

OHOS adaptation (0 patches — same strategy as lame/3.100):
  * The shipped `configure` (2006) uses `umask 077 && mktemp -d` for its
    config.status scratch directory, which creates temp files mode 0600.
    On OHOS's restricted filesystem this manifests as "Permission denied"
    during `config.status`. We fix it at runtime by replacing `umask 077`
    with `umask 022` in the configure script (in-memory, no source patch).
  * The shipped `config.guess`/`config.sub` (2006) predate OpenHarmony and
    reject the `*-linux-ohos` tuple. Rather than patching them, we pass an
    explicit `--host`/`--build` of `aarch64-linux-gnu` and install a uname
    shim that reports "Linux" — autotools then treats OHOS as Linux-ELF
    (which it is at the ABI level), and the shipped config.sub accepts the
    standard linux-gnu tuple without modification.
  * The upstream tarball is a .zip, which does not preserve the executable
    bit on `configure`/`config.guess`/`config.sub`/`install-sh`/`missing`/
    `mkinstalldirs`. We restore those bits at build time.
  * The 2007 release tarball ships a fully pre-generated autotools tree
    (configure, aclocal.m4, Makefile.in, config.h.in) BUT the shipped
    Makefile.in carries automake-1.4-era UNCONDITIONAL rebuild rules
    (no --enable-maintainer-mode gate): `$(srcdir)/Makefile.in: ... &&
    $(AUTOMAKE)`, `configure: && $(AUTOCONF)`, `aclocal.m4: &&
    $(ACLOCAL)`, `config.h.in: && $(AUTOHEADER)`. Any time the inputs
    (configure.in / Makefile.am / aclocal.m4) are mtime-NEWER than the
    generated outputs, `make` re-runs aclocal→autoconf→automake. Two of
    our in-memory edits above (the umask rewrite of `configure` and the
    chunktable $(srcdir) fix on `lib3ds/Makefile.{am,in}`) give those
    files a "now" mtime, which inverts the tarball's original ordering
    and makes the inputs newer than the outputs → the unconditional rules
    fire. That regen then fails hard because the tarball does NOT ship
    `compile` or `mkinstalldirs` (automake aborts: "required file
    './compile' not found") and the automake/1.18 build-requirement's
    aclocal regenerates aclocal.m4 without the 2006 inline libtool.m4,
    so autoconf reports "possibly undefined macro: AC_PROG_LIBTOOL"
    and make reports "LIBTOOL is undefined". Fix: after every recipe edit,
    normalize mtime so the generated autotools files are at least as new
    as their inputs — `touch` configure/aclocal.m4/config.h.in and every
    Makefile.in last. The unconditional rebuild rules then see no out-of-
    date target and `make` uses the upstream-supplied configure/Makefile.in
    verbatim. No autoreconf, no libtool tool_require added.

Upstream test situation:
  * lib3ds 1.3.0 registers NO formal test suite (no `TESTS`/
    `check_PROGRAMS`; `examples/3dsplay.c` is an unbuilt OpenGL demo,
    NOT in SUBDIRS, not a test). Consumer validation is carried entirely
    by test_package/, which exercises the core 3DS API in memory.
  * `3dsdump` is a real installed `bin_PROGRAMS`; `lib3ds-config` is a real
    installed `bin_SCRIPTS` (see commands.json).
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Lib3dsConan(ConanFile):
    name = "lib3ds"
    version = "1.3.0"
    description = "Free ANSI-C library for managing 3D-Studio (.3DS) model files"
    license = "LGPL-2.1"
    homepage = "https://lib3ds.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # lib3ds is pure C; drop the C++ settings so they don't force a
        # libstdc++/libc++ ABI split that this library doesn't use.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        self.tool_requires("automake/1.18")

    def generate(self):
        # Nominal triplet uses -linux-gnu suffix so the 2006-vintage
        # config.sub accepts it; the uname shim in build() makes
        # config.guess report Linux. Real cross-target is set by the
        # profile's CC/CXX (OHOS clang).
        _arch_triplet = {"armv8": "aarch64-linux-gnu", "x86_64": "x86_64-linux-gnu"}
        arch = str(self.settings.arch)
        triplet = _arch_triplet.get(arch)
        if triplet is None:
            raise ConanInvalidConfiguration(
                f"lib3ds 1.3.0 targets HarmonyOS PC, only armv8/x86_64 supported, got arch='{arch}'"
            )
        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--host={triplet}")
        tc.configure_args.append(f"--build={triplet}")
        # static/shared is driven by libtool via --enable-shared/--disable-shared,
        # which AutotoolsToolchain derives from `options.shared` automatically.
        tc.generate()

    # ── OHOS SDK linker runtime path (lld/libxml2.so.16) ──────────────
    # The OHOS clang driver spawns `lld` (ld.lld) for linking. lld is a
    # dynamically linked ELF whose NEEDED list includes libxml2.so.16,
    # resolved via its RUNPATH ($ORIGIN/../lib → the SDK llvm/lib). On some
    # CI workers that directory is not on the ambient LD_LIBRARY_PATH, so
    # lld fails to start with
    #   "Error loading shared library libxml2.so.16 ... xmlFreeDoc: symbol
    #    not found"
    # and clang aborts with "linker command failed". In autotools this
    # surfaces at configure time as
    #   configure: error: C compiler cannot create executables
    # because configure's conftest link step invokes clang → lld.
    #
    # This is NOT a lib3ds source bug (same class as libscrypt/1.22, sord,
    # perl-dbd-pg, clipper2, kio). Fix: prepend the SDK's own llvm/lib so
    # the lld that configure/make/clang invoke loads the SDK's matched
    # libxml2 first. The environment must cover autotools.configure() AND
    # make (and install) — every clang/lld invocation in build()+package().
    # No new Conan dependency is added (libxml2 is the SDK's own runtime,
    # not a lib3ds build input).
    def _cc(self):
        # Resolve the real C compiler from the Conan profile conf; fall
        # back to `clang` on the Conan buildenv PATH if the configured
        # absolute path does not exist on this host. Never hardcodes a user
        # name, an SDK version, or an absolute path.
        import shutil

        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp_execs.get("c", "clang")
        if os.path.isabs(cc):
            return cc if os.path.exists(cc) else "clang"
        return cc if shutil.which(cc) else "clang"

    def _sdk_llvm_libdir(self):
        """Resolve the active OHOS SDK llvm/lib containing libxml2.so.16.

        Derives the dir from the real clang path (tools.build:compiler_executables
        → resolved by _cc()), never hardcoding a user name, an SDK version,
        or an absolute path. On non-OHOS hosts returns "".
        """
        if str(self.settings.os) != "OHOS":
            return ""
        cc_real = os.path.realpath(self._cc())
        llvm_lib = os.path.join(
            os.path.dirname(os.path.dirname(cc_real)), "lib"
        )
        # Only trust the dir if it actually carries libxml2.so.16 — guards
        # against a bare `clang` on PATH whose parent is not the SDK, or a
        # stale profile path.
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""

    def _build_environment(self):
        """Conan Environment that prepends the SDK llvm/lib to LD_LIBRARY_PATH.

        Applied around every autotools.configure()/make()/install() so
        configure → clang → lld and make → clang → lld all inherit it. On
        non-OHOS hosts this is a no-op (empty Environment).
        """
        env = Environment()
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path for lld: {sdk_lib}"
            )
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        return env

    def build(self):
        # 1. The upstream .zip does not preserve exec bits on autotools
        #    helper scripts. Restore them so configure can run.
        for script in glob.glob(
            os.path.join(self.source_folder, "**", "configure"), recursive=True
        ) + [
            os.path.join(self.source_folder, "config.guess"),
            os.path.join(self.source_folder, "config.sub"),
            os.path.join(self.source_folder, "install-sh"),
            os.path.join(self.source_folder, "missing"),
            os.path.join(self.source_folder, "mkinstalldirs"),
        ]:
            if os.path.isfile(script):
                os.chmod(script, 0o755)

        # 2. The shipped config.guess/config.sub (2006) predate aarch64.
        #    Use the copies supplied by the Conan Automake build requirement
        #    instead of relying on host-specific /usr/share paths.
        import shutil
        automake_share = os.path.join(
            self.dependencies.build["automake"].package_folder,
            "share",
            "automake-1.18",
        )
        for _aux in ("config.guess", "config.sub"):
            _src = os.path.join(automake_share, _aux)
            _dst = os.path.join(self.source_folder, _aux)

            if not os.path.isfile(_src):
                raise ConanInvalidConfiguration(
                    f"Automake auxiliary file not found: {_src}"
                )

            shutil.copy2(_src, _dst)
            os.chmod(_dst, 0o755)

        # Fail early instead of silently falling back to the obsolete
        # upstream config.sub.
        self.run(
            f'"{os.path.join(self.source_folder, "config.sub")}" '
            f'aarch64-linux-gnu',
            env="conanbuild",
        )

        # 3. The 2006 configure uses `umask 077` for its config.status
        #    scratch dir, creating temp files mode 0600 — unwritable on
        #    OHOS. Replace with `umask 022` in-memory (no source patch).
        for _cfg in glob.glob(
            os.path.join(self.source_folder, "**", "configure"), recursive=True
        ):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))

        # 4. The 2006 lib3ds/Makefile.in has a custom code-gen rule:
        #      chunktable.h: chunk.h chunktable.sed
        #           sed -f chunktable.sed chunk.h >chunktable.h
        #    It lacks $(srcdir) prefixes. `make` honors VPATH for
        #    *prerequisites* but the `sed` command itself uses bare
        #    filenames, so an out-of-tree build cannot find the source
        #    files in the build dir ("chunktable.sed: No such file").
        #    Fix it in-memory on both Makefile.am and Makefile.in (0 patches).
        for _mf in (
            os.path.join(self.source_folder, "lib3ds", "Makefile.am"),
            os.path.join(self.source_folder, "lib3ds", "Makefile.in"),
        ):
            if os.path.isfile(_mf):
                replace_in_file(
                    self,
                    _mf,
                    "sed -f chunktable.sed chunk.h >chunktable.h",
                    "sed -f $(srcdir)/chunktable.sed $(srcdir)/chunk.h >chunktable.h",
                )

        # 5. Install a uname shim so config.guess reports "Linux" (the
        #    2006 config.guess does not know HarmonyOS). Combined with the
        #    explicit --host/--build triplet above, autotools builds for
        #    linux-ELF which is ABI-compatible with OHOS.
        _shim = os.path.join(self.build_folder, "_uname_shim")
        os.makedirs(_shim, exist_ok=True)
        _u = os.path.join(_shim, "uname")
        _uname_machine = {"armv8": "aarch64", "x86_64": "x86_64"}.get(
            str(self.settings.arch), str(self.settings.arch)
        )
        with open(_u, "w") as _f:
            _f.write(
                "#!/bin/sh\n"
                'case "${1:-}" in\n'
                '  -s|"") echo Linux ;;\n'
                "  -r) echo 6.6 ;;\n"
                f"  -m) echo {_uname_machine} ;;\n"
                '  *) exec /system/bin/uname "$@" 2>/dev/null || exec /bin/uname "$@" ;;\n'
                "esac\n"
            )
        os.chmod(_u, 0o755)
        os.environ["PATH"] = _shim + os.pathsep + os.environ.get("PATH", "")

        # 6. Normalize autotools file timestamps so `make` never re-runs
        #    aclocal/autoconf/automake/autoheader. The shipped Makefile.in
        #    has automake-1.4-era UNCONDITIONAL rebuild rules (no
        #    --enable-maintainer-mode gate): if configure.in / Makefile.am
        #    / aclocal.m4 are mtime-NEWER than configure / Makefile.in /
        #    config.h.in, those rules fire and `make` regenerates the
        #    autotools tree — which fails hard here because the release
        #    tarball does NOT ship `compile`/`mkinstalldirs`, and the
        #    automake/1.18 build-requirement's aclocal rebuilds aclocal.m4
        #    without the 2006 inline libtool.m4 (→ "AC_PROG_LIBTOOL
        #    possibly undefined", "LIBTOOL is undefined",
        #    "required file './compile' not found"). The tarball's original
        #    mtime ordering was correct (inputs older than outputs), but
        #    our in-memory edits above (umask rewrite of `configure`, the
        #    chunktable $(srcdir) fix on lib3ds/Makefile.{am,in}, and the
        #    config.guess/config.sub copy from automake) gave some files a
        #    "now" mtime that can invert the ordering. Re-stamp the
        #    generated files so they are at least as new as every input;
        #    touch the generated outputs LAST so they strictly postdate the
        #    Makefile.am edits. `make` then sees no out-of-date target and
        #    uses the upstream-supplied configure/Makefile.in verbatim —
        #    no autoreconf, no libtool tool_require added. Verified: no
        #    aclocal/autoconf/automake invocation during `make`.
        import time
        _now = time.time()
        # Inputs (must be older or equal): configure.in, all Makefile.am,
        # aclocal.m4, config.h.in candidates that are inputs to autoheader.
        _inputs = [
            os.path.join(self.source_folder, "configure.in"),
            os.path.join(self.source_folder, "Makefile.am"),
            os.path.join(self.source_folder, "lib3ds", "Makefile.am"),
            os.path.join(self.source_folder, "tools", "Makefile.am"),
        ]
        for _p in _inputs:
            if os.path.isfile(_p):
                os.utime(_p, (_now, _now))
        # Generated outputs (touch AFTER inputs so outputs strictly postdate):
        #   configure, aclocal.m4, config.h.in (top), and every Makefile.in.
        _outputs = [
            os.path.join(self.source_folder, "configure"),
            os.path.join(self.source_folder, "aclocal.m4"),
            os.path.join(self.source_folder, "config.h.in"),
            os.path.join(self.source_folder, "Makefile.in"),
            os.path.join(self.source_folder, "lib3ds", "Makefile.in"),
            os.path.join(self.source_folder, "tools", "Makefile.in"),
        ]
        for _p in _outputs:
            if os.path.isfile(_p):
                os.utime(_p, (_now, _now))

        # All configure/make/clang/lld invocations run inside the SDK
        # linker-runtime environment so lld finds the SDK's libxml2.so.16
        # (see _build_environment / _sdk_llvm_libdir). On non-OHOS hosts
        # this is a no-op (empty Environment).
        with self._build_environment().vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        # install() also invokes clang→lld (libtool final link of the
        # shared library), so it needs the same SDK linker-runtime env.
        with self._build_environment().vars(self).apply():
            autotools = Autotools(self)
            autotools.install()

        # Tidy up libtool archives (not needed by conan consumers).
        libdir = os.path.join(self.package_folder, "lib")
        for la in ("lib3ds.la", "lib3ds-1.la"):
            la_path = os.path.join(libdir, la)
            if os.path.isfile(la_path):
                os.remove(la_path)

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # lib3ds builds lib3ds.la with libtool `-release 1`, so the
        # installed runtime objects are lib3ds-1.so.3 / lib3ds-1.so.3.0.0.
        # The 2006-vintage libtool in this release creates the *development*
        # symlink as lib3ds.so (the base name), NOT lib3ds-1.so. CMakeDeps
        # resolves `cpp_info.libs` by looking for lib<name>.so in the
        # package lib dir, so the link name must be `3ds` (matching
        # lib3ds.so), not `3ds-1`. Verified against the actual install tree.
        self.cpp_info.libs = ["3ds"]
        self.cpp_info.set_property("cmake_file_name", "lib3ds")
        self.cpp_info.set_property("cmake_target_name", "lib3ds::lib3ds")
        self.cpp_info.set_property("pkg_config_name", "lib3ds")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
