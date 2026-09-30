#!/usr/bin/env python3
"""Conan recipe for tmatrix 1.4 (digital-rain terminal effect) on HarmonyOS PC.

Upstream: https://github.com/M4444/TMatrix (GPL-2.0-only), CMake 3.8+, C++17,
single executable `tmatrix` linked against ncurses (wide-char flavour).

HarmonyOS adaptation (see notes.md for the full evidence):
  - E092: CMake has no HarmonyOS platform module, so the toolchain declares
    CMAKE_SYSTEM_NAME=Linux with CMAKE_SYSTEM_PROCESSOR=aarch64; the cross
    triplet itself is supplied by the profile's compiler_executables conf.
  - E011: upstream `set(CMAKE_CXX_FLAGS ...)` / `set(CMAKE_CXX_FLAGS_RELEASE ...)`
    clobbers the toolchain-provided flags (including the libc++ selection and
    the optimisation/symbol settings Conan injects). patches/0001 keeps the
    upstream warning set but appends instead of overwriting.
  - The upstream `find_package(Curses REQUIRED)` + `link_libraries(${CURSES_LIBRARIES})`
    is replaced with `find_package(ncurses CONFIG REQUIRED)` +
    `link_libraries(ncurses::ncurses)` (patches/0001) so the conan ncurses/6.6
    static package supplies both the include directory and the archive. The
    FindCurses module has no sysroot notion, so in this cross build it either
    fails outright ("Could NOT find Curses (missing: CURSES_LIBRARY)") or, once
    handed the archive, contributes that archive alone with no include path --
    in which case `#include <ncurses.h>` fails to compile. Resolving the
    dependency through its CONFIG package carries both halves.
  - The same patch makes `gzip` optional for the man page target. That target is
    part of `all`, so a build image without gzip would fail for a cosmetic
    detail; the uncompressed man page is installed instead.
  - E077: the OHOS kernel only loads an ELF that carries a *valid* `.codesign`
    section. A freshly linked executable only gets the linker's unsigned 4096B
    placeholder, so execve() fails with EPERM and every caller sees status 126
    ("operation not permitted") no matter what the file mode is. package()
    therefore runs the four-step E077 flow (remove .codesign -> sign -selfSign 1
    -> restore 0o755) over the packaged ELF; see _sign_packaged_elfs().
  - The `TERMINFO` runenv is deliberately left alone; see package_info().
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


def _is_elf_file(path):
    """True when `path` starts with the ELF magic (qemu/11.1.1 precedent)."""
    try:
        with open(path, "rb") as handle:
            return handle.read(4) == b"\x7fELF"
    except OSError:
        return False


class TmatrixConan(ConanFile):
    name = "tmatrix"
    version = "1.4"
    description = "tmatrix - terminal based replica of the digital rain from The Matrix"
    license = "GPL-2.0-only"
    homepage = "https://github.com/M4444/TMatrix"
    url = "https://github.com/M4444/TMatrix"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS is a Linux-kernel platform, accept both enumerations.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tmatrix {self.version} supports Linux and OHOS, got os={self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # E092: CMake has no `HarmonyOS` platform module -> "System is unknown
        # to cmake". Declare Linux + aarch64 so cmake configures in
        # cross-compile mode against the OHOS toolchain from the profile conf.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Upstream defaults the install prefix to /usr; keep the package
        # self-contained instead (R49 spirit: no writes to a shared prefix).
        tc.cache_variables["CMAKE_INSTALL_PREFIX"] = "/"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # R9: -j1 (deterministic, HMDFS-friendly)
        self.run(f'cmake --build "{self.build_folder}" -- -j1')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_packaged_elfs()

    @staticmethod
    def _find_ohos_tool(name):
        """Locate an OHOS HNP tool, preferring the documented absolute path."""
        return shutil.which(name) or (
            f"/data/service/hnp/bin/{name}"
            if os.path.isfile(f"/data/service/hnp/bin/{name}")
            else None
        )

    def _sign_ohos_elf(self, target):
        """Apply the E077 four-step flow to one packaged ELF.

        Step 1 drops the linker's unsigned `.codesign` placeholder (the signer
        refuses to overwrite an existing section: "section already exists",
        SignElf 29), step 3 self-signs into a sibling file and step 4 restores
        0o755 because signing zeroes the mode. `env -u LD_LIBRARY_PATH` keeps
        the signer resolving its own system libraries instead of the profile's
        SDK path (jupp/3.1.41, blupimania/1.6.3).
        """
        signer = self._find_ohos_tool("binary-sign-tool")
        if not signer:
            # Never claim a signature that was not made (jupp/3.1.41), and do
            # not let self.run fail with 127 on hosts without the OHOS SDK.
            self.output.warning(
                "binary-sign-tool unavailable; packaged ELF stays unsigned "
                "(E077 exec will fail with EPERM/126 on an OHOS device)"
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
        """Self-sign every packaged executable (only bin/tmatrix is an ELF).

        The bash-completion and zsh completion files installed alongside it are
        shell scripts, so they are skipped on the ELF magic check.
        """
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
        # Application package: consumers execute bin/tmatrix.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "tmatrix")
        self.cpp_info.set_property("cmake_target_name", "tmatrix::tmatrix")
        # No runenv_info override for TERMINFO.
        #
        # The terminfo database ships inside the ncurses package, and
        # ncurses/6.6 already exports TERMINFO/TERMINFO_DIRS pointing at it
        # through its own runenv_info. Conan does not forward a transitive
        # dependency's runenv, and the path cannot be recomputed here either:
        # in a consumer that resolves tmatrix from the cache, the dependency's
        # `package_folder` is None (and its includedirs are relative), so any
        # path built from it would be wrong -- which is exactly the bug an
        # earlier revision of this recipe shipped, pointing TERMINFO at a
        # share/terminfo directory inside this package that is never created.
        #
        # Consumers that need the packaged database should require
        # ncurses/6.6 directly; tmatrix itself falls back to the system
        # terminfo, which is what a normal terminal session uses anyway.
