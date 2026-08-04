#!/usr/bin/env python3
"""Conan recipe for libusb 1.0.27."""
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibusbConan(ConanFile):
    name = "libusb"
    version = "1.0.27"
    description = "USB device access library"
    license = "LGPL-2.1-or-later"
    homepage = "https://libusb.info/"
    url = "https://github.com/libusb/libusb"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        self._patch_sources()

    def _patch_sources(self):
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self,
            configure,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        )
        replace_in_file(
            self,
            configure,
            '(umask 077 && mkdir "$tmp")',
            '(umask 022 && mkdir "$tmp")',
        )

        netlink = os.path.join(self.source_folder, "libusb", "os", "linux_netlink.c")
        replace_in_file(
            self,
            netlink,
            "#include <sys/socket.h>\n#include <linux/netlink.h>",
            "#include <sys/socket.h>\n\n"
            "#define sockaddr_storage __linux_sockaddr_storage\n"
            "#include <linux/netlink.h>\n"
            "#undef sockaddr_storage\n"
        )

        usbfs = os.path.join(self.source_folder, "libusb", "os", "linux_usbfs.c")
        replace_in_file(
            self,
            usbfs,
            'atoms = sscanf(uts.release, "%d.%d.%d", &ver->major, &ver->minor, &ver->sublevel);\n'
            "\tif (atoms < 2) {\n"
            '\t\tusbi_err(ctx, "failed to parse uname release \'%s\'", uts.release);',
            'atoms = sscanf(uts.release, "%d.%d.%d", &ver->major, &ver->minor, &ver->sublevel);\n'
            "\tif (atoms < 2) {\n"
            '\t\tif (strstr(uts.release, "HongMeng") != NULL || strstr(uts.release, "OHOS") != NULL) {\n'
            "\t\t\tver->major = 5;\n"
            "\t\t\tver->minor = 10;\n"
            "\t\t\tver->sublevel = 0;\n"
            '\t\t\tusbi_dbg(ctx, "HongMeng/OHOS kernel detected (%s), assuming modern Linux kernel", uts.release);\n'
            "\t\t\treturn 0;\n"
            "\t\t}\n"
            '\t\tusbi_err(ctx, "failed to parse uname release \'%s\'", uts.release);',
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def _configure_args(self):
        args = [
            "--disable-dependency-tracking",
            "--disable-udev",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ]
        if str(self.settings.os) == "OHOS":
            args[:0] = [
                "--build=aarch64-unknown-linux-musl",
                "--host=aarch64-unknown-linux-musl",
            ]
        return args

    def build(self):
        for helper in ("configure", "config.guess", "config.sub", "install-sh"):
            path = os.path.join(self.source_folder, helper)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

        if str(self.settings.os) == "OHOS":
            build_folder = self._prepare_ohos_build_folder()
            self._configure_ohos(build_folder)
            self._use_system_install_helper(build_folder)
            self._make_ohos(build_folder, args=["-j1"])
            check_args = ["-j1"] if can_run(self) else ["-j1", "TESTS="]
            self._make_ohos(build_folder, target="check", args=check_args)
            return

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _prepare_ohos_build_folder(self):
        build_folder = self._ohos_build_folder()
        shutil.rmtree(build_folder, ignore_errors=True)
        os.makedirs(build_folder, exist_ok=True)
        return build_folder

    def _ohos_build_folder(self):
        token = os.path.basename(os.path.dirname(os.path.dirname(self.build_folder)))
        return os.path.join(os.path.expanduser("~"), ".conan-ohos-build", f"{self.name}-{self.version}-{token}")

    def _configure_ohos(self, build_folder):
        shell = self._ohos_shell()
        configure = os.path.join(self.source_folder, "configure")
        args = " ".join(shlex.quote(arg) for arg in self._configure_args())
        command = (
            f'TMPDIR="{build_folder}" CONFIG_SHELL="{shell}" SHELL="{shell}" '
            f'"{shell}" "{configure}" {args}'
        )
        self.run(command.strip(), cwd=build_folder)

    def _make_ohos(self, build_folder, target=None, args=None):
        make = self.conf.get("tools.gnu:make_program", default="make")
        command = " ".join(part for part in ([f'"{make}"', target] + (args or [])) if part)
        command = f'TMPDIR="{build_folder}" SHELL="{self._ohos_shell()}" {command}'
        self.run(command, cwd=build_folder)

    def _use_system_install_helper(self, build_folder):
        for root, _, files in os.walk(build_folder):
            if "Makefile" not in files:
                continue
            makefile = os.path.join(root, "Makefile")
            with open(makefile, encoding="utf-8") as handle:
                lines = handle.readlines()
            fixed_lines = []
            for line in lines:
                if line.startswith("install_sh = "):
                    line = "install_sh = /system/bin/install\n"
                elif line.startswith("MKDIR_P = "):
                    line = "MKDIR_P = /system/bin/install -d\n"
                fixed_lines.append(line)
            with open(makefile, "w", encoding="utf-8", newline="") as handle:
                handle.writelines(fixed_lines)

    def _ohos_shell(self):
        return "/system/bin/sh" if os.path.isfile("/system/bin/sh") else "/bin/sh"

    def package(self):
        if str(self.settings.os) == "OHOS":
            self._make_ohos(
                self._ohos_build_folder(),
                target="install",
                args=[f'DESTDIR="{self.package_folder}"', "prefix="],
            )
        else:
            Autotools(self).install()
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        libdir = os.path.join(self.package_folder, "lib")
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
                signed = path + ".signed"
                subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"], check=True)
                os.replace(signed, path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["usb-1.0"]
        self.cpp_info.includedirs = [os.path.join("include", "libusb-1.0")]
        self.cpp_info.set_property("cmake_file_name", "libusb-1.0")
        self.cpp_info.set_property("cmake_target_name", "libusb-1.0::libusb-1.0")
        self.cpp_info.set_property("pkg_config_name", "libusb-1.0")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
