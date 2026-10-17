#!/usr/bin/env python3
"""Conan recipe — qrtr 1.2 (Meson).

qrtr is the userspace reference implementation of the Qualcomm IPC router
protocol. It installs the libqrtr shared library plus the qrtr-cfg and
qrtr-lookup command-line tools. libqrtr itself only needs libc; the optional
systemd unit and qrtr-ns daemon are controlled by Meson features.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class QrtrConan(ConanFile):
    name = "qrtr"
    version = "1.2"
    description = "Userspace reference implementation of the QRTR IPC router protocol"
    license = "BSD-3-Clause"
    homepage = "https://github.com/linux-msm/qrtr"
    url = "https://github.com/linux-msm/qrtr"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qrtr supports Linux and OHOS only, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # HarmonyOS PC 没有 systemd，显式关闭单元文件探测，避免 dependency('systemd') 阻塞。
        tc.project_options["systemd-service"] = "disabled"
        # qrtr-ns 上游默认 auto（不编译）；显式启用，随包一起交付命名服务。
        tc.project_options["qrtr-ns"] = "enabled"
        tc.generate()

        # conan 的 MesonToolchain 不会把 ar/ranlib 写进 conan_meson_native.ini，
        # meson 会按裸名 llvm-ar 探测，而 OHOS clang 工具链目录不在 PATH 上。
        executables = (
            self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            or {}
        )
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            cc = str(executables.get("c") or "")
            bindir = os.path.dirname(cc)
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(ranlib_candidate):
                    ranlib = ranlib_candidate

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file) as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insert = "[binaries]\nar = '%s'\n" % ar
                if ranlib:
                    insert += "ranlib = '%s'\n" % ranlib
                content = content.replace("[binaries]\n", insert, 1)
                with open(native_file, "w") as handle:
                    handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        # Meson only installs libqrtr.h, so package the project-local QRTR
        # UAPI header here. The build-only linux/socket.h compatibility shim
        # is intentionally not installed for downstream consumers.
        copy(
            self,
            "qrtr.h",
            src=os.path.join(self.source_folder, "include", "linux"),
            dst=os.path.join(self.package_folder, "include", "linux"),
        )

        if self.settings.os == "OHOS":
            bindir = os.path.join(self.package_folder, "bin")
            if os.path.isdir(bindir):
                for entry in sorted(os.listdir(bindir)):
                    candidate = os.path.join(bindir, entry)
                    if os.path.isfile(candidate) and not os.path.islink(candidate):
                        self._resign_ohos_elf(candidate)

    def _resign_ohos_elf(self, path):
        """OHOS 内核校验 ELF 的 .codesign 段：安装/打包后签名失效的可执行文件
        会直接报 `Operation not permitted`（知识库 E077）。按四步流程处理：
        剥旧签名 → 自签 → 恢复可执行位。"""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning(
                "binary-sign-tool unavailable, skip ELF signing: %s" % path
            )
            return
        self.run(
            '"%s" --remove-section .codesign "%s" 2>/dev/null || true'
            % (objcopy, path)
        )
        signed = path + ".signed"
        self.run(
            '"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
            % (signer, path, signed)
        )
        if os.path.isfile(signed):
            os.replace(signed, path)
            os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["qrtr"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "qrtr")
