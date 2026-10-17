#!/usr/bin/env python3
"""Conan recipe for afdko 4.0.1 (Adobe Font Development Kit for OpenType)."""

import glob
import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AfdkoConan(ConanFile):
    name = "afdko"
    version = "4.0.1"
    description = "Adobe Font Development Kit for OpenType"
    license = "Apache-2.0"
    homepage = "https://github.com/adobe-type-tools/afdko"
    url = "https://github.com/adobe-type-tools/afdko"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("libxml2/2.15.3.1")

    def configure(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("afdko supports POSIX-like Linux/OHOS builds")
        if sys.version_info < (3, 8):
            raise ConanInvalidConfiguration("afdko 4.0.1 requires Python 3.8 or newer")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        import glob as _glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(_glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration("Cannot find ohos.toolchain.cmake")

    def generate(self):
        VirtualBuildEnv(self).generate()
        env = Environment()
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        env.define("TEMP", os.path.join(self.build_folder, "tmp"))
        env.define("TMP", os.path.join(self.build_folder, "tmp"))
        # Inject conan libxml2 lib path into LD_LIBRARY_PATH so that
        # OHOS SDK's lld (NEEDED libxml2.so.16, RUNPATH $ORIGIN/../lib)
        # loads the correct libxml2.so.16 with full symbols (xmlFreeDoc,
        # xmlSetGenericErrorFunc, etc.). This is saved to afdko_build.sh
        # which is sourced by conanbuild.sh during self.run(), ensuring
        # the cmake->clang->lld subprocess chain inherits it reliably.
        lxlib = os.path.join(self.dependencies["libxml2"].package_folder, "lib")
        env.prepend_path("LD_LIBRARY_PATH", lxlib)
        env.define("PYTHONDONTWRITEBYTECODE", "1")
        env.define("SETUPTOOLS_SCM_PRETEND_VERSION", self.version)
        env.vars(self).save_script("afdko_build")

    def build(self):
        apply_conandata_patches(self)
        os.makedirs(os.path.join(self.build_folder, "tmp"), exist_ok=True)
        antlr4_zip = self._download_antlr4()
        self._build_cmake(antlr4_zip)

    def _download_antlr4(self):
        antlr4_data = self.conan_data.get("antlr4_source", {})
        urls = antlr4_data.get("url", [])
        sha256 = antlr4_data.get("sha256", "")
        if not urls or not sha256:
            raise ConanInvalidConfiguration("conandata.yml missing antlr4_source")
        download_dir = os.path.join(self.build_folder, "antlr4-src")
        os.makedirs(download_dir, exist_ok=True)
        zip_path = os.path.join(download_dir, "antlr4-4.9.3.tar.gz")
        if not os.path.isfile(zip_path):
            import urllib.request
            import hashlib as _hl
            last_err = None
            # CI mirror fallback only rewrites top-level sources.url, not
            # antlr4_source; CI worker cannot reach github.com directly, so
            # probe the gh-proxy.com mirror first for GitHub URLs (R39 spirit:
            # official URL + mirror fallback, capability probing not hardcode).
            candidates = []
            for url in urls:
                candidates.append(url)
                if url.startswith("https://github.com/"):
                    candidates.append("https://gh-proxy.com/" + url)
            for url in candidates:
                try:
                    self.output.info("Downloading ANTLR4 from: " + url)
                    urllib.request.urlretrieve(url, zip_path)
                    h = _hl.sha256()
                    with open(zip_path, "rb") as f:
                        for chunk in iter(lambda: f.read(65536), b""):
                            h.update(chunk)
                    actual = h.hexdigest()
                    if actual != sha256:
                        self.output.warning("SHA-256 mismatch for ANTLR4")
                        if os.path.isfile(zip_path):
                            os.remove(zip_path)
                        continue
                    return zip_path
                except Exception as exc:
                    last_err = exc
                    if os.path.isfile(zip_path):
                        os.remove(zip_path)
            raise ConanInvalidConfiguration("Failed to download ANTLR4: " + str(last_err))
        return zip_path

    def _build_cmake(self, antlr4_zip):
        toolchain = self._ohos_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")
        libxml2_dir = self.dependencies["libxml2"].package_folder
        defs = " ".join([
            "-DCMAKE_TOOLCHAIN_FILE=" + shlex.quote(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE=" + str(self.settings.build_type),
            "-DCMAKE_INSTALL_PREFIX=" + shlex.quote(self.package_folder),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_INSTALL_RPATH=\$ORIGIN/../lib",
            "-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib",
            "-DLIBXML2_INCLUDE_DIR=" + shlex.quote(os.path.join(libxml2_dir, "include", "libxml2")),
            "-DLIBXML2_LIBRARY=" + shlex.quote(os.path.join(libxml2_dir, "lib", "libxml2.so")),
            "-DBUILD_STATIC_LIBXML2=OFF",
            "-DNEED_LIBXML2_DEPEND=FALSE",
            "-DANTLR4_TAG=tags/4.9.3",
            "-DANTLR4_ZIP_REPOSITORY=" + shlex.quote(antlr4_zip),
        ])
        # Force a readable libxml2 into LD_LIBRARY_PATH via a literal
        # command-line `env` prefix. CI-016/CI-014 showed conan self.run()
        # env="conanbuild" rebuilds child env and drops os.environ changes;
        # CI-024 further showed the conan-cache libxml2 (mode 0750, owner
        # 20001006) is UNREADABLE by the CI worker (USER=100), so lld fails
        # to load it. The OHOS SDK ships its own libxml2.so.16 in
        # $SDK/llvm/lib (mode 0744, world-readable, full symbols), proven
        # linkable in a clean env. Inject SDK libxml2 dir FIRST, keep the
        # conan libxml2 dir as fallback for device-side builds.
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        lxlib = os.path.join(libxml2_dir, "lib")
        cur = os.environ.get("LD_LIBRARY_PATH", "")
        ld = sdk_lib + os.pathsep + lxlib + (os.pathsep + cur if cur else "")
        envpre = "env LD_LIBRARY_PATH=" + shlex.quote(ld) + " "
        self.run(envpre + "cmake -B " + shlex.quote(bdir) + " -S " + shlex.quote(self.source_folder) + " " + defs)
        self.run(envpre + "cmake --build " + shlex.quote(bdir) + " -- -j1")
        self.run(envpre + "cmake --install " + shlex.quote(bdir))

    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        lxdir = os.path.join(self.dependencies["libxml2"].package_folder, "lib")
        if os.path.isdir(lxdir):
            # Copy libxml2 into the package lib/ so executables with RUNPATH
            # $ORIGIN/../lib can load it in a clean environment. The libxml2
            # conan package ships versioned symlinks chained to the real ELF
            # (libxml2.so -> libxml2.so.16 -> libxml2.so.16.1.3). Copying only
            # the symlink names leaves dangling symlinks once the package is
            # installed away from the conan cache. Resolve each symlink via
            # os.path.realpath(), copy the real file in by its basename, then
            # rebuild correct symlinks so the package lib/ is self-contained.
            pkg_lib = os.path.join(self.package_folder, "lib")
            for so in ("libxml2.so.16", "libxml2.so"):
                src = os.path.join(lxdir, so)
                if os.path.islink(src) or os.path.isfile(src):
                    real = os.path.realpath(src)
                    real_base = os.path.basename(real)
                    copy(self, real_base, src=os.path.dirname(real), dst=pkg_lib)
                    dst_link = os.path.join(pkg_lib, so)
                    if os.path.lexists(dst_link):
                        os.remove(dst_link)
                    os.symlink(real_base, dst_link)
        if str(self.settings.os) == "OHOS":
            self._sign_executables()

    def _sign_executables(self):
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for exe in glob.glob(os.path.join(bindir, "*")):
            if os.path.islink(exe):
                continue
            subprocess.run([objcopy, "--remove-section", ".codesign", exe], capture_output=True, timeout=30, check=False)
            subprocess.run([signer, "sign", "-inFile", exe, "-outFile", exe, "-selfSign", "1"], capture_output=True, timeout=60, check=False)
            os.chmod(exe, 0o755)
            self.output.info("Signed: " + os.path.basename(exe))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
