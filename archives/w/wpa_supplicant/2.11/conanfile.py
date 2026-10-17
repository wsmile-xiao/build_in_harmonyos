#!/usr/bin/env python3
"""Conan recipe for wpa_supplicant 2.11 (hostap project).

wpa_supplicant is a Wi-Fi Protected Access (WPA) client and IEEE 802.1X
supplicant. It provides WPA/WPA2/WPA3 authentication for wireless and
wired connections.

Build system: custom Makefile (not autotools/cmake).
Source: hostap project git repo (tag hostap_2_11).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class WpaSupplicantConan(ConanFile):
    name = "wpa_supplicant"
    version = "2.11"
    description = "WPA/WPA2/WPA3 supplicant and IEEE 802.1X supplicant"
    license = "BSD-3-Clause"
    homepage = "https://w1.fi/wpa_supplicant/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Check if source is already populated (e.g., from local cache)
        if os.path.exists(os.path.join(self.source_folder, "wpa_supplicant", "Makefile")):
            self.output.info("Source already populated, skipping download")
            return
        # Try tarball download first
        from conan.tools.files import get
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
            return
        except Exception:
            pass
        # Fall back to git smart HTTP protocol (w1.fi cgit may block tarball/clone)
        import subprocess
        import shutil
        import urllib.request
        import struct

        git_url = "https://git.w1.fi/hostap.git/git-upload-pack"
        commit_sha = "d945ddd368085f255e68328f2d3b020ceea359af"
        self.output.info(f"Tarball failed, using git smart HTTP protocol to download {commit_sha[:8]}")

        # Build git-upload-pack request (v0 protocol with "done")
        want_str = f"want {commit_sha} multi_ack side-band-64k thin-pack ofs-delta agent=git/2.45.2\n"
        want_pkt = f"{len(want_str) + 4:04x}{want_str}"
        deepen_str = "deepen 1\n"
        deepen_pkt = f"{len(deepen_str) + 4:04x}{deepen_str}"
        done_str = "done\n"
        done_pkt = f"{len(done_str) + 4:04x}{done_str}"
        post_data = (want_pkt + deepen_pkt + "0000" + done_pkt + "0000").encode()

        req = urllib.request.Request(git_url, data=post_data, headers={
            "User-Agent": "git/2.45.2",
            "Content-Type": "application/x-git-upload-pack-request",
            "Accept": "application/x-git-upload-pack-result",
            "Content-Length": str(len(post_data)),
        })

        # Download raw response
        with urllib.request.urlopen(req, timeout=600) as resp:
            raw_data = resp.read()

        # Extract pack data from side-band encoded response
        pack_data = bytearray()
        pos = 0
        while pos < len(raw_data):
            if pos + 4 > len(raw_data):
                break
            len_str = raw_data[pos:pos+4]
            try:
                pkt_len = int(len_str, 16)
            except ValueError:
                break
            if pkt_len == 0:
                pos += 4
                continue
            if pkt_len < 4 or pos + pkt_len > len(raw_data):
                break
            pkt_data = raw_data[pos+4:pos+pkt_len]
            pos += pkt_len
            if len(pkt_data) > 0 and pkt_data[0] == 1:
                pack_data.extend(pkt_data[1:])

        if pack_data[:4] != b'PACK':
            raise Exception("Failed to download valid git pack data")

        # Create a temporary git repo and index the pack
        import shutil as _shutil
        git_bin = _shutil.which("git") or "/data/service/hnp/bin/git"
        tmp_git = self.source_folder + ".gitmp"
        os.makedirs(tmp_git, exist_ok=True)
        pack_file = os.path.join(tmp_git, "pack.bin")
        with open(pack_file, 'wb') as f:
            f.write(pack_data)

        subprocess.run([git_bin, "init"], cwd=tmp_git, check=True, capture_output=True)
        subprocess.run([git_bin, "config", "--global", "--add", "safe.directory", tmp_git], check=True, capture_output=True)
        with open(pack_file, 'rb') as f:
            subprocess.run([git_bin, "index-pack", "--stdin", "--fix-thin"], cwd=tmp_git, stdin=f, check=True, capture_output=True)
        os.makedirs(os.path.join(tmp_git, ".git", "refs", "tags"), exist_ok=True)
        with open(os.path.join(tmp_git, ".git", "refs", "tags", "hostap_2_11"), 'w') as f:
            f.write(commit_sha)
        subprocess.run([git_bin, "update-ref", "HEAD", commit_sha], cwd=tmp_git, check=True, capture_output=True)
        subprocess.run([git_bin, "checkout", "hostap_2_11"], cwd=tmp_git, check=True, capture_output=True)

        # Move source files to source_folder
        for item in os.listdir(tmp_git):
            if item != ".git" and item != "pack.bin":
                src_item = os.path.join(tmp_git, item)
                dst_item = os.path.join(self.source_folder, item)
                shutil.move(src_item, dst_item)
        shutil.rmtree(tmp_git, ignore_errors=True)

    def generate(self):
        # Generate build environment from conan dependencies
        from conan.tools.env import Environment
        env = Environment()
        env.define("CC", str(self.settings.compiler) if self.settings.compiler else "clang")
        # Get openssl paths from dependency info
        openssl_info = self.dependencies["openssl"]
        openssl_includedir = openssl_info.cpp_info.includedirs[0] if openssl_info.cpp_info.includedirs else ""
        openssl_libdir = openssl_info.cpp_info.libdirs[0] if openssl_info.cpp_info.libdirs else ""
        if openssl_includedir:
            env.append("CFLAGS", f"-I{openssl_includedir}")
        if openssl_libdir:
            env.append("LIBS", f"-L{openssl_libdir} -lssl -lcrypto")
        envvars = env.vars(self)
        envvars.save_script("wpa_build_env")

    def build(self):
        # Apply patches if any
        apply_conandata_patches(self)
        # Create .config from defconfig with OHOS adaptations
        ws_dir = os.path.join(self.source_folder, "wpa_supplicant")
        defconfig = os.path.join(ws_dir, "defconfig")
        config = os.path.join(ws_dir, ".config")

        # Copy defconfig to .config
        shutil.copy(defconfig, config)

        # R32: Apply OHOS-specific config only on OHOS/Linux platforms
        with open(config, "r") as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            if self.settings.os in ("Linux", "OHOS"):
                # Disable nl80211 driver (requires libnl, not available on OHOS)
                if line.startswith("CONFIG_DRIVER_NL80211=y"):
                    new_lines.append("#" + line)
                # Disable libnl
                elif line.startswith("CONFIG_LIBNL32=y"):
                    new_lines.append("#" + line)
                # Disable WEXT (Linux wireless extensions)
                elif line.startswith("CONFIG_DRIVER_WEXT=y"):
                    new_lines.append("#" + line)
                # Disable MACsec Linux driver
                elif line.startswith("CONFIG_DRIVER_MACSEC_LINUX=y"):
                    new_lines.append("#" + line)
                # Disable D-Bus (not available on OHOS)
                elif line.startswith("CONFIG_CTRL_IFACE_DBUS_NEW=y"):
                    new_lines.append("#" + line)
                elif line.startswith("CONFIG_CTRL_IFACE_DBUS_INTRO=y"):
                    new_lines.append("#" + line)
                # Disable smartcard (pcsclite not available on OHOS)
                elif line.startswith("CONFIG_SMARTCARD=y"):
                    new_lines.append("#" + line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if self.settings.os in ("Linux", "OHOS"):
            new_lines.append("\n# OHOS adaptation\n")
            new_lines.append("CONFIG_DRIVER_NONE=y\n")
            new_lines.append("CONFIG_AP=y\n")
            new_lines.append("NEED_AP_MLME=y\n")

        # Add openssl paths from conan dependency
        openssl_info = self.dependencies["openssl"]
        openssl_includedir = openssl_info.cpp_info.includedirs[0] if openssl_info.cpp_info.includedirs else ""
        openssl_libdir = openssl_info.cpp_info.libdirs[0] if openssl_info.cpp_info.libdirs else ""
        if openssl_includedir:
            new_lines.append(f"\n# OpenSSL from conan\n")
            new_lines.append(f"CFLAGS += -I{openssl_includedir}\n")
            new_lines.append(f"LIBS += -L{openssl_libdir} -lssl -lcrypto\n")
            new_lines.append(f"LDFLAGS += -L{openssl_libdir}\n")

        with open(config, "w") as f:
            f.writelines(new_lines)

        # Build with make - use conanbuild env for proper library paths
        self.run(f"make -C {ws_dir} clean", cwd=ws_dir, env="conanbuild")
        self.run(f"make -C {ws_dir} -j2", cwd=ws_dir, env="conanbuild")

    def package(self):
        import shutil as _shutil
        # Binaries are built in the wpa_supplicant/ source directory
        ws_dir = os.path.join(self.source_folder, "wpa_supplicant")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for binary in ["wpa_supplicant", "wpa_cli", "wpa_passphrase"]:
            src = os.path.join(ws_dir, binary)
            dst = os.path.join(bindir, binary)
            if os.path.exists(src):
                _shutil.copy2(src, dst)
                self.output.info(f"Packaged {binary} ({os.path.getsize(src)} bytes)")
            else:
                self.output.warning(f"Binary not found: {src}")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Not a library, but declare for downstream consumers
        self.cpp_info.libs = []
