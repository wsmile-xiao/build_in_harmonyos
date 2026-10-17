#!/usr/bin/env python3
"""Conan recipe for BusyBox 1.36.1 (static) — statically linked multicall binary for HarmonyOS PC.

BusyBox combines tiny versions of many common UNIX utilities into a single
small executable.  This variant builds a fully statically linked binary
(CONFIG_STATIC=y) that has no runtime dependency on shared libraries.

Build: make defconfig (generates .config), then make, then make install.
Package type: application (the single busybox-static binary).
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BusyboxStaticConan(ConanFile):
    name = "busybox-static"
    version = "1.36.1"
    description = "BusyBox 1.36.1 (static) — statically linked multicall binary combining tiny UNIX utilities"
    license = "GPL-2.0-only"
    homepage = "https://busybox.net/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _config_shell(self):
        return os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

    def build(self):
        apply_conandata_patches(self)

        # ── OHOS shebang fix ──
        # /bin/sh exists on OHOS but the kernel refuses to use it as a
        # shebang interpreter (ELF signing / execution policy).
        # Strategy: (1) rewrite all #!/bin/sh shebangs to bash path,
        #           (2) prefix all script invocations in Makefile/Kbuild
        #               with $(SHELL) so make runs them through bash.
        bash_path = self._config_shell()

        # (1) Fix ALL #!/bin/sh shebangs across the entire source tree
        self.run(
            f"find . -type f -exec grep -q '#!/bin/sh' {{}} \\; "
            f"-exec sed -i '1s|#!/bin/sh|#!{bash_path}|' {{}} \\;",
            cwd=self.source_folder,
        )

        # (2) Fix Makefile: prefix script invocations with $(SHELL)
        self.run(
            "sed -i "
            "'s|$(Q)$(srctree)/scripts/gen_build_files.sh|$(Q)$(SHELL) $(srctree)/scripts/gen_build_files.sh|; "
            " s|$(srctree)/scripts/trylink|$(SHELL) $(srctree)/scripts/trylink|; "
            " s|$(srctree)/scripts/generate_BUFSIZ.sh|$(SHELL) $(srctree)/scripts/generate_BUFSIZ.sh|g; "
            " s|$(srctree)/scripts/mkconfigs|$(SHELL) $(srctree)/scripts/mkconfigs|; "
            " s|$(srctree)/scripts/embedded_scripts|$(SHELL) $(srctree)/scripts/embedded_scripts|; "
            " s|$(srctree)/scripts/setlocalversion|$(SHELL) $(srctree)/scripts/setlocalversion|' Makefile",
            cwd=self.source_folder,
        )

        # (3) Fix Kbuild.src files: prefix script invocations with $(SHELL)
        #     These get copied to Kbuild by gen_build_files.sh.
        self.run(
            "find . -name 'Kbuild.src' -exec sed -i "
            f"'s|$(srctree_slash)applets/usage_compressed|$(SHELL) $(srctree_slash)applets/usage_compressed|g; "
            f" s|$(srctree_slash)applets/busybox.mkscripts|$(SHELL) $(srctree_slash)applets/busybox.mkscripts|g' {{}} \\;",
            cwd=self.source_folder,
        )

        # R33: Get compiler from Conan conf, never from shell env.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"

        # Derive AR/RANLIB paths from compiler location (same toolchain prefix)
        toolchain_dir = os.path.dirname(cc)
        ar = os.path.join(toolchain_dir, "llvm-ar")
        ranlib = os.path.join(toolchain_dir, "llvm-ranlib")
        # Ensure toolchain directory is in PATH for any other tools
        os.environ["PATH"] = toolchain_dir + os.pathsep + os.environ.get("PATH", "")

        # R5: OHOS has no /bin/sh, use CONFIG_SHELL
        config_shell = self._config_shell()

        # R9: always -j1 for reproducibility
        # R26: BusyBox is a pure C application; libc++/C++17 settings are irrelevant
        # OHOS has no gcc: host tools (scripts/basic/fixdep) default to
        # HOSTCC=gcc and fail with "gcc: command not found" — override HOSTCC.
        extra = (f"CC={cc} CXX={cxx} HOSTCC={cc} "
                 f"AR={ar} RANLIB={ranlib} SHELL={config_shell}")

        # Generate default config (enables most applets)
        self.run(f"make defconfig {extra}", cwd=self.source_folder)

        # -- Enable static linking --
        # defconfig may produce either "CONFIG_STATIC=n" or "# CONFIG_STATIC is not set"
        self.run("sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/; s/CONFIG_STATIC=n/CONFIG_STATIC=y/' .config",
                 cwd=self.source_folder)

        # -- OHOS-specific config overrides --
        # OHOS musl does not declare setutxent/getutxent/endutxent in <utmpx.h>
        # (only struct utmpx is defined).  Disable FEATURE_UTMP and its transitive
        # dependents (WHO, W, USERS, FEATURE_WTMP, loginutils applets).
        self.run("sed -i 's/CONFIG_FEATURE_UTMP=y/CONFIG_FEATURE_UTMP=n/' .config",
                 cwd=self.source_folder)

        # OHOS libc <sys/socket.h> and uapi <linux/socket.h> both define
        # 'struct sockaddr_storage' (redefinition error).  Applets that include
        # <linux/if.h> or <linux/netlink.h> (via libiproute/libnetlink.h)
        # trigger this error.  Disable the affected applets.
        for cfg in ("CONFIG_IFPLUGD", "CONFIG_FEATURE_MDEV_DAEMON", "CONFIG_UEVENT",
                     "CONFIG_MDEV"):
            self.run(f"sed -i 's/{cfg}=y/{cfg}=n/' .config", cwd=self.source_folder)

        # OHOS musl lacks BSD extensions getusershell()/endusershell() (su.c).
        self.run("sed -i 's/CONFIG_SU=y/CONFIG_SU=n/' .config", cwd=self.source_folder)

        # uapi sockaddr_storage redefinition (linux/if.h, libiproute/libnetlink.h)
        # net/ip.c is pulled by CONFIG_IPADDR/IPLINK/IPROUTE/..., not only CONFIG_IP.
        for cfg in ("CONFIG_ETHER_WAKE", "CONFIG_IFENSLAVE", "CONFIG_IP",
                     "CONFIG_IPADDR", "CONFIG_IPLINK", "CONFIG_IPROUTE",
                     "CONFIG_IPRULE", "CONFIG_IPTUNNEL", "CONFIG_IPNEIGH",
                     "CONFIG_TC", "CONFIG_SLATTACH"):
            self.run(f"sed -i 's/{cfg}=y/{cfg}=n/' .config", cwd=self.source_folder)

        # No embedded scripts available in the source tarball — disable to
        # avoid undefined 'scripted_main' linker error.
        self.run("sed -i 's/CONFIG_FEATURE_SH_EMBEDDED_SCRIPTS=y/CONFIG_FEATURE_SH_EMBEDDED_SCRIPTS=n/' .config",
                 cwd=self.source_folder)

        # Regenerate include/autoconf.h from the modified .config so that
        # the kbuild system skips disabled applets.  Without this step the
        # headers generated by make defconfig (with CONFIG_*=y) remain stale
        # and the build will compile the then-disabled applets.
        self.run(f"make silentoldconfig {extra} < /dev/null", cwd=self.source_folder)

        # Build the busybox-static binary
        self.run(f"make {extra} -j1", cwd=self.source_folder)

    def package(self):
        # The busybox binary is a statically linked multicall executable.
        # Copy it directly instead of `make install`, which creates ~400
        # applet symlinks — slow (and unreliable) on the OHOS HMDFS-served
        # package folder.  Downstream consumers invoke `busybox <applet>`.
        pkg = self.package_folder
        bin_dir = os.path.join(pkg, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        src_bin = os.path.join(self.source_folder, "busybox")
        if not os.path.isfile(src_bin):
            self.output.error(f"busybox binary not found: {src_bin}")
            raise ConanException("busybox binary not found after build")
        shutil.copy2(src_bin, os.path.join(bin_dir, "busybox"))
        self.output.info("packaged bin/busybox (statically linked multicall binary)")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Consumers invoke busybox directly via PATH; no libs needed
