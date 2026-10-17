#!/usr/bin/env python3
# CPU (Change Password Utility) 1.4.3 -- HarmonyOS PC (OHOS / aarch64) port.
#
# Upstream is an LDAP-centric account administration tool: the `cpu' driver
# program dlopen()s a per-backend method plugin (libcpu_<method>.so).  The
# shipped `ldap' plugin is the functional back end and is what this recipe
# builds; the `passwd' plugin of this release is an upstream stub
# ("Do not use me. I don't work!") and is therefore not enabled.
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, chmod, copy,
                               export_conandata_patches, get, mkdir, rm, rmdir)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class CpuConan(ConanFile):
    name = "cpu"
    version = "1.4.3"
    description = ("CPU - a Change Password Utility: LDAP-backed passwd, shadow "
                   "and group administration tool")
    license = "GPL-2.0-or-later"
    url = "https://cpu.sourceforge.net/"
    homepage = "https://cpu.sourceforge.net/"
    topics = ("ldap", "password", "user-management", "autotools", "ohos")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # openldap 2.6.7 is published on the OHPC binary remote (ohpcd); its
        # availability was confirmed with the Conan client before this recipe
        # was written (see reports/build-report.md).
        self.requires("openldap/2.6.7")

    def validate(self):
        # R32: settings.os must be tested with `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cpu is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # E490: the autotools helper scripts have to be executable; some
        # HarmonyOS PC adaptation paths preserve source content without the
        # mode bits, and `configure' is invoked directly by the build.
        for script in ("configure", "config.guess", "config.sub", "install-sh", "missing"):
            path = os.path.join(self.source_folder, script)
            if os.path.exists(path):
                chmod(self, path, 0o755)

    def generate(self):
        ldap = self.dependencies["openldap"]

        # Private, .la-free prefix built from *real* library files.
        # The OpenLDAP binary package ships libtool archives whose libdir and
        # dependency_libs are non-relocatable (libdir='//lib', so the recorded
        # liblber reference resolves to the missing //lib/liblber.la).  Libtool
        # gives a .la precedence over a sibling .so, and it resolves a symlinked
        # .so back to the package the object was installed from -- where that
        # .la sits -- so a private prefix holding symlinks still ends up opening
        # the broken archive at the first shared link (knowledge E236/E522).
        # Copying the versioned shared object into the build folder and pointing
        # the unversioned/`soname' names at it with relative links leaves
        # libtool a .so with no .la beside it, so the link records the SONAME
        # (DT_NEEDED libldap.so.2) instead of an archive.  Nothing outside the
        # build folder is written and no shared /usr/local tree is touched (R49).
        priv = os.path.join(self.build_folder, "prefix")
        rmdir(self, priv)
        mkdir(self, os.path.join(priv, "lib"))
        os.symlink(os.path.join(ldap.package_folder, "include"),
                   os.path.join(priv, "include"))
        libdir = os.path.join(ldap.package_folder, "lib")
        for lib in ("libldap", "liblber"):
            versioned = sorted(
                name for name in os.listdir(libdir)
                if name.startswith(f"{lib}.so.")
                and len(name.split(".so.")[1].split(".")) == 3
            )[-1]
            copy(self, versioned, src=libdir, dst=os.path.join(priv, "lib"))
            soname = f"{lib}.so.{versioned.split('.so.')[1].split('.')[0]}"
            for alias in (f"{lib}.so", soname):
                os.symlink(versioned, os.path.join(priv, "lib", alias))
        # Libtool follows a .la whenever it can see one and then insists on the
        # directories recorded inside it, so the shadow also needs archives of
        # its own: every archive of the dependency is copied with each recorded
        # directory rewritten to the shadow.  A lookup that reaches them then
        # resolves its closure inside the build folder instead of asking for a
        # path that does not exist (E522: rewrite the whole dependency closure).
        for name in sorted(os.listdir(libdir)):
            if not name.endswith(".la"):
                continue
            with open(os.path.join(libdir, name), "r") as handle:
                text = handle.read()
            old_libdir = None
            for line in text.splitlines():
                if line.startswith("libdir="):
                    old_libdir = line.split("=", 1)[1].strip().strip("'")
                    break
            if old_libdir and old_libdir != os.path.join(priv, "lib"):
                text = text.replace(old_libdir, os.path.join(priv, "lib"))
            with open(os.path.join(priv, "lib", name), "w") as handle:
                handle.write(text)

        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--with-ldap={priv}")
        # Upstream helper scripts are programs; a checkout that lost their mode
        # (export_sources, archive extraction) would break ./configure (E490).
        for script in ("configure", "config.guess", "config.sub", "install-sh",
                       "missing", "ltmain.sh", "compile", "depcomp"):
            path = os.path.join(self.source_folder, script)
            if os.path.exists(path):
                chmod(self, path, 0o755)
        # The upstream Makefiles hard-code the in-tree relative include path
        # (-I../../src/include) which does not resolve inside conan's separate
        # build folder, so point the compiler at the source tree explicitly.
        tc.extra_cflags.append(f"-I{os.path.join(self.source_folder, 'src', 'include')}")
        # OpenLDAP >= 2.4 only declares the (still exported) ldap_get_values()
        # family inside `#if LDAP_DEPRECATED`, so the macro has to be a non-zero
        # value on the compile line; without the declaration the callers fall
        # back to an implicit int return and truncate the pointer on 64 bit.
        # It goes through CFLAGS because the generated Makefiles own CPPFLAGS.
        tc.extra_cflags.append("-DLDAP_DEPRECATED=1")
        # AC_FUNC_MALLOC/AC_FUNC_REALLOC run a *runtime* probe that fails on the
        # OHOS libc (malloc(0) legally returns NULL), which would make config.h
        # define malloc->rpl_malloc/realloc->rpl_realloc; those fallback symbols
        # have no prototype in scope, so the implicit int return truncates the
        # pointer on aarch64. Override the probes with autoconf's own cache vars.
        tc.configure_args.append("ac_cv_func_malloc_0_nonnull=yes")
        tc.configure_args.append("ac_cv_func_realloc_0_nonnull=yes")
        env = tc.environment()
        # OpenLDAP >= 2.4 only declares the (still exported) ldap_get_values()
        # family when LDAP_DEPRECATED is requested; without the declaration the
        # callers fall back to an implicit int return and truncate the pointer
        # on 64 bit.  CPPFLAGS/LDFLAGS are *defined* rather than appended: an
        # inherited -I/-L pointing at a shared /usr/local tree would otherwise
        # come first in the search order, and the libtool archives left there by
        # earlier SYS_PREFIX-style builds are non-relocatable (libdir='//lib',
        # dependency_libs='//lib/liblber.la'), so libtool picks the .la over the
        # private .so and the link dies.  With only the private prefix on the
        # search path the .so is used and the SONAME is recorded (E236/E522/E544).
        env.define("CPPFLAGS", f"-DLDAP_DEPRECATED=1 -I{os.path.join(priv, 'include')}")
        env.define("LDFLAGS", f"-L{os.path.join(priv, 'lib')}")
        # The OHOS libc returns NULL for malloc(0) (POSIX allows it), so
        # AC_FUNC_MALLOC concludes "not GNU libc compatible" and defines
        # malloc=rpl_malloc -- a symbol this package never implements.  Nothing
        # here relies on malloc(0) != NULL, so the autoconf cache override is
        # used instead of patching the sources.
        env.define("ac_cv_func_malloc_0_nonnull", "yes")
        env.define("ac_cv_func_realloc_0_nonnull", "yes")
        tc.generate()

        # The OHOS loader has no default search path for conan-cached shared
        # libraries: configure's conftest programs and the freshly linked
        # plugins need LD_LIBRARY_PATH to resolve libldap.so.2 / liblber.so.2.
        runpath = Environment()
        runpath.append("LD_LIBRARY_PATH", os.path.join(priv, "lib"))
        for libdir in ldap.cpp_info.libdirs:
            runpath.append("LD_LIBRARY_PATH", libdir)
        runpath.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job -- parallel make hits the HMDFS jobserver fifo EPERM (E074)
        autotools.make(args=["-j1"])
        # Upstream 1.4.3 has no automated test suite: the top-level check target
        # exists but carries no TESTS entries, so this is a no-op.  It is kept so
        # that CI runs and records upstream's own check target.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        # libtool archives carry build-time paths and are useless to consumers
        # (knowledge E236); the runtime objects are the .so files.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = ["lib"]
        # The helper library the driver and its method plugins are linked
        # against.  The plugins themselves are dlopen() modules, not link-time
        # libraries, so they are deliberately not listed.
        self.cpp_info.libs = ["cputil"]
