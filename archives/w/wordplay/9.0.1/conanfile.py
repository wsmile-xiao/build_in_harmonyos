#!/usr/bin/env python3
"""Conan recipe for wordplay 9.0.1 (anagram generator, HarmonyOS PC).

Upstream is a single-file C program (wordplay.c, 921 lines) with a four-line
handwritten makefile and no configure/install/test infrastructure.  Two
upstream facts shape this recipe:

1. The makefile hardcodes the link line
   ``$(CC) $(CFLAGS) $(LDFLAGS) $(CPPFLAGS) -O -o wordplay wordplay.c
   -licuio -licui18n -licuuc -licudata``.  ICU is a C++ library: when a C
   compiler drives the link, the C++ runtime must come *after* the ICU static
   libs or lld reports undefined symbols.  That trailing slot cannot be
   injected through any make variable, so the recipe drives the equivalent
   single compile+link command itself instead of shelling out to make (the
   command is otherwise identical to the makefile's recipe).
2. There is no install target and no test suite: the recipe installs
   ``bin/wordplay`` plus the runtime word list ``res/words721.txt`` itself,
   and consumer validation is provided entirely by test_package (see
   test_package/MANIFEST.yml for the audit trail).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class WordplayConan(ConanFile):
    name = "wordplay"
    version = "9.0.1"
    description = (
        "Wordplay: anagram generator - finds anagrams of a string using a "
        "word list (Unicode-aware via ICU)"
    )
    # Upstream tarball ships the full GNU GPL v3 text as LICENSE.
    license = "GPL-3.0-only"
    homepage = "https://github.com/mendelmunkis/wordplay"
    # Official upstream tag archive (commit 29ff967a); byte-identical to
    # the Debian wordplay_9.0.1.orig.tar.gz repack (same sha256).
    url = "https://github.com/mendelmunkis/wordplay"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # wordplay.c includes unicode/ustdio.h, unicode/unorm2.h and
        # unicode/ustring.h and links -licuio -licui18n -licuuc -licudata.
        # icu4c/78 is the repo's validated OHOS static build
        # (--disable-shared, data packaged into libicudata.a).
        self.requires("icu4c/78")

    def validate(self):
        # R32: OHOS must be accepted alongside Linux, never "== Linux".
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wordplay supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def export_sources(self):
        # No patches for wordplay 9.0.1 (upstream compiles clean on OHOS);
        # the conandata patch export convention is kept anyway.
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def _compiler(self):
        # R33: values come from tools.build:compiler_executables, never from
        # shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("c") or "clang"

    def _ohos_tool(self, name, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get(name, default)

    def build(self):
        # conandata patches is {} for 9.0.1; apply is a no-op kept for the
        # project's patch convention.
        apply_conandata_patches(self)

        icu = self.dependencies["icu4c"]
        agg = icu.cpp_info.aggregated_components()
        include_flags = " ".join(
            f'-I"{d}"' for d in agg.includedirs
        )
        lib_flags = " ".join(f'-L"{d}"' for d in agg.libdirs)

        optimization_flags = {
            "Debug": "-g -O0",
            "Release": "-O2",
            "RelWithDebInfo": "-g -O2",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")

        # wordplay.c is K&R-flavoured C89 (implicit int in a couple of
        # helper declarations); -Wno qualifiers only silence the two
        # upstream warnings that are not OHOS issues.
        cflags = f"{optimization_flags} -Wno-implicit-int"

        compiler = self._compiler()
        # Link order: the object, then the ICU libs in the makefile's order
        # (icuio -> icui18n -> icuuc -> icudata), then the C++ runtime
        # (ICU is C++; a C compiler driver will not add it), then the
        # system libs icu4c/78 declares for Linux/OHOS.
        system_libs = "-lm -lpthread -ldl"
        # R9: single translation unit, no parallelism to gain.
        self.run(
            f'"{compiler}" {cflags} {include_flags} '
            f'"{os.path.join(self.source_folder, "wordplay.c")}" '
            f"-o wordplay {lib_flags} "
            f"-licuio -licui18n -licuuc -licudata -lc++ {system_libs}",
            cwd=self.build_folder,
        )

    def package(self):
        copy(self, "wordplay", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        binary = os.path.join(self.package_folder, "bin", "wordplay")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"wordplay executable was not produced by the build: {binary}"
            )

        # Runtime word list: DEFAULT_WORD_FILE is the relative path
        # "words721.txt" (24867 entries despite the historical name), so the
        # file must ship with the package; consumers locate it explicitly
        # via `wordplay ... -f <pkg>/res/words721.txt`.
        copy(self, "words721.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "res"), keep_path=False)
        words = os.path.join(self.package_folder, "res", "words721.txt")
        if not os.path.isfile(words):
            raise ConanInvalidConfiguration(
                f"word list was not packaged: {words}"
            )

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "readme", src=self.source_folder,
             dst=os.path.join(self.package_folder, "res", "doc"),
             keep_path=False)

        # The HNP signing tools only exist on the HarmonyOS worker; a freshly
        # linked binary has no .codesign section, so on a host without them
        # this block is a no-op instead of a hard "command not found" error.
        if str(self.settings.os) == "OHOS":
            sign_tool = self._ohos_tool(
                "sign_tool", "/data/service/hnp/bin/binary-sign-tool"
            )
            objcopy = self._ohos_tool(
                "objcopy", "/data/service/hnp/bin/llvm-objcopy"
            )
            if objcopy and os.path.isfile(objcopy):
                self.run(
                    f'"{objcopy}" --remove-section .codesign "{binary}" '
                    "2>/dev/null || true",
                    cwd=self.package_folder,
                )
            if sign_tool and os.path.isfile(sign_tool):
                signed = binary + ".signed"
                self.run(
                    f'"{sign_tool}" sign -inFile "{binary}" '
                    f'-outFile "{signed}" -selfSign 1',
                    cwd=self.package_folder,
                    quiet=True,
                )
                os.replace(signed, binary)
        os.chmod(binary, 0o755)

    def package_info(self):
        # wordplay is an application package: nothing to link against, the
        # runtime word list lives in res/.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
