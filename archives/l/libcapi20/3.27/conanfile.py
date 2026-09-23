#!/usr/bin/env python3
"""Conan recipe for libcapi20 3.27 (autotools) — CAPI 2.0 user space library.

Upstream: https://github.com/leggewie-DM/libcapi20
The library implements the CAPI 2.0 interface on top of loadable driver
modules (fritzbox / rcapi).  This recipe targets the HarmonyOS PC (aarch64)
toolchain and adds the portability fixes required by that platform.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libcapi20Conan(ConanFile):
    name = "libcapi20"
    version = "3.27"
    description = ("libcapi20 - user space implementation of the CAPI 2.0 "
                   "interface (ISDN / telephony), with loadable driver modules")
    license = "GPL-2.0-only"
    homepage = "https://github.com/leggewie-DM/libcapi20"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # The capi modules shipped by upstream are libtool "-module" plugins and can
    # only be linked as shared objects (a --disable-shared build dies with
    # "libtool: can not build a shared library"), so a shared build is the
    # meaningful default of this package.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            # Shared support stays enabled because of the plugin modules (see the
            # options comment); the static archive is the linkable artifact here.
            tc.configure_args.append("--enable-static")
        # The AC_COMPUTE_INT probe in configure.ac includes "capi_mod.h" from the
        # source tree, which is not on the include path of a separate build dir.
        tc.extra_cflags.append("-I" + self.source_folder)
        # Upstream config.guess (2009) cannot recognize the OHOS triplet.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # configure must be executed by bash: the OHOS /bin/sh picks its own
        # `print` builtin for AS_ECHO and libtool's ECHO, but every script
        # generated afterwards (config.status, libtool) is re-executed with the
        # interpreter recorded in CONFIG_SHELL, which would not know `print`.
        env = tc.environment()
        env.define("CONFIG_SHELL", shutil.which("bash") or "/bin/bash")
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # configure itself must run under bash, not under the /bin/sh interpreter
        # of its shebang: the OHOS /bin/sh has a `print` builtin, so AS_ECHO and
        # libtool's ECHO get detected as `print -r`, while config.status and the
        # generated libtool script are re-executed with bash, which has no
        # `print` builtin (config.status: "print: command not found", libtool:
        # "syntax error near unexpected token `}'"). Running configure with bash
        # makes both sides agree on printf.
        bash = shutil.which("bash") or "/bin/bash"
        self.run('"{}" "{}/configure" {}'.format(bash, self.source_folder,
                                                 autotools._configure_args))
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Upstream installs libcapi20.so.<version> (link with -lcapi20)
        self.cpp_info.libs = ["capi20"]
        # The driver plugins live in <prefix>/lib/capi and are dlopen()-ed at
        # run time; the compile time LIBDIR is not valid for a Conan package, so
        # point the loading code at the packaged directory (patch 0003).
        self.runenv_info.define_path(
            "CAPI20_MODULE_DIR", os.path.join(self.package_folder, "lib", "capi"))
