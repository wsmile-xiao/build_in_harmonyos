#!/usr/bin/env python3
"""Conan recipe — aaudit-server 0.7.2 (Alpine Auditor, pure Lua scripts).

aaudit-server is a collection of Lua scripts for auditing Alpine Linux systems.
It is a pure Lua application (noarch, no compilation needed), consisting of:

- aaudit: main audit tool (shell script wrapper)
- aaudit-server.lua: HTTP server for remote audit queries
- aaudit-common.lua: shared Lua library
- aaudit-update-keys, aaudit-repo: key management tools
- aaudit-shell: restricted shell for audit operations
- aaudit.json, aaudit-server.json: configuration files

Build:  pure Lua scripts, no compilation. Install by copying files to target paths.
Deps:   lua5.2, lua5.2-posix, lua5.2-cjson, lua5.2-socket (host environment)
"""
import os, shutil
from conan import ConanFile
from conan.tools.files import download, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AauditServerConan(ConanFile):
    name = "aaudit-server"
    version = "0.7.2"
    description = "Alpine Auditor — aaudit HTTP server and audit tools"
    license = "GPL-2.0-only"  # Alpine aports states "Unknown" but it's GPL based on Alpine convention
    homepage = "https://git.alpinelinux.org/aports/plain/main/aaudit/"
    topics = ("audit", "alpine", "security")
    package_type = "application"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        """Download all source files from conandata.yml sources.

        Each entry is a plain text file (Lua / shell / JSON), so use
        download() — get() would try to unzip them and fail with BadZipFile.
        """
        src = self.conan_data["sources"]["files"]
        for fname, info in src.items():
            url = info["url"]
            self.output.info(f"Downloading {fname}...")
            download(self, url, sha256=info["sha256"], filename=fname)
        # Apply the bugfix patches declared in conandata.yml (0001-0014).
        # Without this call none of the upstream bugs are fixed in the package.
        apply_conandata_patches(self)

    def package(self):
        # Create target directories
        etc_dir = os.path.join(self.package_folder, "etc", "aaudit")
        bin_dir = os.path.join(self.package_folder, "usr", "bin")
        libexec_dir = os.path.join(self.package_folder, "usr", "libexec", "aaudit")
        lua_dir = os.path.join(self.package_folder, "usr", "share", "lua", "5.2", "aaudit")
        for d in [etc_dir, bin_dir, libexec_dir, lua_dir]:
            os.makedirs(d, exist_ok=True)

        src = self.source_folder

        # aaudit-common.lua → /usr/share/lua/5.2/aaudit/common.lua
        shutil.copy2(os.path.join(src, "aaudit-common.lua"),
                     os.path.join(lua_dir, "common.lua"))

        # aaudit-server.lua → /usr/share/lua/5.2/aaudit/server.lua
        shutil.copy2(os.path.join(src, "aaudit-server.lua"),
                     os.path.join(lua_dir, "server.lua"))

        # aaudit → /usr/bin (executable wrapper)
        shutil.copy2(os.path.join(src, "aaudit"),
                     os.path.join(bin_dir, "aaudit"))
        os.chmod(os.path.join(bin_dir, "aaudit"), 0o755)

        # aaudit-update-keys → /usr/bin
        shutil.copy2(os.path.join(src, "aaudit-update-keys"),
                     os.path.join(bin_dir, "aaudit-update-keys"))
        os.chmod(os.path.join(bin_dir, "aaudit-update-keys"), 0o755)

        # aaudit-repo → /usr/bin
        shutil.copy2(os.path.join(src, "aaudit-repo"),
                     os.path.join(bin_dir, "aaudit-repo"))
        os.chmod(os.path.join(bin_dir, "aaudit-repo"), 0o755)

        # aaudit-shell → /usr/libexec/aaudit (restricted shell)
        shutil.copy2(os.path.join(src, "aaudit-shell"),
                     os.path.join(libexec_dir, "aaudit-shell"))
        os.chmod(os.path.join(libexec_dir, "aaudit-shell"), 0o755)

        # aaudit.json → /etc/aaudit
        shutil.copy2(os.path.join(src, "aaudit.json"),
                     os.path.join(etc_dir, "aaudit.json"))

        # aaudit-server.json → /etc/aaudit
        shutil.copy2(os.path.join(src, "aaudit-server.json"),
                     os.path.join(etc_dir, "aaudit-server.json"))

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []