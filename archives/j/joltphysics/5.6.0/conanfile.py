#!/usr/bin/env python3
"""Conan recipe — joltphysics 5.6.0 (CMake, OpenHarmony PC aarch64).

JoltPhysics is a modern 3D physics engine (C++17, header-heavy core with
153 .cpp sources compiled into a static libJolt.a). Self-contained math
library — no mandatory external dependencies.

Key adaptation notes for HarmonyOS PC (aarch64):
  - x86 SIMD options (USE_SSE4_1/2, USE_AVX, USE_AVX2, USE_LZCNT, USE_TZCNT,
    USE_F16C) are force-disabled: on aarch64 Jolt's Jolt.cmake takes the
    "ARM64 uses no special commandline flags" path (ARM NEON is the
    default-enabled vector path), so these x86-only options are inert
    but turned OFF explicitly for clarity.
  - USE_FMADD=ON (upstream default): FMA is NOT x86-only on this project.
    Core.h auto-defines JPH_USE_FMADD on aarch64 because __ARM_FEATURE_FMA
    is an ARMv8 baseline feature, and the upstream unit tests
    (Vec3Tests/Vec4Tests TestDifferenceOfProducts) assert the fused
    result. CMAKE 4.x maps USE_FMADD=OFF to -ffp-contract=off which
    breaks the fusion of the NEON vmlaq_f32 intrinsics (they degrade to
    separate mul+add), failing those 2 test cases. Keeping the upstream
    default ON makes the full 581-case doctest suite pass.
    (Verified with a minimal repro on the OHOS clang toolchain:
    -ffp-contract=off -> vmlaq results in -128/64/0, =on -> -75.1656.)
  - INTERPROCEDURAL_OPTIMIZATION=OFF: LTO/whole-program-optimization on the
    OHOS clang toolchain is slow/unstable (upstream also disables it for ARM
    cross-compilation paths).
  - JPH_USE_VK / JPH_USE_DX12 / JPH_USE_MTL OFF, JPH_USE_CPU_COMPUTE ON:
    the GPU compute backends require dxc/glslc shader compilers not present
    in the OHOS SDK; the CPU compute path is the portable default.
  - ENABLE_ALL_WARNINGS=OFF: upstream enables -Wall -Werror which breaks on
    OHOS clang 15 differences; warnings are not needed for a binary package.
  - OVERRIDE_CXX_FLAGS=OFF: keep conan toolchain CXX flags (upstream would
    strip them to bare -O3 and drop e.g. -fstack-protector from the profile).
  - GENERATE_DEBUG_SYMBOLS=OFF: no debug symbols in Release package.
  - Cross-compile deterministic build OFF (upstream default, faithful).
  - Uses the OHOS SDK ohos.toolchain.cmake directly (same approach as
    assimp-5/5.4.3): the os=OHOS conan CMakeToolchain maps to a
    CMAKE_SYSTEM_NAME cmake does not accept for this project layout.
  - CMAKE_RANLIB fix: the OHOS SDK llvm/bin only ships llvm-ar (no
    llvm-ranlib) while ohos.toolchain.cmake still points CMAKE_RANLIB at
    llvm/bin/llvm-ranlib — archiving a static lib then fails with
    "Error running link command: no such file or directory". Override both
    CMAKE_AR and CMAKE_RANLIB to the hnp llvm tools (verified: OpenCV,
    SuiteSparse, assimp hit the same issue).
  - Upstream tests ARE built and run (with_tests=True default): the
    UnitTests target (doctest 2.5.2 vendored in UnitTests/doctest.h, no
    external dependency) compiles the 71 test source files of
    UnitTests/{Core,Geometry,Math,ObjectStream,Physics,SoftBody,Vehicle,
    Character,Ragdoll,Compute} and the build() phase runs the whole suite
    via ctest (581 test cases / 514281 assertions, ~35 s on OHOS aarch64).
    The conan test_package additionally compiles the upstream
    HelloWorld.cpp example against the installed libJolt.a and runs a real
    physics simulation (sphere falling onto a static floor box, simulated
    to sleep) to validate the installed package end-to-end.
  - Test runtime env: the UnitTests binary links libc++_shared.so which is
    not in the OHOS default loader search path; it is located via
    `clang++ -print-file-name=libc++_shared.so` introspection and prepended
    to LD_LIBRARY_PATH when running ctest (boost/1.85.0 precedent).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class JoltPhysicsConan(ConanFile):
    name = "joltphysics"
    version = "5.6.0"
    description = ("Jolt Physics is a high performance 3D physics engine "
                   "modern C++17 based library")
    license = "MIT"
    homepage = "https://github.com/jrouwe/JoltPhysics"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "use_asserts": [True, False],
        "double_precision": [True, False],
        "cross_platform_deterministic": [True, False],
        "with_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "use_asserts": False,
        "double_precision": False,
        "cross_platform_deterministic": False,
        "with_tests": True,
    }

    exports_sources = "conandata.yml", "patches/*"

    def requirements(self):
        pass  # self-contained math library, no mandatory deps

    def configure(self):
        if self.options.shared:
            # JPH_BUILD_SHARED_LIBS would require symbol visibility handling;
            # static is the upstream-documented consumption model
            self.output.info("shared=True: building libJolt.so")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        # Auto-discover the OHOS SDK ohos.toolchain.cmake
        # (1) profile [conf] user_toolchain  (2) OHOS_NDK_HOME env
        # (3) glob device/CI SDK layout)
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain",
                           default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "ohos.toolchain.cmake not found: set OHOS_NDK_HOME or profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK llvm/bin ships llvm-ar only (no llvm-ranlib), but
        # ohos.toolchain.cmake points CMAKE_RANLIB at the missing binary.
        # Archiving .a then dies with a bare "no such file or directory".
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""  # SDK has it, no override needed
        return shutil.which("llvm-ranlib") or ""

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = os.path.join(self.source_folder, "Build")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",  # ohos.toolchain 64-bit default is lib64/, normalize to lib
            # library type
            "-DJPH_BUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
            # ARM: x86-only SIMD knobs OFF (NEON is the default vector path, no flags needed)
            "-DUSE_SSE4_1=OFF",
            "-DUSE_SSE4_2=OFF",
            "-DUSE_AVX=OFF",
            "-DUSE_AVX2=OFF",
            "-DUSE_AVX512=OFF",
            "-DUSE_LZCNT=OFF",
            "-DUSE_TZCNT=OFF",
            "-DUSE_F16C=OFF",
            # USE_FMADD stays ON (upstream default): Core.h auto-defines
            # JPH_USE_FMADD on aarch64 via __ARM_FEATURE_FMA and the upstream
            # TestDifferenceOfProducts tests assert the fused result —
            # USE_FMADD=OFF maps to -ffp-contract=off which breaks NEON
            # vmlaq_f32 fusion (degrades to separate mul+add) and fails those
            # 2 cases (verified with a minimal repro on the OHOS clang toolchain).
            "-DUSE_FMADD=ON",
            "-DUSE_WASM_SIMD=OFF",
            # LTO off — slow/unstable on OHOS toolchain, upstream also skips it for ARM
            "-DINTERPROCEDURAL_OPTIMIZATION=OFF",
            # GPU compute backends off (need dxc/glslc); CPU compute is the portable path
            "-DJPH_USE_VK=OFF",
            "-DJPH_USE_DX12=OFF",
            "-DJPH_USE_MTL=OFF",
            "-DJPH_USE_CPU_COMPUTE=ON",
            # upstream doctest unit test suite follows the with_tests option
            # (built AND run in this build() phase, see below);
            # other applications stay off — package only ships the Jolt library
            "-DTARGET_UNIT_TESTS={}".format("ON" if self.options.with_tests else "OFF"),
            "-DTARGET_HELLO_WORLD=OFF",
            "-DTARGET_PERFORMANCE_TEST=OFF",
            "-DTARGET_SAMPLES=OFF",
            "-DTARGET_VIEWER=OFF",
            # flags hygiene
            "-DENABLE_ALL_WARNINGS=OFF",
            "-DGENERATE_DEBUG_SYMBOLS=OFF",
            "-DOVERRIDE_CXX_FLAGS=OFF",
            # faithful-to-upstream defaults (exposed as conan options)
            "-DUSE_ASSERTS={}".format("ON" if self.options.use_asserts else "OFF"),
            "-DDOUBLE_PRECISION={}".format("ON" if self.options.double_precision else "OFF"),
            "-DCROSS_PLATFORM_DETERMINISTIC={}".format(
                "ON" if self.options.cross_platform_deterministic else "OFF"),
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
            _ar = shutil.which("llvm-ar") or ""
            if _ar:
                defs.append('-DCMAKE_AR="{}"'.format(_ar))
        # Ninja generator: GNU make jobserver (FIFO-based, blocked by OHOS
        # SELinux per E074) is unreliable; Ninja has no such dependency and is
        # proven on duckdb/eigenpy. Falls back to Unix Makefiles -j1.
        if shutil.which("ninja"):
            defs.extend(["-G", "Ninja"])
        self.run("cmake -B \"{}\" -S \"{}\" {}".format(bdir, src, " ".join(defs)))
        if shutil.which("ninja"):
            self.run("cmake --build \"{}\" --parallel".format(bdir))
        else:
            # make -j1: FIFO jobserver is blocked on OHOS (E074)
            self.run("cmake --build \"{}\" -- -j1".format(bdir))
        if self.options.with_tests:
            self._run_unit_tests(bdir)

    def _run_unit_tests(self, bdir):
        """Run the upstream doctest unit test suite via ctest.

        The UnitTests binary links libc++_shared.so which is not in the OHOS
        default loader search path; locate it via compiler introspection
        (boost/1.85.0 precedent) and prepend to LD_LIBRARY_PATH. Only run
        when the produced binaries can actually execute (native OHOS build).
        """
        from conan.tools.build import can_run
        if not can_run(self):
            self.output.info("with_tests: cross-building, unit tests built "
                             "but not executed")
            return
        ctest = shutil.which("ctest") or "ctest"
        cmd = "{} --test-dir \"{}\" --output-on-failure".format(ctest, bdir)
        # The UnitTests binary links libc++_shared.so which is not in the
        # OHOS default loader search path. Locate the SDK libc++ dir via
        # compiler introspection (boost/1.85.0 precedent) and export it in
        # this process' environment — conan's self.run() inherits it, and
        # ctest passes its environment down to the test binary.
        cxx = os.environ.get("CXX", "clang++")
        try:
            import subprocess as _sp
            probe = _sp.run([cxx, "-print-file-name=libc++_shared.so"],
                            capture_output=True, text=True, timeout=30)
            libcxx_file = probe.stdout.strip()
            if probe.returncode == 0 and libcxx_file.startswith("/"):
                libcxx_dir = os.path.dirname(libcxx_file)
                if os.path.isdir(libcxx_dir):
                    os.environ["LD_LIBRARY_PATH"] = (
                        libcxx_dir + os.pathsep
                        + os.environ.get("LD_LIBRARY_PATH", ""))
                    self.output.info("unit tests LD_LIBRARY_PATH+={}".format(libcxx_dir))
        except Exception as e:  # noqa: BLE001 - probe is best-effort
            self.output.warning("libc++ probe failed: {}".format(e))
        self.output.info("Running upstream UnitTests (doctest) via ctest...")
        self.run(cmd)

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run("cmake --install \"{}\" --prefix \"{}\"".format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS PC XPM requires code signing for dlopen'd .so and
        # exec'd binaries. Only relevant when building shared.
        import glob as _glob
        targets = _glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += _glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            if os.path.exists(objcopy) and os.path.exists(signer):
                self.run("{} --remove-section .codesign \"{}\" 2>/dev/null || true".format(objcopy, f))
                self.run("{} sign -inFile \"{}\" -outFile \"{}\" -selfSign 1".format(signer, f, f))

    def package_info(self):
        self.cpp_info.libs = ["Jolt"]
        self.cpp_info.set_property("cmake_file_name", "Jolt")
        self.cpp_info.set_property("cmake_target_name", "Jolt::Jolt")
        # PUBLIC compile definitions from the default Release configuration
        # (Jolt.cmake: PROFILER_IN_DEBUG_AND_RELEASE / DEBUG_RENDERER_IN_
        # DEBUG_AND_RELEASE / ENABLE_OBJECT_STREAM are ON by default). They
        # change the Jolt ABI (JPH_VERSION_FEATURES check in Core.h), so
        # consumers MUST compile with the same set — exposed here so that
        # CMakeDeps consumers get them automatically.
        defines = ["JPH_PROFILE_ENABLED", "JPH_DEBUG_RENDERER", "JPH_OBJECT_STREAM"]
        if self.options.double_precision:
            defines.append("JPH_DOUBLE_PRECISION")
        if self.options.cross_platform_deterministic:
            defines.append("JPH_CROSS_PLATFORM_DETERMINISTIC")
        if self.options.use_asserts:
            defines.append("JPH_ENABLE_ASSERTS")
        self.cpp_info.defines = defines
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
