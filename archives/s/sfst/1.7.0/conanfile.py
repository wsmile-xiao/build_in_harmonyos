#!/usr/bin/env python3
"""Conan recipe for sfst 1.7.0 (Stuttgart Finite State Transducer system).

Upstream: https://github.com/santhoshtr/sfst
Build system: CMake (top-level + src/; python bindings guarded off in
source() via replace_in_file, no patch file).
Artifacts: libsfst shared library + fst-* CLI tools (fst-compiler,
fst-infl, fst-mor, fst-print, ...). The release tarball ships an empty
pybind11/ submodule directory, so source() rewrites the unconditional
add_subdirectory(pybind11/python) descent into an EXISTS-guarded block;
libsfst needs only a C++17 compiler
and readline headers, while the fst-* tools additionally need native
FLEX/BISON when available (upstream builds them only when both are
found).

Dependencies (per src/CMakeLists.txt):
  - readline/8.3 (host library, Findreadline.cmake)
  - ncurses/6.6 (static readline needs ncursesw symbols for the
    fst-compiler(-utf8) tools link; same version readline requires)
  - FLEX/BISON are OPTIONAL upstream: src/CMakeLists.txt only builds
    the fst-* tools when BOTH are found ("so executables won't be
    generated" otherwise); libsfst itself needs neither. This recipe
    therefore declares NO flex/bison/m4 tool_requires: forcing the
    conancenter m4/1.4.19 source build breaks the OHOS preflight
    (m4 configure hardcodes /data/service/hnp/bin/bash, inaccessible
    on the HMDFS build dir -> Error 127; see preflight 2026-09-27).
    CMake probes PATH for any native flex/bison and falls back to a
    supported library-only build when they are absent.

Upstream tests: none registered. src/ and python/ define no add_test()
targets (verified: grep add_test => 0 hits; ctest -N => Total Tests: 0).
python/tests/test.py exercises the pybind11 extension only, which is not
built here (submodule absent from the tarball), so it is out of scope for
the C++ conan package. build() therefore does NOT run any upstream check
(upstream_test_in_build: false); the no_tests evidence is produced by
test_package in the test phase every run (cache-hit safe).
"""

import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    copy,
    get,
    replace_in_file,
)


