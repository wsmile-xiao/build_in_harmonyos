#!/usr/bin/env python3
"""Conan recipe for pgexporter 0.8.0 on HarmonyOS."""

import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file


class PgexporterConan(ConanFile):
    name = "pgexporter"
    version = "0.8.0"
    description = "A Prometheus exporter for PostgreSQL"
    license = "BSD-3-Clause"
    homepage = "https://pgexporter.github.io/pgexporter/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("libev/4.33")
        self.requires("libyaml/0.2.5")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")
        self.requires("lz4/1.10.0")
        self.requires("zstd/1.5.6")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    @staticmethod
    def _dep_include_dir(dep):
        for inc in dep.cpp_info.includedirs:
            if not os.path.isabs(inc):
                inc = os.path.join(dep.package_folder, inc)
            if os.path.isdir(inc):
                return inc
        return ""

    @staticmethod
    def _dep_library(dep, lib_base):
        for libdir in dep.cpp_info.libdirs:
            if not os.path.isabs(libdir):
                libdir = os.path.join(dep.package_folder, libdir)
            if not os.path.isdir(libdir):
                continue
            for pattern in (f"lib{lib_base}.so*", f"lib{lib_base}.a"):
                matches = sorted(glob.glob(os.path.join(libdir, pattern)))
                if matches:
                    return min(matches, key=len)
        return lib_base

    def _thread_paths(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        include_dir = ""
        library_path = ""
        try:
            output = subprocess.check_output(
                [cc, "-E", "-Wp,-v", "-"],
                stderr=subprocess.STDOUT, input=b"", timeout=10,
            ).decode()
            in_search = False
            for line in output.splitlines():
                if "#include <...> search starts here:" in line:
                    in_search = True
                    continue
                if "End of search list" in line:
                    break
                if in_search:
                    inc = line.strip()
                    if os.path.isfile(os.path.join(inc, "pthread.h")):
                        include_dir = inc
                        break
        except Exception:
            pass
        try:
            for lib_name in ("libpthread.a", "libpthread.so"):
                lib = subprocess.check_output(
                    [cc, "-print-file-name=" + lib_name], timeout=10,
                ).decode().strip()
                if lib and os.path.isfile(lib):
                    library_path = lib
                    break
        except Exception:
            pass
        return include_dir, library_path

    def generate(self):
        tc = CMakeToolchain(self)
        libev = self.dependencies["libev"]
        tc.cache_variables["LIBEV_INCLUDE_DIR"] = self._dep_include_dir(libev)
        tc.cache_variables["LIBEV_LIBRARY"] = self._dep_library(libev, "ev")
        libyaml = self.dependencies["libyaml"]
        tc.cache_variables["LIBYAML_INCLUDE_DIR"] = self._dep_include_dir(libyaml)
        tc.cache_variables["LIBYAML_LIBRARY"] = self._dep_library(libyaml, "yaml")
        zstd = self.dependencies["zstd"]
        tc.cache_variables["ZSTD_INCLUDE_DIR"] = self._dep_include_dir(zstd)
        tc.cache_variables["ZSTD_LIBRARY"] = self._dep_library(zstd, "zstd")
        lz4 = self.dependencies["lz4"]
        tc.cache_variables["LZ4_INCLUDE_DIR"] = self._dep_include_dir(lz4)
        tc.cache_variables["LZ4_LIBRARY"] = self._dep_library(lz4, "lz4")
        zlib = self.dependencies["zlib"]
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = self._dep_include_dir(zlib)
        tc.cache_variables["ZLIB_LIBRARY"] = self._dep_library(zlib, "z")
        bzip2 = self.dependencies["bzip2"]
        tc.cache_variables["BZIP2_INCLUDE_DIR"] = self._dep_include_dir(bzip2)
        tc.cache_variables["BZIP2_LIBRARIES"] = self._dep_library(bzip2, "bz2")
        openssl = self.dependencies["openssl"]
        openssl_inc = self._dep_include_dir(openssl)
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = openssl_inc
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = self._dep_library(openssl, "ssl")
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = self._dep_library(openssl, "crypto")
        thread_inc, thread_lib = self._thread_paths()
        if thread_inc:
            tc.cache_variables["THREAD_INCLUDE_DIR"] = thread_inc
        if thread_lib:
            tc.cache_variables["THREAD_LIBRARY"] = thread_lib
        else:
            tc.cache_variables["THREAD_LIBRARY"] = "pthread"
        tc.variables["DOCS"] = False
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "CMakeLists.txt"),
            "add_library(pgexporter SHARED ${SOURCES})",
            "add_library(pgexporter ${SOURCES})",
        )
        self.run("pip3 install docutils --quiet")
        # Create rst2man wrapper (docutils installs rst2man.py, CMake needs 'rst2man')
        rst2man = os.path.join(self.build_folder, "rst2man")
        with open(rst2man, "w") as f:
            f.write("#!/usr/bin/env python3\nfrom docutils.core import publish_cmdline\npublish_cmdline(writer_name='manpage')\n")
        os.chmod(rst2man, 0o755)
        os.environ["PATH"] = self.build_folder + os.pathsep + os.environ.get("PATH", "")
        # Fix: lld from OHOS SDK needs libxml2.so.16 in SDK's llvm/lib
        llvm_libs = glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")
        if llvm_libs and os.path.isdir(llvm_libs[0]):
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = f"{llvm_libs[0]}:{existing}" if existing else llvm_libs[0]
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src", "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        if str(self.settings.os) == "OHOS":
            self._sign_elf()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "pgexporter")
        self.cpp_info.set_property("cmake_target_name", "pgexporter::pgexporter")
        self.cpp_info.set_property("pkg_config_name", "pgexporter")
        self.cpp_info.libs = ["pgexporter"]
        self.cpp_info.bindirs = ["bin"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.requires = [
            "libev::libev", "libyaml::libyaml", "openssl::openssl",
            "zlib::zlib", "bzip2::bzip2", "lz4::lz4", "zstd::zstd",
        ]

    def _sign_elf(self):
        hnp_bin = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp_bin, "llvm-objcopy")
        signer = os.path.join(hnp_bin, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("binary-sign-tool / llvm-objcopy unavailable; skipping ELF signing")
            return
        patterns = ("bin/*", "lib/*.so", "lib/*.so.*")
        files = []
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(self.package_folder, pattern)))
        for path in sorted(set(files)):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as handle:
                    if handle.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            self.run('{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true'.format(objcopy=objcopy, path=path))
            self.run('{signer} sign -inFile "{path}" -outFile "{path}.signed" -selfSign 1'.format(signer=signer, path=path))
            if os.path.isfile(path + ".signed"):
                os.replace(path + ".signed", path)
                os.chmod(path, 0o755)
