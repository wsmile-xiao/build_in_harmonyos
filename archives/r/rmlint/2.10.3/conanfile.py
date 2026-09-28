#!/usr/bin/env python3
"""Conan recipe for rmlint 2.10.3 - redundant file finder (SCons build).

rmlint scans directory trees and reports duplicate files, empty folders,
broken symlinks and other disc waste. Upstream: https://github.com/sahib/rmlint

Adaptation notes for HarmonyOS PC (aarch64, OHOS SDK clang 15):

* Build system is SCons (src/SConscript + lib/SConscript + docs/po/gui).
  Neither the OHOS device image nor the CI worker ships a `scons` binary nor
  the SCons python module, and SCons is *not* published in the ohpcd Conan
  registry, so it cannot be a tool_requires. The repo convention for SCons
  projects (merged recipes g/gpsd/3.26, d/dxx-rebirth/0.6, v/vixl/5.1.0) is to
  pip-install SCons into an isolated prefix *inside* the Conan build folder and
  invoke it as `python3 -m SCons` through PYTHONPATH. This recipe follows that
  convention; nothing is installed into the user or system Python
  environment, so the build stays reproducible on a clean worker.

* Hard dependency closure is a single library: glib-2.0 >= 2.64
  (SConstruct: conf.check_pkg('glib-2.0 >= 2.64', 'HAVE_GLIB', required=True)).
  libyaml is *not* used by 2.10.3 (rmlint parses its own config format).

* Everything else upstream probes is optional and turned off for this
  adaptation (path A, minimal viable build):
      --without-blkid    libblkid is not published in ohpcd
      --without-json-glib json-glib-1.0 only powers *reading* .json caches
      --without-libelf   <libelf.h> absent from the OHOS sysroot; only the
                         "non-stripped binary" finder type needs it
      --without-gettext  keeps po/ from requiring msgfmt (user-local tool)
      --without-gui      the optional python GTK frontend is not packaged
      --without-compile-glib-schemas  no dconf/gsettings schemas are shipped
  gio-unix-2.0 is probed with required=False; PkgConfigDeps does not emit a
  gio-unix-2.0.pc for the Conan glib package, so HAVE_GIO_UNIX stays 0. That
  only disables the "is this a non-rotational disk" optimisation, which also
  needs libblkid - already off above.

* xattr and fiemap are kept enabled: the OHOS sysroot does provide
  sys/xattr.h, linux/fs.h and linux/fiemap.h, and HMDFS accepts user.* xattrs
  (measured: setfattr/getfattr round-trip on a regular file succeeds).

* Upstream `scons install` is deliberately not used: docs/SConscript registers
  the sphinx-generated man page as a *default* target and as an `install`
  dependency, and neither sphinx nor rst2man exist on the platform. `package()`
  copies the built binary directly (same approach as merged recipes
  a/abr2gbr/1.0.2 and v/vamps/0.99.2).
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class RmlintConan(ConanFile):
    name = "rmlint"
    version = "2.10.3"
    description = (
        "Tool to find redundant files, empty folders, broken symlinks and "
        "other disc waste, with checksum based and size based duplicate "
        "detection plus scriptable dedup modes."
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/sahib/rmlint"
    url = "https://github.com/sahib/rmlint"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # SCons is a build-time helper only; see the module docstring for why it
    # is bootstrapped into an isolated prefix instead of tool_requires.
    _scons_version = "4.10.1"

    # Upstream AddOption() switches we pass to turn optional faces off.
    _disabled_features = (
        "--without-blkid",
        "--without-json-glib",
        "--without-libelf",
        "--without-gettext",
        "--without-gui",
        "--without-compile-glib-schemas",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The only mandatory upstream dependency (SConstruct, required=True).
        self.requires("glib/2.84.0.1")

    def build_requirements(self):
        # rmlint's SConstruct drives every dependency through pkg-config.
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        # conandata.yml carries an explicit filename because the codeload URL
        # has no file extension (Conan would otherwise sniff it as a ZIP and
        # strip_root would fail).
        get(self, **self.conan_data["sources"], strip_root=True)

    # -- SCons bootstrap (repo convention: gpsd/dxx-rebirth/vixl) -----------

    def _scons_prefix(self):
        return os.path.join(self.build_folder, "_scons_env")

    def _install_scons(self):
        prefix = self._scons_prefix()
        os.makedirs(prefix, exist_ok=True)
        self.run(
            "python3 -m pip install --quiet --no-input --target={} "
            "scons=={}".format(prefix, self._scons_version),
            env="build",
        )

    def _patch_scons_shell(self):
        # HarmonyOS has no /bin/sh; SCons' posix platform hardcodes SHELL='sh'.
        # Patched here (once, in generate) rather than in build() per R33.
        # No-op if the upstream string is already absent.
        prefix = self._scons_prefix()
        script = (
            "import SCons.Platform.posix as m;"
            "f=m.__file__;"
            "s=open(f).read();"
            "old=chr(39)+'sh'+chr(39);"
            "new=chr(39)+'/system/bin/sh'+chr(39);"
            "open(f,'w').write(s.replace(old,new) if old in s else s);"
            "print('scons-shell-patched' if old in s else 'scons-shell-noop')"
        )
        self.run(
            'PYTHONPATH={} python3 -c "{}"'.format(prefix, script),
            env="build",
        )

    def _tool(self, key, fallback):
        # R33: compilers come from the Conan profile conf, never bare shell vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get(key) or fallback

    def _ensure_gio_unix_pc(self):
        """Derive gio-unix-2.0.pc from the generated gio-2.0.pc.

        PkgConfigDeps emits glib-2.0/gio-2.0/gobject/gmodule/gthread .pc for the
        Conan glib package but has no "gio-unix-2.0" component, so upstream's
        conf.check_pkg('gio-unix-2.0', ..., required=False) would set
        HAVE_GIO_UNIX=0. rmlint 2.10.3 cannot build in that state:
        lib/utilities.c guards only the *include* of <gio/gunixmounts.h> with
        #if HAVE_GIO_UNIX (line 56) while rm_util_same_device() (line ~1137)
        calls g_unix_mounts_get()/g_unix_mount_get_mount_path()/
        g_unix_mount_free() unconditionally -> the symbols are simply undeclared.
        The header and the exported symbols do exist in the published glib
        package (include/gio-unix-2.0/gio/gunixmounts.h and nm -D libgio-2.0.so),
        so the fix is to make the module discoverable instead of patching
        upstream: gio-2.0.pc already carries every needed -I (including
        ${includedir}/gio-unix-2.0), -L and -l flag, so a copy with its
        Name/Description rewritten is a correct gio-unix-2.0.pc.
        """
        gens = self.generators_folder
        target = os.path.join(gens, "gio-unix-2.0.pc")
        if os.path.isfile(target):
            return
        base = os.path.join(gens, "gio-2.0.pc")
        if not os.path.isfile(base):
            self.output.warning(
                "gio-2.0.pc not generated; gio-unix-2.0 probe will fail"
            )
            return
        with open(base, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        out = []
        for line in lines:
            if line.startswith("Name:"):
                out.append("Name: GIO unix specific APIs")
            elif line.startswith("Description:"):
                out.append("Description: unix specific headers for glib I/O library")
            else:
                out.append(line)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("\n".join(out) + "\n")
        self.output.info("derived gio-unix-2.0.pc from gio-2.0.pc")

    def generate(self):
        self._install_scons()
        self._patch_scons_shell()

        # glib-2.0.pc for the SConstruct pkg-config probes.
        PkgConfigDeps(self).generate()
        self._ensure_gio_unix_pc()

        # PkgConfigDeps writes the .pc files into generators_folder but the
        # conanbuild environment does not add it to PKG_CONFIG_PATH; append it
        # *before* VirtualBuildEnv.generate() or the injection is lost (CI
        # lesson recorded in archives/a/abiword-plugin-docbook/3.0.8).
        # buildenv_info is a ConanFile attribute, not a VirtualBuildEnv one.
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)
        VirtualBuildEnv(self).generate()

        # Expose the isolated SCons to build()/test hooks.
        env = Environment()
        env.define_path("PYTHONPATH", self._scons_prefix())
        env.vars(self).save_script("scons_env")

    def _scons_command(self, extra=None):
        cc = self._tool("c", "clang")
        # PYTHONPATH is given inline rather than relying on the aggregated
        # conanbuild env: the isolated SCons prefix must be importable by the
        # exact interpreter that resolves `python3` here (G2 measured
        # "No module named SCons" when it was only carried by save_script).
        prefix = self._scons_prefix()
        # PKG_CONFIG_PATH likewise has to be inline: G2 measured
        # "Checking for glib-2.0 >= 2.64... Error: not found" even though
        # PkgConfigDeps had written <generators_folder>/glib-2.0.pc, because the
        # aggregated conanbuild.sh does not carry buildenv_info paths on this
        # Conan/platform combination.
        args = [
            "PYTHONPATH={}".format(prefix),
            "PKG_CONFIG_PATH={}".format(self.generators_folder),
            "python3", "-m", "SCons",
            "-j1",
            "CC={}".format(cc),
            "AR={}".format(self._tool("ar", "ar")),
            "RANLIB={}".format(self._tool("ranlib", "ranlib")),
        ]
        args.extend(self._disabled_features)
        if extra:
            args.extend(extra)
        return " ".join(args)

    def build(self):
        apply_conandata_patches(self)
        # Default targets are librmlint (lib/SConscript), the rmlint program
        # (src/SConscript) and the sphinx man page (docs/SConscript, which
        # self-skips when no sphinx binary is found).
        self.run(self._scons_command(), env="build", cwd=self.source_folder)

    def package(self):
        pkg = self.package_folder
        src = self.source_folder
        binary = os.path.join(src, "rmlint")
        if not os.path.isfile(binary):
            raise ConanException(
                "rmlint binary was not produced at %s" % binary
            )
        copy(self, "rmlint", src=src, dst=os.path.join(pkg, "bin"), keep_path=False)
        os.chmod(os.path.join(pkg, "bin", "rmlint"), 0o755)

        copy(self, "COPYING", src=src, dst=os.path.join(pkg, "licenses"), keep_path=False)
        copy(self, "README.rst", src=src, dst=os.path.join(pkg, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
