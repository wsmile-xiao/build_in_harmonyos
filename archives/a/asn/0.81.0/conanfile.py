#!/usr/bin/env python3
"""Conan recipe for asn 0.81.0 — pure Bash script project.

asn is an ASN / IPv4 / IPv6 / Prefix / AS Path / Organization lookup
and server tool. It is a pure Bash script with no compilation step;
"installation" consists of copying the script to a bin/ directory.

Platform adaptations for OHOS:
  1. Shebang already portable: #!/usr/bin/env bash (no fix needed)
  2. No compilation — script-only package
  3. Runtime dependencies (bash 4+, curl, jq, whois, host, mtr, nmap,
     grepcidr, ipcalc, aha) are system tools, not Conan dependencies

R32: OHOS 适配通过 /usr/bin/env bash 实现平台无关，无需条件判断。
R38: 工具类包，commands.json 已在软件级目录声明。
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AsnConan(ConanFile):
    name = "asn"
    version = "0.81.0"
    description = "ASN/IPv4/IPv6/Prefix/AS Path/Organization lookup and server tool"
    license = "MIT"
    homepage = "https://github.com/nitefood/asn"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Bash script — no compilation step
        # Verify the main script exists
        asn_script = os.path.join(self.source_folder, "asn")
        if not os.path.isfile(asn_script):
            raise Exception(f"asn script not found at {asn_script}")
        self.output.info("asn script verified — pure Bash, no compilation needed")

    def package(self):
        src = self.source_folder
        dst = self.package_folder

        # Main script → bin/
        copy(self, "asn", src=src, dst=os.path.join(dst, "bin"), keep_path=False)

        # Make script executable
        asn_bin = os.path.join(dst, "bin", "asn")
        if os.path.isfile(asn_bin):
            os.chmod(asn_bin, os.stat(asn_bin).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        # Man page → share/man/man1/
        copy(self, "asn.1", src=src, dst=os.path.join(dst, "share", "man", "man1"), keep_path=False)

        # Documentation → share/doc/asn/
        copy(self, "LICENSE", src=src, dst=os.path.join(dst, "share", "doc", "asn"), keep_path=False)
        copy(self, "README.md", src=src, dst=os.path.join(dst, "share", "doc", "asn"), keep_path=False)

        # Bash completion → share/bash-completion/completions/
        copy(self, "asn", src=os.path.join(src, "bash-completion"),
             dst=os.path.join(dst, "share", "bash-completion", "completions"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
