#!/usr/bin/env python3
"""Conan recipe for oils-for-unix 0.37.0 (OHOS aarch64).

oils-for-unix is a C++11 Unix shell that ships OSH (a POSIX shell) and
YSH (a structured-data shell) behind a single busybox-style binary plus
the `osh` and `ysh` symlinks.

Upstream build system is a custom POSIX shell `./configure` + a generated
`_build/oils.sh` compile driver (NOT autotools, NOT a raw Makefile), so this
recipe drives those scripts directly instead of using AutotoolsToolchain.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, chdir
from conan.tools.layout import basic_layout


class OilsForUnixConan(ConanFile):
    name = "oils-for-unix"
    version = "0.37.0"
    description = "Oils for Unix: OSH (POSIX shell) and YSH (structured-data shell)"
    license = "Apache-2.0"
    homepage = "https://oils.pub/"
    url = ""  # CI fills this

    # Command-line tool: produces executable binaries (application package).
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # oils-for-unix has no mandatory third-party dependencies.
        # A C++11 compiler + libc/libc++ are the only build requirements.
        # GNU readline is optional and is deliberately disabled here because
        # OHOS does not provide it; the shells remain fully functional
        # (non-interactive / scripting features) without readline.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: obtain compilers from Conan conf, never from shell ${CC}/${CXX}.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        cxx = comp_execs.get("cpp") or "clang++"
        cxx_base = os.path.basename(cxx)
        toolchain_bin = os.path.dirname(cxx) or "/data/service/hnp/bin"

        # Upstream requires an in-tree build (out-of-tree builds unsupported).
        # Restore executable bits: conan's get()/source-copy can drop the +x on
        # upstream helper scripts (see knowledge E490).
        for script in ("configure", "_build/oils.sh"):
            os.chmod(os.path.join(self.source_folder, script), 0o755)

        with chdir(self, self.source_folder):
            # 1. Feature detection.  `cc` is not available on OHOS, so pass the
            #    C compiler explicitly.  `--without-readline` avoids probing for
            #    the unavailable GNU readline.
            #    NOTE: run via `sh` (not `./configure`) because HMDFS/OHOS MAC
            #    denies exec() of freshly-extracted scripts (chmod is a no-op).
            self.run(
                f"export PATH={toolchain_bin}:/bin:$PATH && "
                f"sh ./configure --prefix={self.package_folder} "
                f"--cxx-for-configure={cc} --without-readline"
            )
            # 2. Compile the C++ shell.  Pass the compiler basename so the
            #    build output directory is predictable (_bin/clang++-opt-sh).
            self.run(
                f"export PATH={toolchain_bin}:/bin:$PATH && "
                f"sh _build/oils.sh --cxx {cxx_base} --without-readline"
            )

    def package(self):
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = comp_execs.get("cpp") or "clang++"
        cxx_base = os.path.basename(cxx)

        # The opt variant produces both `oils-for-unix` and a `.stripped` copy.
        # On OHOS the stripped binary fails to exec with EPERM (platform ELF
        # verification rejects strip-rewritten images), so ship the unstripped
        # binary — it is runnable and functionally identical.
        out_dir = os.path.join(self.source_folder, "_bin", f"{cxx_base}-opt-sh")
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "oils-for-unix", src=out_dir, dst=bin_dir)

        # busybox-style dispatch symlinks.  On OHOS HMDFS, symlink() may be
        # denied in some sandbox contexts; fall back to copying the multi-call
        # binary under the dispatch name (oils-for-unix dispatches on argv[0]).
        import shutil
        for link in ("osh", "ysh"):
            link_path = os.path.join(bin_dir, link)
            if os.path.lexists(link_path):
                os.remove(link_path)
            try:
                os.symlink("oils-for-unix", link_path)
            except OSError:
                shutil.copy2(os.path.join(bin_dir, "oils-for-unix"), link_path)

        # Upstream also installs the man page.
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "osh.1", src=os.path.join(self.source_folder, "doc"), dst=man_dir)

    def package_info(self):
        # Application package: only executables in bin/ (no libs/headers).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
