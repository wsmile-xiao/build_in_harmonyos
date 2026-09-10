#!/usr/bin/env python3
"""Conan recipe for clunk 1.3.261 (real-time 3D binaural sound library).

Upstream 1.3.261 builds with CMake + SDL 1.2. The SDL 1.2 API is provided by
sdl12-compat/1.2.68 (dxx-rebirth precedent). Upstream ships no CTest/make
check suite; the verifiable self-checks are the `f` (MDCT reference vs FFT
comparison) and `t` (FFT roundtrip) modes of the upstream test.cpp program,
executed headlessly in build(). The interactive audio demo path needs physical
audio hardware and carries no assertions, so it is documented as excluded.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ClunkConan(ConanFile):
    name = "clunk"
    version = "1.3.261"
    description = "Real-time 3D (binaural) sound generation library with SDL backend"
    license = "LGPL-2.1-only"
    homepage = "https://sourceforge.net/projects/clunk/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "3d-sound", "sdl", "binaural")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream 1.3.261 targets the SDL 1.2 API; the compatibility package
        # supplies that API over the published SDL2 runtime.
        self.requires("sdl12-compat/1.2.68")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: settings.os check must accept both Linux and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "clunk/1.3.261 only supports Linux/OHOS, got %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_writable_tmp()
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # NOTE: do NOT force CMAKE_SYSTEM_NAME=Linux. The OHOS-adapted Conan
        # maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS by design; forcing
        # Linux was tried and reproduced the identical failure, so the
        # platform name is not the discriminator here.
        # Unknown-system try_compile executables may fail to link on this
        # platform even when the compiler itself is healthy (no Platform/
        # HarmonyOS module in CMake 4.x); building try_compile probes as
        # static libraries skips the executable link step only, while the
        # real library/test link still happens in cmake.build().
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        # Feed the legacy FindSDL module with the declared Conan SDL 1.2
        # package instead of host filesystem discovery.
        sdl_root = self.dependencies["sdl12-compat"].package_folder
        tc.cache_variables["SDL_INCLUDE_DIR"] = os.path.join(
            sdl_root, "include", "SDL").replace("\\", "/")
        tc.cache_variables["SDL_LIBRARY"] = os.path.join(
            sdl_root, "lib", "libSDL-1.2.so").replace("\\", "/")
        # Build the upstream test program so build() can run its headless
        # DSP self-check modes. WITH_SSE stays OFF (x86-only routines).
        tc.cache_variables["BUILD_TEST"] = "ON"
        tc.cache_variables["WITH_SSE"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # The profile-pinned compiler path does not exist on the preflight
        # machine (ENOENT). Bake the repaired absolute driver paths directly
        # into the generated toolchain: a command-line -D alone did NOT win
        # over the toolchain's cached set() (precheck passed yet configure
        # still tried /data/service/hnp/bin/clang), so the toolchain file
        # itself must carry the working paths.
        cc0, cxx0 = self._resolve_compilers()
        tc.cache_variables["CMAKE_C_COMPILER"] = cc0
        tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx0
        tc.generate()
        self._scrub_toolchain(cc0, cxx0)

    def _ensure_writable_tmp(self):
        # E002 + HMBS [readonly_tmp]: /tmp is erofs read-only on HarmonyOS
        # PC, and the hnp clang compiler check needs a writable temp root.
        # Reuse the HMBS-injected TMPDIR/TMP/TEMP when present; otherwise
        # fall back to a writable directory under the build folder. This only
        # redirects the temporary-file root; no tests are skipped or removed.
        candidates = [os.environ.get(var) for var in ("TMPDIR", "TMP", "TEMP")]
        tmpdir = next((c for c in candidates if c), None)
        if not tmpdir:
            tmpdir = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            fallback = os.path.join(self.build_folder, "tmp")
            os.makedirs(fallback, exist_ok=True)
            tmpdir = fallback
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        return tmpdir

    def _resolve_compilers(self):
        return self._resolve_compiler("c"), self._resolve_compiler("cxx")

    def _resolve_compiler(self, lang):
        # The preflight profile pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang(++), but that path does NOT exist on
        # the preflight machine (exec gives ENOENT), which is why every
        # cmake.configure died in project() compiler identification.
        # Resolution order: usable conf path first, then CC/CXX env, then a
        # broad PATH search over common driver names (HMBS prepends the tool
        # dirs to buildenv PATH). Each candidate must exist AND answer
        # `--version` with rc=0; a bare which() hit is not enough proof.
        # Compile flags still come from the Conan toolchain file; only the
        # driver path is repaired here.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        if lang == "c":
            candidates = [executables.get("c"), executables.get("cc"),
                          os.environ.get("CC")]
            fallbacks = ["clang", "cc", "gcc", "ohos-clang"]
        else:
            candidates = [executables.get("cpp"), executables.get("cxx"),
                          executables.get("c++"),
                          os.environ.get("CXX"), os.environ.get("CC")]
            fallbacks = ["clang++", "clang", "c++", "g++", "ohos-clang++"]
        candidates = [c for c in candidates if c] + fallbacks
        seen = set()
        tried = []
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            resolved = shutil.which(candidate)
            if not resolved and os.path.isfile(candidate) and os.access(
                    candidate, os.X_OK):
                resolved = os.path.abspath(candidate)
            if not resolved:
                tried.append("%s(missing)" % candidate)
                continue
            tried.append("%s->%s" % (candidate, resolved))
            try:
                proc = subprocess.run(
                    [resolved, "--version"], capture_output=True,
                    text=True, timeout=60,
                    env={**os.environ,
                         "TMPDIR": os.environ.get("TMPDIR", "/tmp")})
            except (OSError, subprocess.SubprocessError) as error:
                tried[-1] += "[launch-fail:%s]" % error
                continue
            if proc.returncode != 0:
                tried[-1] += "[rc=%d]" % proc.returncode
                continue
            if resolved != candidate:
                self.output.info(
                    "clunk resolved %s compiler %s -> %s"
                    % (lang, candidate, resolved))
            return resolved
        raise ConanException(
            "clunk found no usable %s compiler (tried %s; "
            "tools.build:compiler_executables=%s; PATH=%s)"
            % (lang, tried, executables,
               os.environ.get("PATH", "")[:800]))

    def _scrub_toolchain(self, cc, cxx):
        # Post-process the generated conan_toolchain.cmake: replace any
        # stale reference to the nonexistent profile compiler with the
        # verified absolute paths. This is the load-bearing repair — the
        # previous cycle's command-line -D override lost to the toolchain's
        # cached set(), so the file itself must be corrected.
        broken = []
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        for value in executables.values():
            if value and not (shutil.which(value) or (
                    os.path.isfile(value) and os.access(value, os.X_OK))):
                broken.append(value)
        broken.append("/data/service/hnp/bin/clang++")
        broken.append("/data/service/hnp/bin/clang")
        count = 0
        for root, _dirs, files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" not in files:
                continue
            path = os.path.join(root, "conan_toolchain.cmake")
            try:
                with open(path, "r", encoding="utf-8",
                           errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            original = content
            for bad in dict.fromkeys(broken):
                if bad and bad in content:
                    replacement = cxx if bad.endswith("++") or "cxx" in bad or "cpp" in bad else cc
                    # clang++ path contains the clang substring; replace the
                    # longer c++ name first (list order above guarantees it).
                    content = content.replace(bad, replacement)
            if content != original:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)
                count += 1
                self.output.info("clunk scrubbed stale compiler path in %s" % path)
        if count == 0:
            self.output.info("clunk toolchain scrub: no stale compiler reference found")

    def _precheck_compiler(self):
        # Direct probe: compile+link a trivial C and C++ program with the
        # resolved compilers BEFORE cmake.configure(), and return the exact
        # paths so build() feeds the same drivers to CMake via -D (command
        # line beats the toolchain default). One-line evidence either way.
        tmpdir = self._ensure_writable_tmp()
        cc = self._resolve_compiler("c")
        cxx = self._resolve_compiler("cxx")
        probes = (
            ("c", cc, "probe.c", "int main(void){return 0;}"),
            ("cxx", cxx, "probe.cpp", "int main(){return 0;}"),
        )
        env = dict(os.environ)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env[var] = tmpdir
        for lang, compiler, filename, source in probes:
            src = os.path.join(tmpdir, "clunk_precheck_%s" % filename)
            out = os.path.join(tmpdir, "clunk_precheck_%s" % lang)
            with open(src, "w", encoding="utf-8") as handle:
                handle.write(source + "\n")
            try:
                proc = subprocess.run(
                    [compiler, src, "-o", out], capture_output=True,
                    text=True, timeout=120, env=env)
            except (OSError, subprocess.SubprocessError) as error:
                raise ConanException(
                    "clunk compiler precheck %s FAILED to launch %s: %s"
                    % (lang, compiler, error))
            if proc.returncode != 0:
                detail = (proc.stderr.strip() or proc.stdout.strip()
                          ).replace("\n", " ")[:600]
                raise ConanException(
                    "clunk compiler precheck %s FAILED (%s rc=%d): %s"
                    % (lang, compiler, proc.returncode, detail))
            self.output.info(
                "clunk compiler precheck %s OK (%s)" % (lang, compiler))
        return cc, cxx

    def _fix_pow10f_sources(self):
        # Belt-and-braces for the GNU pow10f() extension (absent on
        # HarmonyOS/musl, true-machine error: "use of undeclared identifier
        # 'pow10f'" in clunk/hrtf.cpp:65). The 0002 patch already rewrites the
        # sole call site to C99 powf(10.0f, x); this in-recipe pass covers the
        # case where the patch was not exported/applied (previous preflight
        # exported only 0001). Replacing the call site -- instead of defining
        # a pow10f macro guarded by `#ifndef pow10f` (function symbols are not
        # macros, so that guard cannot detect a missing function) -- works on
        # every libc. Idempotent: a patched tree is left untouched.
        for rel in ("clunk/hrtf.cpp", "clunk/source.cpp"):
            path = os.path.join(self.source_folder, rel)
            try:
                with open(path, "r", encoding="utf-8",
                           errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            original = content
            if "pow10f(" in content:
                content = content.replace("pow10f(", "powf(10.0f, ")
                self.output.info("clunk %s: rewrote pow10f() call site to powf" % rel)
            if rel == "clunk/hrtf.cpp" and "#include <math.h>" not in content:
                content = content.replace(
                    "#include <stddef.h>",
                    "#include <stddef.h>\n#include <math.h>", 1)
                self.output.info("clunk %s: added missing <math.h>" % rel)
            if content != original:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _fix_fft_ifft_sign(self):
        # True-machine evidence (test_package): fft_roundtrip N=32
        # energy=45.564 worst_residual=1.000000 FAIL. Root cause in
        # clunk/fft_context.h danielson_lanczos<8>: the k=2 twiddle is
        # hardcoded to (0,-1) for both directions, while k=1/k=3 correctly
        # conjugate with SIGN. Forward (SIGN=1) is unaffected; inverse
        # (SIGN=-1) must use (0,+1). Any N>=8 recurses through this
        # specialization, so fft()+ifft() never roundtrips.
        # Fixed here in-recipe (not via patch file): same rationale as the
        # CMakeLists fix — the preflight BSD patch tool matches hunks
        # strictly and prior patch attempts failed, while plain string
        # replace is immune to line offsets. Idempotent.
        path = os.path.join(self.source_folder, "clunk", "fft_context.h")
        try:
            with open(path, "r", encoding="utf-8",
                       errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        original = content
        old = "rotate(data, 2, std::complex<T>(0, -1));"
        new = "rotate(data, 2, std::complex<T>(0, -SIGN));"
        if old in content:
            content = content.replace(old, new)
            self.output.info(
                "clunk fft_context.h: fixed 8-point ifft twiddle to (0,-SIGN)")
        if content != original:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _fix_cmake_config_path(self):
        # Upstream CMakeLists bugs (true-machine evidence):
        # 1) configure_file emits to ${CMAKE_CURRENT_BINARY_DIR}/clunk/config.h
        #    but PUBLIC_HEADERS lists ${CMAKE_CURRENT_BINARY_DIR}/config.h, so
        #    cmake.install() fails with "file INSTALL cannot find
        #    .../build/Release/config.h".
        # 2) PUBLIC_HEADERS omits several shipped headers consumed via the
        #    <clunk/...> prefix (notably clunk/types.h, required by
        #    clunk/buffer.h:23 -> test_package fatal
        #    "'clunk/types.h' file not found"), and
        #    install(FILES ...) flattens clunk/backend/sdl/backend.h to
        #    include/clunk/backend.h instead of include/clunk/backend/sdl/.
        # Fixed here in-recipe (not via patch file): two patch-file attempts
        # failed on the preflight BSD patch tool with strict hunk line
        # matching ("hunk doesn't match at line 57"), so plain string
        # replaces — immune to hunk offsets — are the robust route.
        # Idempotent.
        path = os.path.join(self.source_folder, "CMakeLists.txt")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        original = content
        old = "${CMAKE_CURRENT_BINARY_DIR}/config.h"
        new = "${CMAKE_CURRENT_BINARY_DIR}/clunk/config.h"
        if old in content:
            content = content.replace(old, new)
        old_install = "install(FILES ${PUBLIC_HEADERS} DESTINATION include/clunk)"
        if old_install in content:
            content = content.replace(
                old_install,
                "install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/clunk/ "
                "DESTINATION include/clunk FILES_MATCHING PATTERN \"*.h\")\n"
                "install(FILES ${CMAKE_CURRENT_BINARY_DIR}/clunk/config.h "
                "DESTINATION include/clunk)")
            self.output.info(
                "clunk CMakeLists.txt: switched header install to "
                "DIRECTORY (preserves clunk/ prefix + backend subdirs)")
        if content != original:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
            if old in original:
                self.output.info(
                    "clunk CMakeLists.txt: fixed config.h install path")

    def _find_upstream_test_binary(self):
        for root, _dirs, files in os.walk(self.build_folder):
            if "clunk-test" in files:
                return root
        raise ConanException(
            "clunk-test was not produced; BUILD_TEST=ON build failed to emit it")

    def build(self):
        self._ensure_writable_tmp()
        apply_conandata_patches(self)
        self._fix_pow10f_sources()
        self._fix_fft_ifft_sign()
        self._fix_cmake_config_path()
        cc, cxx = self._precheck_compiler()
        # Belt-and-braces: the toolchain file itself was already corrected
        # in generate(); re-scrub here in case generate() was served from
        # cache, then keep the command-line -D as a second layer.
        self._scrub_toolchain(cc, cxx)
        for var, val in (("CC", cc), ("CXX", cxx)):
            os.environ[var] = val
        cmake = CMake(self)
        try:
            # E103 precedent (dynamips/gflags/gl4es): pass the compat floor
            # on the cmake command line, not only via the toolchain file.
            cmake.configure(variables={
                "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
                "CMAKE_C_COMPILER": cc,
                "CMAKE_CXX_COMPILER": cxx,
            })
        except Exception as error:
            # The preflight summary truncates CMake's multi-line diagnostics,
            # so embed the CMakeError.log tail into the raised exception: the
            # ERROR line survives summarization and carries the real evidence.
            tail = ""
            for root, _dirs, files in os.walk(self.build_folder):
                if "CMakeError.log" in files:
                    candidate = os.path.join(root, "CMakeError.log")
                    try:
                        with open(candidate, "r", encoding="utf-8",
                                   errors="replace") as handle:
                            tail = handle.read()[-1200:].replace("\n", " ")
                    except OSError:
                        pass
                    break
            raise ConanException(
                "clunk cmake configure failed: %s | CMakeError.log tail: %s"
                % (error, tail or "unavailable")) from error
        cmake.build()
        self._run_upstream_self_checks()

    def _run_upstream_self_checks(self):
        # Upstream 1.3.261 registers no CTest cases and has no `make check`
        # target. The two deterministic, headless, assertion-bearing modes of
        # the upstream test.cpp program are the project's test suite:
        #   f = MDCT reference vs FFT implementation comparison (prints both)
        #   t = FFT forward/inverse roundtrip (prints spectrum + residuals)
        # Both exit non-zero on failure; output is verified non-empty with the
        # expected sections (anti silent-skip guard).
        if not can_run(self):
            raise ConanException(
                "clunk upstream self-checks require a runnable host; "
                "refusing to fake a pass")
        bindir = self._find_upstream_test_binary()
        sdl_lib = os.path.join(
            self.dependencies["sdl12-compat"].package_folder, "lib")
        loader_path = bindir + os.pathsep + sdl_lib
        checks = (
            ("f", ("reference:", "fft based:")),
            ("t", (",",)),
        )
        # HMBS [readonly_tmp]: /tmp is read-only on HarmonyOS PC and
        # /bin/sh hardcodes /tmp for its own temp files (shp*.tmp), ignoring
        # TMPDIR. The previous implementation ran
        # `LD_LIBRARY_PATH=... ./clunk-test X > log 2>&1` via self.run(),
        # which forces a shell and its /tmp temp file. Run the binary
        # directly via subprocess (no shell, no redirection metachars) and
        # write the log file from Python, so no shell temp file is needed.
        # Only the temp-file root is redirected; no tests are skipped.
        tmpdir = self._ensure_writable_tmp()
        actual_commands = []
        for mode, sections in checks:
            log_name = "upstream_%s.log" % mode
            display_cmd = ("LD_LIBRARY_PATH=%s ./clunk-test %s"
                           % (loader_path, mode))
            actual_commands.append(display_cmd)
            binary = os.path.join(bindir, "clunk-test")
            log_path = os.path.join(bindir, log_name)
            run_env = dict(os.environ)
            run_env["LD_LIBRARY_PATH"] = loader_path + os.pathsep + run_env.get(
                "LD_LIBRARY_PATH", "")
            for var in ("TMPDIR", "TMP", "TEMP"):
                run_env[var] = tmpdir
            try:
                proc = subprocess.run(
                    [binary, mode], cwd=bindir, env=run_env,
                    capture_output=True, text=True, timeout=120)
            except (OSError, subprocess.SubprocessError) as error:
                raise ConanException(
                    "clunk upstream self-check '%s' failed to launch: %s"
                    % (mode, error))
            output = (proc.stdout or "") + (proc.stderr or "")
            with open(log_path, "w", encoding="utf-8",
                      errors="replace") as handle:
                handle.write(output)
            if proc.returncode != 0:
                raise ConanException(
                    "clunk upstream self-check '%s' exited %d; log tail: %s"
                    % (mode, proc.returncode, output[-800:]))
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                output = handle.read()
            if len(output) < 200:
                raise ConanException(
                    "clunk upstream self-check '%s' produced only %d chars; "
                    "treating exit-0-without-output as a silent skip" % (mode, len(output)))
            for section in sections:
                if section not in output:
                    raise ConanException(
                        "clunk upstream self-check '%s' is missing expected "
                        "section %r; log tail: %s" % (mode, section, output[-800:]))
            self.output.info("clunk upstream self-check '%s' passed (%d chars)" % (mode, len(output)))
        result = {
            "status": "passed",
            "framework": "upstream-self-check",
            "command": " && ".join(actual_commands),
            "discovered": len(checks),
            "executed": len(checks),
            "passed": len(checks),
            "failed": 0,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8") as handle:
            handle.write(json.dumps(result))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._fixup_package_headers()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"))
        self._write_cmake_config()

    def _fixup_package_headers(self):
        # Belt-and-braces for the DIRECTORY-install above: if cmake.install()
        # was served from cache or the in-recipe CMakeLists rewrite did not
        # take effect, explicitly copy every shipped header so the consumer
        # <clunk/...> prefix always resolves (types.h was the observed fatal).
        # Preserves backend/sdl subdirectories via keep_path. Idempotent.
        src_clunk = os.path.join(self.source_folder, "clunk")
        dst_clunk = os.path.join(self.package_folder, "include", "clunk")
        try:
            copy(self, "*.h", src=src_clunk, dst=dst_clunk, keep_path=True)
        except Exception as error:
            self.output.info("clunk header fixup copy skipped: %s" % error)
        # Generated config.h lives under the build tree
        # (${CMAKE_CURRENT_BINARY_DIR}/clunk/config.h); ensure it lands at
        # include/clunk/config.h even if the second install(FILES ...) missed.
        dst_config = os.path.join(dst_clunk, "config.h")
        if not os.path.isfile(dst_config):
            for root, _dirs, files in os.walk(self.build_folder):
                if files == ["config.h"] or "config.h" in files:
                    candidate = os.path.join(root, "config.h")
                    try:
                        with open(candidate, "r", encoding="utf-8",
                                   errors="replace") as handle:
                            probe = handle.read(400)
                    except OSError:
                        continue
                    if "CLUNK" in probe or "clunk" in candidate.lower():
                        try:
                            os.makedirs(dst_clunk, exist_ok=True)
                            shutil.copyfile(candidate, dst_config)
                            self.output.info(
                                "clunk header fixup: installed generated "
                                "config.h from %s" % candidate)
                            break
                        except OSError:
                            continue

    def _write_cmake_config(self):
        # Upstream installs no CMake config files; ship a minimal one so
        # downstream consumers can `find_package(clunk CONFIG)`.
        libname = "libclunk.so" if self.options.shared else "libclunk.a"
        config_dir = os.path.join(self.package_folder, "lib", "cmake", "clunk")
        os.makedirs(config_dir, exist_ok=True)
        with open(os.path.join(config_dir, "clunk-config.cmake"),
                  "w", encoding="utf-8") as handle:
            handle.write(
                "get_filename_component(_CLUNK_PREFIX \"${CMAKE_CURRENT_LIST_FILE}\" PATH)\n"
                "get_filename_component(_CLUNK_PREFIX \"${_CLUNK_PREFIX}\" PATH)\n"
                "get_filename_component(_CLUNK_PREFIX \"${_CLUNK_PREFIX}\" PATH)\n"
                "if(NOT TARGET clunk::clunk)\n"
                "  add_library(clunk::clunk UNKNOWN IMPORTED)\n"
                "  set_target_properties(clunk::clunk PROPERTIES\n"
                "    IMPORTED_LOCATION \"${_CLUNK_PREFIX}/lib/%s\"\n"
                "    INTERFACE_INCLUDE_DIRECTORIES \"${_CLUNK_PREFIX}/include\")\n"
                "endif()\n" % libname)

    def package_info(self):
        self.cpp_info.libs = ["clunk"]
        self.cpp_info.set_property("cmake_file_name", "clunk")
        self.cpp_info.set_property("cmake_target_name", "clunk::clunk")
