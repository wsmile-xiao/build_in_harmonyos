#!/usr/bin/env python3
"""Conan recipe for rats 2.4 — RATS (Rough Auditing Tool for Security).

RATS is an old autoconf/automake-based C auditing tool. The shipped tarball
already carries a generated `configure` + `Makefile.in` (no automake needed
at build time because the lexers are pre-generated `lex.yy*.c`). It has a hard
build dependency on expat (XML parser for its vulnerability database).

OHOS notes:
* The bundled `configure` hard-codes `umask 077 && mktemp`/`mkdir` for its
  config.status scratch dir; HMDFS setgid semantics make the resulting 0700
  directory unwritable, so we strip `umask 077 &&` before running configure.
* `configure` must be executed through the system `/system/bin/sh` because
  HMDFS blocks direct shebang execve of freshly-unpacked scripts.
* The produced `rats` executable is a regular ELF and must be self-signed
  before it can run on a real OHOS device.
"""

import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RatsConan(ConanFile):
    name = "rats"
    version = "2.4"
    description = "RATS - Rough Auditing Tool for Security"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/andrew-d/rough-auditing-tool-for-security"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # Hard build/runtime dependency: RATS parses its vulnerability
        # database (rats-*.xml) with expat.
        self.requires("expat/2.8.4", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rats supports Linux/OHOS native builds, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # expat: inject -I/-L/-l into the autotools environment so that
        # AC_CHECK_HEADERS(expat.h) / AC_CHECK_LIB(expat, ...) succeed.
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        environment = toolchain.environment()

        # RATS's hand-written Makefile.in compiles with $(CFLAGS) only and never
        # references $(CPPFLAGS), so AutotoolsDeps' injected expat include path
        # (which lands in CPPFLAGS) is invisible at compile time. Mirror the
        # dependency include directories into CFLAGS so vuln_db.c etc. find
        # expat.h. (The link rule already uses $(LDFLAGS)/$(LIBS), which
        # AutotoolsDeps populates, so expat linking is fine.)
        expat = self.dependencies["expat"]
        for inc in expat.cpp_info.includedirs:
            environment.append(
                "CFLAGS", f"-I{os.path.join(expat.package_folder, inc)}"
            )

        # OHOS /tmp may be read-only or have setgid issues; keep all
        # configure/make scratch files inside the isolated build dir.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        environment.define_path("TMPPREFIX", os.path.join(tmpdir, "zsh"))

        if self.settings.os == "OHOS":
            # The OHOS SDK clang needs its ABI-matched lib dir on LD_LIBRARY_PATH
            # at configure/probe time.
            sdk_llvm_libs = sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
            )
            if sdk_llvm_libs:
                environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_libs[-1])
        toolchain.generate(env=environment)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # RATS ships a hand-written Makefile.in with NO VPATH support, so an
        # out-of-tree build cannot locate the .c sources. Build in-tree
        # (configure + make both run inside source_folder).
        if self.settings.os == "OHOS":
            self._relax_config_status_tmpdir(
                os.path.join(self.source_folder, "configure")
            )
            configure_script = os.path.join(self.source_folder, "configure")
            command = (
                "CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
                + shlex.join(["/system/bin/sh", configure_script])
            )
            # Force autoconf into cross-compile mode. conan-verify runs with
            # -pr:b == -pr:h == ohos-aarch64, so Conan does not add --host and
            # autoconf would try to *execute* the compiler probe binary. That
            # binary is an aarch64-OHOS ELF that cannot run on the (x86_64)
            # build host / is unsigned on-device, so the probe fails with
            # "cannot run C compiled programs". Declaring an explicit host/build
            # pair that differ makes autoconf skip the run tests.
            cross_flags = (
                "--host=aarch64-unknown-linux-ohos --build=x86_64-pc-linux-gnu"
            )
            # AutotoolsToolchain may emit an empty/"/" --prefix in this
            # build==host setup; force the real package folder explicitly and
            # place it LAST so it wins over any toolchain --prefix.
            prefix_flag = f"--prefix={self.package_folder}"
            tail = " ".join(
                x for x in (autotools._configure_args, cross_flags, prefix_flag) if x
            )
            command = f"{command} {tail}"
            self.run(command, cwd=self.source_folder, env="conanbuild")
        else:
            cfg = "./configure"
            if autotools._configure_args:
                cfg = f"{cfg} {autotools._configure_args}"
            cfg = f"{cfg} --prefix={self.package_folder}"
            self.run(cfg, cwd=self.source_folder, env="conanbuild")
        # A single job avoids make jobserver/FIFO failures on HMDFS.
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run("make install", cwd=self.source_folder, env="conanbuild")
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(os.path.join(self.package_folder, "bin", "rats"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        # rats links libexpat.so at runtime; expose expat's lib dir so the
        # installed binary finds it without the consumer setting LD_LIBRARY_PATH.
        expat = self.dependencies["expat"]
        for lib in expat.cpp_info.libdirs:
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(expat.package_folder, lib)
            )

    @staticmethod
    def _relax_config_status_tmpdir(path):
        # Autoconf's embedded config.status template creates a 0700 temp
        # directory via `umask 077 && mktemp`/`mkdir`. HMDFS adds setgid
        # semantics that make it unwritable. Strip the umask guard (the
        # change is idempotent and only applied when present).
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        patched = content.replace("umask 077 && ", "")
        if patched == content:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(patched)

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing packaged executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed packaged executable has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
