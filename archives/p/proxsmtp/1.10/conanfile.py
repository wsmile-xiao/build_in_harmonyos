"""Package the native proxsmtpd 1.10 SMTP filtering daemon for HarmonyOS PC."""

import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.tools.files import copy, get, patch, replace_in_file
from conan.tools.layout import basic_layout


class ProxsmtpConan(ConanFile):
    name = "proxsmtp"
    version = "1.10"
    description = "SMTP proxy that runs a filter before forwarding mail"
    homepage = "http://thewalter.net/stef/software/proxsmtp/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    license = "BSD-3-Clause"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "build_aux/*", "patches/*"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        copy(
            self,
            "config.sub",
            os.path.join(self.export_sources_folder, "build_aux"),
            self.source_folder,
            keep_path=False,
        )
        os.chmod(os.path.join(self.source_folder, "config.sub"), 0o755)
        for filename in (
            "0001-terminate-full-line-within-buffer.patch",
            "0002-log-pointer-thread-id-with-p.patch",
        ):
            patch(
                self,
                base_path=self.source_folder,
                patch_file=os.path.join(self.export_sources_folder, "patches", filename),
            )

        # The OHOS SDK's linux/socket.h conflicts with sys/socket.h. The
        # configure probe already found IP_TRANSPARENT in netinet/in.h.
        replace_in_file(
            self, os.path.join(self.source_folder, "common", "spio.c"),
            "#include <linux/types.h>\n#include <linux/netfilter_ipv4.h>\n", "",
        )

    def build(self):
        if str(self.settings.os) != "OHOS":
            raise RuntimeError("This recipe is verified for HarmonyOS PC only")
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = shlex.quote(executables.get("c", "clang"))
        # Autotools scratch files cannot be reopened reliably in the shared CI cache.
        with tempfile.TemporaryDirectory(prefix="proxsmtp-build-", dir="/data/storage/el2/base/cache") as work:
            shutil.copytree(self.source_folder, work, dirs_exist_ok=True)
            quoted_work = shlex.quote(work)
            self.run(
                f"TMPDIR={quoted_work} CC={cc} CFLAGS='-O2 -fPIC' "
                "./configure --build=aarch64-unknown-ohos "
                "--host=aarch64-unknown-ohos --disable-capabilities "
                "--enable-tproxy --prefix=/usr --sysconfdir=/etc",
                cwd=work,
            )
            # This old configure script mistakes linux/types.h for Linux netfilter.
            # OHOS has that header but does not provide the Linux socket ABI.
            replace_in_file(self, os.path.join(work, "config.h"),
                            "#define LINUX_NETFILTER 1", "/* #undef LINUX_NETFILTER */")
            self.run("make -j1", cwd=work)
            copy(self, "proxsmtpd", os.path.join(work, "src"),
                 os.path.join(self.build_folder, "src"), keep_path=False)

    def package(self):
        copy(
            self,
            "proxsmtpd",
            os.path.join(self.build_folder, "src"),
            os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "proxsmtpd.conf",
            os.path.join(self.source_folder, "doc"),
            os.path.join(self.package_folder, "res"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
