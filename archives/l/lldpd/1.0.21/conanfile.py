#!/usr/bin/env python3
"""Conan recipe — lldpd 1.0.21

lldpd is an implementation of IEEE 802.1AB (Link Layer Discovery Protocol) for
Unix-like systems. It also handles CDP, EDP, SONMP and FDP. The package builds:
  * lldpd  — the LLDP daemon (sbin)
  * lldpcli — the command-line client (sbin)
  * liblldpctl — the client C library (liblldpctl.so/.a + lldpctl.h)

Homepage: https://lldpd.github.io/
License: ISC

OHOS adaptation notes (see notes.md for the full rationale):
  * Bundled libevent is used (--with-embedded-libevent), so there is no external
    runtime dependency. libevent is only needed by the daemon/client binaries,
    not by liblldpctl itself.
  * Privilege separation, hardening, readline/snmp/seccomp/libbsd are disabled
    to avoid absent OHOS users, headers and libraries.
  * config.guess/config.sub (timestamp 2022-01-09) do not recognise HarmonyOS,
    so they are patched in build() for the CI worker (uname reports HarmonyOS).
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LldpdConan(ConanFile):
    name = "lldpd"
    version = "1.0.21"
    description = (
        "Implementation of IEEE 802.1AB (LLDP) with CDP/EDP/SONMP/FDP support, "
        "shipping the lldpd daemon, lldpcli client and liblldpctl library"
    )
    license = "ISC"
    homepage = "https://lldpd.github.io/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R32: settings.os must allow both Linux and OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libevent is built from the bundled copy (--with-embedded-libevent),
        # so there are no Conan-managed dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The OHOS/musl toolchain ships neither the Linux kernel UAPI headers
        # (<asm/types.h>, <linux/socket.h>, ...) nor the BSD <sys/queue.h>. lldpd
        # bundles a partial include/linux/ set that still expects the kernel
        # headers for a few symbols, and its own sources need <sys/queue.h>.
        # Provide a small self-contained compat include tree so the recipe builds
        # identically on the build container and the CI worker.
        compat_dir = self._prepare_ohos_compat()

        tc = AutotoolsToolchain(self)
        if compat_dir:
            tc.extra_cflags.append(f"-I{compat_dir}")
        # Use the libevent copy bundled in the source tree: no external dependency.
        tc.configure_args.append("--with-embedded-libevent")
        # Privilege separation needs a dedicated lldpd user/group + chroot, which
        # do not exist on OHOS. Disable it.
        tc.configure_args.append("--disable-privsep")
        # Hardening adds _FORTIFY_SOURCE / stack-protector probes that are not
        # useful for a recipe build; disable to keep the toolchain simple.
        tc.configure_args.append("--disable-hardening")
        # Optional features that depend on libraries unavailable on OHOS.
        tc.configure_args.append("--without-readline")
        tc.configure_args.append("--without-snmp")
        tc.configure_args.append("--without-seccomp")
        tc.configure_args.append("--without-libbsd")
        # No documentation build.
        tc.configure_args.append("--disable-doxygen-doc")
        # Build liblldpctl static-only. The CI worker's HMDFS does not reliably
        # resolve the conan cache path (or its soname symlink) at runtime, so a
        # shared liblldpctl.so is unfindable by the loader ("Error loading shared
        # library") even though it is packaged. Static linking bakes the symbols
        # into consumers (test, lldpcli), removing the runtime .so lookup. lldpd's
        # liblldpctl.a already folds in libcommon-daemon-lib + libfixedpoint and
        # needs only libc, so static consumers link cleanly.
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_for_ohos()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def _prepare_ohos_compat(self):
        """Create a small compat include tree under the source folder providing the
        kernel UAPI / BSD headers that the OHOS/musl toolchain lacks.

        Provides: asm/types.h, asm/sockios.h, linux/posix_types.h,
        linux/socket.h (only __kernel_sa_family_t, per lldpd's netlink.h) and
        sys/queue.h (copied from the bundled libevent). Returns the directory to
        add to -I, or None on failure."""
        import shutil
        base = os.path.join(self.source_folder, "ohos-compat")
        try:
            os.makedirs(os.path.join(base, "asm"), exist_ok=True)
            os.makedirs(os.path.join(base, "linux"), exist_ok=True)
            os.makedirs(os.path.join(base, "sys"), exist_ok=True)

            self._write_if_missing(
                os.path.join(base, "asm", "types.h"),
                "/* Minimal Linux UAPI integer types (aarch64 LP64). */\n"
                "#ifndef _OHOS_COMPAT_ASM_TYPES_H\n"
                "#define _OHOS_COMPAT_ASM_TYPES_H\n"
                "typedef unsigned char __u8;\n"
                "typedef signed char __s8;\n"
                "typedef unsigned short __u16;\n"
                "typedef signed short __s16;\n"
                "typedef unsigned int __u32;\n"
                "typedef signed int __s32;\n"
                "typedef unsigned long long __u64;\n"
                "typedef signed long long __s64;\n"
                "#endif\n",
            )

            self._write_if_missing(
                os.path.join(base, "asm", "sockios.h"),
                "/* Socket ioctls needed by lldpd's bundled linux/sockios.h. */\n"
                "#ifndef _OHOS_COMPAT_ASM_SOCKIOS_H\n"
                "#define _OHOS_COMPAT_ASM_SOCKIOS_H\n"
                "#define SIOCGSTAMP_OLD   0x8906\n"
                "#define SIOCGSTAMPNS_OLD 0x8907\n"
                "#define SIOCGSTAMP       0x8906\n"
                "#define SIOCGSTAMPNS     0x8908\n"
                "#endif\n",
            )

            self._write_if_missing(
                os.path.join(base, "linux", "socket.h"),
                "/* lldpd's bundled netlink.h needs only __kernel_sa_family_t. */\n"
                "#ifndef _OHOS_COMPAT_LINUX_SOCKET_H\n"
                "#define _OHOS_COMPAT_LINUX_SOCKET_H\n"
                "typedef unsigned short __kernel_sa_family_t;\n"
                "#endif\n",
            )

            self._write_if_missing(
                os.path.join(base, "linux", "posix_types.h"),
                "/* Minimal Linux UAPI posix types. */\n"
                "#ifndef _OHOS_COMPAT_LINUX_POSIX_TYPES_H\n"
                "#define _OHOS_COMPAT_LINUX_POSIX_TYPES_H\n"
                "#include <asm/types.h>\n"
                "typedef long __kernel_long_t;\n"
                "typedef unsigned long __kernel_ulong_t;\n"
                "typedef __kernel_long_t __kernel_size_t;\n"
                "typedef __kernel_long_t __kernel_ssize_t;\n"
                "typedef __kernel_long_t __kernel_off_t;\n"
                "typedef __kernel_long_t __kernel_time_t;\n"
                "typedef __kernel_long_t __kernel_suseconds_t;\n"
                "typedef __kernel_long_t __kernel_clock_t;\n"
                "typedef int __kernel_pid_t;\n"
                "typedef unsigned int __kernel_uid_t;\n"
                "typedef unsigned int __kernel_gid_t;\n"
                "typedef unsigned int __kernel_ino_t;\n"
                "typedef unsigned short __kernel_mode_t;\n"
                "typedef unsigned short __kernel_nlink_t;\n"
                "typedef int __kernel_ipc_pid_t;\n"
                "typedef unsigned short __kernel_umode_t;\n"
                "typedef __u32 __kernel_dev_t;\n"
                "typedef unsigned long __kernel_fd_mask;\n"
                "typedef struct {\n"
                "    unsigned long fds_bits[1024 / (8 * sizeof(unsigned long))];\n"
                "} __kernel_fd_set;\n"
                "typedef struct { int val[2]; } __kernel_fsid_t;\n"
                "#endif\n",
            )

            # sys/queue.h: reuse the BSD queue.h shipped with the bundled libevent.
            src_queue = os.path.join(
                self.source_folder, "libevent", "compat", "sys", "queue.h")
            dst_queue = os.path.join(base, "sys", "queue.h")
            if os.path.exists(src_queue) and not os.path.exists(dst_queue):
                shutil.copyfile(src_queue, dst_queue)
        except Exception as exc:
            self.output.warning(f"could not prepare OHOS compat headers: {exc}")
            return None
        return base

    def _write_if_missing(self, path, content):
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(content)

    def _patch_config_for_ohos(self):
        """Make every config.guess/config.sub in the source tree recognise
        HarmonyOS/OHOS (R15/E007) and relax config.status umask for HMDFS (E011).

        Both lldpd's own pair and the bundled libevent's pair
        (libevent/build-aux/) must be patched, because --with-embedded-libevent
        runs libevent's configure as a sub-build. Locally the build container
        reports uname=Linux, so these cases are not exercised here; the CI worker
        reports HarmonyOS and needs them."""
        src = self.source_folder
        for root, _dirs, files in os.walk(src):
            for fn in files:
                if fn == "config.guess":
                    self._patch_config_guess(os.path.join(root, fn))
                elif fn == "config.sub":
                    self._patch_config_sub(os.path.join(root, fn))
        # E011: umask 077 -> 022 so HMDFS-created temp dirs are writable.
        for cfg in (
            os.path.join(src, "configure"),
            os.path.join(src, "libevent", "configure"),
        ):
            self._relax_umask(cfg)

    def _patch_config_guess(self, path):
        if not os.path.exists(path):
            return
        with open(path) as f:
            txt = f.read()
        changed = False
        # E007 §2.1: add __OHOS__ to the LIBC detection (only reached when uname
        # reports Linux/GNU; anchor on the __GLIBC__ branch).
        if "__OHOS__" not in txt and "#elif defined(__GLIBC__)" in txt:
            txt = txt.replace(
                "#elif defined(__GLIBC__)\n\tLIBC=gnu",
                "#elif defined(__GLIBC__)\n\tLIBC=gnu\n#elif defined(__OHOS__)\n\tLIBC=ohos",
                1,
            )
            changed = True
        # E007 §2.2: add a HarmonyOS case as the first entry of the main
        # `case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION` so
        # that uname -s == HarmonyOS resolves to a linux-ohos triplet directly,
        # without any compile test (which hits an HMDFS temp-dir Permission
        # denied at the fallback path on the CI worker).
        anchor = "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
        if "HarmonyOS" not in txt and anchor in txt:
            block = (
                "    *:HarmonyOS:*:*)\n"
                '\tcase "$UNAME_MACHINE" in\n'
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)          MACHINE=i686 ;;\n"
                '\t    *)             MACHINE="$UNAME_MACHINE" ;;\n'
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n"
            )
            txt = txt.replace(anchor, anchor + block, 1)
            changed = True
        if changed:
            with open(path, "w") as f:
                f.write(txt)
            os.chmod(path, 0o755)

    def _patch_config_sub(self, path):
        if not os.path.exists(path):
            return
        with open(path) as f:
            txt = f.read()
        changed = False
        # E007 §3.1: ohos-linux triplet, appended after the android-linux block
        # (shell ignores indentation, so the inserted block's indent is cosmetic).
        if "ohos-linux" not in txt:
            txt, n = re.subn(
                r'(android-linux\)\n\t+basic_machine=\$field1-unknown\n\t+basic_os=linux-android\n\t+;;)',
                r'\1\n\t\tohos-linux)\n\t\t\tbasic_machine=$field1-unknown\n\t\t\tbasic_os=linux-ohos\n\t\t\t;;',
                txt,
                count=1,
            )
            if n:
                changed = True
        # E007 §3.2: add ohos* to the portable OS list.
        if "ohos*" not in txt and "gnu* | android* | bsd*" in txt:
            txt = txt.replace("gnu* | android* | bsd*", "gnu* | android* | ohos* | bsd*", 1)
            changed = True
        # E007 §3.3: accept linux-ohos in the kernel-OS validation list. Guard on
        # the exact result (§3.1 already injects a "linux-ohos" substring via
        # basic_os, so a naive guard would skip this).
        if "| linux-ohos* )" not in txt and "| linux-uclibc* )" in txt:
            txt = txt.replace("| linux-uclibc* )", "| linux-uclibc* | linux-ohos* )", 1)
            changed = True
        if changed:
            with open(path, "w") as f:
                f.write(txt)
            os.chmod(path, 0o755)

    def _relax_umask(self, path):
        if not os.path.exists(path):
            return
        with open(path) as f:
            txt = f.read()
        if "umask 077" in txt:
            txt = txt.replace("umask 077", "umask 022")
            with open(path, "w") as f:
                f.write(txt)
            os.chmod(path, 0o755)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # liblldpctl is the consumable library; lldpd/lldpcli are executables
        # installed under sbin/ by the autotools install step.
        self.cpp_info.libs = ["lldpctl"]
