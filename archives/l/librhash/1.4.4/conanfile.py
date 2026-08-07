#!/usr/bin/env python3
"""Conan recipe — librhash 1.4.4 (configure + make)"""
import os, glob, re, shutil
from io import StringIO

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches

class LibrhashConan(ConanFile):
    name = "librhash"
    version = "1.4.4"
    description = "LibRHash shared library for computing hash sums（哈希计算库，configure+make 构建，鸿蒙 PC 适配）"
    license = "0BSD"
    homepage = "https://github.com/rhash/RHash"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = "llvm-ar"

        # cflags driven by build_type and fPIC option; -O2 for Release-like builds.
        # Note: configure() removes the fPIC option when shared=True, so we must
        # also force -fPIC for shared builds (shared objects always need PIC).
        if self.settings.build_type == "Debug":
            cflags = "-O0 -g"
        elif self.settings.build_type == "RelWithDebInfo":
            cflags = "-O2 -g"
        elif self.settings.build_type == "MinSizeRel":
            cflags = "-Os"
        else:
            cflags = "-O2"  # Release (default)
        if self.options.shared or self.options.get_safe("fPIC", False):
            cflags += " -fPIC"

        # Configure: build only the librhash library; target depends on shared/static.
        args = [
            "./configure",
            f"--cc={cc}",
            f"--ar={ar}",
            f"--prefix={self.package_folder}",
            f"--libdir={os.path.join(self.package_folder, 'lib')}",
            f"--extra-cflags='{cflags}'",
        ]
        if self.options.shared:
            args += ["--enable-lib-shared", "--disable-static"]
        else:
            # librhash configure controls the librhash library via --enable-lib-static
            # (not --enable-static, which flips the rhash binary link mode).
            # --disable-lib-shared suppresses the shared lib; --disable-shared is NOT
            # a recognized configure option (configure exits 1 on it).
            args += ["--enable-lib-static", "--disable-lib-shared"]
        args.append("--disable-openssl")
        self.run(" ".join(args))

        # Fix Makefile: remove SOLINK_TARGET dependency that fails when
        # LIBRHASH_SO_MAJ == LIBRHASH_SHARED (the test returns non-zero
        # and breaks the build before the .so is actually compiled).
        self.run("sed -i 's/$(SOLINK_TARGET)//' librhash/Makefile")

        # Build librhash only (not the rhash command-line tool); target bound to shared.
        make_target = "lib-shared" if self.options.shared else "lib-static"
        self.run(f"make -C librhash -j1 {make_target}")

        # Build the rhash CLI binary too — upstream tests (test_rhash.sh) exercise
        # the command-line tool, and the recipe ships it as bin/rhash.
        self.run("make -j1 build")

        # Sign the rhash CLI for OHOS (executables need ELF signatures too).
        # Error handling aligned with the shared-lib signing block below:
        # a missing signer is a loud failure, not a silent skip — otherwise an
        # unsigned CLI would ship while the pipeline reports success (漏报).
        if self.settings.os == "OHOS":
            signer = os.environ.get("BINARY_SIGN_TOOL", "binary-sign-tool")
            cli_path = os.path.join(self.source_folder, "rhash")
            if not os.path.isfile(cli_path):
                raise ConanException(f"rhash CLI not found: {cli_path}")
            if not shutil.which(signer):
                raise ConanException(f"signer not found: {signer}")
            self.run(f'{signer} sign -inFile "{cli_path}" -outFile "{cli_path}" -selfSign 1')

        # Sign shared lib for OHOS (static libs don't need signing)
        if self.settings.os == "OHOS" and self.options.shared:
            libdir = os.path.join(self.source_folder, "librhash")
            sos = glob.glob(os.path.join(libdir, "*.so*"))
            # Tool paths read from environment with sensible defaults so the
            # recipe works across CI workers and local dev setups. Missing tools
            # are reported rather than silently swallowed.
            objcopy = os.environ.get("LLVM_OBJCOPY", "llvm-objcopy")
            signer = os.environ.get("BINARY_SIGN_TOOL", "binary-sign-tool")
            readelf = os.environ.get("LLVM_READELF", "llvm-readelf")
            # shared=True 时 make lib-shared 必须产出 .so；若未产出说明
            # 构建有缺陷，显式报错而非静默返回（避免"编译通过但产物缺失"误导）。
            if not sos:
                raise ConanException(
                    "no .so produced by `make lib-shared` in "
                    f"{libdir} (shared=True)"
                )
            # Validate objcopy is executable once up front (loud fail on missing tool).
            if not shutil.which(objcopy):
                raise ConanException(f"objcopy not found: {objcopy}")
            if not shutil.which(signer):
                raise ConanException(f"signer not found: {signer}")
            if not shutil.which(readelf):
                raise ConanException(f"readelf not found: {readelf}")
            for so in sos:
                if os.path.islink(so):
                    continue
                # Strip .codesign only when the exact section is present: llvm-objcopy
                # exits non-zero if the section is absent. Anchor the readelf probe to
                # a whitespace boundary so `.codesign_backup` etc. don't false-positive.
                buf = StringIO()
                self.run(f'{readelf} -S "{so}"', stdout=buf, stderr=StringIO(), ignore_errors=True)
                if re.search(r'\.codesign(?=\s)', buf.getvalue()):
                    # ignore_errors: tolerate a stale probe result (e.g. a section named
                    # `.codesign_v2` that the regex accepted but objcopy strips narrowly).
                    self.run(f'{objcopy} --remove-section .codesign "{so}"', ignore_errors=True)
                self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package(self):
        # Install librhash library and headers manually
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)

        # Copy headers
        copy(self, "rhash.h", src=os.path.join(self.source_folder, "librhash"),
              dst=incdir)
        copy(self, "rhash_torrent.h", src=os.path.join(self.source_folder, "librhash"),
              dst=incdir)

        # Copy library
        src_libdir = os.path.join(self.source_folder, "librhash")
        for lib in glob.glob(os.path.join(src_libdir, "*.so*")):
            copy(self, os.path.basename(lib), src=src_libdir, dst=libdir)
        for lib in glob.glob(os.path.join(src_libdir, "*.a")):
            copy(self, os.path.basename(lib), src=src_libdir, dst=libdir)

        # Create librhash.so → librhash.so.1 symlink so CMakeDeps can find it
        # (upstream builds only librhash.so.1; CMake find_package needs the
        # unversioned .so).
        so_maj = os.path.join(libdir, "librhash.so.1")
        so_link = os.path.join(libdir, "librhash.so")
        if os.path.isfile(so_maj) and not os.path.exists(so_link):
            os.symlink("librhash.so.1", so_link)

        # Copy the rhash CLI binary (built by `make build`) to bin/
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        cli_src = os.path.join(self.source_folder, "rhash")
        if os.path.isfile(cli_src):
            copy(self, "rhash", src=self.source_folder, dst=bindir)

    def package_info(self):
        self.cpp_info.libs = ["rhash"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "Rhash")
        self.cpp_info.set_property("cmake_target_name", "Rhash::Rhash")
        self.cpp_info.set_property("pkg_config_name", "librhash")
