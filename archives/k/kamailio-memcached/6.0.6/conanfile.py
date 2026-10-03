#!/usr/bin/env python3
"""Conan recipe — kamailio-memcached 6.0.6 (Kamailio SIP server `memcached` module).

Distribution package: the in-tree `memcached` module of the Kamailio 6.0.6
source release (`src/modules/memcached` -> `memcached.so`).  This is exactly
the content of the distro sub-package named `kamailio-memcached`
(Alpine `_mod_list_memcached="memcached"`, Debian
`kamailio-memcached-modules`, OBS/RHEL `%package memcached`).

Build: Kamailio's own Makefile system — `make cfg` followed by
`make modules modules=modules/memcached`.  Only the memcached module is
built.  As with every Kamailio module, the Kamailio core is *not* linked
into the module: `memcached.so` resolves the core API (`dprint_*`,
`_km_log_func`, `pv_*`, `MD5StringArray`, ...) from the Kamailio binary at
dlopen() time.

OHOS notes:
  * `src/modules/memcached/Makefile` discovers libmemcached through
    pkg-config (`BUILDER = $(shell which pkg-config)`).  Under GNU make's
    default `/bin/sh` on HarmonyOS that probe is unreliable, so make is
    driven with an explicit `SHELL=<bash>`; no source patch is needed.
  * libmemcached/1.0.18 is a *static*, C++-implemented archive.  The .pc
    shipped inside the libmemcached package declares only
    `-lmemcached -lmemcachedutil`, while its `package_info` declares
    `system_libs=["m","c++"]`.  Linking against the shipped .pc leaves
    `__gxx_personality_v0`, `_ZSt9terminatev` and `__cxa_begin_catch`
    unresolved inside `memcached.so` (a shared object link still exits 0),
    and the module then fails to dlopen().  The recipe therefore feeds
    kamailio's `pkg-config --libs libmemcached` with the .pc synthesised by
    Conan's PkgConfigDeps generator, which carries the declared system_libs.

Upstream tests: Kamailio 6.0.6 ships no test suite — there is no top-level
`test/` directory, `src/modules/memcached` contains no tests, no
`make check`/`TESTS` target exists anywhere in the Makefile hierarchy, and
the in-tree Alpine APKBUILD states `options="!check" # no testsuite`.
The genuine upstream entry point is the build entry
(`make modules modules=modules/memcached`); the audit is recorded in
`reports/upstream-test-audit.md` and the consumer harness in
`test_package/`.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, chdir, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

MODULE_NAME = "memcached.so"
MODULE_SUBDIR = os.path.join("src", "modules", "memcached")


class KamailioMemcachedConan(ConanFile):
    name = "kamailio-memcached"
    version = "6.0.6"
    description = ("Kamailio SIP server memcached module (memcached.so): "
                   "key/value persistence backed by libmemcached")
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org/"
    url = "https://www.kamailio.org/"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "kamailio-memcached only supports Linux/OHOS, not %s"
                % self.settings.os)

    def export_sources(self):
        # No patches are needed for OHOS today (the platform adaptation is
        # carried entirely by the build settings); the hook keeps the recipe
        # ready to ship one via conandata.yml without changing its shape.
        export_conandata_patches(self)

    def requirements(self):
        # Direct, mandatory third-party dependency of src/modules/memcached:
        # Makefile:13-14 (`pkg-config --cflags/--libs libmemcached`),
        # CMakeLists.txt:6 (`pkg_check_modules(memcached REQUIRED ...)`),
        # memcached.h:28 (`#include <libmemcached/memcached.h>`).
        self.requires("libmemcached/1.0.18")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # The synthesised .pc carries libmemcached's declared system_libs
        # (`-lm -lc++`), which the .pc shipped in the package omits.
        PkgConfigDeps(self).generate()

    # ── build helpers ────────────────────────────────────────────────
    def _compiler(self, lang="c"):
        execs = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(execs, dict):
            found = execs.get(lang)
            if found:
                return found
        return "clang++" if lang == "cpp" else "clang"

    def _bash(self):
        shell = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        return shell if os.path.isfile(shell) else ""

    def _build_env(self):
        cc = self._compiler("c")
        env = Environment()
        env.define("CC", cc)
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        # make / pkg-config / clang all live in the OHOS toolchain bin; prepend
        # it explicitly so the build does not depend on an inherited PATH.
        for bin_dir in ("/data/service/hnp/bin", os.path.dirname(cc)):
            if bin_dir and os.path.isdir(bin_dir):
                env.prepend_path("PATH", bin_dir)
        shell = self._bash()
        if shell:
            env.define("SHELL", shell)
        return env

    def _make_shell_arg(self):
        shell = self._bash()
        return "SHELL=%s" % shell if shell else ""

    def build(self):
        work = os.path.join(self.build_folder, "worktree")
        if os.path.exists(work):
            shutil.rmtree(work)
        shutil.copytree(self.source_folder, work)
        shell_arg = self._make_shell_arg()
        with self._build_env().vars(self, scope="build").apply():
            with chdir(self, work):
                # Step 1: generate src/config.mak + src/modules.lst.
                self.run("make -C src cfg %s" % shell_arg)
                # Step 2: build only the memcached module.
                self.run("make -C src modules modules=modules/memcached -j1 %s"
                         % shell_arg)

    def package(self):
        candidates = [
            os.path.join(self.build_folder, "worktree", MODULE_SUBDIR, MODULE_NAME),
        ]
        src_so = next((p for p in candidates if os.path.isfile(p)), None)
        if not src_so:
            raise ConanException(
                "expected build product %s not found (tried: %s)"
                % (MODULE_NAME, ", ".join(candidates)))
        copy(self, MODULE_NAME, src=os.path.dirname(src_so),
             dst=os.path.join(self.package_folder, "lib", "kamailio", "modules"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # The module is a dlopen() plugin, not a link library: no libs to
        # link, no headers to include.  Expose the module directory so a
        # Kamailio core package can consume it.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = []
