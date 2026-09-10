#!/usr/bin/env python3
"""Conan recipe — naga 1.0 (ncurses terminal snake game).

naga is a terminal implementation of the Snake game (BSD-3-Clause) using
ncurses and pthread. Upstream ships a plain Makefile with a hardcoded
``CC=gcc``, an install rule that moves the binary to ``/usr/local/bin``
(no DESTDIR support) and no test suite, so this recipe compiles the 7
translation units directly with the Conan-provided clang instead of
invoking the upstream Makefile (nudoku precedent). Upstream
``src/curses_wrapper.c`` includes ``<curses.h>`` directly, satisfied by
the ncurses Conan package headers with no source adaptation.

ncurses is provided as the ``ncurses/6.6`` Conan dependency (nsnake
precedent). The 6.6 recipe is the repo-local autotools static wide-char
build with OHOS support (no CMake/ninja tool edge); 6.6 is not published
on ConanCenter so resolution stays on the ohpcd remote. The previous
bundled-headers + ``-lncurses``-against-system approach is removed: the
HarmonyOS preflight worker has no system ncurses library
(``ld.lld: unable to find library -lncurses``), so the link must use the
dependency's ``cpp_info`` include/lib dirs and wide-char libs.

The curses-free game logic (engine/naga/utils/keypress) is additionally
archived as libnaga.a so test_package can exercise the real game APIs
without a terminal (nudoku precedent); the interactive ``naga`` binary
cannot run in a non-interactive CI environment.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NagaConan(ConanFile):
    name = "naga"
    version = "1.0"
    description = "naga - terminal implementation of the Snake game using ncurses"
    license = "BSD-3-Clause"
    homepage = "https://github.com/anayjoshi/naga"
    url = "https://github.com/anayjoshi/naga"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # nsnake precedent: ncurses from Conan. Pin 6.6 (repo-local
        # autotools static wide-char build with OHOS _build_ohos support;
        # not on ConanCenter, so no broken cmake/ninja closure).
        self.requires("ncurses/6.6")

    def validate(self):
        # R32: platform check must cover OHOS, not `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"naga supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        # R33: compiler/ar from the Conan conf dict, never from shell env vars.
        # Resilience (preflight 2026-09-08: conf supplied
        # "/data/service/hnp/bin/clang" but the file was inaccessible on the
        # worker): conf stays primary; only when the absolute path is
        # missing/non-executable do we fall back to the bare tool name so the
        # shell resolves it via the HMBS-prepended conanbuild PATH.
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        raw_cc = ce.get("c") or "clang"
        if os.path.sep in raw_cc:
            if os.path.isfile(raw_cc) and os.access(raw_cc, os.X_OK):
                cc = raw_cc
            else:
                self.output.warning(
                    f"conf compiler '{raw_cc}' inaccessible, "
                    "falling back to 'clang' via conanbuild PATH"
                )
                cc = "clang"
        else:
            cc = raw_cc
        ar = ce.get("ar")
        if not ar:
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            cand = os.path.join(bindir, "llvm-ar") if bindir else ""
            if cand and os.path.isfile(cand):
                ar = cand
        if not ar:
            ar = "llvm-ar"
        return cc, ar

    def _ncurses_flags(self):
        # Resolve the ncurses dependency to absolute include/lib dirs and
        # link flags, preserving the recipe's lib order (consumers first,
        # core provider last). nsnake precedent.
        dep = self.dependencies["ncurses"]
        pkg = dep.package_folder
        raw_inc = list(dep.cpp_info.includedirs or [])
        raw_lib = list(dep.cpp_info.libdirs or [])
        inc_dirs = [
            d if os.path.isabs(d) else os.path.join(pkg, d) for d in raw_inc
        ] or [os.path.join(pkg, "include")]
        lib_dirs = [
            d if os.path.isabs(d) else os.path.join(pkg, d) for d in raw_lib
        ] or [os.path.join(pkg, "lib")]
        libs = list(dep.cpp_info.libs or []) or ["ncursesw"]
        inc_flags = " ".join(f'-I"{d}"' for d in inc_dirs)
        lib_flags = " ".join([f'-L"{d}"' for d in lib_dirs]
                             + [f"-l{lib}" for lib in libs])
        return inc_flags, lib_flags

    def build(self):
        apply_conandata_patches(self)
        cc, ar = self._toolchain()
        src = self.source_folder
        out = self.build_folder

        # ncurses headers/libs come from the ncurses/6.6 Conan dependency
        # (no bundled res/, no system -lncurses assumption).
        nc_inc_flags, nc_lib_flags = self._ncurses_flags()

        cflags = f'-O2 -Wall {nc_inc_flags}'
        units = ["main", "naga", "keypress", "curses_wrapper", "utils", "render", "engine"]
        for unit in units:
            self.run(f'"{cc}" {cflags} -c "{src}/src/{unit}.c" -o "{out}/{unit}.o"',
                     env="conanbuild")
        objects = " ".join(f'"{out}/{unit}.o"' for unit in units)
        # Game binary: all objects + ncurses dep libs + pthread, keeping the
        # upstream Makefile LIB order (pthread alongside curses).
        self.run(
            f'"{cc}" {objects} {nc_lib_flags} -lpthread -o "{out}/naga"',
            env="conanbuild",
        )
        # Logic static lib (curses-free units only) for API tests.
        self.run(
            f'"{ar}" rcs "{out}/libnaga.a" '
            f'"{out}/engine.o" "{out}/naga.o" "{out}/utils.o" "{out}/keypress.o"',
            env="conanbuild",
        )
        # ── 上游官方测试 ──
        # 上游无测试套件（审计见 test_package/MANIFEST.yml 的 upstream_test_audit）：
        # Makefile 没有 check/test 目标，且 TEST_SOURCES 引用的
        # src/tests/run_tests.c 在源码包中不存在。故无可执行的上游测试，
        # 如实输出 no_tests 标记。用 print(flush=True) 直达 stdout
        #（nethogs/airlift-slice 经验：Conan output 在 build 阶段可能不落
        # 预检日志；且 conan create 命中缓存时 build() 不执行，test_package
        # 侧会再次输出同一标记，保证每次预检都有证据）。
        print(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none",'
            '"command":"none (upstream ships no test suite)",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,'
            '"reason":"Makefile has no check/test target; '
            'src/tests/run_tests.c absent from the source tree"}',
            flush=True,
        )

    def package(self):
        copy(self, "naga", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libnaga.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        for header in ("utils.h", "naga.h", "engine.h", "keypress.h", "config.h"):
            copy(self, header, src=os.path.join(self.source_folder, "src"),
                 dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["naga"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
