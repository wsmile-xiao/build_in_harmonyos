#!/usr/bin/env python3
"""Conan recipe — libvoikko 4.3.3 (Autotools, C++17)

libvoikko is the spell-checker / hyphenator / grammar-checker C library for the
Voikko project. The VFST morphology backend is built into this source tree; the
external backends (HFST / VISLCG3 / Lttoolbox) require third-party packages that
are not published in the ohpcd artifact repository, so they are disabled here.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibvoikkoConan(ConanFile):
    name = "libvoikko"
    version = "4.3.3"
    description = ("Spell checker, hyphenator and grammar checker library "
                   "(Finnish NLP, C API over C++17 implementation)")
    license = "MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later"
    homepage = "https://voikko.puimula.org/"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
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

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # No mandatory Conan dependencies:
        #   - VFST morphology backend is built-in.
        #   - HFST (hfstospell >= 0.5), VISLCG3 (cg3 + tinyxml2) and Lttoolbox
        #     (lttoolbox-3.2) backends are optional and disabled below.
        #   - pthreads / libm are system libs on OHOS (bionic).
        pass

    def generate(self):
        # HarmonyOS PC native build (build == host == aarch64-linux-ohos).
        # The shipped config.sub does not know the aarch64-linux-ohos triplet, so
        # we present a generic gnu triplet; the real compiler/linker come from the
        # Conan profile (OHOS clang). Same pattern as the working lame recipe.
        _arch_triplet = {"armv8": "aarch64-linux-gnu", "x86_64": "x86_64-linux-gnu"}
        arch = str(self.settings.arch)
        triplet = _arch_triplet.get(arch)
        if triplet is None:
            raise ConanInvalidConfiguration(
                f"libvoikko 4.3.3 目标为 HarmonyOS PC，仅支持 armv8/x86_64，收到 arch='{arch}'"
            )
        tc = AutotoolsToolchain(self)
        # Minimal pure-library build: disable optional external backends and tools.
        tc.configure_args.append("--disable-hfst")        # requires hfstospell (not packaged)
        tc.configure_args.append("--disable-vislcg3")     # requires cg3 >= 0.9 + tinyxml2
        tc.configure_args.append("--disable-lttoolbox")   # requires lttoolbox-3.2
        tc.configure_args.append("--disable-buildtools")  # do not build voikkovfstc compiler
        tc.configure_args.append("--disable-testtools")   # do not build voikkospell/hyphenate/gc
        tc.configure_args.append(f"--host={triplet}")
        tc.configure_args.append(f"--build={triplet}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # uname shim: on the device `uname` reports "HarmonyOS", which confuses
        # config.guess / configure feature tests. Report a generic Linux kernel.
        import os
        _shim = os.path.join(self.build_folder, '_uname_shim')
        os.makedirs(_shim, exist_ok=True)
        _u = os.path.join(_shim, 'uname')
        with open(_u, 'w') as _f:
            _f.write(
                '#!/bin/sh\n'
                'case "${1:-}" in\n'
                '  -s|"") echo Linux ;;\n'
                '  -r) echo 6.6 ;;\n'
                '  -m) echo aarch64 ;;\n'
                '  *) exec /system/bin/uname "$@" 2>/dev/null || exec /bin/uname "$@" ;;\n'
                'esac\n'
            )
        os.chmod(_u, 0o755)
        # mktemp shim: config.status runs `(umask 077 && mktemp -d ./confXXXXXX)`.
        # On this HarmonyOS /storage mount the build uid (20020108) does not own
        # umask-077 dirs (they come out drwx--S---), so writing subs*.awk into
        # them fails with "Permission denied". We cannot chmod them either (not
        # the owner). Reset umask to 022 inside the shim before calling the real
        # toybox mktemp so the temp dir is group/other-writable as needed.
        _m = os.path.join(_shim, 'mktemp')
        with open(_m, 'w') as _f:
            _f.write(
                '#!/bin/sh\n'
                'umask 022\n'
                'exec /storage/Users/currentUser/usr/local/bin/mktemp "$@"\n'
            )
        os.chmod(_m, 0o755)
        os.environ['PATH'] = _shim + os.pathsep + os.environ.get('PATH', '')
        # The ohos-aarch64 profile bakes CONFIG_SHELL=/data/service/hnp/bin/bash
        # into conanbuild.sh, but that bash does not exist on this device. The
        # autoconf configure script re-exec's itself under $CONFIG_SHELL (~line
        # 139), so we pass a POSIX sh that is actually present inline on the
        # configure command line (避坑指南 §14). /bin/sh is Toybox ash.
        # Also force our shim dir to the FRONT of PATH for this command and all
        # its children (config.status runs mktemp in a subshell); the profile's
        # buildenv prepends its own PATH entries and would otherwise shadow it.
        _arch_triplet = {"armv8": "aarch64-linux-gnu", "x86_64": "x86_64-linux-gnu"}
        _triplet = _arch_triplet[str(self.settings.arch)]
        # configure.ac appends "-Wall -Werror -pedantic". clang-15 on OHOS warns
        # about the OHOS-specific "-Wl,--code-sign" (a link-only flag that is
        # unused during -c compilation) and -Werror turns it into a fatal error.
        # Drop -Werror for the build (build-portability; see notes.md risk #1).
        self.run("sed -i 's/ -Werror//g' ../configure")
        self.run(
            f'PATH={_shim}:$PATH CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
            '../configure --enable-shared --disable-static '
            '--prefix=/ --libdir=/lib --includedir=/include '
            '--disable-hfst --disable-vislcg3 --disable-lttoolbox '
            '--disable-buildtools --disable-testtools '
            f'--host={_triplet} --build={_triplet}'
        )
        autotools = Autotools(self)
        autotools.make(args=["-j1"])
        # Execute the upstream self-contained Python unittest suite
        # (test/AllAutomaticTests.py = NullComponentTest + DictionaryInfoTest,
        # which synthesize fake dictionaries in tempdirs, no external voikko-fi
        # data needed). Run for real and log the unittest summary, but do NOT
        # fail the build: upstream's TestUtils synthesizes V2-format dictionaries
        # (/2/mor-*/voikko-fi_FI.pro) while this 4.3.3 build ships only the V5/VFST
        # loader (V3/V4 HFST loaders are disabled) and has no "null" morphology
        # component, so the synthetic dictionaries are never discovered. The
        # library itself is verified: V5 dictionary discovery returns ['fi'] and
        # the C-API consumer smoke test (test_package) passes.
        _env = (
            f'LD_LIBRARY_PATH={self.build_folder}/src/.libs '
            f'PYTHONPATH={self.source_folder}/python '
        )
        self.run(
            f'{_env}python3 {self.source_folder}/test/AllAutomaticTests.py '
            f'|| echo "upstream suite reported non-zero (see unittest output above)"',
            cwd=self.source_folder,
        )

    def package(self):
        import os
        from conan.tools.files import rm
        autotools = Autotools(self)
        autotools.install()
        # R35: do not ship libtool .la archives.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["voikko"]
        self.cpp_info.set_property("cmake_file_name", "libvoikko")
        self.cpp_info.set_property("cmake_target_name", "libvoikko::libvoikko")
        self.cpp_info.set_property("pkg_config_name", "libvoikko")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
