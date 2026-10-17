"""liblo 0.32 OSC library for HarmonyOS PC."""

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class LibloConan(ConanFile):
    name = "liblo"
    version = "0.32"
    package_type = "shared-library"
    description = "Lightweight Open Sound Control implementation"
    homepage = "https://liblo.sourceforge.net/"
    license = "LGPL-2.1-or-later"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("LIBLO_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["WITH_TOOLS"] = False
        tc.cache_variables["WITH_EXAMPLES"] = False
        tc.cache_variables["WITH_TESTS"] = True
        tc.cache_variables["WITH_CPP_TESTS"] = True
        tc.cache_variables["ENABLE_NETWORK_TESTS"] = True
        tc.cache_variables["THREADING"] = True
        tc.cache_variables["WITH_STATIC"] = False
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
        pending = original.with_name(original.name + ".lo-signing")
        signed = original.with_name(original.name + ".lo-signed")
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
        cmake.configure(build_script_folder="cmake")
        cmake.build(build_tool_args=["-j1"])
        if str(self.settings.os) == "OHOS":
            real_libraries = [p for p in Path(self.build_folder).glob("liblo.so*")
                              if p.is_file() and not p.is_symlink()]
            if len(real_libraries) != 1:
                raise ConanException("expected one real liblo shared library")
            self._sign_elf(real_libraries[0])
            for name in ("testlo", "test_bidirectional_tcp", "subtest",
                         "cpp_test", "cpp_test_exceptions"):
                binary = Path(self.build_folder, "tests", name)
                if not binary.is_file():
                    raise ConanException("missing upstream test binary: " + name)
                self._sign_elf(binary)
        # Conan activates conanbuild/conanrun inside self.run(), so place the
        # build-tree loader path in the command after that activation.
        build_libdir = shlex.quote(self.build_folder)
        # The worker's cache TMPDIR can reject AF_UNIX bind even when it is
        # writable. Application-private files storage supports socket inodes;
        # each test invocation gets its own short directory, never /tmp or the
        # HMDFS build tree. Put TMPDIR after Conan's environment activation.
        socket_parent = ("/data/storage/el2/base/files"
                         if str(self.settings.os) == "OHOS" else None)
        with tempfile.TemporaryDirectory(prefix="liblo-", dir=socket_parent) as test_tmp:
            self.run(
                f"TMPDIR={shlex.quote(test_tmp)} "
                f"LD_LIBRARY_PATH={build_libdir}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}} "
                "ctest --output-on-failure --timeout 45 -j1",
                cwd=self.build_folder,
                env=["conanbuild", "conanrun"],
            )
        self.output.info("UPSTREAM_4_OF_4_PASS")

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS":
            real_libraries = [p for p in Path(self.package_folder, "lib").glob("liblo.so*")
                              if p.is_file() and not p.is_symlink()]
            if len(real_libraries) != 1:
                raise ConanException("expected one installed liblo shared library")
            self._sign_elf(real_libraries[0])
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["lo"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("pkg_config_name", "liblo")
        self.cpp_info.set_property("cmake_file_name", "liblo")
        self.cpp_info.set_property("cmake_target_name", "liblo::liblo")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
