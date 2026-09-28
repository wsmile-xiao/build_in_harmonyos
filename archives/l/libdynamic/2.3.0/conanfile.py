#!/usr/bin/env python3
"""Conan recipe — libdynamic 2.3.0 (Autotools: configure + make).

The upstream git archive ships no generated `configure`, so build()
bootstraps with `autoreconf -fi` (abiword-plugin pattern).  The OHOS
build host lacks automake/aclocal/libtoolize on PATH, so they are pulled
in as tool_requires (same approach as abiword-plugin-clarisworks /
argp-standalone).

Environment fixes applied in build() (generated files, cannot be patches):
  - E007: config.guess gains a HarmonyOS branch (aarch64-unknown-linux-ohos)
  - E114: drop `umask 077` from configure/config.status temp-dir creation
          (HMDFS: drwx--S--- temp dirs are not writable even by owner)
  - libtool: init `echo="$ECHO"` and use `$oldlib` (mixed 1.5.22/2.4.7
          installs leave `$echo`/`$tool_oldlib` undefined)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that do not exist in this environment.  Point the
    env vars at whatever is actually on PATH."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` so configure/config.status can create temp dirs."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir -m 0777 "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _patch_config_guess(conanfile, path):
    """E007: add a HarmonyOS branch so config.guess emits
    aarch64-unknown-linux-ohos without needing the C probe."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    if "HarmonyOS" in data:
        return
    marker = "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in"
    branch = marker + """
    *:HarmonyOS:*:*)
	case "$UNAME_MACHINE" in
	    aarch64|arm64) MACHINE=aarch64 ;;
	    armv7*|armv8*) MACHINE=arm ;;
	    x86_64|amd64)  MACHINE=x86_64 ;;
	    i?86)         MACHINE=i686 ;;
	    *)            MACHINE="$UNAME_MACHINE" ;;
	esac
	echo ${MACHINE}-unknown-linux-ohos
	exit ;;

"""
    data = data.replace(marker, branch, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _fix_libtool(conanfile, path):
    """Init `$echo` and use `$oldlib` (mixed libtool install leaves
    `$echo`/`$tool_oldlib` undefined, which breaks arg parsing/archive)."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace('ECHO="print -r --"\n',
                        'ECHO="print -r --"\necho="$ECHO"\n', 1)
    data = data.replace("$RANLIB $tool_oldlib", "$RANLIB $oldlib")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class LibdynamicConan(ConanFile):
    name = "libdynamic"
    version = "2.3.0"
    description = "C library for various dynamic container types (libdynamic 2.3.0)"
    license = "MIT"
    homepage = "https://github.com/fredrikwidlund/libdynamic"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The git archive ships no `configure`, so build() must run
        # `autoreconf -fi` to bootstrap.  The build host (CI sandbox /
        # minimal OHOS image) lacks automake/aclocal/libtoolize, so pull
        # them in as tool_requires (abiword-plugin-clarisworks pattern).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libdynamic is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload archive URLs end with the tag name (no .tar.gz suffix),
        # so conan cannot infer the archive format; pass an explicit
        # filename with the proper extension.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="libdynamic-2.3.0.tar.gz")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        _prepare_autotools_env()
        apply_conandata_patches(self)
        # Bootstrap: the git archive ships no configure.
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # Generated-file fixes (cannot be source patches).
        _patch_config_guess(self, os.path.join(self.source_folder, "autotools", "config.guess"))
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        cs_path = os.path.join(self.build_folder, "config.status")
        mk_path = os.path.join(self.build_folder, "Makefile")
        _drop_umask_077(self, cs_path)
        _fix_libtool(self, os.path.join(self.build_folder, "libtool"))
        if os.path.exists(cs_path) and not os.path.exists(mk_path):
            _drop_umask_077(self, cs_path)
            self.run("cd " + self.build_folder + " && bash config.status")
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["dynamic"]
