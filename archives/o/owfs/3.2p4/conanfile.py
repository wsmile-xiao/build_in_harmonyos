#!/usr/bin/env python3
"""Conan recipe for owfs 3.2p4 — OHOS-ready.

Build system: Autotools (autoconf + automake + libtool)
Upstream: https://github.com/owfs/owfs

owfs provides a virtual filesystem and network server for Dallas/Maxim
1-wire devices.  The initial OHOS port focuses on the network-only
components (owserver, owhttpd, owftpd, owshell, ownet, owcapi) with
hardware bus-master adapters (USB, i2c, W1, parport, FTDI) disabled.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OwfsConan(ConanFile):
    name = "owfs"
    version = "3.2p4"
    description = "1-Wire filesystem — access Dallas/Maxim 1-wire devices via virtual FS or network"
    license = "GPL-2.0-only AND LGPL-2.0-only"
    homepage = "https://owfs.org/"
    url = "https://github.com/owfs/owfs"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "fuse": [True, False],
        "usb": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "fuse": False,
        "usb": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        if self.options.fuse:
            self.requires("libfuse/3.18.2")
        if self.options.usb:
            self.requires("libusb/1.0.27")
        self.requires("uthash/2.4.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("owfs supports only Linux and OHOS")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        self._patch_sources()

    def _patch_sources(self):
        """Recipe-side patches that are easier to express as replace_in_file."""

        # --- umask fix: OHOS HMDFS umask 077 makes temp dirs unreadable
        #     by child processes (same root cause as libusb).
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            replace_in_file(
                self, configure,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            )
            replace_in_file(
                self, configure,
                '(umask 077 && mkdir "$tmp")',
                '(umask 022 && mkdir "$tmp")',
            )
        # --- config.guess: inject OHOS detection so AC_CANONICAL_TARGET
        #     recognises the aarch64-unknown-linux-musl triple on OHOS devices.
        config_guess = os.path.join(self.source_folder, "config.guess")
        if os.path.isfile(config_guess):
            self._inject_ohos_into_config_guess(config_guess)

        # --- config.sub: register "ohos" as a known OS alias so that
        #     --host=aarch64-unknown-linux-musl is accepted without error.
        config_sub = os.path.join(self.source_folder, "config.sub")
        if os.path.isfile(config_sub):
            self._inject_ohos_into_config_sub(config_sub)

        # --- sd-daemon.c (vendored systemd copy) calls mq_getattr.  The
        #     OHOS sysroot provides librt only as a static archive and
        #     libtool cannot cleanly link it into libow.so, so the build
        #     defines the upstream SD_DAEMON_DISABLE_MQ guard (see
        #     generate()); sd_is_mq() then becomes a no-op and owfs has
        #     no callers of it, so no functionality is lost.  Modules
        #     that depend on it (owserver/owhttpd/owftpd/owtap/owmon/
        #     owexternal) remain disabled pending a full revalidation.

        # --- error.c: clang 15 rejects undeclared variable 'sl' in
        #     fatal_error().  Add missing declaration.
        error_c = os.path.join(
            self.source_folder, "module", "ownet", "c", "src", "c", "error.c"
        )
        if os.path.isfile(error_c):
            replace_in_file(
                self, error_c,
                "char buf[MAXLINE + 1];\n\tva_start(ap, fmt);",
                "char buf[MAXLINE + 1];\n\tenum e_err_print sl;\n\tva_start(ap, fmt);",
            )

    @staticmethod
    def _inject_ohos_into_config_guess(path):
        """Inject OHOS / HongMeng kernel detection into config.guess.

        The stock config.guess from older autotools does not recognise the
        HongMeng / OHOS kernel version string ('HongMeng Kernel X.Y.Z'),
        causing the host-triple guess to fall through to 'unknown'.
        We insert a block right after ``Linux|GNU|GNU/*`` that checks for
        OHOS-specific indicators and forces the musl-libc variant.
        """
        marker = "Linux|GNU|GNU/*"
        injection = (
            "\t# OHOS / HongMeng kernel detection (injected by Conan)\n"
            "\tcase \"$(uname -r 2>/dev/null)\" in\n"
            "\t\t*HongMeng*|*OHOS*)\n"
            "\t\t\tLIBC=musl\n"
            "\t\t\tGUESS=$UNAME_MACHINE-unknown-linux-$LIBC\n"
            "\t\t\techo \"$GUESS\"\n"
            "\t\t\texit\n"
            "\t\t\t;;\n"
            "\tesac\n"
        )
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if "HongMeng" in content:
            return  # already injected (idempotent)
        content = content.replace(marker, marker + "\n" + injection, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def _inject_ohos_into_config_sub(path):
        """Register 'ohos' as a valid OS in config.sub.

        The stock config.sub does not know about 'ohos' so passing
        ``--host=aarch64-ohos`` would fail.  We add a normalisation
        alias: ``*ohos*`` → ``linux-gnu`` (the closest generic match;
        the actual libc is musl, handled by compiler flags).
        """
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if "ohos" in content:
            return  # already injected (idempotent)
        # Insert before the final catch-all ``*`` case
        marker = "\t  ;;\n\t*"
        injection = (
            "\t  ;;\n"
            "\t*-*-ohos*\n"
            "\t\tbasic_machine=$field1\n"
            "\t\tbasic_os=linux-gnu\n"
            "\t\t;;\n"
            "\t*"
        )
        if marker in content:
            content = content.replace(marker, injection, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        if str(self.settings.os) == "OHOS":
            # owfs Makefile.am uses relative -I paths:
            #   -I../include          (module's own include dir)
            #   -I../../../owlib/src/include  (owlib shared include dir)
            # These break in out-of-tree builds.  Inject absolute paths.
            tc.extra_cflags.append(f"-I{self.source_folder}/module/owlib/src/include")
            tc.extra_cflags.append(f"-I{self.source_folder}/module/owshell/src/include")
            tc.extra_cflags.append(f"-I{self.source_folder}/module/owhttpd/src/include")
            tc.extra_cflags.append(f"-I{self.source_folder}/module/owserver/src/include")
            tc.extra_cflags.append(f"-I{self.source_folder}/module/owftpd/src/include")
            tc.extra_cflags.append(f"-I{self.source_folder}/module/owcapi/src/include")
            tc.extra_cflags.append(f"-I{self.source_folder}/module/ownet/c/src/include")
            tc.extra_cflags.append(f"-I{self.source_folder}/src/include")
            # mq_getattr (POSIX message queues): the OHOS sysroot has no
            # librt.so (only librt.a) and libtool cannot link it into
            # libow.so without breaking .la metadata.  Define the
            # upstream SD_DAEMON_DISABLE_MQ guard so sd_is_mq() compiles
            # to a no-op (returns 0); owfs has no callers of sd_is_mq.
            tc.extra_cflags.append("-DSD_DAEMON_DISABLE_MQ")
        tc.generate()

    def _configure_args(self):
        args = [
            "--disable-dependency-tracking",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if not self.options.shared else "--enable-static",
            # Disable optional hardware bus masters (not available on OHOS)
            "--disable-usb" if not self.options.usb else "--enable-usb",
            "--disable-i2c",
            "--disable-w1",
            "--disable-parport",
            "--disable-ftdi",
            # Disable optional service discovery
            "--disable-avahi",
            # Disable language bindings (SWIG-based, not needed)
            "--disable-swig",
            "--disable-owpython",
            "--disable-owphp",
            "--disable-owperl",
            "--disable-owtcl",
            # Disable testing & debug overhead
            "--disable-unittest",
            "--disable-owmalloc",
            "--disable-mutexdebug",
            "--disable-profiling",
            # Disable systemd unit generation (out-of-tree build path bug + OHOS no systemd)
            "--without-systemdsystemunitdir",
            # Core modules only: the server/daemon executables (owserver/
            # owhttpd/owftpd/owtap/owmon/owexternal) are disabled on OHOS
            # for now; owlib/owshell/owcapi cover the C API use case.
            "--enable-owlib",
            "--enable-owshell",
            "--disable-owserver",
            "--disable-owhttpd",
            "--disable-owftpd",
            "--disable-ownet",
            "--disable-ownetlib",
            "--enable-owcapi",
            "--disable-owexternal",
            "--disable-owtap",
            "--disable-owmon",
            # Disable owfs FUSE mount (depends on kernel FUSE support)
            "--disable-owfs" if not self.options.fuse else "--enable-owfs",
        ]

        # FUSE paths — tell configure where to find fuse3 headers/libs
        if self.options.fuse:
            fuse_info = self.dependencies["libfuse"].cpp_info
            fuse_root = self.dependencies["libfuse"].package_folder
            args.append(f"--with-fuseinclude={os.path.join(fuse_root, 'include')}")
            args.append(f"--with-fuselib={os.path.join(fuse_root, 'lib')}")

        # OHOS cross-compilation triples
        if str(self.settings.os) == "OHOS":
            args[:0] = [
                "--build=aarch64-unknown-linux-musl",
                "--host=aarch64-unknown-linux-musl",
            ]

        return args

    def build(self):
        # Ensure helper scripts are executable
        for helper in ("configure", "config.guess", "config.sub", "install-sh"):
            path = os.path.join(self.source_folder, helper)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

        autotools = Autotools(self)
        autotools.configure()

        # On OHOS: fix systemd .service.in srcdir doubling bug in
        # out-of-tree builds.
        if str(self.settings.os) == "OHOS":
            self._fix_systemd_srcdir(self.build_folder)

        autotools.make(args=["-j4"])

    @staticmethod
    def _fix_systemd_srcdir(build_folder):
        """Disable systemd subdirectory build in out-of-tree OHOS builds.

        The owfs systemd Makefile.in has a srcdir doubling bug when
        building out-of-tree: the sed command for .service files
        constructs a path like $(builddir)/$(srcdir)/foo.in which
        resolves to a non-existent doubled directory.
        """
        scripts_makefile = os.path.join(build_folder, "src", "scripts", "Makefile")
        if not os.path.isfile(scripts_makefile):
            return
        with open(scripts_makefile, encoding="utf-8") as fh:
            lines = fh.readlines()
        new_lines = []
        for line in lines:
            if line.lstrip().startswith("SUBDIRS") or line.lstrip().startswith("DIST_SUBDIRS"):
                # Remove 'systemd' token and fix trailing backslash
                import re
                line = re.sub(r'\bsystemd\b\s*', '', line)
                # If the line now ends with just '\' (nothing after it), clean up
                line = re.sub(r'\\\s*$', '', line.rstrip()) + '\n'
            new_lines.append(line)
        with open(scripts_makefile, "w", encoding="utf-8") as fh:
            fh.writelines(new_lines)

    # ---- package ----

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # License files
        for lic in ("COPYING", "COPYING.LIB"):
            src = os.path.join(self.source_folder, lic)
            if os.path.isfile(src):
                copy(self, lic, self.source_folder,
                     os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """Sign .so files for OHOS (same pattern as libusb recipe)."""
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
                signed = path + ".signed"
                subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
                    check=True,
                )
                os.replace(signed, path)
                os.chmod(path, 0o755)

    def package_info(self):
        # Core C API library
        self.cpp_info.libs = ["owcapi"]
        self.cpp_info.includedirs = ["include"]

        # pkg-config names for downstream consumers
        self.cpp_info.set_property("pkg_config_name", "libowcapi")
        self.cpp_info.set_property("cmake_file_name", "owfs")
        self.cpp_info.set_property("cmake_target_name", "owfs::owcapi")

        if self.settings.os in ("Linux",):
            self.cpp_info.system_libs = ["pthread", "dl", "rt"]
        elif self.settings.os in ("OHOS",):
            # pthread is part of libc on OHOS; dl/rt linked implicitly
            self.cpp_info.system_libs = ["pthread"]
