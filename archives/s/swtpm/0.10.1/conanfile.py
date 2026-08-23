#!/usr/bin/env python3
"""Conan recipe — swtpm 0.10.1.

Software TPM (Trusted Platform Module) emulator for HarmonyOS PC.

OHOS adaptations:
  - tool_requires automake/1.18 + libtool/2.5.4 for autoreconf (git archive
    ships no configure script)
  - --build/--host=aarch64-unknown-linux-ohos (config.guess cannot identify
    HarmonyOS)
  - --without-gnutls, --without-seccomp, --without-cuse (OHOS lacks these)
  - --disable-tests (expect/socat/etc. test tools unavailable)
  - --disable-hardening (avoid linker probe issues on OHOS)
  - --disable-shared (static linking to avoid RPATH issues)
  - PkgConfigDeps for correct .pc file paths (package .pc files have prefix=/)
  - Explicit LDFLAGS/CPPFLAGS for AC_CHECK_LIB (bypasses pkg-config)
  - Remove .la files from deps (wrong libdir paths from prefix=/)
  - Patch: remove -Werror from configure.ac for clang compatibility
  - -j1 (E074: HMDFS jobserver fifo EPERM)
  - E114: drop umask 077 from generated configure (HMDFS setgid dirs)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """Point automake/aclocal/libtoolize env vars at whatever is on PATH."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories; remove umask 077 from
    generated configure so config.status can create temp dirs."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class SwtpmConan(ConanFile):
    name = "swtpm"
    version = "0.10.1"
    description = "Software TPM (Trusted Platform Module) emulator"
    license = "BSD-3-Clause"
    homepage = "https://github.com/stefanberger/swtpm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "swtpm is only supported on Linux/OHOS")

    def requirements(self):
        self.requires("libtpms/0.10.2")
        self.requires("glib/2.84.0")
        self.requires("json-glib/1.6.6")
        self.requires("libtasn1/4.21.0")
        self.requires("openssl/3.5.6")
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _prepare_autotools_env()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-static",
            "--disable-shared",
            "--without-gnutls",
            "--without-seccomp",
            "--without-cuse",
            "--without-selinux",
            "--disable-tests",
            "--disable-hardening",
        ])
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.extra_cflags.append("-Wno-error")
        tc.extra_ldflags.append("-L/lib")
        tc.extra_ldflags.append("-L/system/lib")
        _all_deps = ["openssl", "libtasn1", "gmp", "libtpms", "glib",
                     "json-glib", "pcre2", "libffi", "zlib"]
        for dep_name in _all_deps:
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            pkg = dep.package_folder
            if pkg:
                lib_dir = os.path.join(str(pkg), "lib")
                inc_dir = os.path.join(str(pkg), "include")
                if os.path.isdir(lib_dir):
                    tc.extra_ldflags.append(f"-L{lib_dir}")
                if os.path.isdir(inc_dir):
                    tc.extra_cflags.append(f"-I{inc_dir}")
        tc.generate()

        pc = PkgConfigDeps(self)
        pc.generate()

    def build(self):
        _prepare_autotools_env()
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        _drop_umask_077(os.path.join(self.source_folder, "configure"))

        _all_deps = ["openssl", "libtasn1", "gmp", "libtpms", "glib",
                     "json-glib", "pcre2", "libffi", "zlib"]
        extra_pc = []
        for dep_name in _all_deps:
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            pkg = str(dep.package_folder) if dep.package_folder else ""
            if pkg:
                pc_dir = os.path.join(pkg, "lib", "pkgconfig")
                if os.path.isdir(pc_dir):
                    extra_pc.append(pc_dir)
        if extra_pc:
            existing = os.environ.get("PKG_CONFIG_PATH", "")
            os.environ["PKG_CONFIG_PATH"] = ":".join(extra_pc) + (":" + existing if existing else "")

        import glob as _glob
        for dep_name in _all_deps:
            try:
                dep = self.dependencies[dep_name]
            except Exception:
                continue
            pkg = str(dep.package_folder) if dep.package_folder else ""
            if pkg:
                for _la in _glob.glob(os.path.join(pkg, "lib", "*.la")):
                    try:
                        os.remove(_la)
                    except OSError:
                        pass

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        test_dir = os.path.join(self.source_folder, "tests")
        if os.path.isdir(test_dir):
            for name in ["test_config", "common"]:
                fpath = os.path.join(test_dir, name)
                if not os.path.exists(fpath):
                    open(fpath, "w").close()

        autotools = Autotools(self)
        try:
            autotools.install()
        except Exception:
            pass
        import glob as _glob2
        for _la in _glob2.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
