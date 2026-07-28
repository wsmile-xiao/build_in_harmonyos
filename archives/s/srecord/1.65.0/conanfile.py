#!/usr/bin/env python3
"""Conan recipe — srecord 1.65.0 (CMake CLI tools + static lib_srecord).

Aligns with Homebrew srecord 1.65.0:
  cmake -S . -B build -DSRECORD_BUILD_DOCUMENTATION=OFF
  cmake --build build && ctest --test-dir build && cmake --install build

Produces: srec_cat, srec_cmp, srec_info, liblib_srecord.a, headers.
Runtime crypto features require libgcrypt (+ libgpg-error).
"""
import glob
import os
import platform
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SrecordConan(ConanFile):
    name = "srecord"
    version = "1.65.0"
    description = "Manipulate EPROM load files (Motorola S-Record, Intel HEX, etc.)"
    license = "GPL-3.0-or-later"
    homepage = "https://srecord.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("libgcrypt/1.11.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _foreign_aarch64(self):
        """True when targeting aarch64/armv8 on a non-aarch64 build machine.

        Using both -pr:h/-pr:b=ohos-aarch64 makes Conan cross_building() False even
        on an x86_64 SDK host; detect the real execution gap instead.
        """
        target = str(self.settings.arch)
        if target not in ("armv8", "armv8.3", "armv8.7", "arm64"):
            return False
        return platform.machine() not in ("aarch64", "arm64")

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["SRECORD_BUILD_DOCUMENTATION"] = False

        # Upstream uses check_include_files(gcrypt.h) + find_library(gcrypt).
        prefixes = []
        rpaths = []
        for name in ("libgcrypt", "libgpg-error"):
            dep = self.dependencies[name]
            prefixes.append(dep.package_folder)
            for include_dir in dep.cpp_info.includedirs:
                tc.extra_cflags.append(f"-I{include_dir}")
                tc.extra_cxxflags.append(f"-I{include_dir}")
            for lib_dir in dep.cpp_info.libdirs:
                tc.extra_exelinkflags.append(f"-L{lib_dir}")
                tc.extra_sharedlinkflags.append(f"-L{lib_dir}")
                # E019: musl does not expand $ORIGIN; bake absolute rpath.
                rpaths.append(lib_dir)
                tc.extra_exelinkflags.append(f"-Wl,-rpath,{lib_dir}")

        if prefixes:
            tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(prefixes)
            tc.cache_variables["CMAKE_LIBRARY_PATH"] = ";".join(
                d for name in ("libgcrypt", "libgpg-error")
                for d in self.dependencies[name].cpp_info.libdirs
            )
            tc.cache_variables["CMAKE_INCLUDE_PATH"] = ";".join(
                d for name in ("libgcrypt", "libgpg-error")
                for d in self.dependencies[name].cpp_info.includedirs
            )
        if rpaths:
            # Also set CMake rpath vars so install tree keeps the same paths.
            tc.cache_variables["CMAKE_BUILD_RPATH"] = ";".join(rpaths)
            tc.cache_variables["CMAKE_INSTALL_RPATH"] = ";".join(rpaths)

        # R32 / E092
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        tc.generate()

    def _dep_libdirs(self):
        dirs = []
        for name in ("libgcrypt", "libgpg-error"):
            for libdir in self.dependencies[name].cpp_info.libdirs:
                if libdir not in dirs:
                    dirs.append(libdir)
        return dirs

    def _ensure_tmpdir(self):
        """E002: prefer a writable dir inside the Conan build tree."""
        tmpdir = os.path.join(self.build_folder, "_ctest_tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        return tmpdir

    def _ensure_run_libs(self):
        """OHOS conanrun often omits LD_LIBRARY_PATH; set it explicitly (E019)."""
        libdirs = self._dep_libdirs()
        if not libdirs:
            raise ConanInvalidConfiguration("missing libgcrypt/libgpg-error libdirs")
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            libdirs + ([existing] if existing else [])
        )
        self.output.info(f"LD_LIBRARY_PATH={os.environ['LD_LIBRARY_PATH']}")

    def _runtime_lib_files(self):
        """Collect libgcrypt / libgpg-error shared objects (incl. soname links)."""
        files = []
        for libdir in self._dep_libdirs():
            files.extend(sorted(glob.glob(os.path.join(libdir, "lib*.so*"))))
        return files

    def _stage_runtime_libs(self, dest_dirs):
        """Colocate .so next to CLI tools as a fallback when rpath is ignored."""
        lib_files = self._runtime_lib_files()
        if not lib_files:
            raise ConanInvalidConfiguration(
                "no libgcrypt/libgpg-error shared libraries found to stage"
            )
        for dest in dest_dirs:
            if not dest or not os.path.isdir(dest):
                continue
            for src in lib_files:
                dst = os.path.join(dest, os.path.basename(src))
                if os.path.lexists(dst):
                    os.remove(dst)
                if os.path.islink(src):
                    os.symlink(os.readlink(src), dst)
                else:
                    shutil.copy2(src, dst)
            self.output.info(f"staged {len(lib_files)} runtime libs into {dest}")

    def _sign_elf(self, path):
        """E077/E082: OHOS kernel rejects unsigned ELF with Operation not permitted.

        No-op when binary-sign-tool is absent (e.g. Linux host / foreign SDK).
        """
        if not path or not os.path.isfile(path) or os.path.islink(path):
            return False
        try:
            with open(path, "rb") as fh:
                if fh.read(4) != b"\x7fELF":
                    return False
        except OSError:
            return False

        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool) or not os.path.isfile(objcopy):
            return False

        tmp_signed = path + ".signed"
        # .codesign may be absent; ignore remove failures.
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=False,
            capture_output=True,
        )
        r = subprocess.run(
            [
                sign_tool,
                "sign",
                "-inFile",
                path,
                "-outFile",
                tmp_signed,
                "-selfSign",
                "1",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not os.path.isfile(tmp_signed):
            self.output.warning(
                f"ELF sign failed for {os.path.basename(path)}: {r.stderr or r.stdout}"
            )
            return False
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)
        self.output.info(f"ELF signed: {os.path.basename(path)}")
        return True

    def _sign_package_binaries(self, bindir):
        """Sign CLI tools (and staged real .so files) for native OHOS execution."""
        if not os.path.isdir(bindir):
            return
        for name in ("srec_cat", "srec_cmp", "srec_info"):
            self._sign_elf(os.path.join(bindir, name))
        for so in sorted(glob.glob(os.path.join(bindir, "lib*.so*"))):
            self._sign_elf(so)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Upstream official CTest suite (208 shell-driven cases).
        # Native OHOS CI (aarch64 worker) runs them directly. On an x86_64 SDK
        # host the OHOS dynamic binaries cannot be executed via qemu-user
        # (loader / SIGILL), so only verify build outputs locally.
        if self._foreign_aarch64():
            for name in ("srec_cat", "srec_cmp", "srec_info"):
                candidate = os.path.join(self.build_folder, name, name)
                if not os.path.isfile(candidate):
                    raise ConanInvalidConfiguration(f"missing build output: {candidate}")
            self.output.warning(
                "foreign aarch64 host: skipped upstream CTest (208 cases); "
                "native OHOS CI executes ctest"
            )
        else:
            tmpdir = self._ensure_tmpdir()
            self._ensure_run_libs()
            test_wd = os.path.join(self.build_folder, "test")
            os.makedirs(test_wd, exist_ok=True)
            self._stage_runtime_libs(
                [
                    os.path.join(self.build_folder, "srec_cat"),
                    os.path.join(self.build_folder, "srec_cmp"),
                    os.path.join(self.build_folder, "srec_info"),
                    test_wd,
                ]
            )
            ld = os.environ["LD_LIBRARY_PATH"]
            # OHOS/HMDFS: getcwd may fail in deep Conan build paths. Force an
            # absolute cwd + PWD before spawning CTest shell tests (E002-adjacent).
            os.chdir(test_wd)
            os.environ["PWD"] = test_wd
            os.environ["SRECORD_TEST_HERE"] = test_wd
            # Inline env: OHOS conanrun may drop LD_LIBRARY_PATH/TMPDIR/PWD.
            # Call ctest directly (skip make test jobserver/mkfifo).
            self.run(
                f'cd "{test_wd}" && '
                f'TMPDIR="{tmpdir}" PWD="{test_wd}" '
                f'SRECORD_TEST_HERE="{test_wd}" LD_LIBRARY_PATH="{ld}" '
                f'ctest --test-dir "{self.build_folder}" --output-on-failure',
                env="conanrun",
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            self._stage_runtime_libs([bindir])
            # cmake install / RPATH rewrite can invalidate .codesign; resign so
            # test_package/smoke_test.sh can exec package bin/srec_* on OHOS.
            self._sign_package_binaries(bindir)

    def package_info(self):
        # Upstream target name is lib_srecord → archive liblib_srecord.a
        self.cpp_info.libs = ["lib_srecord"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "srecord")
        self.cpp_info.set_property("cmake_target_name", "srecord::srecord")
        self.cpp_info.requires = ["libgcrypt::libgcrypt"]
