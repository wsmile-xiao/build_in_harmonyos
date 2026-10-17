#!/usr/bin/env python3
"""Conan recipe — asm6809 2.15

Portable cross-assembler targeting Motorola 6809 and Hitachi 6309.
This is a command-line tool (application), not a library.

Build system: Autotools (configure.ac, Makefile.am, autogen.sh).
The upstream tarball is a git snapshot without pre-generated configure,
so autoreconf is run in build() to generate it.

OHOS-specific adaptations:
  - CC wrapper signs output binaries (E077) so configure conftest
    programs and the final asm6809 binary can execute.
  - -fuse-ld=/data/service/hnp/bin/ld to use GNU ld instead of the
    broken OHOS SDK lld (missing libxml2.so.16 dependency).
  - Build on tmpfs (/data/storage/el2/base) to avoid HMDFS umask 077
    quirk that breaks config.status (E011/E002).
  - No --host/--build/--target flags (native build, not cross-compile).

License: GPL-3.0-or-later
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Asm6809Conan(ConanFile):
    name = "asm6809"
    version = "2.15"
    description = "Portable cross-assembler targeting Motorola 6809 and Hitachi 6309"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jmparis/asm6809"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc_wrapper_path(self):
        """Return path to the CC wrapper script that signs output binaries."""
        wrapper = os.path.join(self.build_folder, ".cc-wrapper.sh")
        return wrapper

    def _create_cc_wrapper(self):
        """Create a CC wrapper script that calls clang with GNU ld and
        signs the output binary with binary-sign-tool (E077)."""
        wrapper = self._cc_wrapper_path()
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        clang = "/data/service/hnp/bin/clang"
        ld_flag = "-fuse-ld=/data/service/hnp/bin/ld"
        content = f"""#!/data/service/hnp/bin/bash
# CC wrapper for OHOS: clang + GNU ld + sign output (E077)
SIGN_TOOL="{sign_tool}"
LD_FLAG="{ld_flag}"
CLANG="{clang}"

OUTPUT=""
prev=""
for arg in "$@"; do
    if [ "$prev" = "-o" ]; then
        OUTPUT="$arg"
    fi
    prev="$arg"
done

$CLANG $LD_FLAG "$@"
RET=$?

if [ $RET -eq 0 ] && [ -n "$OUTPUT" ] && [ -f "$OUTPUT" ]; then
    if head -c 4 "$OUTPUT" 2>/dev/null | grep -q $'\\x7fELF'; then
        # Remove existing .codesign if present, then re-sign (E077 four-step)
        /data/service/hnp/bin/llvm-objcopy --remove-section .codesign "$OUTPUT" 2>/dev/null
        SIGNED="${{OUTPUT}}.signed"
        "$SIGN_TOOL" sign -selfSign 1 -inFile "$OUTPUT" -outFile "$SIGNED" > /dev/null 2>&1
        if [ -f "$SIGNED" ]; then
            mv "$SIGNED" "$OUTPUT"
            chmod 755 "$OUTPUT"
        fi
    fi
fi
exit $RET
"""
        with open(wrapper, "w") as f:
            f.write(content)
        os.chmod(wrapper, 0o755)
        return wrapper

    def _choose_build_root(self):
        """Return a tmpfs build root to avoid HMDFS umask 077 quirk (E011)."""
        root = "/data/storage/el2/base/.conan-build-asm6809-2.15"
        work = os.path.join(root, "src")
        install_dir = os.path.join(root, "install")
        return work, install_dir

    def generate(self):
        # No AutotoolsToolchain needed — we run configure manually
        # with a CC wrapper for binary signing.
        pass

    def build(self):
        apply_conandata_patches(self)
        work, install_dir = self._choose_build_root()

        # Copy patched sources to tmpfs
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        self.run(f'cp -a "{self.source_folder}/." "{work}/"')

        tmpdir = os.path.join(os.path.dirname(work), "build-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.makedirs(install_dir, exist_ok=True)

        # Create CC wrapper for binary signing (E077)
        wrapper = self._create_cc_wrapper()

        # R33: Get compiler from Conan conf, not undefined shell variables
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "/data/service/hnp/bin/clang"

        # Build environment
        env = (
            f"PATH=/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:"
            + os.environ.get("PATH", "")
            + f" TMPDIR={tmpdir} CONFIG_SHELL=/data/service/hnp/bin/bash"
            + f" CC={wrapper}"
            + f' CFLAGS="-fPIC -O2"'
            + f' LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld"'
        )

        # Step 1: autoreconf to generate configure (git snapshot, no pre-generated configure)
        self.run(f'bash -c \'cd {work} && export {env} && autoreconf -fi\'')

        # Step 2: configure (native build, no --host)
        self.run(f'bash -c \'cd {work} && export {env} && umask 022 && ./configure --prefix={install_dir}\'')

        # Step 3: make
        self.run(f'bash -c \'cd {work} && export {env} && make -j1\'')

        # Step 4: make install
        self.run(f'bash -c \'cd {work} && export {env} && make install\'')

        # Step 5: Re-sign installed binary (install -c may strip signature)
        bin_path = os.path.join(install_dir, "bin", "asm6809")
        if os.path.isfile(bin_path):
            subprocess.run([
                "/data/service/hnp/bin/llvm-objcopy",
                "--remove-section", ".codesign", bin_path
            ], check=False)
            signed = bin_path + ".signed"
            subprocess.run([
                "/data/service/hnp/bin/binary-sign-tool",
                "sign", "-selfSign", "1",
                "-inFile", bin_path, "-outFile", signed
            ], check=True)
            shutil.move(signed, bin_path)
            os.chmod(bin_path, 0o755)

        self._store = (work, install_dir)

    def package(self):
        store = getattr(self, "_store", None)
        if store is None:
            return
        _work, install_dir = store
        # Copy bin/
        src_bin = os.path.join(install_dir, "bin")
        if os.path.isdir(src_bin):
            dst_bin = os.path.join(self.package_folder, "bin")
            shutil.copytree(src_bin, dst_bin, dirs_exist_ok=True)
        # Copy man page if available
        src_man = os.path.join(install_dir, "share", "man", "man1")
        if os.path.isdir(src_man):
            dst_man = os.path.join(self.package_folder, "share", "man", "man1")
            shutil.copytree(src_man, dst_man, dirs_exist_ok=True)
        # Copy license
        from conan.tools.files import copy as conan_copy
        conan_copy(self, "COPYING.GPL", src=self.source_folder,
                   dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # asm6809 is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
