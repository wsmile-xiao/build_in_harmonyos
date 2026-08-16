#!/usr/bin/env python3
"""Conan recipe for dfu-util 0.11 — USB DFU (Device Firmware Upgrade) host utilities.

Build system: autotools (the release tarball ships a pre-generated configure).
Dependency: libusb-1.0. The HarmonyOS PC CI worker has no system libusb, so this
recipe bundles libusb 1.0.27 source and builds it statically (the same proven
approach as dfu-programmer). OHOS-specific patches: umask 077→022 and OHOS
kernel release parsing for libusb.
"""
import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DfuUtilConan(ConanFile):
    name = "dfu-util"
    version = "0.11"
    description = "USB DFU (Device Firmware Upgrade) host utilities"
    license = "GPL-2.0-or-later"
    homepage = "https://dfu-util.sourceforge.net/"
    url = "https://dfu-util.sourceforge.net/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["libusb_source"],
            destination=os.path.join(self.source_folder, "_libusb_source"),
            strip_root=True,
        )

    # ---------- bundled libusb helpers (mirrors dfu-programmer) ----------

    def _libusb_source_folder(self):
        return os.path.join(self.source_folder, "_libusb_source")

    def _bundled_libusb_prefix(self):
        return os.path.join(self.build_folder, "_libusb_prefix")

    def _replace_in_existing(self, relpath, replacements, root=None):
        path = os.path.join(root or self.source_folder, relpath)
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        updated = content
        for old, new in replacements:
            updated = updated.replace(old, new)
        if updated != content:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(updated)

    def _prepare_libusb_source(self):
        libusb_source = self._libusb_source_folder()
        for relpath in ("configure", "config.guess", "config.sub"):
            self._replace_in_existing(relpath, [("umask 077", "umask 022")], root=libusb_source)

        self._replace_in_existing(
            "libusb/os/linux_netlink.c",
            [(
                "#include <sys/socket.h>\n#include <linux/netlink.h>",
                "#include <sys/socket.h>\n\n"
                "#define sockaddr_storage __linux_sockaddr_storage\n"
                "#include <linux/netlink.h>\n"
                "#undef sockaddr_storage\n"
            )],
            root=libusb_source,
        )
        self._replace_in_existing(
            "libusb/os/linux_usbfs.c",
            [(
                "atoms = sscanf(uts.release, \"%d.%d.%d\", &ver->major, &ver->minor, &ver->sublevel);\n"
                "\tif (atoms < 2) {\n"
                "\t\tusbi_err(ctx, \"failed to parse uname release '%s'\", uts.release);\n"
                "\t\treturn -1;\n"
                "\t}",
                "atoms = sscanf(uts.release, \"%d.%d.%d\", &ver->major, &ver->minor, &ver->sublevel);\n"
                "\tif (atoms < 2) {\n"
                "\t\tif (strstr(uts.release, \"HongMeng\") != NULL ||\n"
                "\t\t    strstr(uts.release, \"OHOS\") != NULL) {\n"
                "\t\t\tver->major = 5;\n"
                "\t\t\tver->minor = 10;\n"
                "\t\t\tver->sublevel = 0;\n"
                "\t\t\tusbi_dbg(ctx, \"HongMeng/OHOS kernel detected (%s), assuming modern Linux kernel\", uts.release);\n"
                "\t\t\treturn 0;\n"
                "\t\t}\n"
                "\t\tusbi_err(ctx, \"failed to parse uname release '%s'\", uts.release);\n"
                "\t\treturn -1;\n"
                "\t}",
            )],
            root=libusb_source,
        )

    def _build_libusb(self):
        libusb_prefix = self._bundled_libusb_prefix()
        libusb_archive = os.path.join(libusb_prefix, "lib", "libusb-1.0.a")
        if os.path.isfile(libusb_archive):
            return

        self._prepare_libusb_source()
        configure = os.path.join(self._libusb_source_folder(), "configure")
        configure_args = [
            shlex.quote(configure),
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            f"--prefix={shlex.quote(libusb_prefix)}",
            "--disable-shared",
            "--enable-static",
            "--disable-udev",
        ]
        self.run(" ".join(configure_args), env="conanbuild", cwd=self._libusb_source_folder())
        self.run("make -j1", env="conanbuild", cwd=self._libusb_source_folder())
        self.run("make install", env="conanbuild", cwd=self._libusb_source_folder())
        if not os.path.isfile(libusb_archive):
            raise Exception(f"Bundled libusb static library was not produced: {libusb_archive}")

    def _write_libusb_pc(self, prefix):
        pkgconfig_dir = os.path.join(self.generators_folder, "pkgconfig")
        os.makedirs(pkgconfig_dir, exist_ok=True)
        pc_path = os.path.join(pkgconfig_dir, "libusb-1.0.pc")
        with open(pc_path, "w", encoding="utf-8") as pc:
            pc.write(
                "\n".join([
                    f"prefix={prefix}",
                    "exec_prefix=${prefix}",
                    "libdir=${prefix}/lib",
                    "includedir=${prefix}/include/libusb-1.0",
                    "",
                    "Name: libusb-1.0",
                    "Description: USB access library",
                    "Version: 1.0.27",
                    "Libs: -L${libdir} -l:libusb-1.0.a -lpthread",
                    "Cflags: -I${includedir}",
                    "",
                ])
            )
        return pkgconfig_dir

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            libusb_prefix = self._bundled_libusb_prefix()
            libusb_archive = os.path.join(libusb_prefix, "lib", "libusb-1.0.a")
            include_flags = (
                f"-I{libusb_prefix}/include/libusb-1.0 "
                f"-I{libusb_prefix}/include "
                f"-I{self._libusb_source_folder()}/libusb"
            )
            ld_flags = f"-L{libusb_prefix}/lib"
            lib_flags = f"{libusb_archive} -lpthread"
            pkgconfig_dir = self._write_libusb_pc(libusb_prefix)

            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
                f"PKG_CONFIG_PATH={pkgconfig_dir}:{libusb_prefix}/lib/pkgconfig",
                f"CPPFLAGS={include_flags}",
                f"LDFLAGS={ld_flags}",
                f"USB_CFLAGS={include_flags}",
                f"USB_LIBS={lib_flags}",
                f"LIBUSB_CFLAGS={include_flags}",
                f"LIBUSB_LIBS={lib_flags}",
                f"ac_cv_search_libusb_init={lib_flags}",
            ])
        tc.generate()

    def build(self):
        self._build_libusb()
        # HMDFS 上 Autoconf 生成的 config.status 默认 umask 077，创建
        # subs1.awk 后自身无法读取（Permission denied）；先替换为 022。
        if str(self.settings.os) == "OHOS":
            self._replace_in_existing("configure", [("umask 077", "umask 022")])
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for binary in ("dfu-util", "dfu-prefix", "dfu-suffix"):
            path = os.path.join(self.package_folder, "bin", binary)
            if os.path.exists(path):
                self._sign_binary(path)

    def _sign_binary(self, path):
        os.chmod(path, 0o755)
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if str(self.settings.os) != "OHOS" or not (os.path.exists(sign_tool) and os.path.exists(objcopy)):
            return
        tmp_signed = path + ".signed"
        remove_result = subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=False,
            capture_output=True,
            text=True,
        )
        remove_output = "\n".join(
            part for part in (remove_result.stdout, remove_result.stderr) if part
        ).strip()
        missing_codesign = (
            ".codesign" in remove_output
            and "not found" in remove_output.lower()
        )
        if remove_result.returncode != 0 and not missing_codesign:
            detail = remove_output or f"exit code {remove_result.returncode}"
            raise RuntimeError(f"failed to remove stale .codesign section from {path}: {detail}")
        if remove_result.returncode != 0:
            self.output.warning(f"Skipping stale .codesign removal: {remove_output}")
        subprocess.run(
            [sign_tool, "sign", "-inFile", path, "-outFile", tmp_signed, "-selfSign", "1"],
            check=True,
        )
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        # CLI 工具包：只产可执行文件，无可链接库。
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]