#!/usr/bin/env python3
"""Conan recipe — libarcus 5.0.0 (CMake)."""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibarcusConan(ConanFile):
    name = "libarcus"
    version = "5.0.0"
    description = "Communication library between internal components for Ultimaker software"
    license = "LGPL-3.0"
    homepage = "https://github.com/Ultimaker/libArcus"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("cura", "protobuf", "socket", "cpp")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("protobuf/3.17.3", transitive_headers=True)
        # Round 16 (strategy cycle 3, recipe-RREV axis): force the adapted
        # Autotools zlib instead of the conancenter CMake zlib. protobuf
        # requires zlib/1.3.1, whose ohpcd/conancenter RREV resolution in
        # preflight selects the unadapted CMake recipe (line-81
        # cmake.configure(), build/Release/generators layout, package
        # e80f2bcb) that fails the HarmonyOS-unknown project() compiler
        # check. zlib/1.3.1.1 exists only on ohpcd (Autotools ./configure
        # --static + CFLAGS=-fPIC, no CMake at all), so override=True pins
        # the adapted RREV for the transitive requirement. Precedent:
        # archives/a/abiword-plugin-sdw/3.0.8 + archives/e/exult/1.12.1
        # both use self.requires("zlib/1.3.1.1", override=True) to unify a
        # zlib/1.3.1 transitive chain onto the adapted recipe. -fPIC objects
        # also suit static libz.a absorption. This does not touch protobuf
        # options (with_zlib stays default True) and does not repeat the
        # exhausted with_zlib toggle in either direction.
        self.requires("zlib/1.3.1.1", override=True)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Round 14 (strategy cycle 2, package-ID axis): round-1 set
        # protobuf/*:with_zlib=False to dodge a conancenter zlib source build.
        # That changed the protobuf package ID (libarcus 37afb6 -> b9804b,
        # protobuf 13a81cb, 11 compatible configs, none found) and forced a
        # non-default-config protobuf source build with no ohpcd binary.
        # Default-config (with_zlib=True) is the recipe's tested path and the
        # only config with a chance of a binary hit, so restore it. If the
        # next preflight still source-builds, the failure fingerprint will at
        # least move off the 14-times-identical line-121 ID, giving fresh
        # evidence instead of another byte-identical loop.

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libarcus supports Linux and OHOS, not %s" % self.settings.os
            )
        check_min_cppstd(self, 17)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _usable_file(path):
        if not path:
            return None
        if os.path.isabs(path):
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
            return None
        found = shutil.which(path)
        return found or None

    @staticmethod
    def _real_binary(path):
        # No sibling-prefix substitution: wrapper/shim paths are used
        # directly and never rewritten to a same-directory sibling
        # (a prefix match can otherwise resolve clang -> clang-check,
        # which rejects -o and fails every compile).
        return path

    def _resolve_validated_compiler(self, lang):
        # OHOS-only validated compiler discovery (new axis for the
        # own-package CMakeLists.txt:1 project() compiler-identification
        # failure; prior axes -- TMPDIR passthrough, Ninja, Linux
        # presentation, lowmem flags -- left this fingerprint unmoved).
        # Accepts only basenames starting with clang (rejects generic
        # shims), probes in order: conf value, env (CC/CXX), PATH,
        # well-known OHOS toolchain path from ci/conan/profiles/ohos-aarch64
        # (last, existence-checked). Analysis-tool basenames are refused.
        if lang == "c":
            analysis = ("clang-check", "clang-tidy", "clang-format")
            env_keys = ("CC",)
            path_names = ("clang", "clang-15")
            conf_key = "c"
            common = ("/data/service/hnp/bin/clang",)
        else:
            analysis = ("clang-check", "clang-tidy", "clang-format")
            env_keys = ("CXX",)
            path_names = ("clang++", "clang++-15")
            conf_key = "cpp"
            common = ("/data/service/hnp/bin/clang++",)
        try:
            execs = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except ConanException:
            execs = {}
        candidates = []
        if execs:
            configured = execs.get(conf_key)
            if configured:
                candidates.append(configured)
        for key in env_keys:
            val = os.environ.get(key)
            if val:
                candidates.append(val)
        for name in path_names:
            found = shutil.which(name)
            if found:
                candidates.append(found)
        candidates.extend(common)
        for cand in candidates:
            usable = self._usable_file(cand)
            if not usable:
                continue
            base = os.path.basename(usable)
            if base in analysis:
                self.output.warning(
                    "validated compiler: refusing analysis tool %s" % usable)
                continue
            if not base.startswith("clang"):
                continue
            return self._real_binary(usable)
        return None

    def generate(self):
        # E002/R10: HarmonyOS mounts /tmp read-only. HMBS injects a writable
        # per-task TMPDIR; export it (plus TMP/TEMP aliases) into this
        # package's buildenv so CMake/clang temp files avoid /tmp.
        # This hardens libarcus's own configure step; it cannot retroactively
        # fix already-exported dependency builds (protobuf/zlib), which resolve
        # from remotes before this recipe's generate() runs.
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if tmpdir:
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.vars(self).save_script("hmbs_tmpdir")
        # HMBS lowmem (Signal 9/OOM mitigation, additive only): append
        # -O1 -g0 to CFLAGS/CXXFLAGS via buildenv. Never overwrites
        # profile/toolchain flags (sysroot lives in the toolchain file);
        # only lowers per-TU peak RSS and object size. Heavy optional
        # stack stays OFF (BUILD_PYTHON=False below); single-job comes
        # from HMBS tools.build:jobs=1; no test is skipped.
        try:
            lowmem = Environment()
            lowmem.append("CFLAGS", ["-O1", "-g0"])
            lowmem.append("CXXFLAGS", ["-O1", "-g0"])
            lowmem.vars(self).save_script("hmbs_lowmem")
        except Exception:
            pass
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Validated compiler pin (OHOS only): point CMake at the
        # existence-checked clang resolved above instead of trusting the
        # profile absolute path blindly (preflight workers have resolved
        # it to a missing/stale file before). Warns and keeps the
        # toolchain default when nothing validates, so the failure stays
        # explicit instead of silently falling back to an invalid path.
        if str(self.settings.os) == "OHOS":
            cc = self._resolve_validated_compiler("c")
            cxx = self._resolve_validated_compiler("cxx")
            if cc:
                tc.variables["CMAKE_C_COMPILER"] = cc
            else:
                self.output.warning(
                    "validated compiler: no usable clang found; "
                    "keeping toolchain default for C")
            if cxx:
                tc.variables["CMAKE_CXX_COMPILER"] = cxx
            else:
                self.output.warning(
                    "validated compiler: no usable clang++ found; "
                    "keeping toolchain default for CXX")
        # OHOS /bin/sh is not usable for CMake's Unix Makefiles generator
        # (same reason archives/p/protobuf/3.17.3 forces Ninja: Permission
        # denied from the default generator). Use Ninja for this package's
        # own configure step on OHOS; HMBS guarantees a Ninja binary on PATH
        # (HMBS_BUILD_TOOLS). Scoped to OHOS so Linux defaults are untouched.
        # This cannot affect the already-exported protobuf dependency build,
        # which runs before this recipe's generate().
        if str(self.settings.os) == "OHOS":
            tc.generator = "Ninja"
        # OHOS cmake presentation: CMakeToolchain maps os=OHOS to
        # CMAKE_SYSTEM_NAME=HarmonyOS (see ci/conan/profiles/ohos-aarch64),
        # but cmake 4.4.3 ships no Platform/HarmonyOS module -- the
        # preflight log shows "System is unknown to cmake" followed by
        # project() C/CXX compiler checks failing on this package own
        # CMakeLists.txt:1 (line-113 cmake.configure). Present as Linux
        # (precedent: archives/a/abcmidi/20260609/conanfile.py) so the
        # known Linux platform module drives try_compile; the OHOS clang
        # target/sysroot flags from the toolchain still emit OHOS binaries
        # (same basis as archives/r/rttr/0.9.6 notes). Scoped to OHOS.
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            )
        tc.variables["BUILD_PYTHON"] = False
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fail fast if the resolved C compiler is an analysis tool
        # (clang-check/tidy/format accept no -o and fail every compile).
        if str(self.settings.os) == "OHOS":
            cc = self._resolve_validated_compiler("c")
            if cc and os.path.basename(cc) in (
                    "clang-check", "clang-tidy", "clang-format"):
                raise ConanException(
                    "resolved CC=%s is not a compiler; refusing to build" % cc)
        self._append_lowmem_flags()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _append_lowmem_flags(self):
        # HMBS lowmem (Signal 9/OOM with empty log): append -O1 -g0 to
        # CMAKE_C/CXX_FLAGS at the end of the generated
        # conan_toolchain.cmake (idempotent HMBS_LOWMEM_FLAGS marker,
        # after any Release -O3/-g lines so the lower setting wins
        # per-TU). Additive only; bypasses -D/toolchain ordering.
        try:
            path = os.path.join(self.generators_folder,
                                "conan_toolchain.cmake")
        except Exception:
            return
        if not os.path.isfile(path):
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        if "HMBS_LOWMEM_FLAGS" in content:
            return
        content += (
            "\n# HMBS_LOWMEM_FLAGS: Signal 9/OOM mitigation "
            "(additive, no test skipped)\n"
            'string(APPEND CMAKE_C_FLAGS " -O1 -g0")\n'
            'string(APPEND CMAKE_CXX_FLAGS " -O1 -g0")\n'
        )
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        except OSError as exc:
            self.output.warning(
                "HMBS lowmem flags: cannot write %s: %s" % (path, exc))
            return
        self.output.info("HMBS lowmem flags appended (-O1 -g0)")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["Arcus"]
        self.cpp_info.set_property("cmake_file_name", "Arcus")
        self.cpp_info.set_property("cmake_target_name", "Arcus")
        self.cpp_info.defines = ["ARCUS"]
        if str(self.settings.build_type) == "Debug":
            self.cpp_info.defines.append("ARCUS_DEBUG")
        if str(self.settings.os) in ("Linux", "FreeBSD", "Macos"):
            self.cpp_info.system_libs.append("pthread")
