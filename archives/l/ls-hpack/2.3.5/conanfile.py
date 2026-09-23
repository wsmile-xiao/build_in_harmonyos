#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ls-hpack 2.3.5 — HarmonyOS PC (OHOS) Conan recipe
#
# Upstream: https://github.com/litespeedtech/ls-hpack  (tag v2.3.5)
# License:  MIT
#
# Library-only package:
#   - Upstream bin/ CLI tools (encode-qif/decode-qif) are gated on
#     CMAKE_SYSTEM_NAME STREQUAL "Linux"; the OHOS toolchain sets
#     CMAKE_SYSTEM_NAME=OHOS, so no executables are produced and no
#     commands.json is required (library package).
#   - Upstream CMakeLists has no install() rules, so package()
#     collects the static library and public headers manually.
#
# Upstream official tests (test/CMakeLists.txt: 4 test_hpack matrix
# variants hash{0,1}xhttp{0,1} + test_int, driven by CTest) are built
# from a separate build tree and executed on the target in build(),
# following the repo convention (see leveldb 1.23).
#
# Upstream enables tests + ASan only when CMAKE_BUILD_TYPE != Release,
# so the test tree is configured as RelWithDebInfo-free "Debug" style
# build WITHOUT overriding upstream's ASan flag handling.

import contextlib
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get


