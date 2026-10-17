#!/usr/bin/env python3
"""Conan recipe for lutefisk 1.0.7 (de novo peptide sequencing) on HarmonyOS PC.

Upstream: lutefisk 1.0.7 (Richard S. Johnson, 1995-2006), GPL-2.0-or-later.
Source: the Debian `+dfsg` repack of the original SourceForge `lutefiskxp`
tarball (upstream site www.hairyfatguy.com/lutefisk is gone); upstream homepage
recorded in the Debian .dsc is used as `homepage`.

Build system: hand-written per-platform Makefiles (src/Makefile.<os>). The Linux
variant is a flat `.c.o` rule plus one explicit link line, so `make -f
Makefile.linux` is driven directly and CC/CFLAGS/LFLAGS are injected from the
Conan profile (R33: never bare ${CC}).

HarmonyOS adaptation notes (full evidence in notes.md):
  - The Makefile's `CC= gcc -O` / `CFLAGS= -D__LINUX` are plain (non-`override`)
    assignments, so command-line values from this recipe win; `-D__LINUX`
    selects the little-endian / 32-bit-int typedefs in LutefiskDefinitions.h,
    which is also what aarch64 needs.
  - patches/0001 adds the missing <math.h>: sqrt()/fabs() were implicitly
    declared, so C89 implicit `int` truncated the double return value on LP64.
  - patches/0002..0005 clean up the printf conversions and the pathname buffers
    (see conandata.yml for one line per patch).
  - Only libc and libm are needed; the program ships its own getopt for
    Mac/Win32 and does not compile it on Linux.
  - E077: the OHOS kernel only loads an ELF carrying a valid `.codesign`
    section, so package() self-signs the packaged executable when the OHOS
    signing tools are present, and warns (never fakes success) when they are not.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Runtime data the program reads at run time: params/residues/details plus the
# searchable sequence database. Installed under share/lutefisk so a consumer can
# point -d/-p/-r/-s at them.
DATA_FILES = (
    "Lutefisk.details",
    "Lutefisk.residues",
    "Lutefisk.params",
    "Lutefisk.paramsLCQ",
    "Lutefisk.lcq_params",
    "Lutefisk.qtof_params",
    "database.sequence",
)

DOC_FILES = (
    "License.txt",
    "README.txt",
    "HISTORY.txt",
)

# The upstream sample spectrum plus the reference result the upstream author
# published for it (2005, LutefiskXP v1.0.4). The reference file is what the
# regression test compares the de novo peptide ranking against.
EXAMPLE_FILES = (
    "Qtof_ELVISLIVESK.dta",
    "Qtof_ELVISLIVESK.lut",
)

SHARE_DIR = os.path.join("share", "lutefisk")
EXAMPLES_DIR = os.path.join(SHARE_DIR, "examples")


def _is_elf_file(path):
    """True when `path` starts with the ELF magic."""
    try:
        with open(path, "rb") as handle:
            return handle.read(4) == b"\x7fELF"
    except OSError:
        return False


class LutefiskConan(ConanFile):
    name = "lutefisk"
    version = "1.0.7"
    description = "De novo interpretation of peptide CID tandem mass spectra"
    license = "GPL-2.0-or-later"
    homepage = "http://www.hairyfatguy.com/lutefisk/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS is a Linux-kernel platform, accept both enumerations.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lutefisk {self.version} supports Linux and OHOS, got os={self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Apply here, not in build(): build() compiles straight out of
        # source_folder, and a patch applied after a copy step would silently
        # do nothing (the "Apply patch" log line still prints).
        apply_conandata_patches(self)

    def build(self):
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang")

        # -D__LINUX keeps upstream's own platform typedefs (little-endian,
        # 32-bit INT_4/UINT_4) which is what the OHOS aarch64 target needs.
        cflags = "-D__LINUX -O2 -fPIE"
        # RELRO + immediate binding for the L4 hardening gate; -pie because the
        # profile's clang defaults to PIE but the Makefile links by hand.
        lflags = "-pie -Wl,-z,relro,-z,now -lm -o"

        self.run(
            f'make -f Makefile.linux -j1 CC="{cc}" CFLAGS="{cflags}" LFLAGS="{lflags}"',
            cwd=os.path.join(self.source_folder, "src"),
        )

    def package(self):
        top = self.source_folder
        build_src = os.path.join(top, "src")
        copy(self, "lutefisk", src=build_src, dst=os.path.join(self.package_folder, "bin"))
        share = os.path.join(self.package_folder, SHARE_DIR)
        for name in DATA_FILES + DOC_FILES:
            copy(self, name, src=top, dst=share)
        for name in EXAMPLE_FILES:
            copy(self, name, src=top, dst=os.path.join(self.package_folder, EXAMPLES_DIR))
        if str(self.settings.os) == "OHOS":
            self._sign_packaged_elfs()

    @staticmethod
    def _find_ohos_tool(name):
        """Locate an OHOS HNP tool, preferring the documented absolute path."""
        import shutil

        found = shutil.which(name)
        if found:
            return found
        absolute = f"/data/service/hnp/bin/{name}"
        return absolute if os.path.isfile(absolute) else None

    def _sign_ohos_elf(self, target):
        """Apply the E077 four-step self-sign flow to one packaged ELF.

        Step 1 drops the linker's unsigned `.codesign` placeholder (the signer
        refuses to overwrite an existing section), step 3 self-signs into a
        sibling file, step 4 restores 0o755 because signing zeroes the mode.
        """
        signer = self._find_ohos_tool("binary-sign-tool")
        if not signer:
            self.output.warning(
                "binary-sign-tool unavailable; packaged ELF stays unsigned "
                "(E077: exec fails with EPERM/126 on a real OHOS device)"
            )
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        if objcopy:
            self.run(
                f'env -u LD_LIBRARY_PATH "{objcopy}" --remove-section .codesign "{target}"'
                " 2>/dev/null || true"
            )
        signed = f"{target}.signed"
        self.run(
            f'env -u LD_LIBRARY_PATH "{signer}" sign -inFile "{target}" '
            f'-outFile "{signed}" -selfSign 1'
        )
        if not os.path.isfile(signed):
            raise ConanException(f"binary-sign-tool produced no output for {target}")
        os.replace(signed, target)
        os.chmod(target, 0o755)

    def _sign_packaged_elfs(self):
        """Self-sign every packaged executable (only bin/lutefisk is an ELF)."""
        bin_dir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bin_dir):
            return
        for name in sorted(os.listdir(bin_dir)):
            path = os.path.join(bin_dir, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            if not _is_elf_file(path):
                continue
            self._sign_ohos_elf(path)
            self.output.info(f"E077: self-signed {name}")

    def package_info(self):
        # Application package: consumers execute bin/lutefisk and point it at
        # the data files under share/lutefisk.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "lutefisk")
        self.cpp_info.set_property("cmake_target_name", "lutefisk::lutefisk")
