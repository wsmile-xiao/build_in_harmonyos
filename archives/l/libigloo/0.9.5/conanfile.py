#!/usr/bin/env python3
"""Conan recipe for libigloo 0.9.5 (Autotools, OHOS-adapted).

libigloo is the Icecast common C framework library: a compiled shared/static
library (LT_INIT in configure.ac, lib_LTLIBRARIES in Makefile.am) providing
reference-counted objects, string pool, TAP test harness, PRNG, UUID, digest,
time and locking helpers. It is NOT header-only and NOT itself a test
framework-only package: it ships igloo/tap.h as part of its public API but
builds a real libigloo.so/.a.

Upstream: https://gitlab.xiph.org/xiph/icecast-libigloo (LGPL-2.0-or-later).

OHOS adaptation notes (validated on aarch64-unknown-linux-ohos):
- The official tag tarball ships no generated `configure`; the recipe runs
  `autogen.sh` (autoreconf -isf) first. m4/pkg.m4 must be present before
  autoreconf so PKG_CHECK_MODULES expands (pkg.m4 is exported alongside the
  recipe and copied into m4/ before bootstrapping, see export_sources).
- rhash/1.4.6 is a hard dependency (configure.ac:105). It is found via
  pkg-config (PKG_CHECK_MODULES) when available; the fallback path
  AC_CHECK_HEADER/AC_CHECK_LIB is not used on OHOS because PkgConfigDeps
  generates a librhash.pc in the rhash package. The cached rhash package
  is static-only, so the validated configuration links it statically into
  libigloo.a; for a shared libigloo.so the static non-PIC librhash.a cannot
  be linked, therefore this recipe defaults to static and enables shared
  only when the dependency provides a shared variant (not the case today).
- config.guess/config.sub carry HarmonyOS (linux-ohos) detection patches
  applied AFTER autoreconf --install (which would otherwise overwrite them
  with the stock automake-1.18 copies lacking HarmonyOS), see patches/.
- Upstream TAP tests (`make check`) run as part of build(): 10 test
  programs, 763/763 PASS on OHOS aarch64 (see notes.md).
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibiglooConan(ConanFile):
    name = "libigloo"
    version = "0.9.5"
    description = "Common framework library by the Icecast project (ro, sp, tap, prng, uuid, digest, time)"
    license = "LGPL-2.0-or-later"
    homepage = "https://gitlab.xiph.org/xiph/icecast-libigloo"
    url = "https://gitlab.xiph.org/xiph/icecast-libigloo"
    topics = ("icecast", "framework", "reference-counting", "uuid")

    package_type = "library"
    implements = ["auto_shared_fpic"]

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # pkg-config aclocal macro (pkg.m4) needed by configure.ac PKG_CHECK_MODULES;
        # copied into m4/ before autoreconf so the macro expands instead of
        # producing the "PKG_CHECK_MODULES undefined" cascade (E089 root cause).
        copy(self, "m4-pkg.m4", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # configure.ac:105 — librhash is required (digest backend).
        # rhash/1.4.6 in the ohpcd artifacts repo is static-only.
        self.requires("rhash/1.4.6")

    def build_requirements(self):
        # Official tag tarball has no generated configure; autogen.sh runs
        # autoreconf -isf which needs aclocal (automake) and libtoolize
        # (libtool). Same minimal CI-proven set as libfyaml/0.9.6.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libigloo supports Linux and OHOS, not {self.settings.os}"
            )
        # rhash/1.4.6 publishes only a static library (non-PIC). A shared
        # libigloo.so cannot link it in; validated configuration is static.
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "shared=True requires a shared/PIC rhash build; "
                "rhash/1.4.6 in ohpcd is static-only, use shared=False"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Host-dependent compiler availability is resolved before any toolchain
        # generator runs, so every generator (AutotoolsToolchain env, CMakeToolchain
        # of consumer test packages) sees the same, existing compiler.
        self._resolve_conf_compiler()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        # Expose the recipe's m4 dir (m4-pkg.m4) to aclocal via ACLOCAL_PATH
        # so PKG_CHECK_MODULES expands during autoreconf.
        self.buildenv_info.append_path("ACLOCAL_PATH", self.export_sources_folder)

    def _resolve_conf_compiler(self):
        """Point tools.build:compiler_executables at a compiler that exists.

        The ohos-aarch64 CI profile pins CC/CXX to /data/service/hnp/bin/clang,
        a device-only deployment path that does not exist on the build host
        (hnp/bin contains only git). When the pinned compiler is missing,
        fall back to the first clang/clang++ on PATH (shutil.which, no
        hard-coded paths) so AutotoolsToolchain, CMakeToolchain (dependency
        test_package consumers) and conanbuild envs all agree on one compiler.
        """
        compilers = dict(self.conf.get("tools.build:compiler_executables", check_type=dict) or {})
        changed = False
        for lang, name in (("c", "clang"), ("cpp", "clang++")):
            pinned = compilers.get(lang)
            if pinned and not (os.path.isfile(pinned) and os.access(pinned, os.X_OK)):
                found = shutil.which(name)
                if not found:
                    raise ConanInvalidConfiguration(
                        f"libigloo: profile compiler for {lang} ({pinned}) does not "
                        f"exist on this host and no {name} was found on PATH"
                    )
                compilers[lang] = found
                changed = True
        if changed:
            self.conf.define("tools.build:compiler_executables", compilers)

    def _build_env_config_shell(self):
        """CONFIG_SHELL as composed into the current build environment.

        env="conanbuild" sources the generated conanbuild.sh, whose trailing
        (winning) exports come from the profile [buildenv]; read the value
        there instead of guessing at profile internals.
        """
        script = os.path.join(self.generators_folder, "conanbuild.sh")
        if not os.path.isfile(script):
            return None
        with open(script, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r"^(?:export\s+)?CONFIG_SHELL=(.+)$", line)
                if match:
                    return match.group(1).strip().strip("'\"")
        return None

    def _resolve_config_shell(self):
        """Shell that configure/autoreconf must run under on this host.

        The ohos profile may inject CONFIG_SHELL pointing at a device-only
        deployment path that does not exist on the build host; configure
        would embed that dangling path as the Makefile $(SHELL) and the
        config.status launcher, killing configure and every make recipe.
        Resolution order, no hardcoded paths:
        1. build-env CONFIG_SHELL when it names an existing executable;
        2. first bash on PATH (shutil.which);
        3. ConanInvalidConfiguration when neither exists.
        """
        candidate = self._build_env_config_shell() or os.environ.get("CONFIG_SHELL")
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        bash = shutil.which("bash")
        if bash:
            return bash
        raise ConanInvalidConfiguration(
            "libigloo needs a real shell for configure/autoreconf on the build "
            f"host: CONFIG_SHELL={candidate or 'unset'!r} is not an existing "
            "executable and no bash was found on PATH"
        )

    def build(self):
        # 1) m4/pkg.m4 must be in place BEFORE autoreconf so PKG_CHECK_MODULES
        #    expands; autogen.sh runs `autoreconf -isf` (installs stock
        #    config.guess/config.sub lacking HarmonyOS support).
        shutil.copy(
            os.path.join(self.export_sources_folder, "m4-pkg.m4"),
            os.path.join(self.source_folder, "m4", "pkg.m4"),
        )
        # 2) Generate configure (official tag ships none). env="conanbuild"
        #    puts tool_requires (automake/aclocal, libtool/libtoolize) on PATH.
        #    CONFIG_SHELL is pinned to a shell that really exists on this host
        #    (the profile value may point at a device-only path), so autoreconf
        #    and any configure re-exec run under a real interpreter.
        config_shell = self._resolve_config_shell()
        self.run(
            f'CONFIG_SHELL="{config_shell}" sh autogen.sh',
            cwd=self.source_folder,
            env="conanbuild",
        )
        # 3) OHOS detection patches AFTER autoreconf --install (it installs
        #    stock config.guess/config.sub from automake-1.18 that lack
        #    HarmonyOS/linux-ohos recognition).
        apply_conandata_patches(self)
        # 4) HMDFS temp-dir workaround (E136): config.status creates ./confXXXXXX
        #    with umask 077 -> drwx--S--- unwritable by the current user; patch
        #    the freshly generated configure (which embeds config.status).
        #    Local exploratory build did NOT trigger this (autoconf 2.71 emits
        #    `umask 000`), so the replace is a no-op there; kept for the CI
        #    sandbox where libfyaml/0.9.6 (same pattern) hit it for real.
        cfg = os.path.join(self.source_folder, "configure")
        with open(cfg, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        content = content.replace("umask 077", "umask 002")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(content)
        autotools = Autotools(self)
        # SHELL= is picked up by AC_OUTPUT as the Makefile $(SHELL) and the
        # config.status launcher; CONFIG_SHELL= covers configure re-execs and
        # `config.status --recheck` re-runs. Both point at the resolved host
        # shell; make check below still forces SHELL=/bin/sh (E553) regardless.
        # Inline CONFIG_SHELL prefix instead of autotools.configure():
        # env="conanbuild" composes the profile [buildenv], whose CONFIG_SHELL
        # can point at a device-only deployment path missing on the build host.
        # configure's prologue re-exec (`exec $CONFIG_SHELL "$0" ...`) fires
        # BEFORE option parsing, so a CONFIG_SHELL=... command-line argument is
        # exported too late (observed: configure[139] ... inaccessible, error
        # 127). An inline assignment prefixing the command beats every env
        # composition and is inherited through the re-exec. The SHELL= argument
        # is picked up by AC_OUTPUT as the Makefile $(SHELL) and the
        # config.status launcher; make check below still forces SHELL=/bin/sh
        # (E553) regardless.
        configure_script = os.path.join(self.source_folder, "configure")
        self.run(
            f'CONFIG_SHELL="{config_shell}" "{configure_script}"'
            " --disable-shared --enable-static --prefix=/"
            " '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin'"
            " '--libdir=${prefix}/lib' '--includedir=${prefix}/include'"
            " '--oldincludedir=${prefix}/include'"
            f" SHELL={config_shell}",
            cwd=self.build_folder if os.path.isdir(self.build_folder) else self.source_folder,
            env="conanbuild",
        )
        autotools.make(args=["-j1"])
        # Layer 1: upstream official TAP test suite (R51). 10 programs,
        # 763/763 PASS on OHOS aarch64.
        # SHELL=/bin/sh is REQUIRED for make check on HarmonyOS: the ported
        # bash 5.3 injected via the ohos profile buildenv (and picked as
        # $(SHELL) by configure) fails to
        # propagate a group-command fd redirection into pipeline elements
        # (`{ ... | cat >&3; } 3>log` -> "3: Bad file descriptor"), which
        # breaks tap-driver.sh's awk `print | "cat >&3"` log channel and
        # makes every test report ERROR "missing test plan". /bin/sh (mksh
        # family) handles fd 3 inheritance correctly; overriding SHELL on
        # the make command line re-runs check-TESTS with /bin/sh and the
        # full suite goes green. Minimal repro + analysis in notes.md.
        autotools.make(target="check", args=["-j1", "SHELL=/bin/sh"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["igloo"]
        # igloo.pc: Libs: -ligloo -pthread  /  Cflags: -pthread
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.requires = ["rhash::rhash"]
        self.cpp_info.set_property("cmake_file_name", "libigloo")
        self.cpp_info.set_property("cmake_target_name", "libigloo::libigloo")
        self.cpp_info.set_property("pkg_config_name", "igloo")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
