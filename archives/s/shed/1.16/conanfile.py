#!/usr/bin/env python3
"""Conan recipe for shed 1.16 - Simple Hex EDitor (C, ncurses, autotools).

HarmonyOS PC adaptation points:
- Piped input (`cat file | shed`) is buffered in a tmpfile(). The OHOS musl
  tmpfile() is hard-wired to /data/local/tmp (NDK libc.a holds the template
  "/data/local/tmp/tmpfile_XXXXXX") and ignores $TMPDIR; ordinary processes
  cannot write there, so upstream aborts with "tmpfile() failed.".
  patches/0001 creates the buffer with mkstemp() + unlink() in $TMPDIR and
  keeps tmpfile() as the fallback when $TMPDIR is unset.
- configure.ac has no AC_CANONICAL_HOST. With the OHOS profile used for both
  build and host, Conan passes no --host and configure insists on executing
  a conftest, which aborts on the x86 runner ("cannot run C compiled
  programs"). Naming only --host makes configure probe instead: native on an
  OHOS builder, cross on the x86 runner. config.sub is never consulted.
- config.status creates its scratch directory with `umask 077 && mktemp -d`;
  files cannot be created inside such a 0700 directory on the HMDFS build
  tree of OHOS builders (E129/E114), so a plain mkdir is used there.
- ncurses/6.6 ships only the wide-character libraries: configure's
  AC_CHECK_LIB(ncurses, initscr) finds nothing and the libraries come from
  AutotoolsDeps (LIBS=... -lncursesw). The terminfo database stays in the
  ncurses package, so the requirement is run=True (TERMINFO via conanrun).
- The shipped Autotools scripts get their execute bits restored (E490).
- make -j1: parallel make on HMDFS hits jobserver fifo EPERM (E074).
  Upstream `make check` registers no tests; it is still run (R51).
- The .codesign section emitted by the SDK linker is not accepted by the
  OHOS loader (E077/E077B): the packaged executable is re-signed, with
  LD_LIBRARY_PATH removed from the signer environment.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ShedConan(ConanFile):
    name = "shed"
    version = "1.16"
    description = "Simple Hex EDitor: full-screen curses hex editor with a pico-like interface"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/shed/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("hex-editor", "ncurses", "terminal")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Static ncurses still owns the terminfo database: run=True keeps the
        # ncurses binary in consumer graphs so its runenv exports TERMINFO.
        self.requires("ncurses/6.6", run=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"shed supports Linux and OHOS, not {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS" and not cross_building(self):
            tc.update_configure_args({"--host": "aarch64-linux-ohos"})
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: keep the shipped Autotools scripts executable on OHOS paths.
        for script in ("configure", "compile", "depcomp", "install-sh", "missing"):
            path = os.path.join(self.source_folder, script)
            os.chmod(path, os.stat(path).st_mode | 0o111)
        if self.settings.os == "OHOS":
            configure = os.path.join(self.source_folder, "configure")
            replace_in_file(self, configure,
                            '(umask 077 && mktemp -d "./confXXXXXX")',
                            '(mkdir "./conf$$" && echo "./conf$$")')
            replace_in_file(self, configure,
                            '(umask 077 && mkdir "$tmp")',
                            '(mkdir "$tmp")')
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream registers no TESTS/check_PROGRAMS; run the target anyway (R51).
        autotools.make(target="check", args=["-j1"])

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "shed", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "shed.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(os.path.join(self.package_folder, "bin", "shed"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            self.output.warning("binary-sign-tool/llvm-objcopy not found: bin/shed left unsigned")
            return
        env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
        work = os.path.join(self.build_folder, "codesign")
        os.makedirs(work, exist_ok=True)
        unsigned = os.path.join(work, "shed")
        signed = unsigned + ".signed"
        shutil.copy2(path, unsigned)
        subprocess.run([objcopy, "--remove-section", ".codesign", unsigned],
                       check=True, env=env, timeout=60)
        subprocess.run([signer, "sign", "-inFile", unsigned, "-outFile", signed,
                        "-selfSign", "1"], check=True, env=env, timeout=120)
        shutil.copy2(signed, path)
        os.chmod(path, 0o755)
