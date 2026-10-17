#!/usr/bin/env python3
"""Conan recipe for ScaLAPACK 2.2.3 (CMake)."""

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    copy,
    export_conandata_patches,
    get,
    load,
    replace_in_file,
)


# The exact published provider and component passed the C/Fortran ABI gate
# recorded in notes.md and the external W0 closure.
_MPI_REF = "mpich/5.0.1.2"
_MPI_COMPONENT = "mpich::c"


class ScalapackConan(ConanFile):
    name = "scalapack"
    version = "2.2.3"
    description = "Distributed-memory dense linear algebra library"
    license = "BSD-3-Clause"
    homepage = "https://www.netlib.org/scalapack/"
    url = "https://github.com/Reference-ScaLAPACK/scalapack"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "scalapack/2.2.3 is validated only for os=OHOS arch=armv8"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "Static ScaLAPACK is disabled until a host-visible Flang "
                "runtime package can be propagated to consumers"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openblas/0.3.34")
        if _MPI_REF:
            self.requires(_MPI_REF)

    def build_requirements(self):
        self.tool_requires(
            "flang-ohos/20.1.0",
            package_id_mode="full_mode",
        )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        blacs_test = os.path.join(
            self.source_folder, "BLACS", "TESTING", "blacstest.f"
        )
        gridexit_marker = "         WRITE(OUTNUM,*) 'DONE BLACS_GRIDEXIT'\n"
        # The BLACS abort test intentionally terminates every MPI rank. Flush
        # rank zero's completion marker before MPI_Abort discards stdio buffers.
        replace_in_file(
            self,
            blacs_test,
            gridexit_marker,
            gridexit_marker + "         FLUSH(OUTNUM)\n",
        )
        blacs_runner = os.path.join(
            self.source_folder, "BLACS", "TESTING", "runtest.cmake"
        )
        # The upstream harness copies these executables away from the
        # $ORIGIN-relative build RPATH before running them.
        replace_in_file(
            self,
            blacs_runner,
            "file(COPY ${RUNTIMEDIR}/${TEST_PROG} DESTINATION ${OUTPUTDIR})\n\n",
            "",
        )
        replace_in_file(
            self,
            blacs_runner,
            "./${TEST_PROG}",
            "${RUNTIMEDIR}/${TEST_PROG}",
        )
        replace_in_file(
            self,
            blacs_runner,
            'tmp ${TESTSTRING})',
            'tmp "${TESTSTRING}")',
        )

    def _mpi_wrapper(self, *names):
        mpi_name = _MPI_REF.split("/", 1)[0]
        mpi = self.dependencies.host[mpi_name]
        bindirs = list(mpi.cpp_info.bindirs or ["bin"])
        for bindir in bindirs:
            if not os.path.isabs(bindir):
                bindir = os.path.join(mpi.package_folder, bindir)
            for name in names:
                candidate = os.path.join(bindir, name)
                if os.path.isfile(candidate):
                    return candidate
        raise ConanInvalidConfiguration(
            f"MPI package {_MPI_REF} does not provide any of: {', '.join(names)}"
        )

    def _openblas_library(self):
        dependency = self.dependencies.host["openblas"]
        stems = dependency.cpp_info.libs or ["openblas"]
        for libdir in dependency.cpp_info.libdirs:
            if not os.path.isabs(libdir):
                libdir = os.path.join(dependency.package_folder, libdir)
            for stem in stems:
                for filename in (
                    f"lib{stem}.so",
                    f"lib{stem}.a",
                    f"{stem}.lib",
                ):
                    candidate = os.path.join(libdir, filename)
                    if os.path.isfile(candidate):
                        return candidate
        raise ConanInvalidConfiguration(
            "openblas/0.3.34 did not expose a linkable BLAS/LAPACK library"
        )

    def generate(self):
        mpicc = self._mpi_wrapper("mpicc")
        mpifort = self._mpi_wrapper("mpifort", "mpif90")
        mpiexec = self._mpi_wrapper("mpiexec", "mpirun")
        openblas = self._openblas_library()

        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_C_COMPILER"] = mpicc
        toolchain.variables["CMAKE_Fortran_COMPILER"] = mpifort
        toolchain.variables["MPI_C_COMPILER"] = mpicc
        toolchain.variables["MPI_Fortran_COMPILER"] = mpifort
        toolchain.variables["MPIEXEC"] = mpiexec
        toolchain.variables["MPIEXEC_EXECUTABLE"] = mpiexec
        toolchain.variables["MPIEXEC_NUMPROC_FLAG"] = "-n"
        toolchain.variables["BLAS_LIBRARIES"] = openblas
        toolchain.variables["LAPACK_LIBRARIES"] = openblas
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["SCALAPACK_BUILD_TESTS"] = True
        if str(self.settings.os) == "OHOS" and self.options.shared:
            toolchain.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
            for language in ("C", "Fortran"):
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"
                ] = "-Wl,-soname,"
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"
                ] = "-Wl,-rpath,"
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"
                ] = ":"
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"
                ] = "-Wl,-rpath-link,"
            toolchain.variables[
                "CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN"
            ] = "$ORIGIN"
            toolchain.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        toolchain.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        # ScaLAPACK executes target probes during configure and MPI programs
        # during CTest. Keep Conan's host dependency runtime visible throughout.
        with VirtualRunEnv(self).vars().apply():
            cmake.configure()
            self._verify_configure_contract()
            cmake.build(build_tool_args=["-j1"])
            self._sign_elf_tree(self.build_folder)
            cmake.test(build_tool_args=["-j1"])

    def _cache_value(self, key):
        cache_path = os.path.join(self.build_folder, "CMakeCache.txt")
        contents = load(self, cache_path)
        match = re.search(
            r"^{}:[^=]+=(.*)$".format(re.escape(key)),
            contents,
            re.MULTILINE,
        )
        if not match:
            raise ConanInvalidConfiguration(
                "CMake cache is missing required entry: {}".format(key)
            )
        return match.group(1).strip().strip('"')

    def _verify_configure_contract(self):
        truthy = {"1", "ON", "TRUE", "YES", "Y"}
        for key in ("LAPACK_FOUND", "SCALAPACK_BUILD_TESTS", "BUILD_SHARED_LIBS"):
            if self._cache_value(key).upper() not in truthy:
                raise ConanInvalidConfiguration(
                    "CMake configuration did not enable {}".format(key)
                )

        expected = os.path.normcase(os.path.realpath(self._openblas_library()))
        for key in ("BLAS_LIBRARIES", "LAPACK_LIBRARIES"):
            configured = self._cache_value(key)
            entries = [entry for entry in configured.split(";") if entry]
            resolved = [
                os.path.normcase(os.path.realpath(entry)) for entry in entries
            ]
            if resolved != [expected]:
                raise ConanInvalidConfiguration(
                    "{} must resolve only to openblas/0.3.34; got {}".format(
                        key, configured
                    )
                )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_elf_tree(self.package_folder)

    @staticmethod
    def _is_loadable_elf(path):
        if not os.path.isfile(path) or os.path.islink(path):
            return False
        with open(path, "rb") as stream:
            header = stream.read(18)
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return False
        byteorder = "little" if header[5] == 1 else "big"
        return int.from_bytes(header[16:18], byteorder=byteorder) in (2, 3)

    def _find_ohos_tool(self, name):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(executables.get("c", ""))
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _sign_elf_tree(self, root):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        readelf = self._find_ohos_tool("llvm-readelf")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not readelf or not signer:
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires llvm-objcopy, llvm-readelf, and "
                "binary-sign-tool"
            )
        candidates = []
        for directory, _, filenames in os.walk(root):
            for filename in filenames:
                path = os.path.join(directory, filename)
                if self._is_loadable_elf(path):
                    candidates.append(path)
        if not candidates:
            raise ConanInvalidConfiguration(
                "OHOS ELF signing found no executable or shared-library target"
            )
        for path in sorted(candidates):
            self._sign_elf_atomically(path, objcopy, readelf, signer)

    def _verify_signed_elf(self, path, readelf):
        if not self._is_loadable_elf(path):
            raise ConanInvalidConfiguration(
                "signed output is not an ET_EXEC or ET_DYN ELF: {}".format(path)
            )
        completed = subprocess.run(
            [readelf, "-SW", path],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode != 0:
            raise ConanInvalidConfiguration(
                "llvm-readelf failed for signed ELF {}: {}".format(
                    path, completed.stdout
                )
            )
        sections = re.findall(
            r"^\s*\[\s*\d+\]\s+\.codesign\s+(\S+)\s+"
            r"[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s+([0-9A-Fa-f]+)\b",
            completed.stdout,
            re.MULTILINE,
        )
        if len(sections) != 1 or sections[0][0] != "PROGBITS" or int(
            sections[0][1], 16
        ) == 0:
            raise ConanInvalidConfiguration(
                "signed ELF must contain exactly one non-empty PROGBITS "
                ".codesign section: {}".format(path)
            )

    def _sign_elf_atomically(self, path, objcopy, readelf, signer):
        original_mode = os.stat(path).st_mode
        temporary = "{}.signing".format(path)
        try:
            shutil.copy2(path, temporary)
            self.run(
                '"{}" --remove-section .codesign "{}"'.format(
                    objcopy, temporary
                )
            )
            self.run(
                '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                    signer, temporary, temporary
                )
            )
            os.chmod(temporary, original_mode)
            self._verify_signed_elf(temporary, readelf)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def package_info(self):
        self.cpp_info.libs = ["scalapack"]
        # Upstream installs only the library and CMake/pkg-config metadata.
        # Avoid exporting Conan's default non-existent include directory.
        self.cpp_info.includedirs = []
        self.cpp_info.requires = ["openblas::openblas"]
        if _MPI_COMPONENT:
            self.cpp_info.requires.append(_MPI_COMPONENT)
        self.cpp_info.set_property("cmake_file_name", "scalapack")
        self.cpp_info.set_property(
            "cmake_target_name", "scalapack::scalapack"
        )
        self.cpp_info.set_property("pkg_config_name", "scalapack")
