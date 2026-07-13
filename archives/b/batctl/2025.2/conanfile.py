#!/usr/bin/env python3
"""Conan recipe for batctl 2025.2 — B.A.T.M.A.N. advanced control tool.

batctl is a command-line tool for controlling and managing batman-adv
mesh networking. It uses a simple Makefile (not autotools) and depends
on libnl (libnl-3.0, libnl-genl-3.0).

This recipe vendors libnl development files (headers + shared libraries)
in libnl-deps.tar.gz because CI workers may not have libnl pre-installed.
If system libnl headers exist at CMAKE_PREFIX_PATH, those are used instead.

E119 fix: OHOS platform has conflicting sockaddr_storage definitions
in linux/socket.h and sys/socket.h. Patches add -include ohos_compat.h
to CFLAGS in the Makefile, and create ohos_compat.h which pre-defines
_UAPI_LINUX_SOCKET_H to skip the kernel header and manually provides
__kernel_sa_family_t.
"""
import os
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BatctlConan(ConanFile):
    name = "batctl"
    version = "2025.2"
    description = "B.A.T.M.A.N. advanced control and management tool"
    license = "GPL-2.0"
    homepage = "https://www.open-mesh.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # batctl is a CLI tool, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Vendored libnl development files (headers + shared libraries)
    exports_sources = "libnl-deps.tar.gz"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"batctl only supports Linux/OHOS, got {self.settings.os}"
            )
        # VirtualBuildEnv for standard build environment (SHELL etc.)
        env = VirtualBuildEnv(self)
        env.generate()

    def _ensure_libnl(self):
        """Ensure libnl development files are available.

        If the system has libnl headers at CMAKE_PREFIX_PATH, use them.
        Otherwise, extract vendored headers and libraries from
        libnl-deps.tar.gz to the build folder.
        Returns (inc_dir, lib_dir).
        """
        prefix = os.environ.get("CMAKE_PREFIX_PATH", "")
        if not prefix:
            prefix = os.path.join(os.path.expanduser("~"), "usr", "local")
        prefix = prefix.split(":")[0]

        sys_inc = os.path.join(prefix, "include", "libnl3")
        sys_lib = os.path.join(prefix, "lib")

        if os.path.isdir(sys_inc):
            self.output.info(f"Using system libnl at {prefix}")
            return sys_inc, sys_lib

        # Extract vendored libnl deps to build folder
        deps_dir = os.path.join(self.build_folder, "libnl-deps")
        inc_dir = os.path.join(deps_dir, "include", "libnl3")
        lib_dir = os.path.join(deps_dir, "lib")

        if not os.path.isdir(inc_dir):
            tarball = os.path.join(self.source_folder, "libnl-deps.tar.gz")
            if os.path.isfile(tarball):
                os.makedirs(deps_dir, exist_ok=True)
                with tarfile.open(tarball) as tar:
                    tar.extractall(deps_dir)
                self.output.info(f"Extracted vendored libnl to {deps_dir}")
            else:
                self.output.warning(f"libnl-deps.tar.gz not found at {tarball}")

        return inc_dir, lib_dir

    def _get_libnl_flags(self):
        """Build LIBNL_CFLAGS/LIBNL_LDLIBS to bypass pkg-config.

        The batctl Makefile checks for libnl via pkg-config. We bypass it
        by passing LIBNL_CFLAGS/LIBNL_LDLIBS on the make command line.
        """
        inc_dir, lib_dir = self._ensure_libnl()
        nl_cflags = f"-I{inc_dir}"
        nl_ldlibs = f"-L{lib_dir} -lnl-3"
        genl_ldlibs = f"-L{lib_dir} -lnl-genl-3"
        self.output.info(f"libnl flags: cflags={nl_cflags} ldlibs={nl_ldlibs}")
        return nl_cflags, nl_ldlibs, nl_cflags, genl_ldlibs

    def build(self):
        # Apply patches (E119 fix: ohos_compat.h creation + Makefile -include)
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        # Bypass pkg-config check by passing LIBNL_* flags directly to make.
        nl_cflags, nl_ldlibs, genl_cflags, genl_ldlibs = self._get_libnl_flags()
        env_vars = (
            f'CC="{cc}"'
            f' LIBNL_CFLAGS="{nl_cflags}" LIBNL_LDLIBS="{nl_ldlibs}"'
            f' LIBNL_GENL_CFLAGS="{genl_cflags}" LIBNL_GENL_LDLIBS="{genl_ldlibs}"'
        )
        self.run(
            f"make {env_vars} -j1 PREFIX=/usr/local",
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        # LIBNL_* flags needed because Makefile evaluates them at parse-time
        # even for the install target.
        nl_cflags, nl_ldlibs, genl_cflags, genl_ldlibs = self._get_libnl_flags()
        env_vars = (
            f'LIBNL_CFLAGS="{nl_cflags}" LIBNL_LDLIBS="{nl_ldlibs}" '
            f'LIBNL_GENL_CFLAGS="{genl_cflags}" LIBNL_GENL_LDLIBS="{genl_ldlibs}" '
        )
        self.run(
            f"make {env_vars}install SBINDIR=/bin MANDIR=/share/man "
            f"DESTDIR={self.package_folder}",
            cwd=self.source_folder,
            env=["conanbuild"],
        )
        # Install vendored libnl shared libraries if system doesn't have them
        prefix = os.environ.get("CMAKE_PREFIX_PATH", "")
        if not prefix:
            prefix = os.path.join(os.path.expanduser("~"), "usr", "local")
        sys_lib = os.path.join(prefix.split(":")[0], "lib")
        if not os.path.isfile(os.path.join(sys_lib, "libnl-3.so.200")):
            deps_lib = os.path.join(self.build_folder, "libnl-deps", "lib")
            if os.path.isdir(deps_lib):
                dest_lib = os.path.join(self.package_folder, "lib")
                os.makedirs(dest_lib, exist_ok=True)
                tarball = os.path.join(self.source_folder, "libnl-deps.tar.gz")
                with tarfile.open(tarball) as tar:
                    for member in tar.getmembers():
                        if member.name.startswith("lib/"):
                            tar.extract(member, self.package_folder)
                self.output.info("Installed vendored libnl libraries to package")

    def package_info(self):
        # batctl is a CLI tool — binary in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
