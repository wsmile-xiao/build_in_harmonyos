#!/usr/bin/env python3
"""Conan recipe — lib3ds 1.3.0 (Autotools).

Upstream lib3ds is the free ANSI-C library for 3D-Studio (.3DS) model files.
The 1.3.0 release ships a pre-generated autotools `configure` (2006 vintage)
plus `Makefile.am`; every Linux distribution builds it with that autotools
chain (Debian, Fedora, Gentoo, FreeBSD). We follow the same path — no CMake
exists in this release.

OHOS adaptation (0 patches — same strategy as lame/3.100):
  * The shipped `configure` (2006) uses `umask 077 && mktemp -d` for its
    config.status scratch directory, which creates temp files mode 0600.
    On OHOS's restricted filesystem this manifests as "Permission denied"
    during `config.status`. We fix it at runtime by replacing `umask 077`
    with `umask 022` in the configure script (in-memory, no source patch).
  * The shipped `config.guess`/`config.sub` (2006) predate OpenHarmony and
    reject the `*-linux-ohos` tuple. Rather than patching them, we pass an
    explicit `--host`/`--build` of `aarch64-linux-gnu` and install a uname
    shim that reports "Linux" — autotools then treats OHOS as Linux-ELF
    (which it is at the ABI level), and the shipped config.sub accepts the
    standard linux-gnu tuple without modification.
  * The upstream tarball is a .zip, which does not preserve the executable
    bit on `configure`/`config.guess`/`config.sub`/`install-sh`/`missing`/
    `mkinstalldirs`. We restore those bits at build time.

Upstream test situation:
  * lib3ds 1.3.0 registers NO formal test suite (no `TESTS`/
    `check_PROGRAMS`; `examples/3dsplay.c` is an unbuilt OpenGL demo,
    NOT in SUBDIRS, not a test). Consumer validation is carried entirely
    by test_package/, which exercises the core 3DS API in memory.
  * `3dsdump` is a real installed `bin_PROGRAMS`; `lib3ds-config` is a real
    installed `bin_SCRIPTS` (see commands.json).
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Lib3dsConan(ConanFile):
    name = "lib3ds"
    version = "1.3.0"
    description = "Free ANSI-C library for managing 3D-Studio (.3DS) model files"
    license = "LGPL-2.1"
    homepage = "https://lib3ds.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # lib3ds is pure C; drop the C++ settings so they don't force a
        # libstdc++/libc++ ABI split that this library doesn't use.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        self.tool_requires("automake/1.18")

    def generate(self):
        # Nominal triplet uses -linux-gnu suffix so the 2006-vintage
        # config.sub accepts it; the uname shim in build() makes
        # config.guess report Linux. Real cross-target is set by the
        # profile's CC/CXX (OHOS clang).
        _arch_triplet = {"armv8": "aarch64-linux-gnu", "x86_64": "x86_64-linux-gnu"}
        arch = str(self.settings.arch)
        triplet = _arch_triplet.get(arch)
        if triplet is None:
            raise ConanInvalidConfiguration(
                f"lib3ds 1.3.0 targets HarmonyOS PC, only armv8/x86_64 supported, got arch='{arch}'"
            )
        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--host={triplet}")
        tc.configure_args.append(f"--build={triplet}")
        # static/shared is driven by libtool via --enable-shared/--disable-shared,
        # which AutotoolsToolchain derives from `options.shared` automatically.
        tc.generate()

    def build(self):
        # 1. The upstream .zip does not preserve exec bits on autotools
        #    helper scripts. Restore them so configure can run.
        for script in glob.glob(
            os.path.join(self.source_folder, "**", "configure"), recursive=True
        ) + [
            os.path.join(self.source_folder, "config.guess"),
            os.path.join(self.source_folder, "config.sub"),
            os.path.join(self.source_folder, "install-sh"),
            os.path.join(self.source_folder, "missing"),
            os.path.join(self.source_folder, "mkinstalldirs"),
        ]:
            if os.path.isfile(script):
                os.chmod(script, 0o755)

        # 2. The shipped config.guess/config.sub (2006) predate aarch64.
        #    Use the copies supplied by the Conan Automake build requirement
        #    instead of relying on host-specific /usr/share paths.
        import shutil
        automake_share = os.path.join(
            self.dependencies.build["automake"].package_folder,
            "share",
            "automake-1.18",
        )
        for _aux in ("config.guess", "config.sub"):
            _src = os.path.join(automake_share, _aux)
            _dst = os.path.join(self.source_folder, _aux)

            if not os.path.isfile(_src):
                raise ConanInvalidConfiguration(
                    f"Automake auxiliary file not found: {_src}"
                )

            shutil.copy2(_src, _dst)
            os.chmod(_dst, 0o755)

        # Fail early instead of silently falling back to the obsolete
        # upstream config.sub.
        self.run(
            f'"{os.path.join(self.source_folder, "config.sub")}" '
            f'aarch64-linux-gnu',
            env="conanbuild",
        )

        # 3. The 2006 configure uses `umask 077` for its config.status
        #    scratch dir, creating temp files mode 0600 — unwritable on
        #    OHOS. Replace with `umask 022` in-memory (no source patch).
        for _cfg in glob.glob(
            os.path.join(self.source_folder, "**", "configure"), recursive=True
        ):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))

        # 4. The 2006 lib3ds/Makefile.in has a custom code-gen rule:
        #      chunktable.h: chunk.h chunktable.sed
        #           sed -f chunktable.sed chunk.h >chunktable.h
        #    It lacks $(srcdir) prefixes. `make` honors VPATH for
        #    *prerequisites* but the `sed` command itself uses bare
        #    filenames, so an out-of-tree build cannot find the source
        #    files in the build dir ("chunktable.sed: No such file").
        #    Fix it in-memory on both Makefile.am and Makefile.in (0 patches).
        for _mf in (
            os.path.join(self.source_folder, "lib3ds", "Makefile.am"),
            os.path.join(self.source_folder, "lib3ds", "Makefile.in"),
        ):
            if os.path.isfile(_mf):
                replace_in_file(
                    self,
                    _mf,
                    "sed -f chunktable.sed chunk.h >chunktable.h",
                    "sed -f $(srcdir)/chunktable.sed $(srcdir)/chunk.h >chunktable.h",
                )

        # 5. Install a uname shim so config.guess reports "Linux" (the
        #    2006 config.guess does not know HarmonyOS). Combined with the
        #    explicit --host/--build triplet above, autotools builds for
        #    linux-ELF which is ABI-compatible with OHOS.
        _shim = os.path.join(self.build_folder, "_uname_shim")
        os.makedirs(_shim, exist_ok=True)
        _u = os.path.join(_shim, "uname")
        _uname_machine = {"armv8": "aarch64", "x86_64": "x86_64"}.get(
            str(self.settings.arch), str(self.settings.arch)
        )
        with open(_u, "w") as _f:
            _f.write(
                "#!/bin/sh\n"
                'case "${1:-}" in\n'
                '  -s|"") echo Linux ;;\n'
                "  -r) echo 6.6 ;;\n"
                f"  -m) echo {_uname_machine} ;;\n"
                '  *) exec /system/bin/uname "$@" 2>/dev/null || exec /bin/uname "$@" ;;\n'
                "esac\n"
            )
        os.chmod(_u, 0o755)
        os.environ["PATH"] = _shim + os.pathsep + os.environ.get("PATH", "")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Tidy up libtool archives (not needed by conan consumers).
        libdir = os.path.join(self.package_folder, "lib")
        for la in ("lib3ds.la", "lib3ds-1.la"):
            la_path = os.path.join(libdir, la)
            if os.path.isfile(la_path):
                os.remove(la_path)

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # lib3ds builds lib3ds.la with libtool `-release 1`, so the
        # installed runtime objects are lib3ds-1.so.3 / lib3ds-1.so.3.0.0.
        # The 2006-vintage libtool in this release creates the *development*
        # symlink as lib3ds.so (the base name), NOT lib3ds-1.so. CMakeDeps
        # resolves `cpp_info.libs` by looking for lib<name>.so in the
        # package lib dir, so the link name must be `3ds` (matching
        # lib3ds.so), not `3ds-1`. Verified against the actual install tree.
        self.cpp_info.libs = ["3ds"]
        self.cpp_info.set_property("cmake_file_name", "lib3ds")
        self.cpp_info.set_property("cmake_target_name", "lib3ds::lib3ds")
        self.cpp_info.set_property("pkg_config_name", "lib3ds")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
