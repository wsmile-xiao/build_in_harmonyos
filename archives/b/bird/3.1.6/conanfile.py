#!/usr/bin/env python3
"""Conan recipe for BIRD Internet Routing Daemon 3.1.6.

BIRD is a dynamic IP routing daemon supporting BGP, OSPF, RIP, Babel, etc.
Core executables: bird (daemon), birdcl (simple CLI client).

OHOS adaptation notes:
- Source tarball is a GitLab archive (no pre-generated configure script)
- Requires autoconf + autoheader to generate build files
- OHOS sysroot provides Linux kernel headers at non-standard path
- linux/socket.h conflicts with sys/socket.h (sockaddr_storage redefinition)
- ncurses not available → --disable-client (birdc disabled, birdcl still built)
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, save, mkdir, load
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.build import build_jobs


class BirdConan(ConanFile):
    name = "bird"
    version = "3.1.6"
    description = "BIRD Internet Routing Daemon - dynamic IP routing daemon supporting BGP, OSPF, RIP, Babel"
    license = "GPL-2.0-or-later"
    homepage = "https://bird.nic.cz/"
    url = ""

    # R32: settings.os must allow both Linux and OHOS
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # BIRD has no Conan-managed dependencies.
        # ncurses is needed for birdc (ncurses client) but is not available on OHOS.
        # birdcl (simple CLI client) and bird (daemon) have no external deps.
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception as e:
            # Fallback for CI workers without Python SSL module
            self.output.warning(f"Standard download failed: {e}")
            self.output.info("Trying fallback download with curl...")
            import hashlib
            url = self.conan_data["sources"]["url"]
            expected_sha = self.conan_data["sources"]["sha256"]
            filename = url.split("/")[-1]
            filepath = os.path.join(self.source_folder, filename)
            self.run(f'curl -sL -o "{filepath}" "{url}"')
            with open(filepath, "rb") as f:
                actual = hashlib.sha256(f.read()).hexdigest()
            if actual != expected_sha:
                raise Exception(f"SHA256 mismatch: expected {expected_sha}, got {actual}")
            self.run(f'tar xzf "{filepath}" --strip-components=1 -C "{self.source_folder}"')
            os.remove(filepath)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Disable ncurses client (not available on OHOS)
        tc.configure_args.append("--disable-client")
        # OHOS: Add sysroot include paths for Linux kernel headers
        if self.settings.os == "OHOS":
            sysroot = os.environ.get("OHOS_SYSROOT", "")
            if not sysroot:
                # Auto-detect OHOS SDK sysroot (avoid hardcoding SDK version)
                import glob
                candidates = sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot"))
                if candidates:
                    sysroot = candidates[-1]  # Latest SDK version
            if sysroot:
                tc.extra_cflags.append(f"-I{sysroot}/usr/include")
                tc.extra_cflags.append(f"-I{sysroot}/usr/include/aarch64-linux-ohos")
                tc.extra_ldflags.append(f"-L{sysroot}/usr/lib/aarch64-linux-ohos")
            else:
                self.output.warning(
                    "OHOS sysroot not found. Set OHOS_SYSROOT env var.")
        # OHOS: Pre-create ohos_compat.h so -include works during configure test
        if self.settings.os == "OHOS":
            ohos_compat_path = os.path.join(self.source_folder, "tools", "ohos_compat.h")
            # Create the file before generate() outputs CFLAGS
            mkdir(self, os.path.join(self.source_folder, "tools"))
            save(self, ohos_compat_path,
                 "/* OHOS compat: define __kernel_sa_family_t, skip linux/socket.h */\n"
                 "#ifndef _OHOS_COMPAT_H\n"
                 "#define _OHOS_COMPAT_H\n"
                 "typedef unsigned short __kernel_sa_family_t;\n"
                 "#define _K_SS_MAXSIZE 128\n"
                 "#define _UAPI_LINUX_SOCKET_H\n"
                 "#endif\n")
            # Use absolute path for -include to work from build directory
            tc.extra_cflags.append(f"-include {ohos_compat_path}")
        tc.generate()

    def _patch_config_guess(self, config_guess):
        """Patch config.guess to recognize HarmonyOS (E007)."""
        content = load(self, config_guess)
        if "HarmonyOS" in content:
            self.output.info("config.guess already has HarmonyOS detection")
        else:
            # Insert HarmonyOS case in the main case statement
            # Target: case "$UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION" in
            main_case = 'case "$UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION" in\n'
            if main_case in content:
                harmony_block = (
                    main_case +
                    '    *:HarmonyOS:*:*)\n'
                    '\tcase "$UNAME_MACHINE" in\n'
                    '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                    '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                    '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                    '\t    i?86)         MACHINE=i686 ;;\n'
                    '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                    '\tesac\n'
                    '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                    '\techo "$GUESS"; exit ;;\n'
                    '\n'
                )
                content = content.replace(main_case, harmony_block, 1)
                save(self, config_guess, content)
                self.output.info("Patched config.guess for HarmonyOS detection")
            else:
                self.output.warning("Could not find main case statement in config.guess")
        # Ensure executable
        os.chmod(config_guess, 0o755)

    def _patch_config_sub(self, config_sub):
        """Patch config.sub to accept linux-ohos* OS (E007).

        Three places need patching:
        1. OS splitting list (~line 118): add linux-ohos* so tuple splits correctly
        2. OS validation list (~line 1387): add -linux-ohos* so OS is validated
        3. OS case handler (~line 1424): add -linux-ohos* case before -linux* case
        """
        content = load(self, config_sub)
        if "linux-ohos" not in content:
            # 1. Add linux-ohos* to the OS splitting list
            content = content.replace(
                "linux-uclibc* | uclinux-uclibc*",
                "linux-uclibc* | linux-ohos* | uclinux-uclibc*",
                1)
            # 2. Add -linux-ohos* to the OS validation list
            content = content.replace(
                "-linux-uclibc* \\",
                "-linux-uclibc* | -linux-ohos* \\",
                1)
            # 3. Add -linux-ohos* case handler before -linux* case
            ohos_case = (
                "\t-linux-ohos*)\n"
                "\t\tos=-linux-ohos\n"
                "\t\t;;\n"
            )
            target = "\t-linux*)\n"
            if target in content:
                content = content.replace(target, ohos_case + target, 1)
            save(self, config_sub, content)
            self.output.info("Patched config.sub for linux-ohos (3 locations)")
        # Ensure executable
        os.chmod(config_sub, 0o755)

    def build(self):
        apply_conandata_patches(self)
        # E007: Patch config.guess/config.sub for HarmonyOS detection
        # BIRD's config.guess (2018-03-08) doesn't recognize HarmonyOS
        if self.settings.os == "OHOS":
            tools_dir = os.path.join(self.source_folder, "tools")
            config_guess = os.path.join(tools_dir, "config.guess")
            config_sub = os.path.join(tools_dir, "config.sub")
            # Python-based patching (reliable, no external dependencies)
            if os.path.exists(config_guess):
                self._patch_config_guess(config_guess)
            if os.path.exists(config_sub):
                self._patch_config_sub(config_sub)
        # GitLab archive tarball has no pre-generated configure script
        # Run autoheader + autoconf to generate build files
        self.run("autoheader", cwd=self.source_folder)
        self.run("autoconf", cwd=self.source_folder)
        # OHOS E114: Fix HMDFS temp dir permission issue
        # On OHOS, autoconf's config.status creates temp awk scripts in the
        # build directory and tries to execute them. HMDFS denies execution
        # from that path. The ac_tmp=$tmp line appears in both the configure
        # script and the embedded config.status template, so patching configure
        # fixes both. This is a necessary R6 exception for HMDFS compatibility:
        # setting TMPDIR alone does not fix config.status on the autoconf
        # version used by OHOS CI (which creates temp dirs in $PWD, not TMPDIR).
        if self.settings.os == "OHOS":
            import tempfile
            fixed_tmp = os.path.join(tempfile.gettempdir(), "bird-conan-fixed")
            os.makedirs(fixed_tmp, exist_ok=True)
            configure_path = os.path.join(self.source_folder, "configure")
            if os.path.exists(configure_path):
                content = load(self, configure_path)
                if "ac_tmp=$tmp" not in content:
                    raise ConanException(
                        "E114: ac_tmp=$tmp pattern not found in configure; "
                        "autoconf may have changed the template")
                content = content.replace("ac_tmp=$tmp", f"ac_tmp={fixed_tmp}")
                save(self, configure_path, content)
                os.chmod(configure_path, 0o755)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j{}".format(build_jobs(self))])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # BIRD produces executables (bird, birdcl), not libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
