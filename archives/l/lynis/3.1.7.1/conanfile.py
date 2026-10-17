#!/usr/bin/env python3
"""Conan recipe for lynis 3.1.7 — shell script security auditing tool.

Lynis is a pure shell script tool with no compiled binaries. The upstream
shebang is #!/bin/sh; on OpenHarmony the bash interpreter lives at
/data/service/hnp/bin/bash, so patch 0004 rewrites the shebang across the
63 script files. Lynis' main entry uses WORKDIR=$(pwd) to find ./include,
so the package keeps the whole tree together under share/lynis/ and a
wrapper at bin/lynis cd's into it before exec'ing the real entry.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LynisConan(ConanFile):
    name = "lynis"
    version = "3.1.7.1"
    description = "Security and system auditing tool (shell script based)"
    license = "GPL-3.0"
    homepage = "https://cisofy.com/lynis/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git"
    topics = ("security", "auditing", "hardening", "compliance")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True  # pure shell scripts, no build step

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "ohos-ps", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self)  # source_folder = s/, patches resolve with strip:1

    def package_id(self):
        del self.info.settings.arch  # pure shell, arch-independent
        del self.info.settings.compiler
        del self.info.settings.build_type

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply shebang + HarmonyOS runtime adaptation patches.
        apply_conandata_patches(self)
        # Static syntax check on the main entry — catches broken shell
        # syntax early without needing to exec lynis (HMDFS noexec safe).
        lynis_script = os.path.join(self.source_folder, "lynis")
        self.run(f"sh -n {lynis_script}", env="conanrun")

    def package(self):
        # Install the OHOS ps compatibility wrapper (Toybox ps lacks the
        # procps -C/-ax/-aux flags Lynis uses; the wrapper falls back to
        # the native listing form and lets Lynis filter by name).
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "ohos-ps", src=self.export_sources_folder, dst=bin_dir)
        self.output.info("Installed OHOS ps compatibility wrapper as bin/ps")
        wrapper_src = os.path.join(bin_dir, "ohos-ps")
        wrapper_dst = os.path.join(bin_dir, "ps")
        os.replace(wrapper_src, wrapper_dst)

        # Install the lynis tree to share/lynis/ — lynis' main entry uses
        # WORKDIR=$(pwd) to find ./include, so the tree must stay together
        # and be run from its own directory (can't flatten to bin/).
        # Exclude ohos-ps (it's a wrapper we ship separately at bin/ps;
        # export_sources copies it into source_folder, so filter it out
        # here to avoid leaking a stray #!/bin/sh script into share/lynis/).
        share_dir = os.path.join(self.package_folder, "share", "lynis")
        os.makedirs(share_dir, exist_ok=True)
        for item in os.listdir(self.source_folder):
            if item == "ohos-ps":
                continue
            s = os.path.join(self.source_folder, item)
            d = os.path.join(share_dir, item)
            if os.path.isdir(s):
                copy(self, "*", src=s, dst=d)
            else:
                copy(self, item, src=self.source_folder, dst=share_dir)

        # Install default/developer profiles to etc/lynis/ so lynis can
        # locate them via SCRIPT_DIR/../etc/lynis (patch 0003 adds the
        # SCRIPT_DIR search path).
        etc_dir = os.path.join(self.package_folder, "etc", "lynis")
        os.makedirs(etc_dir, exist_ok=True)
        copy(self, "default.prf", src=self.source_folder, dst=etc_dir)
        copy(self, "developer.prf", src=self.source_folder, dst=etc_dir)

        # Install the man page.
        copy(self, "lynis.8", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man8"))

        # Install a wrapper at bin/lynis that cd's into share/lynis/ before
        # invoking the real entry. This preserves the WORKDIR=$(pwd)
        # contract the upstream scripts rely on (include/, db/, plugins/
        # all resolved relative to CWD).
        lynis_wrapper = os.path.join(bin_dir, "lynis")
        with open(lynis_wrapper, "w", encoding="utf-8") as fh:
            fh.write(
                "#!/data/service/hnp/bin/bash\n"
                "# lynis wrapper — cd into the tree so WORKDIR=$(pwd) finds include/.\n"
                'cd "$(dirname "$0")/../share/lynis" || exit 1\n'
                'exec /data/service/hnp/bin/bash lynis "$@"\n'
            )

        # Ensure executable bit on wrapper, real entry, and ps wrapper.
        # os.chmod may fail on HMDFS (noexec); fall back to chmod binary.
        # If both fail, surface loudly instead of shipping non-executable
        # scripts that break downstream with "Permission denied".
        for target in (lynis_wrapper,
                       os.path.join(share_dir, "lynis"),
                       wrapper_dst):
            try:
                os.chmod(target, 0o755)
            except (IOError, OSError):
                r = subprocess.run(["chmod", "755", target], capture_output=True)
                if r.returncode != 0:
                    msg = (
                        f"chmod binary failed rc={r.returncode} for {target}: "
                        f"{r.stderr.decode(errors='replace').strip()}"
                    )
                    self.output.warn(msg)
                    raise ConanException(msg)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
