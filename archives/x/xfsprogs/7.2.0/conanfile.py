#!/usr/bin/env python3
"""Conan recipe — xfsprogs 7.2.0 (Autotools, HarmonyOS PC).

HarmonyOS adaptation notes (full log in notes.md):
- ``--enable-gettext=no``: the HarmonyOS toolchain has no msgmerge and the
  published gettext package provides libintl only; NLS is disabled.
- xfsprogs' make rules honor CFLAGS/CXXFLAGS for include paths (its plain
  ``%.o`` and ``-MM`` rules do not use CPPFLAGS), so dependency include
  directories are forwarded to both.
- The liburcu/libuuid packages ship libtool ``.la`` stubs whose libdir is
  ``//lib`` and whose dependency_libs point at non-existent paths; dependency
  archives are staged into a private directory without the ``.la`` files.
- Only ``-lurcu`` is exposed to configure's link tests: injecting ``-luuid``
  would make ``AC_CHECK_FUNCS(uuid_compare)`` succeed and leave ``LIBUUID``
  empty in include/builddefs (tools would then link without -luuid).
- ``INSTALL_USER``/``INSTALL_GROUP`` are derived from the filesystem because
  id(1) is not available on the device and xfsprogs' install-sh needs numeric
  owner/group arguments.
- The profile [buildenv] sets ``CONFIG_SHELL``/``SHELL`` to hnp bash 5.3.0,
  which cannot getcwd() when PWD is absent/stale on this device; a trailing
  env script restores ``/bin/sh`` (mksh) for this package.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XfsprogsConan(ConanFile):
    name = "xfsprogs"
    version = "7.2.0"
    package_type = "application"
    description = "XFS filesystem utilities (mkfs.xfs, xfs_repair, xfs_db, xfs_io, ...)"
    license = "GPL-2.0-only AND LGPL-2.1-only"
    homepage = "https://xfs.wiki.kernel.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("inih/r58")
        self.requires("libuuid/2.40.4")
        self.requires("liburcu/0.15.6")
        self.requires("libblkid/2.42.2")

    def layout(self):
        basic_layout(self)
        # xfsprogs' configure does `. ./VERSION` and its Makefiles assume an
        # in-tree build; build in the source folder like upstream/distros do.
        self.folders.build = "."
        self.folders.generators = "conan"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # HarmonyOS has no msgmerge; NLS off keeps the build reproducible.
        tc.configure_args.append("--enable-gettext=no")

        # Stage dependency include dirs (-> CFLAGS/CXXFLAGS) and archives
        # (-> private lib dir without broken libtool .la stubs).
        dep_libs_dir = os.path.join(self.build_folder, "dep-libs")
        os.makedirs(dep_libs_dir, exist_ok=True)
        for dep in self.dependencies.values():
            cppinfo = dep.cpp_info.aggregated_components()
            for inc in cppinfo.includedirs:
                tc.extra_cflags.append("-I" + inc)
                tc.extra_cxxflags.append("-I" + inc)
            for libdir in cppinfo.libdirs:
                if not os.path.isdir(libdir):
                    continue
                for name in os.listdir(libdir):
                    if name.endswith(".la"):
                        continue
                    src = os.path.join(libdir, name)
                    dst = os.path.join(dep_libs_dir, name)
                    if os.path.isfile(src) and not os.path.exists(dst):
                        shutil.copy2(src, dst)
        tc.extra_ldflags.append("-L" + dep_libs_dir)

        env = tc.environment()
        # Only -lurcu for configure's link tests (AC_HAVE_LIBURCU_ATOMIC64);
        # -luuid/-linih/-lblkid are resolved by xfsprogs' own AC_CHECK macros.
        env.append("LIBS", ["-lurcu"])
        # install-sh needs numeric owner/group; id(1) is missing on device.
        st = os.stat(self.source_folder)
        env.define("INSTALL_USER", str(st.st_uid))
        env.define("INSTALL_GROUP", str(st.st_gid))
        tc.generate(env)

        # HarmonyOS device quirk: the profile [buildenv] points CONFIG_SHELL and
        # SHELL at hnp bash 5.3.0, which cannot getcwd() when PWD is absent or
        # stale ("configure: error: working directory cannot be determined").
        # Register a trailing env script so /bin/sh (mksh) is used for this
        # package (autoconf would otherwise re-exec configure into $CONFIG_SHELL).
        VirtualBuildEnv(self).generate()
        shell_env = Environment()
        shell_env.define("CONFIG_SHELL", "/bin/sh")
        shell_env.define("SHELL", "/bin/sh")
        shell_env.vars(self).save_script("conanbuild_xfsprogs_shellfix")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI tool package: tools are installed into bin/ (the Autotools
        # toolchain maps sbindir to ${prefix}/bin).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
