#!/usr/bin/env python3
"""Conan recipe for illustrate 0.0-git20200923.217db48 (HarmonyOS PC).

Illustrate is David Goodsell's biomolecular illustration program: it reads
a PDB coordinate file plus a command-card file on stdin and writes a
non-photorealistic PPM ("P3") rendering of the molecule (DS Goodsell &
AJ Olson (1992) J. Mol. Graphics 10, 235-240).  Upstream is a single
fixed-form F77 source with no build system (README: "gfortran illustrate.f
-o illustrate"); the recipe compiles it with the repo's flang-ohos tool
package and links through the profile's native OHOS clang driver, exactly
like fortran-shlex/2.0.1: flang-ohos ships the Fortran frontend plus the
FortranRuntime/FortranDecimal static libraries but no OHOS sysroot or CRT,
so the final link must come from the platform driver
(tools.build:compiler_executables["c"]) to pick up Scrt1.o, libc, libunwind
and compiler-rt.

Version 0.0-git20200923.217db48 is the upstream git snapshot
(2020-09-23, commit 217db488ce060d8cd0e85433898de50389dffacc, "correct
version").  The upstream repository has no release tags; Debian packages
this same snapshot as illustrate 0.0+git20200923.217db48 and its orig
tarball has an identical file listing (verified locally).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class IllustrateConan(ConanFile):
    name = "illustrate"
    version = "0.0-git20200923.217db48"
    description = (
        "Goodsell-style biomolecular illustration: renders PDB structures "
        "as non-photorealistic PPM images"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/ccsb-scripps/Illustrate"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"illustrate targets a POSIX system, not {self.settings.os}"
            )

    def build_requirements(self):
        # Fortran frontend + FortranRuntime/FortranDecimal (same tool
        # requirement as fortran-shlex/2.0.1; this F77 program uses no
        # modules, so no additional frontend features are needed).
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _tools(self):
        flang_package = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(flang_package, "bin", "flang")
        fortran_runtime = os.path.join(
            flang_package, "lib", "libFortranRuntime.a"
        )
        fortran_decimal = os.path.join(
            flang_package, "lib", "libFortranDecimal.a"
        )

        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        # flang-ohos carries no OHOS sysroot or Clang resource directory, so
        # the platform driver from the profile does the final link (it
        # supplies Scrt1.o, libc, libunwind and compiler-rt).
        cc = compilers.get("c", "/data/service/hnp/bin/clang")

        for tool in (flang, cc, fortran_runtime, fortran_decimal):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration(
                    "required native HarmonyOS build tool is missing: {}".format(
                        tool
                    )
                )
        return flang, cc, fortran_runtime, fortran_decimal

    def build(self):
        flang, cc, fortran_runtime, fortran_decimal = self._tools()

        source = os.path.join(self.source_folder, "illustrate.f")
        obj = os.path.join(self.build_folder, "illustrate.o")
        self.run(
            f'"{flang}" -O2 -c "{source}" -o "{obj}"',
            env="conanbuild",
        )

        # .f is fixed-form F77; flang compiles it directly.  The link goes
        # through the profile's native clang driver with the Fortran runtime
        # libraries passed explicitly (the platform driver does not know
        # about them).  -lm is required: illustrate calls sqrt/sin/cos/exp.
        illustrate = os.path.join(self.build_folder, "illustrate")
        self.run(
            f'"{cc}" "{obj}" "{fortran_runtime}" "{fortran_decimal}" '
            f'-lm -o "{illustrate}"'
        )
        if not os.path.isfile(illustrate):
            raise ConanException("expected build output missing: illustrate")

    def package(self):
        copy(
            self,
            "illustrate",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Upstream ships its documented sample scene (2hhb.inp + 2hhb.pdb,
        # the hemoglobin example from README); installing it keeps
        # `illustrate < share/illustrate/2hhb.inp` working out of the box.
        copy(
            self,
            "2hhb.inp",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "illustrate"),
            keep_path=False,
        )
        copy(
            self,
            "2hhb.pdb",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "illustrate"),
            keep_path=False,
        )

        bin_path = os.path.join(self.package_folder, "bin", "illustrate")
        os.chmod(bin_path, 0o755)
        self._sign_ohos_binary(bin_path)

    def _sign_ohos_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return

        signer = self.conf.get("user.ohos:sign_tool", default="", check_type=str)
        signer = (
            signer
            or os.environ.get("OHOS_SIGN_TOOL", "")
            or shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; skipping OHOS ELF signing"
            )
            return

        objcopy = self.conf.get("user.ohos:objcopy", default="", check_type=str)
        objcopy = (
            objcopy
            or os.environ.get("OHOS_OBJCOPY", "")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if os.path.isfile(objcopy):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}"',
                ignore_errors=True,
            )

        signed = f"{path}.signed"
        self.run(
            f'"{signer}" sign -inFile "{path}" '
            f'-outFile "{signed}" -selfSign 1'
        )
        if not os.path.isfile(signed):
            raise ConanException(f"binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.conf_info.define("user.illustrate:version", self.version)
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
