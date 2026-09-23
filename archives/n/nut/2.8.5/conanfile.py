#!/usr/bin/env python3
"""Conan recipe for Network UPS Tools (NUT) 2.8.5.

The first HarmonyOS package targets the software-only dummy-ups driver and
the core NUT clients/daemons. Hardware drivers and optional integrations are
disabled so their separate dependency packages are not pulled into this PR.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NutConan(ConanFile):
    name = "nut"
    version = "2.8.5"
    description = "Network UPS Tools for monitoring and managing UPS devices"
    license = "GPL-2.0-or-later"
    homepage = "https://networkupstools.org/"
    url = "https://github.com/networkupstools/nut"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported; use Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _configure_args(self):
        return [
            "--prefix=/",
            "--exec-prefix=/",
            "--sysconfdir=/etc",
            "--with-confdir=/etc/nut",
            "--with-confdir-examples=/share/nut",
            "--with-statepath=/var/lib/nut",
            "--with-altpidpath=/var/run/nut",
            "--with-pidpath=/var/run/nut",
            "--with-powerdownflag=/var/run/nut/killpower",
            "--with-drvpath=/libexec/nut",
            "--with-drivers=dummy-ups",
            "--with-serial=no",
            "--with-usb=no",
            "--with-snmp=no",
            "--with-neon=no",
            "--with-powerman=no",
            "--with-modbus=no",
            "--with-gpio=no",
            "--with-avahi=no",
            "--with-ipmi=no",
            "--with-freeipmi=no",
            "--with-linux_i2c=no",
            "--with-macosx_ups=no",
            "--with-upower=no",
            "--with-pynut=no",
            "--with-nut_monitor=no",
            "--with-nut-scanner=no",
            "--with-cgi=no",
            "--with-nutconf=no",
            "--with-dev-libnutconf=no",
            "--with-wrap=no",
            "--with-libltdl=no",
            "--with-ssl=no",
            "--with-nss=no",
            "--with-openssl=no",
            "--with-doc=no",
            "--with-udev-dir=no",
            "--with-hotplug-dir=no",
            "--with-devd-dir=no",
            "--with-freebsd-quirks-dir=no",
            "--with-systemdsystemunitdir=no",
            "--with-systemdsystempresetdir=no",
            "--with-systemdshutdowndir=no",
            "--with-systemdtmpfilesdir=no",
            "--with-systemdsysusersdir=no",
            "--with-dev=yes",
            "--enable-static",
            "--disable-shared",
            "--enable-shared-private-libs=no",
            "--enable-cppunit=no",
            "--disable-check-NIT",
        ]

    def generate(self):
        tc = AutotoolsToolchain(self)
        # HarmonyOS is detected by the patched config.guess. Do not bypass
        # that probe with a synthetic --build/--host pair.
        tc.configure_args = [
            arg
            for arg in tc.configure_args
            if not str(arg).startswith("--build=")
            and not str(arg).startswith("--host=")
        ]
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # E002/E011: HMDFS /tmp is read-only and config.status scratch
        # directories need 022 on linux-ohos. Keep scratch data in $HOME;
        # non-OHOS configure runs retain the upstream 077 mode.
        tmpdir = os.path.join(os.path.expanduser("~"), ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        # E165: configure and generated makefiles need the native device shell.
        if str(self.settings.os) == "OHOS":
            hnp_bin = "/data/service/hnp/bin"
            path = os.environ.get("PATH", "")
            if hnp_bin not in path.split(":"):
                os.environ["PATH"] = hnp_bin + (":" + path if path else "")
            os.environ.setdefault("CONFIG_SHELL", "/system/bin/sh")

        configure_args = [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
        ]
        configure_args.extend(self._configure_args())
        configure_path = os.path.join(self.source_folder, "configure")
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            configure_command = " ".join(
                ["/system/bin/sh", shlex.quote(configure_path)]
                + [shlex.quote(arg) for arg in configure_args]
            )
            self.run(
                "PATH=/data/service/hnp/bin:$PATH "
                "AR=/data/service/hnp/bin/llvm-ar "
                "RANLIB=/data/service/hnp/bin/llvm-ranlib "
                "CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
                + configure_command,
                cwd=self.build_folder,
                env="conanbuild",
            )
        else:
            autotools.configure()

        autotools.make(args=["-j1"])
        # Run the upstream non-NIT unit/regression checks in the build phase.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

        # Libtool archives embed the absolute /lib staging path and are not
        # useful to Conan consumers once the static library is packaged.
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for root, _, files in os.walk(libdir):
                for filename in files:
                    if filename.endswith(".la"):
                        os.remove(os.path.join(root, filename))

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin", "libexec/nut"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["upsclient"]
        self.cpp_info.set_property("cmake_file_name", "nut")
        self.cpp_info.set_property("pkg_config_name", "libupsclient")
