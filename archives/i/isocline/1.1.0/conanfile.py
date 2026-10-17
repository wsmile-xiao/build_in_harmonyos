#!/usr/bin/env python3
"""Conan recipe — isocline 1.1.0 (CMake).

Isocline is a portable GNU readline alternative written in pure C99
(multiline editing, history, completion, syntax highlighting, bbcode
terminal output). Upstream ships its own CMakeLists.txt that builds a
static library ``isocline`` plus a shared library ``isocline_shared``
(both with OUTPUT_NAME ``isocline``).

OHOS notes:
  - Pure C99, zero external dependencies (no pthread/math/dlopen: only
    libc termios/ioctl/locale usage), so no patches are needed.
  - Upstream always builds both static and shared targets and ignores
    BUILD_SHARED_LIBS; package() therefore keeps only the artefact
    matching the ``shared`` option so each package revision ships a
    single library form.
  - Upstream has no automated test suite (no enable_testing/add_test,
    no check target; test/ holds interactive TTY demos only, see
    test_package/MANIFEST.yml audit), so build() runs no upstream
    tests; IC_BUILD_TESTS is OFF (the example/test_colors demos need
    an interactive terminal and are not installed by upstream either).
"""

import fnmatch
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class IsoclineConan(ConanFile):
    name = "isocline"
    version = "1.1.0"
    description = "A portable GNU readline alternative (multiline editing, history, completion, syntax highlighting)"
    license = "MIT"
    homepage = "https://github.com/daanx/isocline"
    url = "https://github.com/daanx/isocline"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "isocline is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        # [readonly_tmp]: /tmp is read-only on the device. Prefer the
        # HMBS-injected task-private TMPDIR/TMP/TEMP after a real
        # creatability probe (isdir alone is not proof); fall back to a
        # dir under build_folder so CMake try-compiles and clang temp
        # files never touch /tmp. Only the temp root is replaced.
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                try:
                    probe = os.path.join(candidate, ".hmbs_write_probe")
                    with open(probe, "w") as handle:
                        handle.write("ok")
                    os.remove(probe)
                    return candidate
                except OSError:
                    continue
        fallback = os.path.join(self.build_folder, "hmbs-tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _resolve_tool_compiler(self, kind):
        # Aggregated experience: the repo profile pins absolute compiler
        # paths via tools.build:compiler_executables. On a healthy runner
        # the pinned path exists -> use it as-is (zero change). When the
        # pinned path is absent on a given preflight runner, fall back to
        # PATH discovery (hmbs prepends its tool dirs to PATH) instead of
        # failing the CMake compiler check. Only CC/CXX are overridden;
        # CFLAGS/LDFLAGS are untouched.
        try:
            configured = self.conf.get(
                "tools.build:compiler_executables:%s" % kind, check_type=str)
        except Exception:
            configured = None
        if configured:
            if os.path.exists(configured):
                return configured
            base = os.path.basename(configured)
            for cand in ([base]
                         + (["clang", "cc"] if kind == "c"
                            else ["clang++", "c++"])):
                found = shutil.which(cand)
                if found:
                    self.output.warning(
                        "configured %s compiler missing: %s; "
                        "falling back to PATH: %s" % (kind, configured, found))
                    return found
            self.output.warning(
                "configured %s compiler missing: %s; no PATH fallback "
                "found, using basename %s so the failure surfaces as an "
                "explicit environment fault" % (kind, configured, base))
            return base
        # No conf value: prefer env, then PATH, then generic name.
        for key in ("CC", "CXX"):
            if kind == ("c" if key == "CC" else "cpp"):
                val = os.environ.get(key)
                if val and (os.path.exists(val) or shutil.which(val)):
                    return val
        default = "clang" if kind == "c" else "clang++"
        return shutil.which(default) or default

    def _probe_compiler(self, path):
        # Best-effort `--version` probe: distinguishes "binary actually
        # missing/inaccessible (infra)" from "binary runs but the CMake
        # test-compile fails (recipe/toolchain issue)". Never raises.
        try:
            proc = subprocess.run(
                [path, "--version"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=60)
            first = (proc.stdout or "").strip().splitlines()
            self.output.info("compiler probe %s rc=%s: %s"
                             % (path, proc.returncode,
                                (first[0] if first else "")[:200]))
            return proc.returncode == 0
        except Exception as exc:
            self.output.warning("compiler probe %s failed: %s" % (path, exc))
            return False

    def _asm_compiler_for_ohos(self, cc):
        # Upstream declares project(libisocline C CXX ASM) but ships no
        # .S/.s sources (src/isocline.c only). The OHOS profile pins only
        # c/cpp executables, so CMake aborts with "No CMAKE_ASM_COMPILER
        # could be found". Point ASM at the same resolved clang used for
        # C, which can assemble; no source semantics change.
        if cc:
            return cc
        try:
            conf_cc = self.conf.get(
                "tools.build:compiler_executables:c", check_type=str)
        except Exception:
            conf_cc = None
        if conf_cc:
            return conf_cc
        return "clang"

    def generate(self):
        tc = CMakeToolchain(self)
        # example/test_colors are interactive TTY demos, not an automated
        # suite (upstream installs neither); keep the build to the libs.
        tc.variables["IC_BUILD_TESTS"] = False
        cc = self._resolve_tool_compiler("c")
        cxx = self._resolve_tool_compiler("cpp")
        self._probe_compiler(cc)
        if cxx != cc:
            self._probe_compiler(cxx)
        # Bake the resolved compilers into the toolchain file so the
        # CMake compiler checks use a binary that exists on this runner;
        # on healthy runners resolved == pinned path (no-op).
        tc.variables["CMAKE_C_COMPILER"] = cc
        tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.variables["CMAKE_ASM_COMPILER"] = self._asm_compiler_for_ohos(cc)
        tc.generate()
        tmpdir = self._writable_tmpdir()
        env = Environment()
        for key in ("TMPDIR", "TMP", "TEMP"):
            env.define(key, tmpdir)
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.vars(self).save_script("hmbs_tmp")

    def build(self):
        apply_conandata_patches(self)
        tmpdir = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        # Same resolved values as generate(): healthy runners keep the
        # pinned absolute paths; runners where they are absent use the
        # PATH fallback for every child process.
        os.environ["CC"] = self._resolve_tool_compiler("c")
        os.environ["CXX"] = self._resolve_tool_compiler("cpp")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream installs both libisocline.a and libisocline.so
        # regardless of BUILD_SHARED_LIBS; keep only the selected form.
        self._keep_selected_library_form()
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def _keep_selected_library_form(self):
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        keep_shared = bool(self.options.shared)
        for root, _dirs, files in os.walk(libdir):
            for fname in files:
                is_shared = (fnmatch.fnmatch(fname, "*.so*")
                             or fnmatch.fnmatch(fname, "*.dylib"))
                is_static = fnmatch.fnmatch(fname, "*.a")
                stale = (is_shared and not keep_shared) or (is_static and keep_shared)
                if stale:
                    path = os.path.join(root, fname)
                    try:
                        os.remove(path)
                        self.output.info("removed non-selected artefact: %s" % path)
                    except OSError as exc:
                        self.output.warning("cannot remove %s: %s" % (path, exc))

    def package_info(self):
        self.cpp_info.libs = ["isocline"]
        self.cpp_info.set_property("cmake_file_name", "isocline")
        self.cpp_info.set_property("cmake_target_name", "isocline::isocline")
        self.cpp_info.set_property("pkg_config_name", "isocline")