class LsHpackConan(ConanFile):
    name = "ls-hpack"
    version = "2.3.5"
    description = "LiteSpeed HPACK (RFC 7541) header compression library, used by lsquic"
    license = "MIT"
    url = "https://github.com/litespeedtech/ls-hpack"
    homepage = "https://github.com/litespeedtech/ls-hpack"
    topics = ("hpack", "http2", "header-compression", "quic", "lsquic")
    package_type = "static-library"
    languages = "C"
    no_copy_source = True

    # L0p: all four settings required by the OHOS profile
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    def layout(self):
        cmake_layout(self)

    def source(self):
        # conan.tools.files.get() handles download + sha256 check
        # (L0o: no external curl/wget). URLs in conandata.yml.
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
            destination=self.source_folder,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream: CMAKE_MINIMUM_REQUIRED(VERSION 2.8) — new CMake
        # (>= 3.27) refuses compatibility with < 3.5 without this.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Bundle xxhash (upstream deps/xxhash) into the library —
        # lshpack.c references XXH32 symbols (XXH_HEADER_NAME).
        tc.cache_variables["LSHPACK_XXH"] = "ON"
        # OHOS clang15/musl: verified upstream code needs no patch.
        tc.generate()

    # ── OHOS SDK linker host runtime (lld / libxml2.so.16) ───────────
    #
    # Online CI (PR #7487) root cause: the OHOS clang driver spawns
    # `lld` for the final link step. lld is a dynamically linked HOST
    # ELF whose NEEDED list includes libxml2.so.16 (normally resolved
    # via its RUNPATH $ORIGIN/../lib → the SDK llvm/lib, which the CI
    # host loader does not expand), so on CI workers lld fails to even
    # start:
    #     Error loading shared library libxml2.so.16:
    #     needed by .../ohos/native/llvm/bin/lld
    #     xmlFreeDoc/xmlReadMemory/xmlDocGetRootElement: symbol not found
    #     The C compiler is not able to compile a simple test program.
    # This is a host-runtime problem of the SDK linker itself, not an
    # ls-hpack source error. Fix (repo-proven abseil/libcello pattern,
    # extended with a REAL compile+link probe): before cmake.configure()
    # verify the configured clang can compile AND link a minimal C
    # program; when the ambient environment fails, dynamically locate a
    # libxml2.so.16 host-runtime dir derived from the active toolchain
    # and scope the build under an LD_LIBRARY_PATH prepend. No CMake
    # bypass (no CMAKE_C_COMPILER_WORKS / FORCED / skipped compiler
    # check) — the real CMake compiler probe must succeed on its own.

    def _get_cc(self):
        # Compiler comes from the Conan conf first (the authoritative
        # source the OHOS profile sets to the SDK clang); if that path
        # does not exist, fall back to basename + PATH resolution only.
        # Never a hardcoded toolchain path.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            return shutil.which("clang") or "clang"
        if os.path.isfile(cc):
            return cc
        return shutil.which(os.path.basename(cc)) or cc

    def _resolve_lld(self, cc):
        # The linker the clang driver actually invokes at the final link
        # step, derived from the toolchain itself: ask the driver
        # (-print-prog-name=ld.lld) first, then the compiler's real bin
        # dir, then PATH.
        candidates = []
        try:
            proc = subprocess.run(
                [cc, "-print-prog-name=ld.lld"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=60, check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                candidates.append(proc.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
        bin_dir = os.path.dirname(os.path.realpath(cc))
        candidates += [os.path.join(bin_dir, "ld.lld"),
                       os.path.join(bin_dir, "lld")]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return os.path.realpath(candidate)
            resolved = shutil.which(candidate)
            if resolved:
                return os.path.realpath(resolved)
        return ""

    def _libxml2_host_libdirs(self, cc, lld):
        """Candidate host-runtime dirs that may hold the libxml2.so.16
        lld needs — derived ONLY from the active toolchain and the
        current environment, in priority order (no CI-worker paths):
          1. the configured compiler's real LLVM tree
          2. the resolved lld's real LLVM tree
          3. the compiler resource-dir tree (clang -print-resource-dir)
          4. tool-related dirs in the current PATH
          5. the current LD_LIBRARY_PATH
          6. a bounded upward walk from the toolchain binaries
        Returns only dirs that actually contain libxml2.so.16.
        """
        candidates = []
        for tool in (cc, lld):
            if tool and os.path.sep in tool:
                llvm_root = os.path.dirname(
                    os.path.dirname(os.path.realpath(tool))
                )
                candidates.append(os.path.join(llvm_root, "lib"))
        try:
            proc = subprocess.run(
                [cc, "-print-resource-dir"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=60, check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                # <prefix>/lib/clang/<ver> → <prefix>/lib
                candidates.append(
                    os.path.dirname(os.path.dirname(proc.stdout.strip()))
                )
        except (OSError, subprocess.SubprocessError):
            pass
        candidates += [
            p for p in (os.environ.get("PATH") or "").split(os.pathsep) if p
        ]
        candidates += [
            p for p in (os.environ.get("LD_LIBRARY_PATH") or "").split(os.pathsep)
            if p
        ]
        # Bounded upward walk from the toolchain binaries (covers SDK
        # layouts reached through symlinked wrapper dirs).
        for tool in (lld, cc):
            if not tool or os.path.sep not in tool:
                continue
            node = os.path.dirname(os.path.realpath(tool))
            for _ in range(4):
                node = os.path.dirname(node)
                if node in ("", os.path.sep):
                    break
                candidates.append(os.path.join(node, "lib"))
                candidates.append(os.path.join(node, "llvm", "lib"))
        found = []
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                found.append(candidate)
        return found

    def _cc_link_probe(self, cc, extra_ld_library_path=None):
        """REAL compile+link probe: build `int main(void) { return 0; }`
        with the configured OHOS clang. A bare `clang --version` is not
        enough — CMake's compiler check compiles testCCompiler.c AND
        links it, and the link step is exactly where lld dies when its
        libxml2.so.16 host dependency cannot be loaded.
        Returns (returncode, combined_output).
        """
        probe_dir = os.path.join(self.build_folder, "linker-probe")
        os.makedirs(probe_dir, exist_ok=True)
        source = os.path.join(probe_dir, "probe.c")
        binary = os.path.join(probe_dir, "probe")
        with open(source, "w") as fh:
            fh.write("int main(void) { return 0; }\n")
        env = os.environ.copy()
        if extra_ld_library_path:
            current = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                p for p in (extra_ld_library_path, current) if p
            )
        try:
            proc = subprocess.run(
                [cc, source, "-o", binary],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=env, timeout=180, check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return 127, str(error)
        finally:
            if os.path.exists(binary):
                try:
                    os.unlink(binary)
                except OSError:
                    pass
        return proc.returncode, (proc.stdout or "").strip()

    def _linker_runtime_environment(self):
        """Linker host-runtime gate (online CI PR #7487).

        Verifies the configured OHOS clang can compile+link a minimal C
        program BEFORE cmake.configure(). When the ambient environment
        fails (lld cannot load its libxml2.so.16 host dependency),
        dynamically discovers a usable host-runtime dir and returns a
        build-scoped Environment prepending it to LD_LIBRARY_PATH; the
        user environment is never modified globally. Raises
        ConanException with full diagnostics when the linker cannot be
        made to work — the error is never hidden and CMake is never
        bypassed.
        """
        if str(self.settings.os) != "OHOS":
            return None

        cc = self._get_cc()
        lld = self._resolve_lld(cc)
        self.output.info(f"OHOS linker probe: clang={cc}")
        self.output.info(f"OHOS linker probe: lld={lld or '(unresolved)'}")

        # 1) Ambient environment: can the configured clang compile+link?
        rc, log = self._cc_link_probe(cc)
        if rc == 0:
            self.output.info(
                "OHOS linker probe: minimal C compile+link OK "
                "(ambient environment)"
            )
            return None

        # 2) Link failed — find a libxml2.so.16 host-runtime dir derived
        #    from the active toolchain and retry the probe with it
        #    prepended to LD_LIBRARY_PATH.
        self.output.warning(
            f"OHOS linker probe: minimal C compile+link FAILED in the "
            f"ambient environment (rc={rc}); locating the SDK host "
            f"runtime (libxml2.so.16) ..."
        )
        if log:
            self.output.info(f"OHOS linker probe output:\n{log}")
        candidates = self._libxml2_host_libdirs(cc, lld)
        if not candidates:
            raise ConanException(
                "OHOS linker probe: the configured C compiler "
                f"'{cc}' cannot compile+link a minimal program and no "
                "directory containing libxml2.so.16 could be derived "
                f"from the active toolchain (lld={lld or 'unresolved'}). "
                f"Probe output:\n{log or '(empty)'}"
            )
        for libdir in candidates:
            rc, log = self._cc_link_probe(cc, extra_ld_library_path=libdir)
            if rc == 0:
                self.output.info(
                    "OHOS linker probe: minimal C compile+link OK with "
                    f"{libdir} prepended to LD_LIBRARY_PATH"
                )
                env = Environment()
                env.prepend_path("LD_LIBRARY_PATH", libdir)
                return env
        raise ConanException(
            "OHOS linker probe: the configured C compiler "
            f"'{cc}' cannot compile+link a minimal program even with "
            "the discovered libxml2.so.16 host runtime. Candidates "
            f"tried: {', '.join(candidates)}; lld={lld or 'unresolved'}. "
            f"Last probe output:\n{log or '(empty)'}"
        )

    def _quoted(self, value):
        return '"{}"'.format(str(value).replace('"', '\\"'))

    def _build_upstream_tests(self):
        """Configure/build upstream CTest suite in a separate tree and
        run it on the target (HarmonyOS PC, aarch64, musl).

        Upstream only enables the test subdirectory for non-Release
        build types, so this tree is configured as Debug. Upstream
        adds -fsanitize=address for non-Release builds itself.
        """
        test_build_folder = os.path.join(self.build_folder, "upstream-tests")
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        configure_args = [
            "cmake",
            "-S", self.source_folder,
            "-B", test_build_folder,
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
            "-DCMAKE_BUILD_TYPE=Debug",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DLSHPACK_XXH=ON",
        ]
        self.run(" ".join(self._quoted(arg) for arg in configure_args))
        self.run(
            "cmake --build {} --parallel".format(self._quoted(test_build_folder))
        )

        if not can_run(self):
            self.output.info(
                "cross-building: upstream tests compiled but cannot run"
            )
            return
        self.run(
            "ctest --output-on-failure --no-tests=error",
            cwd=test_build_folder,
        )

    def build(self):
        # Linker host-runtime gate (PR #7487): verify the configured OHOS
        # clang can compile+link a minimal C program BEFORE configure; if
        # the ambient env is broken (lld cannot load libxml2.so.16),
        # dynamically discover the SDK host runtime and scope it to the
        # build via LD_LIBRARY_PATH (repo-proven abseil pattern). No CMake
        # compiler-check bypass — the probe either passes for real or the
        # build stops with full diagnostics.
        link_env = self._linker_runtime_environment()
        cmake = CMake(self)
        with (link_env.vars(self).apply() if link_env else contextlib.nullcontext()):
            cmake.configure()
            cmake.build()
            # The upstream-tests tree runs its own cmake configure+build
            # (same clang + lld link step), so it shares the scoped env.
            self._build_upstream_tests()

    def package(self):
        # License
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Public headers (lshpack.h includes lsxpack_header.h)
        copy(self, "lshpack.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "lsxpack_header.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        # Static library (upstream has no install() rules); the main
        # build tree only — the upstream-tests/ tree is a separate
        # Debug build whose identically-named archive must not leak
        # into the package.
        for f in os.listdir(self.build_folder):
            if f.endswith(".a"):
                copy(self, f, src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["ls-hpack"]
        # xxhash is bundled into the library via LSHPACK_XXH (upstream
        # deps/xxhash), so no external xxhash dependency is exposed.
        self.cpp_info.set_property("cmake_file_name", "ls-hpack")
        self.cpp_info.set_property("cmake_target_name", "ls-hpack::ls-hpack")
        self.cpp_info.set_property("pkg_config_name", "ls-hpack")
