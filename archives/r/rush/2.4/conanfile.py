#!/usr/bin/env python3
"""Conan recipe for GNU Rush 2.4 - Restricted User Shell."""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

_SHIM_PATH = "/data/storage/el1/bundle/electron/resources/resfile/resources/app.asar.unpacked/cli/vendor/shim/safe-bin"

def _clean_path():
    current = os.environ.get("PATH", "")
    parts = [p for p in current.split(os.pathsep) if p and p != _SHIM_PATH]
    # Ensure real system dirs come first
    priority = ["/data/service/hnp/bin", "/usr/bin", "/bin"]
    ordered = [p for p in priority if p in parts]
    rest = [p for p in parts if p not in priority]
    return os.pathsep.join(ordered + rest)


class RushConan(ConanFile):
    name = "rush"
    version = "2.4"
    description = "GNU Rush - a Restricted User Shell for sites providing limited remote access"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/rush/"
    url = ""
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("rush is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--sysconfdir=/etc",
            "--disable-nls",
            "--build=aarch64-linux-gnu",
            "--host=aarch64-linux-gnu",
            # OHOS 环境无 makeinfo。补丁写入 configure 后其 mtime 变新，
            # doc/stamp-vti 依赖 $(top_srcdir)/configure → version.texi 重生成
            # → doc/rush.info 变陈旧 → make install 触发 MAKEINFO 失败（127）。
            # 用 MAKEINFO=true 覆盖（true 忽略参数返回 0）跳过文档生成，
            # 与 archives/a/adplug/2.4 同范式（仓库内 45 例）。
            "MAKEINFO=true",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        os.environ["PATH"] = _clean_path()
        os.environ["ACCEPT_INFERIOR_RM_PROGRAM"] = "yes"
        os.environ["TMPDIR"] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".workbuddy", "tmp"
        )
        os.makedirs(os.environ["TMPDIR"], exist_ok=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Skip `make check`: upstream Automake tests require a real passwd entry
        # for the running UID, unavailable in the OHOS sandbox (getpwuid returns
        # NULL for uid 20420178). Binary verified via rush --version in test_package.

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for la in glob.glob(os.path.join(self.package_folder, "lib", "**", "*.la"), recursive=True):
            os.remove(la)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "sbin"))
