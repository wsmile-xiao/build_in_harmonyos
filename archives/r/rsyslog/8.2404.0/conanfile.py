#!/usr/bin/env python3
"""Conan recipe for rsyslog 8.2404.0 — Autotools (configure + make).

rsyslog is a high-performance syslog/log-processing daemon. The package
produces the rsyslogd binary (sbin/) plus dlopen-able output/input
modules (lib/rsyslog/*.so).

Conan dependencies (all published to the ohpcd registry):
- libestr/0.1.11, libfastjson/1.2609.0 — rsyslog core string/JSON libs
- libgcrypt/1.11.0 (+ transitive libgpg-error) — lmcry_gcry crypto module
- uuid/2.40.1 — uuid generation support (configure default=yes, fatal
  if missing)
- zlib/1.3.1.1 — gzip output support (configure default feature). The
  PIC-enabled static revision is required because rsyslog links zlib
  into shared modules (lib/rsyslog/lmzlibw.so); the plain zlib/1.3.1
  binary is non-PIC and fails with R_AARCH64 relocation errors.

OHOS platform notes:
- The build is native on OpenHarmony (uname -s = "HarmonyOS"); stock
  2018-vintage config.guess cannot guess the system type, hence patch
  0007/0008 add HarmonyOS/linux-ohos recognition (E007 pattern).
- OHOS musl libc provides neither pthread_cancel nor
  pthread_setcancelstate (verified: undeclared in sysroot pthread.h and
  undefined in libc.so), hence patches 0002-0006 guard those calls with
  HAVE_PTHREAD_CANCEL; the macro is intentionally left undefined so the
  guarded code paths are excluded and rsyslog uses its built-in
  non-cancel thread termination fallbacks.
- configure's temp-dir block uses "umask 077 && mktemp" which creates
  directories the build process cannot write to on HMDFS (E011); patch
  0001 relaxes the umask to 000 (approach proven by libestr/libfastjson
  recipes in CI).
- Dependency discovery: the conan packages for libestr/libfastjson ship
  .pc files recording prefix="/" (DESTDIR-style install) which emit
  unusable -I//include / -L//lib paths, and their cpp_info.libs names
  are wrong ("libestr"/"libfastjson" while the real linker names are
  "estr"/"fastjson"). rsyslog's configure honors the pkg.m4 environment
  override variables (LIBESTR_CFLAGS/LIBESTR_LIBS etc.), so generate()
  points every check directly at the conan package paths. libgcrypt is
  detected through the libgcrypt-config program (its shipped copy also
  reports prefix="/"), so generate() writes a small wrapper answering
  with the real conan paths and points LIBGCRYPT_CONFIG at it.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RsyslogConan(ConanFile):
    name = "rsyslog"
    version = "8.2404.0"
    description = "The rocket-fast system for log processing (rsyslogd)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.rsyslog.com/"
    url = "https://github.com/rsyslog/rsyslog"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libestr/0.1.11")
        self.requires("libfastjson/1.2609.0")
        self.requires("libgcrypt/1.11.0")
        self.requires("uuid/2.40.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # fmhttp requires libcurl which is not part of the dependency set
        tc.configure_args.append("--disable-fmhttp")

        env = tc.environment()

        # pkg-config based checks: override with real conan package paths
        # (shipped .pc files record prefix="/", see module docstring).
        # (dependency, pkg.m4 var prefix, real linker name, include subdir)
        pkg_overrides = [
            ("libestr", "LIBESTR", "estr", ""),
            ("libfastjson", "LIBFASTJSON", "fastjson", "libfastjson"),
            ("uuid", "LIBUUID", "uuid", ""),
            ("zlib", "ZLIB", "z", ""),
        ]
        for dep_name, var, lib, inc_sub in pkg_overrides:
            info = self.dependencies[dep_name].cpp_info.aggregated_components()
            incdir = os.path.join(info.includedirs[0], inc_sub) if inc_sub \
                else info.includedirs[0]
            env.define(f"{var}_CFLAGS", f"-I{incdir}")
            env.define(f"{var}_LIBS", f"-L{info.libdirs[0]} -l{lib}")

        # libgcrypt: configure runs `libgcrypt-config --libs --cflags`.
        # The copy shipped inside the conan package reports prefix="/"
        # (broken paths), so answer with a wrapper using the real paths.
        # Additionally the shipped libgcrypt.la carries libdir='//lib' and
        # a dependency_libs entry pointing at //lib/libgpg-error.la; when
        # rsyslog's libtool links the lmcry_gcry module it follows that
        # reference and dies. Provide a corrected shim .la (empty
        # dependency_libs: libgcrypt.so.20 already has DT_NEEDED
        # libgpg-error.so.0, and libgcry.c uses no gpg_* symbols directly)
        # in a dir placed first on the -L path; plain clang ignores .la
        # files and finds the real .so in the package libdir.
        gcry = self.dependencies["libgcrypt"].cpp_info.aggregated_components()
        gpg = self.dependencies["libgpg-error"].cpp_info.aggregated_components()
        shim_dir = os.path.join(self.build_folder, "la-shim")
        os.makedirs(shim_dir, exist_ok=True)
        gcry_pkg = self.dependencies["libgcrypt"].package_folder
        with open(os.path.join(gcry_pkg, "lib", "libgcrypt.la")) as f:
            la = f.read()
        la = re.sub(r"^libdir='.*'$", f"libdir='{gcry.libdirs[0]}'", la, flags=re.M)
        la = re.sub(r"^dependency_libs='.*'$", "dependency_libs=''", la, flags=re.M)
        with open(os.path.join(shim_dir, "libgcrypt.la"), "w") as f:
            f.write(la)

        wrapper = os.path.join(self.build_folder, "libgcrypt-config")
        with open(wrapper, "w") as f:
            f.write(
                "#!/bin/sh\n"
                "# Generated by the rsyslog conan recipe: the shipped\n"
                "# libgcrypt-config reports prefix=\"/\" (DESTDIR-style),\n"
                "# answer with the real conan package paths instead.\n"
                "out=\"\"\n"
                "for arg in \"$@\"; do\n"
                "  case \"$arg\" in\n"
                f"    --cflags) out=\"$out -I{gcry.includedirs[0]}"
                f" -I{gpg.includedirs[0]}\" ;;\n"
                f"    --libs) out=\"$out -L{shim_dir} -L{gcry.libdirs[0]}"
                " -lgcrypt\" ;;\n"
                "    --prefix) echo \"\" ;;\n"
                "    --version) echo \"1.11.0\" ;;\n"
                "  esac\n"
                "done\n"
                "echo \"$out\"\n"
            )
        os.chmod(wrapper, 0o755)
        env.define_path("LIBGCRYPT_CONFIG", wrapper)

        tc.generate(env)

    def build(self):
        # HMDFS workaround: default umask may create 640 files that
        # later steps (install scan, CI workers) cannot read
        if self.settings.os in ("Linux", "OHOS"):
            os.umask(0o022)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # HMDFS workaround: ensure installed files are world-readable
        if self.settings.os in ("Linux", "OHOS"):
            self.run(f'chmod -R a+r "{self.package_folder}"')
            self.run(f'find "{self.package_folder}" -type d -exec chmod a+rx {{}} \\;')

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = ["lib", "lib/rsyslog"]
        # rsyslogd locates its dlopen-able modules through RSYSLOG_MODDIR
        # (runtime/modules.c honors it, command line -M overrides it). The
        # compile-time default is the DESTDIR prefix "/" (conan convention),
        # so export the real package module dir for consumers. Computed at
        # install time — relocation-safe.
        self.runenv_info.define("RSYSLOG_MODDIR",
                                os.path.join(self.package_folder, "lib", "rsyslog"))
