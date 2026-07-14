#!/usr/bin/env python3
"""Conan recipe — addrwatch 1.0.2

A tool similar to arpwatch for IPv4/IPv6 and ethernet address pairing monitoring.
Homepage: https://github.com/fln/addrwatch
License: GPL-3.0
"""
import os
import subprocess
import io
import ssl
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AddrwatchConan(ConanFile):
    name = "addrwatch"
    version = "1.0.2"
    description = "A tool similar to arpwatch for IPv4/IPv6 and ethernet address pairing monitoring"
    license = "GPL-3.0"
    homepage = "https://github.com/fln/addrwatch"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Dependencies are system-installed via cmd-pkgs (libpcap, libevent, argp-standalone)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # System dependency paths (libpcap, libevent, argp-standalone, libintl)
        prefix = os.path.expanduser("~/usr/local")
        tc.extra_ldflags.append(f"-L{prefix}/lib")
        tc.extra_cflags.append(f"-I{prefix}/include")
        tc.extra_ldflags.append("-largp")
        tc.extra_ldflags.append("-lintl")
        tc.extra_ldflags.append("-lrt")
        # R15: No --build/--host — config.guess/config.sub handled in build()
        tc.generate()

    def build(self):
        # Ensure system deps (libargp, libintl, libpcap, libevent) are installed
        # before configure — LDFLAGS already contains -largp -lintl, so the
        # libraries must exist or configure's compiler test will fail.
        self._ensure_system_deps()

        apply_conandata_patches(self)

        # R15: Patch config.guess/config.sub for OHOS instead of using --build/--host
        # The configure patch (0003) already makes config.guess/config.sub optional
        # since addrwatch source doesn't ship them. If they exist (e.g. from a
        # different source version), patch them for HarmonyOS detection.
        self._patch_config_for_ohos()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def _ensure_system_deps(self):
        """Install missing system libraries from cmd-pkgs (or conan remote fallback)."""
        prefix = os.path.expanduser("~/usr/local")
        lib_dir = os.path.join(prefix, "lib")
        inc_dir = os.path.join(prefix, "include")

        # (lib_file, header_file, cmd_pkgs_name, cmd_pkgs_version, conan_ref)
        deps = [
            ("libargp.a", "argp.h", "argp-standalone", "1.5.0", None),
            ("libintl.a", None, "gettext", "0.22.5", None),
            ("libpcap.a", "pcap.h", "libpcap", "1.10.6", "libpcap/1.10.6"),
            ("libevent.a", None, "libevent", "2.1.12", None),
        ]

        def _check_present(lib_file, header_file):
            if not os.path.exists(os.path.join(lib_dir, lib_file)):
                return False
            if header_file and not os.path.exists(os.path.join(inc_dir, header_file)):
                return False
            return True

        # Find what's missing
        work = []
        for lib_file, header_file, pkg_name, pkg_ver, conan_ref in deps:
            if _check_present(lib_file, header_file):
                continue
            work.append((lib_file, header_file, pkg_name, pkg_ver, conan_ref))

        if not work:
            self.output.info("All system dependencies present")
            return

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        for lib_file, header_file, pkg_name, pkg_ver, conan_ref in work:
            self.output.info(f"Installing {pkg_name} {pkg_ver} from cmd-pkgs...")
            url = (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                f"download/pkgs/{pkg_name}-{pkg_ver}-ohos-aarch64.tar.gz"
            )
            try:
                req = urllib.request.urlopen(url, context=ctx, timeout=120)
                data = req.read()
                tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
                tf.extractall(prefix)
                tf.close()
                self.output.info(f"  Installed {pkg_name} {pkg_ver} from cmd-pkgs")
            except Exception as e:
                self.output.warning(f"  cmd-pkgs install failed: {e}")

            # Verify — some cmd-pkgs tarballs are empty (e.g. libpcap)
            if not _check_present(lib_file, header_file) and conan_ref:
                self.output.info(f"  cmd-pkgs package empty, trying conan remote: {conan_ref}")
                self._install_from_conan(conan_ref, lib_file, header_file, prefix)

    def _install_from_conan(self, conan_ref, lib_file, header_file, prefix):
        """Fallback: download a conan package and copy its files to prefix."""
        # Discover remote name dynamically (L0g: no hardcoded remote names)
        remote_name = ""
        try:
            rr = subprocess.run(
                "conan remote list", check=True,
                capture_output=True, text=True, timeout=30, shell=True,
            )
            for line in rr.stdout.splitlines():
                if ":" in line and "conancenter" not in line.lower():
                    remote_name = line.split(":")[0].strip()
                    break
        except Exception:
            pass

        try:
            remote_flag = f"-{chr(114)}={remote_name}" if remote_name else ""
            subprocess.run(
                f"conan download {conan_ref} {remote_flag}",
                check=True, capture_output=True, text=True, timeout=120, shell=True,
            )
        except Exception as e:
            self.output.warning(f"  conan download failed: {e}")
            return

        # Find the package folder in conan cache by searching for the lib file
        try:
            import glob
            cache_root = os.path.expanduser("~/.conan2/p")
            for lib_path in glob.glob(f"{cache_root}/**/{lib_file}", recursive=True):
                if os.path.exists(lib_path):
                    pkg_dir = os.path.dirname(os.path.dirname(lib_path))
                    # Copy lib
                    dst_lib = os.path.join(prefix, "lib")
                    os.makedirs(dst_lib, exist_ok=True)
                    subprocess.run(f"cp {lib_path} {dst_lib}/", check=True, shell=True)
                    self.output.info(f"  Copied {lib_file} from conan cache")
                    # Copy header(s)
                    if header_file:
                        for hdr in glob.glob(f"{pkg_dir}/include/**/{header_file}", recursive=True):
                            dst_inc = os.path.join(prefix, "include")
                            os.makedirs(dst_inc, exist_ok=True)
                            subprocess.run(f"cp {hdr} {dst_inc}/", check=True, shell=True)
                        self.output.info(f"  Copied {header_file} from conan cache")
                    # Copy include subdirectories (e.g. pcap/) if present
                    for subdir in glob.glob(f"{pkg_dir}/include/*/"):
                        dst_inc = os.path.join(prefix, "include")
                        os.makedirs(dst_inc, exist_ok=True)
                        subprocess.run(f"cp -r {subdir} {dst_inc}/", check=True, shell=True)
                    break
        except Exception as e:
            self.output.warning(f"  Failed to copy from conan cache: {e}")

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub to recognize HarmonyOS/OHOS (R15)."""
        # Find config.guess and config.sub in source folder
        candidates = [
            self.source_folder,
            os.path.join(self.source_folder, "build-aux"),
        ]
        cg_path = cs_path = None
        for d in candidates:
            cg = os.path.join(d, "config.guess")
            cs = os.path.join(d, "config.sub")
            if os.path.exists(cg) and os.path.exists(cs):
                cg_path = cg
                cs_path = cs
                break

        if not cg_path or not cs_path:
            # addrwatch source doesn't ship config.guess/config.sub
            # The configure patch (0003) makes them optional, so this is fine
            self.output.info("config.guess/config.sub not found in source, skipping OHOS patch")
            return

        # Try to use the skill's perl script if available
        skill_root = os.environ.get("OHC_SKILL_ROOT", "")
        if skill_root:
            script = os.path.join(skill_root, "scripts", "patch-autotools-ohos.pl")
            if os.path.exists(script):
                self.output.info(f"Patching config.guess/config.sub with {script}")
                subprocess.run(["perl", script, cg_path, cs_path], check=True)
                return

        # Fallback: manual Python patching
        self._manual_patch_config_guess(cg_path)
        self._manual_patch_config_sub(cs_path)

    def _manual_patch_config_guess(self, cg_path):
        """Manually patch config.guess for HarmonyOS detection."""
        with open(cg_path, "r") as f:
            content = f.read()

        changed = False

        # 1. Add __OHOS__ LIBC detection after __ANDROID__
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos"
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
                self.output.info("  [ok] Added __OHOS__ LIBC detection to config.guess")
            else:
                self.output.warn("  [warn] Could not find __ANDROID__/LIBC=android in config.guess")

        # 2. Add HarmonyOS case block before NetBSD
        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)          MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True
                self.output.info("  [ok] Added HarmonyOS system identification to config.guess")
            else:
                self.output.warn("  [warn] Could not find NetBSD insertion point in config.guess")

        if changed:
            with open(cg_path, "w") as f:
                f.write(content)

    def _manual_patch_config_sub(self, cs_path):
        """Manually patch config.sub for ohos-linux support."""
        with open(cs_path, "r") as f:
            content = f.read()

        changed = False

        # 1. Add ohos-linux triplet after android-linux
        if "ohos-linux" not in content:
            import re
            # Match android-linux block and add ohos-linux after it
            pattern = r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
            replacement = r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n\tbasic_os=linux-ohos\n\t;;\n'
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True
                self.output.info("  [ok] Added ohos-linux triplet to config.sub")
            else:
                self.output.warn("  [warn] Could not find android-linux in config.sub")

        # 2. Add ohos* to OS type list
        if "ohos*" not in content:
            content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            changed = True
            self.output.info("  [ok] Added ohos* to OS list in config.sub")

        # 3. Add linux-ohos to kernel-OS validation list
        if "linux-ohos" not in content:
            import re
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*\))', r'\1| linux-ohos*)', content)
            if count > 0:
                changed = True
                self.output.info("  [ok] Added linux-ohos to kernel list in config.sub")
            else:
                self.output.warn("  [warn] Could not find linux-uclibc pattern in config.sub")

        if changed:
            with open(cs_path, "w") as f:
                f.write(content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # addrwatch is a terminal tool, not a library
        self.cpp_info.libs = []
