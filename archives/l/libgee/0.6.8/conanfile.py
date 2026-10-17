#!/usr/bin/env python3
"""Conan recipe for libgee 0.6.8 (Autotools, Gee 1.0 API)."""

import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibgeeConan(ConanFile):
    name = "libgee"
    version = "0.6.8"
    description = "GObject collection library providing the Gee 1.0 API"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/Projects/Libgee"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _build_env(self):
        env = Environment()
        # R33: never fall back to a bare "clang" name — non-interactive CI
        # shells do not have the toolchain bindir on PATH.  Prefer the
        # profile's absolute compiler_executables, then a pre-set CC/CXX.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or os.environ.get("CC")
        cxx = compilers.get("cpp") or os.environ.get("CXX")
        if cc:
            env.define("CC", cc)
        if cxx:
            env.define("CXX", cxx)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            pkg_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkg_dir):
                env.append_path("PKG_CONFIG_PATH", pkg_dir)
            for lib_dir in dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, lib_dir))
        return env

    def generate(self):
        PkgConfigDeps(self).generate()
        env = self._build_env()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate(env=env)

    def _gtester_command(self):
        """gtester runner for `make check`.

        glib >= 2.74 stopped shipping gtester while libgee 0.6.8's tests
        target it.  The test programs are plain executables, so when no
        system gtester exists emit a minimal runner that executes each
        program and propagates its exit code.
        """
        import shutil

        existing = shutil.which("gtester")
        if existing:
            return existing
        shim = os.path.join(self.build_folder, "gtester-minimal")
        with open(shim, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#!/bin/sh\n"
                "ret=0\n"
                "for a in \"$@\"; do\n"
                "  case \"$a\" in -*) continue ;; esac\n"
                "  if [ -f \"./$a\" ]; then p=\"./$a\"; "
                "elif [ -f \"$a\" ]; then p=\"$a\"; else continue; fi\n"
                "  echo \"TEST: $a\"\n"
                "  if \"$p\"; then echo \"PASS: $a\"; "
                "else echo \"FAIL: $a\"; ret=1; fi\n"
                "done\n"
                "exit $ret\n"
            )
        os.chmod(shim, 0o755)
        return shim

    def build(self):
        apply_conandata_patches(self)
        # HNP bash may call getcwd() after Conan changes cwd.  Exporting the
        # actual build path lets Autoconf retain the cwd on OHOS/HMDFS.
        os.environ["PWD"] = str(self.build_folder)
        autotools = Autotools(self)
        env = self._build_env()
        with env.vars(self).apply():
            autotools.configure()
            # Some OHOS Conan dependencies ship libtool .la files with a baked-in
            # /lib prefix.  libtool follows those archives to //lib and fails;
            # Conan's pkg-config and cpp_info metadata already provide the links.
            import glob
            for dep in self.dependencies.values():
                if not dep.package_folder:
                    continue
                for libdir in dep.cpp_info.libdirs:
                    for la_file in glob.glob(os.path.join(dep.package_folder, libdir, "*.la")):
                        os.remove(la_file)
            autotools.make(args=["-j1"])
            import shlex

            self.run("make check -j1 GTESTER={}".format(shlex.quote(self._gtester_command())))

    def package(self):
        Autotools(self).install(args=["-j1"])
        la_file = os.path.join(self.package_folder, "lib", "libgee.la")
        if os.path.isfile(la_file):
            os.remove(la_file)

    def package_info(self):
        self.cpp_info.libs = ["gee"]
        self.cpp_info.includedirs = ["include/gee-1.0"]
        self.cpp_info.requires = ["glib::glib"]
        self.cpp_info.set_property("pkg_config_name", "gee-1.0")
        self.cpp_info.set_property("cmake_file_name", "libgee")
        self.cpp_info.set_property("cmake_target_name", "libgee::libgee")
