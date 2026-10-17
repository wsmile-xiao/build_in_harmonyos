#!/usr/bin/env python3
"""Conan recipe for wtmpdb 0.75.0 — record logins/logouts in an SQLite db.

Meson + C. Upstream targets Linux with PAM + systemd; on OHOS:
- libpam is NOT part of the sysroot: meson's find_library('pam') hard-fails
  (meson.build:94), satisfied here via the published linux-pam/1.7.2 package;
- sqlite3 comes from the registry (find_library('sqlite3'));
- audit/libsystemd/wtmpdbd are feature:auto and explicitly disabled
  (no systemd on OHOS), so the delivered surface is libwtmpdb + wtmpdb CLI
  + pam_wtmpdb.so, without the wtmpdbd daemon.
Upstream registers 6 real meson tests (tst-dlopen dlopens pam_wtmpdb.so),
executed in build() via meson.test().
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class WtmpdbConan(ConanFile):
    name = "wtmpdb"
    version = "0.75.0"
    description = "wtmpdb - record login/logout information in a sqlite database (PAM module + CLI)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/thkukuk/wtmpdb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("pam", "lastlog", "wtmp", "sqlite")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("wtmpdb is packaged for POSIX/Linux-like targets (Linux/OHOS)")
        if not self.options.shared:
            raise ConanInvalidConfiguration("upstream meson builds libwtmpdb as a shared library only")

    def requirements(self):
        self.requires("sqlite3/3.53.4")
        self.requires("linux-pam/1.7.2")

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_paths(self):
        # package_folder lib/include directly (both deps use the standard
        # layout); avoids cpp_info component-aggregation API differences.
        libdirs, incdirs = [], []
        for ref in ("sqlite3", "linux-pam"):
            pf = self.dependencies[ref].package_folder
            for sub, bucket in (("lib", libdirs), ("include", incdirs)):
                p = os.path.join(pf, sub)
                if os.path.isdir(p):
                    bucket.append(p)
        return sorted(set(libdirs)), sorted(set(incdirs))

    def generate(self):
        PkgConfigDeps(self).generate()
        libdirs, incdirs = self._dep_paths()
        # find_library('pam')/('sqlite3') bypass pkg-config; give the linker
        # and the compiler search paths for the conan-provided deps, and make
        # libpam.so.0 resolvable at meson-test time (tst-dlopen dlopens the
        # PAM module which DT_NEEDEDs libpam).
        env = Environment()
        env.prepend_path("LIBRARY_PATH", ":".join(libdirs))
        env.prepend_path("LD_LIBRARY_PATH", ":".join(libdirs))
        env.prepend_path("CPATH", ":".join(incdirs))
        env.vars(self, scope="build").save_script("wtmpdb_deppaths")
        tc = MesonToolchain(self)
        # conan's meson flow installs with prefix=/ + DESTDIR=package_folder;
        # upstream's rootprefix check only passes with rootprefix='/', which
        # is exactly split-usr=true semantics (pamlibdir -> /lib/security,
        # lands under package_folder via DESTDIR).
        tc.project_options["split-usr"] = "true"
        tc.project_options["wtmpdbd"] = "disabled"
        tc.project_options["audit"] = "disabled"
        tc.project_options["systemd"] = "disabled"
        tc.project_options["man"] = "disabled"
        tc.project_options["compat-symlink"] = False
        tc.generate()
        self._inject_binaries()

    def _tool_path(self, executables, conf_key, names):
        """Absolute path for an aux binutils tool, resolved in three layers.

        The shared CI profile sets tools.build:compiler_executables with only
        the c/cpp keys, so executables.get("ar") is None there and meson falls
        back to bare-name PATH lookup ('llvm-ar'), which CI workers cannot
        resolve (their PATH has no ~/usr/local/bin) -> "Unknown linker(s):
        [['llvm-ar']]" while the same recipe is green on device.
        """
        value = executables.get(conf_key)
        if value:
            return value
        for key in ("cpp", "c"):
            compiler = executables.get(key)
            if not compiler:
                continue
            for name in names:
                cand = os.path.join(os.path.dirname(compiler), name)
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return None

    def _inject_binaries(self):
        # MesonToolchain locks compilers but writes no [binaries] ar/pkgconfig
        # entries and conan's build PATH lacks the toolchain dir (plocate
        # precedent): pin absolute paths from the profile conf.
        import re
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        native = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native):
            self.output.warning(
                "conan_meson_native.ini not found; [binaries] pinning skipped, "
                "meson will resolve ar/ranlib/strip/pkgconfig from PATH")
            return
        with open(native, encoding="utf-8") as f:
            content = f.read()
        pc = None
        if "pkgconf" in self.dependencies.build:
            pkg = self.dependencies.build["pkgconf"]
            binds = pkg.cpp_info.bindirs
            if binds:
                for name in ("pkgconf", "pkg-config"):
                    cand = os.path.join(pkg.package_folder, binds[0], name)
                    if os.path.isfile(cand):
                        pc = cand
                        break
        # strip is deliberately not derived: the OHOS clang wrapper signs the
        # ELF at link time, so an installed-binary strip would invalidate it.
        unresolved = []
        for key, names in (("ar", ("llvm-ar", "ar")),
                           ("ranlib", ("llvm-ranlib", "ranlib"))):
            value = self._tool_path(executables, key, names)
            if not value:
                unresolved.append(key)
                continue
            if re.search(r"(?m)^%s\s*=" % re.escape(key), content):
                continue
            content = content.replace("[binaries]\n",
                                      "[binaries]\n%s = '%s'\n" % (key, value), 1)
        for key, value in (("strip", executables.get("strip")),
                           ("pkgconfig", pc)):
            if not value or re.search(r"(?m)^%s\s*=" % re.escape(key), content):
                continue
            content = content.replace("[binaries]\n",
                                      "[binaries]\n%s = '%s'\n" % (key, value), 1)
        if unresolved:
            # Never skip silently: an unpinned ar/ranlib only fails on CI.
            raise ConanException(
                "cannot resolve %s to an absolute path: "
                "tools.build:compiler_executables carries no such key, "
                "nothing executable with those names sits next to the "
                "compiler, and none is on PATH; meson would probe the bare "
                "name and fail on CI workers" % ", ".join(unresolved))
        with open(native, "w", encoding="utf-8") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream registers 6 real tests (tests/meson.build), including
        # tst-dlopen which dlopen()s the freshly built pam_wtmpdb.so.
        meson.test()

    def package(self):
        Meson(self).install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["wtmpdb"]
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.set_property("pkg_config_name", "libwtmpdb")
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
