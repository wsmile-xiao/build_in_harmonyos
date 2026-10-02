#!/usr/bin/env python3
"""Conan recipe for swapspace 1.18 (dynamic swap space manager).

swapspace monitors system memory and automatically creates or removes
swapfiles so that free space stays within a configured window.  Upstream
ships only ``configure.ac`` in the release tarball (no generated
``configure``), so the autotools path would need autoreconf in CI.  The
recipe instead reproduces the target/source mapping of upstream's own
hand-written ``src/Makefile.static`` with direct clang invocations, which
keeps the package free of any host build-system dependency.

Runtime scope: the binary is a complete, unmodified build of the upstream
sources.  Swap *activation* additionally needs a writable swappath, root
privileges and a kernel that implements CONFIG_SWAP; on HarmonyOS PC the
configuration, option parsing, validation and reporting paths are fully
functional and are what test_package exercises.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class SwapspaceConan(ConanFile):
    name = "swapspace"
    version = "1.18"
    description = "Dynamic swap space manager for Linux"
    license = "GPL-2.0-only"
    homepage = "https://github.com/Tookmund/Swapspace"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    _swap_sources = (
        "log.c", "main.c", "memory.c", "opts.c", "state.c",
        "support.c", "swaps.c",
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"swapspace targets a POSIX/Linux system, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        src = os.path.join(self.source_folder, "src")

        # The release tarball has no generated configure/config.h.  Upstream
        # ships the hand-maintained config.h.static for its static Makefile
        # path; reuse it and add the PACKAGE_* identifiers that autoheader
        # would otherwise generate from AC_INIT.  Values mirror AC_INIT in
        # configure.ac so --version output matches upstream releases.
        config_h = os.path.join(src, "config.h")
        shutil.copyfile(os.path.join(src, "config.h.static"), config_h)

        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = compilers.get("c", "clang")

        # Values are single-quoted at the shell level so that the embedded
        # double quotes (and the space in DATE / PACKAGE_STRING) survive.
        # VARPREFIX/ETCPREFIX correspond to automake's localstatedir/sysconfdir
        # roots. src/swaps.c declares the default swap directory as
        # VARPREFIX"/lib/swapspace" and src/opts.c declares the default
        # config file as ETCPREFIX"/swapspace.conf", so these must be the
        # directory *parents*: /var yields /var/lib/swapspace (matching
        # Makefile.am's $(localstatedir)/lib/swapspace) and /etc yields
        # /etc/swapspace.conf (matching sysconf_DATA, which installs with no
        # subdirectory).
        defines = [
            "-DSUPPORT_LARGE_FILES",
            "'-DVERSION=\"1.18\"'",
            "'-DDATE=\"Sat Jan 22 2022\"'",
            "'-DVARPREFIX=\"/var\"'",
            "'-DETCPREFIX=\"/etc\"'",
            "'-DPACKAGE_NAME=\"swapspace\"'",
            "'-DPACKAGE_VERSION=\"1.18\"'",
            "'-DPACKAGE_STRING=\"swapspace 1.18\"'",
        ]
        # swapspace is C99 plus POSIX sigaction(); keep the upstream gnu99 mode.
        cflags = ["--std=gnu99", "-O2", "-Wall"] + defines

        objects = []
        for unit in self._swap_sources:
            obj = os.path.join(self.build_folder, unit[:-2] + ".o")
            self.run(
                f'"{cc}" {" ".join(cflags)} '
                f'-I"{src}" -c "{os.path.join(src, unit)}" -o "{obj}"',
                cwd=src,
            )
            objects.append(obj)

        swap_bin = os.path.join(self.build_folder, "swapspace")
        self.run(f'"{cc}" {" ".join(objects)} -o "{swap_bin}"', cwd=src)

        # `hog` is upstream's separate memory-hog helper (noinst_PROGRAMS in
        # src/Makefile.am); it has its own main() and is used to drive the
        # daemon under manual memory pressure.  Upstream does not install it,
        # so it is built (to keep the delivered build faithful to
        # `make -f Makefile.static all`) but not packaged.
        hog_obj = os.path.join(self.build_folder, "hog.o")
        self.run(
            f'"{cc}" {" ".join(cflags)} '
            f'-I"{src}" -c "{os.path.join(src, "hog.c")}" -o "{hog_obj}"',
            cwd=src,
        )
        self.run(
            f'"{cc}" "{hog_obj}" -o "{os.path.join(self.build_folder, "hog")}"',
            cwd=src,
        )

        for path in (swap_bin, os.path.join(self.build_folder, "hog")):
            if not os.path.isfile(path):
                raise ConanException(f"expected build output missing: {path}")

    def package(self):
        copy(
            self,
            "swapspace",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "swapspace.8",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "share", "man", "man8"),
            keep_path=False,
        )
        # ETCPREFIX"/swapspace.conf" is where the daemon looks for its config, so
        # the sample is installed at exactly that relative path.
        copy(
            self,
            "swapspace.conf",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "etc"),
            keep_path=False,
        )
        # Upstream ships the GPL-2.0 text as COPYING.
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        bin_path = os.path.join(self.package_folder, "bin", "swapspace")
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
        self.conf_info.define("user.swapspace:version", self.version)
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
