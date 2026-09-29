#!/usr/bin/env python3
"""Conan recipe - sysrepo 3.7.11 (CMake) for HarmonyOS PC (aarch64)."""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rmdir

required_conan_version = ">=2.0"


class SysrepoConan(ConanFile):
    name = "sysrepo"
    version = "3.7.11"
    description = (
        "sysrepo is a configuration datastore and YANG data manipulation "
        "library, which allows you to store, modify and retrieve YANG data "
        "according to RFC7950 through APIs separated into groups of core, "
        "plugin, and notification functions."
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/sysrepo/sysrepo"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Upstream CMakeLists.txt pins LIBYANG_DEP_VERSION 3.13.2 and
        # LIBYANG_DEP_SOVERSION 3.9.11, then calls
        # find_package(LibYANG ${LIBYANG_DEP_SOVERSION} REQUIRED).
        # libyang/3.13.6 is the published release that satisfies that range.
        # sysrepo.h includes <libyang/libyang.h> in its public API, so the
        # dependency has to be transitive for consumers.
        self.requires("libyang/3.13.6", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # Upstream only builds tests/ when find_package(CMocka 1.0.1) succeeds,
        # and it is NOT a REQUIRED package, so a missing CMocka silently drops
        # the whole CTest suite.  Requiring it keeps the suite real (same
        # reasoning as libyang/3.13.6 and authselect/1.7.1).
        self.test_requires("cmocka/2.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _joined(paths):
        return ";".join(str(p) for p in paths)

    @staticmethod
    def _lib_paths(pkg):
        """Absolute paths of every library a dependency package exposes."""
        info = pkg.cpp_info
        out = []
        for lib in info.libs:
            for libdir in info.libdirs:
                for stem in ("lib%s.so", "lib%s.a", "%s.lib"):
                    cand = os.path.join(str(libdir), stem % lib)
                    if os.path.isfile(cand):
                        out.append(cand)
                        break
        return out

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)

        # OHOS runs on the HongMeng Linux-compatible kernel; CMake 4.x has no
        # Platform/HarmonyOS module, so map the target to Linux/aarch64
        # (same fix as the sibling libyang/3.13.6 recipe).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # OHOS musl libc does not implement the POSIX robust mutex functions
        # (neither libc.so nor libpthread.a exports them).  Enable the
        # fallback shim in src/common.h (see patches/) through a project-level
        # macro; patch files must stay free of platform macros (R8/PF5).
        if self.settings.os == "OHOS":
            tc.preprocessor_definitions["SR_NO_ROBUST_MUTEX"] = "1"
            # OHOS processes run under app UIDs absent from /etc/passwd.
            tc.preprocessor_definitions["SR_NO_PASSWD_ENTRIES"] = "1"

        # Upstream declares an old cmake_minimum_required range that CMake 4.x
        # rejects outright.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # Upstream defaults the datastore repository to /etc/sysrepo, which is
        # a read-only mount on HarmonyOS PC; a relative destination keeps the
        # install skeleton inside the Conan package prefix instead of the
        # host root filesystem.
        tc.cache_variables["REPO_PATH"] = "etc/sysrepo"
        # A fresh repository is initialised from the internal YANG modules.
        # Bake SR_YANG_PATH to a build-tree directory (relative values get
        # absolutized against CMAKE_BINARY_DIR) that build() fills from the
        # source modules, so every repository (test_package and the upstream
        # per-test repositories) finds its modules.
        tc.cache_variables["YANG_MODULE_PATH"] = "sysrepo-yang"

        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # ohos.toolchain otherwise defaults the 64-bit lib dir to lib64/.
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        # Test suite: built, never executed by the recipe itself.  Valgrind and
        # coverage variants are not available on this platform.
        tc.cache_variables["ENABLE_TESTS"] = "ON"
        tc.cache_variables["ENABLE_VALGRIND_TESTS"] = "OFF"
        tc.cache_variables["ENABLE_COVERAGE"] = "OFF"
        tc.cache_variables["ENABLE_PERF_TESTS"] = "OFF"

        # Not part of the library deliverable.
        tc.cache_variables["ENABLE_EXAMPLES"] = "OFF"
        tc.cache_variables["ENABLE_COMMON_TARGETS"] = "OFF"
        tc.cache_variables["INSTALL_SYSCTL_CONF"] = "OFF"

        # Optional datastore backends.  Neither mongo-c-driver nor hiredis is
        # published in the platform artifact repo, and upstream leaves both off
        # by default; pin them so a stray system copy cannot change the API
        # surface of the shipped library.
        tc.cache_variables["ENABLE_DS_MONGO"] = "OFF"
        tc.cache_variables["ENABLE_DS_REDIS"] = "OFF"

        # sysrepo ships its own CMakeModules/ and appends it to
        # CMAKE_MODULE_PATH, so find_package(LibYANG)/find_package(CMocka) run
        # in MODULE mode against in-tree Find scripts that only look at fixed
        # system prefixes.  Feed the modules through every input they honour.
        #
        # Both the singular *and* the plural cache entries are pre-seeded, and
        # so is the package root: the plural pair is what FindLibYANG's
        # "already in cache" early-exit gates on, and FindCMocka's library
        # search is broken by construction (its find_library PATHS points at
        # ${CMOCKA_ROOT_DIR}/include, where libraries never live), so the root
        # variable alone can never produce CMOCKA_LIBRARY.  Seeding the result
        # variables makes find_* skip the search entirely and lets
        # find_package_handle_standard_args succeed on the real Conan paths.
        # Same reasoning as the in-tree FindPCRE2/FindCMocka handling in
        # archives/l/libyang/3.13.6/conanfile.py.
        ly = self.dependencies["libyang"]
        # libyang's *public* header tree_data.h includes <pcre2.h>, and the
        # libyang/3.13.6 recipe propagates pcre2 transitively (headers and
        # libs, via its cpp_info.requires).  That propagation only
        # reaches consumers that use the Conan-generated CMake target; sysrepo
        # consumes libyang through its in-tree FindLibYANG module, so the
        # transitive include dir has to be folded into what we hand the module
        # or compiling sysrepo.c dies on "pcre2.h file not found".
        ly_includes = [str(p) for p in ly.cpp_info.includedirs]
        ly_libraries = list(self._lib_paths(ly))
        for extra in ("pcre2",):
            try:
                dep = self.dependencies[extra]
            except KeyError:
                continue
            ly_includes += [str(p) for p in dep.cpp_info.includedirs]
            ly_libraries += self._lib_paths(dep)
        ly_include = ";".join(ly_includes).replace("\\", "/")
        ly_library = ";".join(ly_libraries).replace("\\", "/")
        for key, value in (
            ("LIBYANG_INCLUDE_DIR", ly_include),
            ("LIBYANG_INCLUDE_DIRS", ly_include),
            ("LIBYANG_LIBRARY", ly_library),
            ("LIBYANG_LIBRARIES", ly_library),
        ):
            tc.cache_variables[key] = value

        ck = self.dependencies["cmocka"]
        # Upstream gates its test suite on the ALL-CAPS CMOCKA_FOUND, which
        # only the in-tree FindCMocka module ever sets (module-mode FPHSA
        # compat).  Conan's config package only sets cmocka_FOUND, so seed
        # the uppercase flag explicitly - cmocka is really available.
        tc.cache_variables["CMOCKA_FOUND"] = "1"
        ck_include = self._joined(ck.cpp_info.includedirs).replace("\\", "/")
        ck_library = self._joined(self._lib_paths(ck)).replace("\\", "/")
        for key, value in (
            ("CMOCKA_INCLUDE_DIR", ck_include),
            ("CMOCKA_INCLUDE_DIRS", ck_include),
            ("CMOCKA_LIBRARY", ck_library),
            ("CMOCKA_LIBRARIES", ck_library),
        ):
            tc.cache_variables[key] = value
        tc.cache_variables["CMOCKA_ROOT_DIR"] = ck.package_folder.replace("\\", "/")

        # Belt and braces: the modules also honour CMAKE_INCLUDE_PATH and
        # CMAKE_LIBRARY_PATH in their search lists.
        tc.cache_variables["CMAKE_INCLUDE_PATH"] = ";".join(
            ly_includes + [str(p) for p in ck.cpp_info.includedirs]
        )
        tc.cache_variables["CMAKE_LIBRARY_PATH"] = ";".join(
            ly_libraries + [str(p) for p in ck.cpp_info.libdirs]
        )


        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Fill the baked YANG_MODULE_PATH directory with the internal
        # module files from the source tree.
        yang_dst = os.path.join(str(self.build_folder), "sysrepo-yang")
        os.makedirs(yang_dst, exist_ok=True)
        yang_src = os.path.join(str(self.source_folder), "modules")
        for name in os.listdir(yang_src):
            if name.endswith(".yang"):
                shutil.copy2(
                    os.path.join(yang_src, name), os.path.join(yang_dst, name)
                )
        if self.settings.os == "OHOS":
            # OHOS requires signed ELFs: unsigned shared libraries are
            # rejected by the dynamic loader even though unsigned executables
            # run (same hardening as archives/l/libyang/3.13.6).
            self._sign_build_artifacts()

    def _sign_build_artifacts(self):
        # Sign every ELF in the build tree (test binaries fork+exec on the
        # device during the upstream ctest run); _sign_paths filters
        # non-ELF files itself.
        self._sign_tree(self.build_folder)

    def _sign_tree(self, root):
        candidates = glob.glob(
            os.path.join(root, "**", "*.so*"), recursive=True
        )
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if name.endswith(".signing"):
                    continue
                candidates.append(os.path.join(dirpath, name))
        self._sign_paths(candidates, required=True)

    def _sign_paths(self, paths, required):
        paths = sorted(
            {
                path
                for path in paths
                if os.path.isfile(path)
                and not os.path.islink(path)
                and self._is_elf(path)
            }
        )
        if not paths:
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            message = "HarmonyOS execution requires llvm-objcopy and binary-sign-tool"
            if required:
                raise ConanInvalidConfiguration(message)
            self.output.warning(message)
            return
        for path in paths:
            self._sign_elf_atomically(path, objcopy, signer)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c", "") or compilers.get("cpp", "")
        compiler_dir = os.path.dirname(compiler)
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _shell_join(self, arguments):
        return shlex.join([str(argument) for argument in arguments])

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(
                self._shell_join(
                    [objcopy, "--remove-section", ".codesign", temporary]
                ),
                env="conanbuild",
            )
            self.run(
                self._shell_join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        temporary,
                        "-outFile",
                        temporary,
                        "-selfSign",
                        "1",
                    ]
                ),
                env="conanbuild",
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # "share" is REQUIRED at runtime: share/yang/modules/sysrepo holds
        # the internal YANG modules a fresh repository is initialised from.
        for empty in ("lib/pkgconfig", "state"):
            rmdir(self, os.path.join(self.package_folder, empty))
        if self.settings.os == "OHOS":
            # The installed artifacts must carry valid signatures: the
            # dynamic loader rejects unsigned shared libraries even though
            # unsigned executables run.  Sign the package tree in place
            # (build-tree signing alone does not survive packaging).
            self._sign_tree(self.package_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "sysrepo")
        self.cpp_info.set_property("cmake_config_name", "sysrepo")
        self.cpp_info.set_property("cmake_target_name", "sysrepo::sysrepo")
        self.cpp_info.set_property("pkg_config_name", "sysrepo")
        self.cpp_info.libs = ["sysrepo"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        # libyang is re-exposed through the public sysrepo.h API.
        self.cpp_info.requires = ["libyang::libyang"]
        if self.settings.os in ("Linux", "OHOS"):
            # Upstream links pthread + m, and dlopens its own plugins.
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
