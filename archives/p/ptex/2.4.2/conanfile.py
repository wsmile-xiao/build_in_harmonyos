"""Ptex 2.4.2 shared library and ptxinfo for HarmonyOS PC."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class PtexConan(ConanFile):
    name = "ptex"
    version = "2.4.2"
    package_type = "shared-library"
    description = "Per-face texture mapping library"
    homepage = "https://github.com/wdas/ptex"
    license = "BSD-3-Clause"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def requirements(self):
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("PTEX_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["PTEX_BUILD_STATIC_LIBS"] = False
        tc.cache_variables["PTEX_BUILD_SHARED_LIBS"] = True
        tc.cache_variables["PTEX_VER"] = "v2.4.2"
        tc.cache_variables["PTEX_SHA"] = "a9418bf808de9470c0226c7fab879ddd2745bff4"
        tc.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not signer or not readelf:
            raise ConanInvalidConfiguration("OHOS ELF signer/readelf missing")
        original = Path(path)
        pending = original.with_name(original.name + ".ptex-signing")
        signed = original.with_name(original.name + ".ptex-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale signing sibling")
        try:
            shutil.copy2(original, pending)
            subprocess.run([signer, "sign", "-inFile", str(pending),
                            "-outFile", str(signed), "-selfSign", "1"],
                           check=True, capture_output=True, text=True, timeout=40)
            sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                      capture_output=True, text=True, timeout=20)
            if ".codesign" not in sections.stdout:
                raise ConanException("signed ELF lacks .codesign section")
            os.chmod(signed, original.stat().st_mode)
            os.replace(signed, original)
        finally:
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])
        libdir = Path(self.build_folder, "src", "ptex")
        if str(self.settings.os) == "OHOS":
            libraries = [p for p in libdir.glob("libPtex.so*")
                         if p.is_file() and not p.is_symlink()]
            if len(libraries) != 1:
                raise ConanException("expected one real Ptex shared library")
            self._sign_elf(libraries[0])
            for name in ("wtest", "rtest", "ftest", "halftest"):
                binary = Path(self.build_folder, "src", "tests", name)
                if not binary.is_file():
                    raise ConanException("missing upstream test binary: " + name)
                self._sign_elf(binary)
            self._sign_elf(Path(self.build_folder, "src", "utils", "ptxinfo"))
        runtime_libdir = shlex.quote(str(libdir))
        self.run(
            f"LD_LIBRARY_PATH={runtime_libdir}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}} "
            "ctest --output-on-failure -j1",
            cwd=self.build_folder,
            env=["conanbuild", "conanrun"],
        )
        self.output.info("PTEX_UPSTREAM_4_OF_4_PASS")

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS":
            libdir = Path(self.package_folder, "lib")
            libraries = [p for p in libdir.glob("libPtex.so*")
                         if p.is_file() and not p.is_symlink()]
            if len(libraries) != 1:
                raise ConanException("expected one installed Ptex shared library")
            self._sign_elf(libraries[0])
            self._sign_elf(Path(self.package_folder, "bin", "ptxinfo"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["Ptex"]
        self.cpp_info.set_property("cmake_file_name", "Ptex")
        self.cpp_info.set_property("cmake_target_name", "Ptex::Ptex")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
