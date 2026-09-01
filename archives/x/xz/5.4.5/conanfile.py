#!/usr/bin/env python3
"""Conan recipe for xz 5.4.5 — Autotools build system (configure + make).

XZ Utils provide liblzma (LZMA2 compression library) and xz/xzdec tools.
Build: ./configure && make && make check && make install
No external dependencies.

Adaptation lessons applied:
- E007: config.guess cannot guess OHOS — patch config.guess and config.sub.
- E011: config.status temp-dir creation may hit Permission denied on
  hmdfs — mktemp wrapper + umask 077→022 replacement in configure.
- OHOS has no /bin/sh — scripts disabled, CONFIG_SHELL propagated.
"""
import os
import shutil
import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class XzConan(ConanFile):
    name = "xz"
    version = "5.4.5"
    description = "XZ Utils — general-purpose data compression with high ratio (LZMA2)"
    license = "0BSD"
    homepage = "https://tukaani.org/xz/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
        # causing config.status to fail. Create a mktemp wrapper that fixes perms.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True, parents=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        tc = AutotoolsToolchain(self)
        # OHOS: scripts (xzdiff, xzgrep, etc.) use /bin/sh which doesn't exist.
        # Disable scripts to skip test_scripts.sh and avoid installing broken scripts.
        tc.configure_args.append("--disable-scripts")
        # Link binaries (xz, lzmadec, lzmainfo) statically against liblzma.a
        # so they don't need LD_LIBRARY_PATH at runtime (L2 smoke test).
        # liblzma.so is still built for consumers who need shared linking.
        tc.extra_ldflags.append("-static")
        tc.generate()

        # OHOS: override CONFIG_SHELL — profile may point to non-existent
        # /data/service/hnp/bin/bash. Use bash from usr/local if available,
        # otherwise fall back to /bin/sh.
        env = Environment()
        bash_path = shutil.which("bash") or "/bin/sh"
        env.define("CONFIG_SHELL", bash_path)
        env.define("SHELL", bash_path)
        env.prepend_path("PATH", str(wrapper_dir))
        # Set LD_LIBRARY_PATH for make check (test programs need liblzma.so
        # from build tree, but rpath points to install prefix /lib)
        lib_build_dir = os.path.join(self.build_folder, "src", "liblzma", ".libs")
        env.prepend_path("LD_LIBRARY_PATH", lib_build_dir)
        env.vars(self).save_script("ohos_env")

    def _fix_conanbuild_shell(self):
        """Patch generated env scripts to fix non-existent tool paths from profile.

        Host profile references /data/service/hnp/bin/{bash,clang,clang++}
        which may not exist on this OHOS device.  Replace with actual paths.
        """
        clang = shutil.which("clang") or "clang"
        clangxx = shutil.which("clang++") or "clang++"
        bash = shutil.which("bash") or "/bin/sh"
        bad_prefix = "/data/service/hnp/bin"
        good_prefix = os.path.dirname(clang)
        # Fix all generated env scripts in the generators folder
        if os.path.isdir(self.generators_folder):
            for fname in os.listdir(self.generators_folder):
                if not fname.endswith(".sh"):
                    continue
                fpath = os.path.join(self.generators_folder, fname)
                with open(fpath, "r") as f:
                    content = f.read()
                if bad_prefix not in content:
                    continue
                content = content.replace(f"{bad_prefix}/clang++", clangxx)
                content = content.replace(f"{bad_prefix}/clang", clang)
                content = content.replace(f"{bad_prefix}/bash", bash)
                with open(fpath, "w") as f:
                    f.write(content)

    def build(self):
        apply_conandata_patches(self)
        # E011 (CI #29098): config.status applies umask 077 internally,
        # creating temp dirs with 0700 perms — HMDFS owner/UID mismatch
        # → Permission denied. Replace with umask 022 in configure script.
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r") as f:
            content = f.read()
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as f:
                f.write(content)
        # OHOS: fix CONFIG_SHELL in generated scripts before autotools runs
        self._fix_conanbuild_shell()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # L1: Run upstream official test suite (make check)
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["lzma"]
        # CLI tools installed by autotools to bin/
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            self.output.info(f"PATH={bindir}")
            self.cpp_info.bindirs = ["bin"]