class SfstConan(ConanFile):
    name = "sfst"
    version = "1.7.0"
    description = "Stuttgart Finite State Transducer system: morphology compiler and runtime tools"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/santhoshtr/sfst"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("fst", "morphology", "nlp", "finite-state", "transducer")
    # Ships libsfst AND fst-* CLI tools; "library" matches the lttoolbox/
    # apertium precedent (lib + bins in one package).
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        # src/CMakeLists.txt: find_package(readline); fst-compiler(-utf8)
        # link plain `readline`. readline/8.3 is static by default, so its
        # symbols need ncursesw at link time; declare it explicitly (same
        # 6.6 version readline itself requires) so generate() can pass
        # absolute ncurses libs to the tools build.
        self.requires("readline/8.3")
        self.requires("ncurses/6.6")

    def build_requirements(self):
        # No flex/bison/m4 tool_requires (deliberate).
        # Upstream src/CMakeLists.txt treats FLEX+BISON as optional:
        # libsfst always builds; fst-* tools only when BOTH are found.
        # Forcing conancenter flex/2.6.4 + bison/3.8.2 + m4/1.4.19 makes
        # the OHOS preflight build m4/1.4.19 from source, whose configure
        # hardcodes /data/service/hnp/bin/bash -- inaccessible on the
        # HMDFS conan build dir (Error 127, preflight 2026-09-27) -- so
        # the whole create fails before sfst itself compiles. Rely on
        # native flex/bison via PATH when present, else take the
        # upstream-supported library-only build.
        pass

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sfst is prepared for Linux/OHOS targets only, not {}".format(
                    self.settings.os
                )
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._guard_python_bindings()
        self._fix_library_only_install()
        self._fix_readline_link()

    def _guard_python_bindings(self):
        """Guard the pybind11/python descent without a patch file.

        The 1.7.0 release tarball archives an empty pybind11/ directory
        (git submodule content is not part of GitHub auto-generated
        tarballs), so an unconditional add_subdirectory(pybind11) fails
        with "no CMakeLists.txt found". Rewritten here with
        replace_in_file instead of a unified-diff patch: the previous
        patch route kept failing in apply_conandata_patches (patch_ng
        "extra lines for hunk" / "Failed to parse patch") because the
        hunk header start/count did not match the 22-line upstream
        top-level CMakeLists.txt, and every header recount kept the
        fragile parsing gate. A direct string replacement has no hunk
        headers to miscount and fails loudly if upstream changes shape.
        """
        top = os.path.join(self.source_folder, "CMakeLists.txt")
        old_block = (
            "# add python bindings\n"
            "add_subdirectory(pybind11)\n"
            "add_subdirectory(python)\n"
        )
        new_block = (
            "# add python bindings when the pybind11 submodule is present.\n"
            "# The release tarball ships an empty pybind11/ directory, so guard\n"
            "# the descent to keep the C++ library/tools build self-contained.\n"
            'if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/pybind11/CMakeLists.txt")\n'
            "  add_subdirectory(pybind11)\n"
            "  add_subdirectory(python)\n"
            "endif()\n"
        )
        with open(top, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        if 'EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/pybind11/CMakeLists.txt"' in content:
            return
        if old_block not in content:
            raise ConanInvalidConfiguration(
                "sfst source guard failed: expected python-bindings block "
                "not found in top-level CMakeLists.txt"
            )
        replace_in_file(self, top, old_block, new_block)
        with open(top, "r", encoding="utf-8", newline="") as f:
            guarded = f.read()
        if 'EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/pybind11/CMakeLists.txt"' not in guarded:
            raise ConanInvalidConfiguration(
                "sfst source guard failed: replacement did not take effect"
            )

    def _fix_library_only_install(self):
        """Make the header install list conditional on BISON.

        Upstream src/CMakeLists.txt unconditionally lists the
        BISON-generated ${CMAKE_CURRENT_BINARY_DIR}/fst-compiler.h in
        HEADERS, but that file only exists when BISON_FOUND (BISON_TARGET
        step). In the upstream-supported library-only build (native
        FLEX/BISON absent on this host) `cmake --install` therefore fails
        with "file INSTALL cannot find .../src/fst-compiler.h" even though
        libsfst itself built fine (preflight 2026-09-27 round 3). Append
        the generated header only when BISON generated it; no platform
        macro, no behavior change when tools are enabled.
        """
        cmake_lists = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        with open(cmake_lists, "r", encoding="utf-8", newline="") as f:
            lines = f.read().splitlines(keepends=True)
        if any(
            "list(APPEND HEADERS" in line and "fst-compiler.h" in line
            for line in lines
        ):
            return
        out = []
        replaced = False
        i = 0
        while i < len(lines):
            line = lines[i]
            # The unconditional HEADERS entry carries both the last static
            # header (utf8.h) and the generated fst-compiler.h on one line;
            # split it into a static entry plus a BISON-guarded append.
            # Whitespace-tolerant: match by tokens, not exact columns.
            if (
                not replaced
                and "utf8.h" in line
                and "fst-compiler.h" in line
                and "HEADERS" not in line
                and "list(" not in line
            ):
                indent = line[: len(line) - len(line.lstrip())]
                out.append("{}alphabet.h basic.h fst.h interface.h mem.h utf8.h\n".format(indent))
                out.append(")\n")
                out.append("if(BISON_FOUND)\n")
                out.append(
                    "    list(APPEND HEADERS"
                    " ${CMAKE_CURRENT_BINARY_DIR}/fst-compiler.h)\n"
                )
                out.append("endif()\n")
                replaced = True
                i += 1
                # Drop the original combined line plus its closing paren
                # (the next line is the lone ")" of set(HEADERS ...)).
                if i < len(lines) and lines[i].strip() == ")":
                    i += 1
                continue
            out.append(line)
            i += 1
        if not replaced:
            raise ConanInvalidConfiguration(
                "sfst library-only install fix failed: HEADERS line with "
                "utf8.h + fst-compiler.h not found in src/CMakeLists.txt"
            )
        with open(cmake_lists, "w", encoding="utf-8", newline="") as f:
            f.writelines(out)
        with open(cmake_lists, "r", encoding="utf-8", newline="") as f:
            fixed = f.read()
        if "list(APPEND HEADERS ${CMAKE_CURRENT_BINARY_DIR}/fst-compiler.h)" not in fixed:
            raise ConanInvalidConfiguration(
                "sfst library-only install fix failed: replacement did not take effect"
            )

    def _fix_readline_link(self):
        """Link fst-compiler(-utf8) against absolute Conan libraries.

        CI #63222: with native FLEX+BISON present the tools build is
        enabled, but upstream links the literal `readline` library name
        (target_link_libraries(fst-compiler readline)) without ever using
        the READLINE::READLINE imported target its own Findreadline.cmake
        creates. No -L<conan-readline>/lib reaches the link line, so lld
        fails with `unable to find library -lreadline` even though
        readline/8.3 is in the Conan graph ("Readline not found, so
        executables won't be generated." is printed, yet the build still
        enters the BISON_FOUND AND FLEX_FOUND block). Prefer the absolute
        imported target when found, fall back to READLINE_LIBRARY
        (pinned by generate()), and only then to the plain name to keep
        system-readline hosts working. Static readline additionally needs
        ncursesw symbols, passed via SFST_NCURSES_LIBS (absolute files
        pinned by generate()); guarded by DEFINED so library-only and
        system builds are unchanged.
        """
        cmake_lists = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        with open(cmake_lists, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        if "SFST_NCURSES_LIBS" in content:
            return
        old_compiler = (
            "    target_link_libraries(fst-compiler libsfst)\n"
            "    target_link_libraries(fst-compiler readline)\n"
        )
        new_compiler = (
            "    target_link_libraries(fst-compiler libsfst)\n"
            "    if(TARGET READLINE::READLINE)\n"
            "      target_link_libraries(fst-compiler READLINE::READLINE)\n"
            "    elseif(DEFINED READLINE_LIBRARY)\n"
            "      target_link_libraries(fst-compiler ${READLINE_LIBRARY})\n"
            "    else()\n"
            "      target_link_libraries(fst-compiler readline)\n"
            "    endif()\n"
            "    if(DEFINED SFST_NCURSES_LIBS)\n"
            "      target_link_libraries(fst-compiler ${SFST_NCURSES_LIBS})\n"
            "    endif()\n"
        )
        old_utf8 = (
            "    target_link_libraries(fst-compiler-utf8 libsfst)\n"
            "    target_link_libraries(fst-compiler-utf8 readline)\n"
        )
        new_utf8 = (
            "    target_link_libraries(fst-compiler-utf8 libsfst)\n"
            "    if(TARGET READLINE::READLINE)\n"
            "      target_link_libraries(fst-compiler-utf8 READLINE::READLINE)\n"
            "    elseif(DEFINED READLINE_LIBRARY)\n"
            "      target_link_libraries(fst-compiler-utf8 ${READLINE_LIBRARY})\n"
            "    else()\n"
            "      target_link_libraries(fst-compiler-utf8 readline)\n"
            "    endif()\n"
            "    if(DEFINED SFST_NCURSES_LIBS)\n"
            "      target_link_libraries(fst-compiler-utf8 ${SFST_NCURSES_LIBS})\n"
            "    endif()\n"
        )
        if old_compiler not in content or old_utf8 not in content:
            raise ConanInvalidConfiguration(
                "sfst readline link fix failed: expected "
                "target_link_libraries(fst-compiler[-utf8] readline) "
                "not found in src/CMakeLists.txt"
            )
        replace_in_file(self, cmake_lists, old_compiler, new_compiler)
        replace_in_file(self, cmake_lists, old_utf8, new_utf8)
        with open(cmake_lists, "r", encoding="utf-8", newline="") as f:
            fixed = f.read()
        if "SFST_NCURSES_LIBS" not in fixed:
            raise ConanInvalidConfiguration(
                "sfst readline link fix failed: replacement did not take effect"
            )

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # CMake has no HarmonyOS platform module (E092 precedent:
            # julius/oystr/jwt-cpp/adamstark-audiofile): the OHOS
            # clang/sysroot is Linux-compatible for this ordinary C++
            # target, so present as Linux/aarch64. Without this,
            # CMakeToolchain emits CMAKE_SYSTEM_NAME=HarmonyOS and
            # configure fails at project() with "System is unknown to
            # cmake" plus CMAKE_C/CXX_COMPILER sanity errors
            # (preflight 2026-09-27). STATIC_LIBRARY skips only the
            # try_compile link step for the compiler check.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.shared else "OFF"
        )
        # Help the custom Findreadline.cmake locate the Conan package
        # even if CMAKE_PREFIX_PATH handling differs on the worker.
        # CI #63222: HINTS ${READLINE_ROOT} alone is not enough -- the
        # module looks for readline/readline.h directly under the hint
        # (real file is include/readline/readline.h) and for `readline`
        # under lib/ only when CMAKE_INSTALL_LIBDIR suffixes apply, so
        # detection prints "Readline not found" on the worker. Pin the
        # exact include dir + library file as CMake variables; find_path
        # /find_library honour pre-set values and the link fix in
        # _fix_readline_link() reuses them as absolute fallbacks.
        try:
            readline_pkg = self.dependencies["readline"]
            tc.variables["READLINE_ROOT"] = readline_pkg.package_folder.replace(
                "\\", "/"
            )
            r_inc = os.path.join(readline_pkg.package_folder, "include")
            r_libdir = os.path.join(readline_pkg.package_folder, "lib")
            tc.variables["READLINE_INCLUDE_DIR"] = r_inc.replace("\\", "/")
            r_lib = None
            for _name in (
                "libreadline.a",
                "readline.lib",
                "libreadline.so",
                "libreadline.dylib",
            ):
                _cand = os.path.join(r_libdir, _name)
                if os.path.isfile(_cand):
                    r_lib = _cand
                    break
            if r_lib is None:
                # Shared layout (libreadline.so.X) or versioned dylib:
                # take the first readline library file present.
                try:
                    for _entry in sorted(os.listdir(r_libdir)):
                        if _entry.startswith("libreadline."):
                            _cand = os.path.join(r_libdir, _entry)
                            if os.path.isfile(_cand):
                                r_lib = _cand
                                break
                except Exception:
                    pass
            if r_lib is not None:
                tc.variables["READLINE_LIBRARY"] = r_lib.replace("\\", "/")
                self.output.info("sfst readline lib=%s" % r_lib)
            else:
                self.output.warning(
                    "sfst readline library file not found in %s" % r_libdir
                )
        except Exception as exc:
            self.output.warning("sfst readline pin failed: %s" % exc)
        # Static readline needs ncursesw symbols at fst-compiler link
        # time; pass absolute archives so the tools link has no -L/-l
        # search dependency. Missing files are skipped, never fatal.
        try:
            ncurses_pkg = self.dependencies["ncurses"]
            n_libdir = os.path.join(ncurses_pkg.package_folder, "lib")
            _found = []
            for _name in (
                "libncursesw.a",
                "libformw.a",
                "libmenuw.a",
                "libpanelw.a",
            ):
                _cand = os.path.join(n_libdir, _name)
                if os.path.isfile(_cand):
                    _found.append(_cand.replace("\\", "/"))
            if _found:
                tc.variables["SFST_NCURSES_LIBS"] = ";".join(_found)
                self.output.info("sfst ncurses libs=%s" % ";".join(_found))
        except Exception as exc:
            self.output.warning("sfst ncurses pin failed: %s" % exc)
        # Preflight 2026-09-27 round 2: SYSTEM_NAME=Linux alone did not fix
        # "compiler identification is unknown" for /data/service/hnp/bin/
        # clang(++). Same class as leatherman R18 / zydis / bzrtp: the
        # profile absolute compiler path is invisible inside the preflight
        # sandbox, so project() cannot execute it. Resolve sandbox-first
        # (existing profile path wins, else PATH lookup) and rewrite the
        # baked value in conan_toolchain.cmake (cache_variables alone do
        # not move it, zydis 2026-09-18 evidence).
        _c = self._resolve_cmake_compiler("c", ("clang", "cc"), "CC")
        _cxx = self._resolve_cmake_compiler("cpp", ("clang++", "c++"), "CXX")
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("sfst cmake compilers c=%s cxx=%s" % (_c, _cxx))
        tc.generate()
        self._fix_generated_toolchain(_c, _cxx)

    def _resolve_cmake_compiler(self, key, fallback_names, env_name):
        """Sandbox-first compiler pick for the CMake configure step."""
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            executables = {}
        if not isinstance(executables, dict):
            executables = {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        for name in fallback_names:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        env_hit = os.environ.get(env_name, "")
        if env_hit and os.path.isfile(env_hit):
            return env_hit
        return configured or None

    def _fix_generated_toolchain(self, c, cxx):
        """Rewrite stale absolute compiler paths baked into the generated
        conan_toolchain.cmake. Only rewrites when the configured path is
        missing and the resolved one exists, so CI workers with a valid
        toolchain are untouched."""
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            executables = {}
        if not isinstance(executables, dict):
            executables = {}
        pairs = []
        for key, resolved in (("c", c), ("cpp", cxx)):
            old = executables.get(key)
            if (
                old
                and resolved
                and old != resolved
                and not os.path.exists(old)
                and os.path.exists(resolved)
            ):
                pairs.append((old, resolved))
        if not pairs:
            return
        path = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        try:
            if not os.path.isfile(path):
                self.output.warning("cmake toolchain file not found: %s" % path)
                return
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            orig = text
            for old_p, new_p in pairs:
                text = text.replace(old_p, new_p)
            if text != orig:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.output.info("fixed stale compiler path in %s" % path)
            for line in text.splitlines():
                s = line.strip()
                if "CMAKE_C_COMPILER" in s or "CMAKE_CXX_COMPILER" in s:
                    self.output.info("toolchain %s" % s)
        except Exception as exc:
            self.output.warning("toolchain compiler fix failed: %s" % exc)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream has no test suite (audited: no add_test() in src/ or
        # python/, ctest -N reports Total Tests: 0 -- see
        # test_package/MANIFEST.yml upstream_test_audit). build() therefore
        # does NOT invoke any upstream check (upstream_test_in_build: false);
        # the HMBS_UPSTREAM_TEST_RESULT status=no_tests evidence is produced
        # by test_package/conanfile.py in the test phase every run
        # (cache-hit safe). A non-empty upstream_check_command /
        # in_build:true in MANIFEST makes the hmbs lister treat the library
        # as upstream-has-tests and reject no_tests/0.

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        cmake = CMake(self)
        cmake.install()
        # Upstream install() only declares RUNTIME DESTINATION for libsfst,
        # which does not cover the shared library on ELF platforms; ensure
        # the built library, headers, and tools land in the package.
        self._copy_fallback_artifacts()

    def _copy_fallback_artifacts(self):
        build_src = Path(self.build_folder)
        # Candidates: cmake_layout puts the src/ build under build/src
        # (or build/<config>/src for multi-config generators).
        search_roots = [build_src]
        for child in build_src.iterdir() if build_src.is_dir() else []:
            if child.is_dir():
                search_roots.append(child)
                nested = child / "src"
                if nested.is_dir():
                    search_roots.append(nested)
        src_dir = build_src / "src"
        if src_dir.is_dir():
            search_roots.append(src_dir)

        lib_patterns = ("libsfst.so*", "libsfst.a", "libsfst.static.a", "sfst.lib")
        for root in search_roots:
            for pattern in lib_patterns:
                copy(
                    self,
                    pattern,
                    src=str(root),
                    dst=os.path.join(self.package_folder, "lib"),
                    keep_path=False,
                )

        # Public headers live in the source tree (plus generated
        # fst-compiler.h / version.h in the build tree).
        for header_root in (
            Path(self.source_folder) / "src",
            build_src / "src",
        ):
            if header_root.is_dir():
                copy(
                    self,
                    "*.h",
                    src=str(header_root),
                    dst=os.path.join(self.package_folder, "include", "sfst"),
                    keep_path=False,
                )

        # CLI tools (fst-compiler, fst-infl, ...) when FLEX/BISON/READLINE
        # were all found at configure time.
        for root in search_roots:
            copy(
                self,
                "fst-*",
                src=str(root),
                dst=os.path.join(self.package_folder, "bin"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = ["sfst"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "sfst")]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "sfst")
        self.cpp_info.set_property("cmake_target_name", "sfst::sfst")
