#!/usr/bin/env python3
"""Conan recipe for acpid 2.0.34 — ACPI event daemon for HarmonyOS PC.

acpid is a Linux ACPI event daemon (Autotools project) that listens
for ACPI events (battery/thermal/lid) via /proc/acpi/event or the
ACPI netlink interface and dispatches them to user-space handlers.

Packaged as an application (daemon + acpi_listen utility), not a
library, so package_type = "application" and test_package verifies
the executable binaries instead of a library API.

No third-party conan dependencies (only libc / kernel headers).

Known limitation on OHOS dev hosts:
  hmdfs FUSE filesystem cannot handle autotools' config.status temp
  dirs (umask 077 quirk).  On such hosts the build is redirected to
  a tmpfs path (/data/storage/el2/base) automatically — same
  workaround as the sed 4.9 recipe.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AcpidConan(ConanFile):
    name = "acpid"
    version = "2.0.34"
    description = "acpid — ACPI event daemon for Linux / HarmonyOS PC"
    license = "GPL-2.0-only"
    homepage = "https://sourceforge.net/projects/acpid2/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _choose_build_root(self):
        """Return (work, install_dir) on tmpfs.

        On OHOS dev hosts the Conan build folder sits on hmdfs FUSE,
        which breaks autotools' config.status (umask 077 → unwritable
        temp dirs).  We always build on tmpfs at /data/storage/el2/base.
        """
        root = "/data/storage/el2/base/.conan-build-acpid-2.0.34"
        return os.path.join(root, "src"), os.path.join(root, "install")

    def build(self):
        apply_conandata_patches(self)
        work, install_dir = self._choose_build_root()

        # Work dir — copy patched sources to tmpfs
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        self.run(f'cp -a "{self.source_folder}/." "{work}/"')

        tmpdir = os.path.join(os.path.dirname(work), "build-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.makedirs(install_dir, exist_ok=True)

        env = (
            "PATH=/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:"
            + os.environ.get("PATH", "")
            + f' TMPDIR={tmpdir} CONFIG_SHELL=/data/service/hnp/bin/bash'
            + ' CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++'
            # E091: OHOS sysroot linux/socket.h 与 sys/socket.h 重复定义
            # sockaddr_storage，-D__MUSL__ 触发 sys/socket.h 的守卫
            + ' CFLAGS="-pipe -D__MUSL__"'
        )

        self.run(f'bash -c \'cd {work} && export {env}'
                 f' && ./configure --prefix={install_dir} --disable-silent-rules\'')

        jobs = os.cpu_count() or 1
        self.run(f'bash -c \'cd {work} && export {env} && make -j{jobs}\'')
        self.run(f'bash -c \'cd {work} && export {env} && make install\'')

        self._store = (work, install_dir)

    def package(self):
        store = getattr(self, "_store", None)
        if store is None:
            return
        _work, install_dir = store
        for sub in ("bin", "sbin"):
            src = os.path.join(install_dir, sub)
            if os.path.isdir(src):
                dst = os.path.join(self.package_folder, sub)
                shutil.copytree(src, dst, dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # acpid 安装到 sbin/、acpi_listen 到 bin/：让 VirtualRunEnv
        # 把两个目录都加入 PATH（test_package 依赖此来定位二进制）
        self.cpp_info.bindirs = ["bin", "sbin"]
        # package_type = "application": consumers use the binaries
        # (acpid / acpi_listen) at runtime, not a library API.
