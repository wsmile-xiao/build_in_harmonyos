#!/usr/bin/env python3
"""Conan recipe — awall 1.14.0 (Alpine Wall, pure Lua firewall config tool).

awall is a pure Lua (noarch) package: no C compilation, install = copying
Lua modules and JSON policy templates into the target tree, driven by the
upstream Makefile (make LUA_VERSION=5.5 install ROOT_DIR=...).

Install layout (LUA_VERSION=5.5):
  awall/*.lua (+ awall/modules/*.lua)  → usr/share/lua/5.5/awall/
  mandatory/*.json                      → usr/share/awall/mandatory/
  optional/*.json                       → usr/share/awall/optional/
  awall-cli                             → usr/sbin/awall  (mode 755)
  sample-policy.json                    → usr/share/awall/sample/
  usr/share/awall/modules               → symlink ../lua/5.5/awall/modules

Runtime deps (host Lua modules): cjson/lpc/posix/stringy/alt_getopt/schema.
Only lua/5.5.0 is published in ohpcd; the other Lua modules are NOT declared
as conan requirements (following aaudit-server/acf-pingu precedent).

Upstream: https://gitlab.alpinelinux.org/alpine/awall
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AwallConan(ConanFile):
    name = "awall"
    version = "1.14.0"
    description = "Alpine Wall — extensible firewall configuration tool (pure Lua)"
    license = "GPL-2.0-only"  # awall is GPLv2 (see LICENSE in tarball)
    homepage = "https://gitlab.alpinelinux.org/alpine/awall"
    url = "https://gitlab.alpinelinux.org/alpine/awall/-/archive/v1.14.0/awall-v1.14.0.tar.bz2"
    topics = ("firewall", "netfilter", "lua", "alpine")
    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Only lua is published in ohpcd; Lua helper modules (cjson, lpc,
        # posix, stringy, alt_getopt, schema) are host env deps and are not
        # declared as conan requires (aaudit-server/acf-pingu precedent).
        self.requires("lua/5.5.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # No compilation: apply the Lua 5.5 compat patch to optfrag.lua
        # (combinations() arg-counting fix), nothing else to build.
        apply_conandata_patches(self)

    def package(self):
        lua_dir = os.path.join(self.package_folder, "usr", "share", "lua", "5.5", "awall")
        awall_dir = os.path.join(self.package_folder, "usr", "share", "awall")
        sbin_dir = os.path.join(self.package_folder, "usr", "sbin")

        # Lua modules (recursive: awall/modules/*.lua preserved under modules/)
        copy(
            self,
            "*.lua",
            src=os.path.join(self.source_folder, "awall"),
            dst=lua_dir,
        )

        # Policy JSON templates
        copy(
            self,
            "*.json",
            src=os.path.join(self.source_folder, "mandatory"),
            dst=os.path.join(awall_dir, "mandatory"),
        )
        copy(
            self,
            "*.json",
            src=os.path.join(self.source_folder, "optional"),
            dst=os.path.join(awall_dir, "optional"),
        )

        # CLI: awall-cli → usr/sbin/awall
        os.makedirs(sbin_dir, exist_ok=True)
        cli_src = os.path.join(self.source_folder, "awall-cli")
        cli_dst = os.path.join(sbin_dir, "awall")
        copy(self, "awall-cli", src=self.source_folder, dst=sbin_dir, keep_path=False)
        os.rename(os.path.join(sbin_dir, "awall-cli"), cli_dst)
        os.chmod(cli_dst, 0o755)

        # Sample policy
        copy(
            self,
            "sample-policy.json",
            src=self.source_folder,
            dst=os.path.join(awall_dir, "sample"),
            keep_path=False,
        )

        # Empty config dirs (upstream Makefile creates them)
        for d in (
            os.path.join(self.package_folder, "etc", "awall"),
            os.path.join(self.package_folder, "etc", "awall", "optional"),
            os.path.join(self.package_folder, "etc", "awall", "private"),
            os.path.join(awall_dir, "private"),
        ):
            os.makedirs(d, exist_ok=True)

        # usr/share/awall/modules → ../lua/5.5/awall/modules (relative symlink,
        # matches upstream Makefile; conan copy skips symlinks so create manually)
        modules_link = os.path.join(awall_dir, "modules")
        if not os.path.lexists(modules_link):
            os.symlink("../lua/5.5/awall/modules", modules_link)

        # License
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["usr/sbin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["usr/share/awall", "usr/share/lua/5.5/awall"]
