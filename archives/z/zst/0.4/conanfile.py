#!/usr/bin/env python3
"""Conan recipe — zst 0.4 (HarmonyOS PC / aarch64).

zst is a tiny single-binary front-end that unifies the four "essential"
compressor libraries (zstd, xz, gzip, bzip2) behind one CLI, picking the
algorithm from --tool / file extension / argv[0].

Build system: CMake (upstream CMakeLists.txt, cmake_minimum_required 2.8.12),
driven with the OHOS NDK ohos.toolchain.cmake self-discovered at build time
(no conan_toolchain dependency: under os=OHOS it degenerates to a
CMAKE_SYSTEM_NAME cmake does not recognise — ML-0035).

Dependencies (all from ohpcd): zlib/bzip2/xz/zstd. Upstream's CMakeLists
locates them with CHECK_LIBRARY_EXISTS(<name>) and then links `-l<name>`.
All four are linked **statically** into the single `zst` binary: the tool's
whole purpose is to be a small standalone compressor, and static linking
keeps the runtime free of any loader/RPATH dependency on the conan cache.
A private lib dir exposing only the deps' .a files makes the linker pick
static (a .so on the search path would win otherwise).

First real error on OHOS: CMake 4.x dropped compatibility with
`cmake_minimum_required(VERSION <3.5)` while upstream declares 2.8.12 →
configure fails hard; fixed with -DCMAKE_POLICY_VERSION_MINIMUM=3.5.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZstConan(ConanFile):
    name = "zst"
    version = "0.4"
    description = "Unified compressor CLI (zstd/xz/gzip/bzip2) in one small binary"
    license = "GPL-2.0-or-later OR BSD-1-Clause"
    homepage = "https://github.com/kilobyte/zst"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8.2")
        self.requires("xz/5.6.2")       # provides liblzma
        self.requires("zstd/1.5.7.1")   # ships libzstd.a (static) alongside .so

    def layout(self):
        # cmake is driven manually (ohos toolchain approach) — no conan cmake
        # generators are needed.
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        # Self-discover the OHOS NDK toolchain: 1) profile [conf] user_toolchain
        # 2) OHOS_NDK_HOME env 3) glob the device/CI SDK layout.
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for cand in list(ut) + ([os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")] if ndk else []):
            if cand and os.path.isfile(cand):
                return cand
        found = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if found:
            return found[-1]
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake: set OHOS_NDK_HOME or profile conf user_toolchain")

    def _static_lib_dir(self):
        """Collect the dependencies' static archives into a private dir.

        Upstream links with `-l<name>`, so only the .a files are exposed: the
        linker then resolves every compressor statically and the resulting
        `zst` binary keeps libc as its single DT_NEEDED entry.
        Returns (libdir, include_dirs).
        """
        libdir = os.path.join(self.build_folder, "zst-static-libs")
        os.makedirs(libdir, exist_ok=True)
        includes = []
        for dep in ("zlib", "bzip2", "xz", "zstd"):
            pkg = self.dependencies[dep].package_folder
            includes.append(os.path.join(pkg, "include"))
            archives = sorted(glob.glob(os.path.join(pkg, "lib", "*.a")))
            if not archives:
                raise ConanInvalidConfiguration(
                    "dependency '{}' ships no static archive in {}".format(dep, pkg))
            for archive in archives:
                link = os.path.join(libdir, os.path.basename(archive))
                if not os.path.exists(link):
                    try:
                        os.symlink(archive, link)
                    except OSError:            # HMDFS may reject symlinks
                        shutil.copy2(archive, link)
        return libdir, includes

    def build(self):
        apply_conandata_patches(self)   # patches: {} → no-op
        toolchain = self._ohos_toolchain()
        libdir, includes = self._static_lib_dir()
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            # cmake 4.x removed compatibility with cmake_minimum_required(<3.5)
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            # dependency headers live in the conan packages (zlib.h/bzlib.h/
            # lzma.h/zstd.h); FIND_ROOT_PATH_MODE=ONLY hides them from cmake's
            # search, so pass them explicitly (quoted: several -I in one value).
            '"-DCMAKE_C_FLAGS={}"'.format(" ".join("-I" + i for i in includes)),
            # wire the static lib dir into CHECK_LIBRARY_EXISTS and the link
            '"-DCMAKE_REQUIRED_LINK_OPTIONS=-L{}"'.format(libdir),
            '"-DCMAKE_EXE_LINKER_FLAGS=-L{}"'.format(libdir),
        ]
        self.run('cmake -G Ninja -B "{b}" -S "{s}" {d}'.format(
            b=bdir, s=self.source_folder, d=" ".join(defs)))
        self.run('cmake --build "{b}" -- -j$(nproc)'.format(b=bdir))
        self._bdir = bdir

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{b}" --prefix "{p}"'.format(b=bdir, p=self.package_folder))
        self._sign_binary()

    def _sign_binary(self):
        # HarmonyOS PC requires a valid code signature on executables; the SDK
        # toolchain's self-sign is not honoured, so strip .codesign and re-sign.
        bindir = os.path.join(self.package_folder, "bin")
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool missing ({}): skipping code signing. "
                                "Unsigned binaries are rejected by XPM on device.".format(signer))
            return
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as fh:
                if fh.read(4) != b"\x7fELF":
                    continue
            self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, path))
            self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, path, path))
            # binary-sign-tool drops the permission bits — restore the exec bit
            # or the packaged CLI cannot be launched (conan test → Permission denied).
            os.chmod(path, 0o755)

    def package_info(self):
        # R38: CLI tool → declare bindirs so CI recognises the shipped binary.
        self.cpp_info.bindirs = ["bin"]
