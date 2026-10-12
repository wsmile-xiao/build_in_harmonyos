#!/usr/bin/env python3
"""Conan recipe for WeeChat 4.9.4 (CMake)."""

import glob
import os
import shlex
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


class WeechatConan(ConanFile):
    name = "weechat"
    version = "4.9.4"
    description = "Extensible chat client with curses and headless interfaces"
    license = "GPL-3.0-or-later"
    homepage = "https://weechat.org/"
    url = "https://github.com/weechat/weechat"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    default_options = {
        "ncurses/*:shared": False,
        "zstd/*:shared": True,
    }

    def requirements(self):
        self.requires("ncurses/6.6")
        self.requires("zlib/1.3.1.1")
        self.requires("gnutls/3.8.10")
        self.requires("libgcrypt/1.11.0")
        self.requires("curl/8.15.0")
        self.requires("zstd/1.5.7.1")
        self.requires("cjson/1.7.19")

    def build_requirements(self):
        self.test_requires("cpputest/4.0_r2")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports Linux/OHOS builds only"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _host_libdirs(self):
        libdirs = []
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                if libdir:
                    libdirs.append(os.path.join(dep.package_folder, libdir))
        return libdirs

    def _install_rpaths(self):
        rpaths = []
        for libdir in self._host_libdirs():
            rpaths.append(libdir)
            # cover both Conan home layouts used on device and build farm
            rpaths.append(libdir.replace("/.conan2/", "/.cache/conan2/"))
            rpaths.append(libdir.replace("/.cache/conan2/", "/.conan2/"))
        return list(
            dict.fromkeys(rpath for rpath in rpaths if rpath and rpath != "/")
        )

    def _alias_libcjson_pc(self):
        # upstream asks pkg-config for module "libcjson"; the cjson package
        # only generates "cjson.pc"
        src = os.path.join(self.generators_folder, "cjson.pc")
        dst = os.path.join(self.generators_folder, "libcjson.pc")
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copyfile(src, dst)

    def _ohos_sysroot_include(self):
        # include directory of the OHOS SDK sysroot: musl provides <iconv.h>
        # and iconv_open() there, outside the host-style paths (/usr/include)
        # the in-tree FindIconv.cmake searches
        def has_iconv(directory):
            return os.path.isfile(os.path.join(directory, "iconv.h"))

        candidates = []
        for env_name in ("OHOS_SDK_NATIVE", "OHOS_SDK_HOME", "DEVECO_SDK_HOME"):
            base = os.environ.get(env_name)
            if not base:
                continue
            candidates.append(os.path.join(base, "sysroot", "usr", "include"))
            candidates.append(
                os.path.join(base, "native", "sysroot", "usr", "include")
            )
        for pattern in (
            "/data/service/hnp/*/*/ohos/native/sysroot/usr/include/iconv.h",
            "/data/service/hnp/*/ohos/native/sysroot/usr/include/iconv.h",
        ):
            for hit in sorted(glob.glob(pattern), reverse=True):
                candidates.append(os.path.dirname(hit))
        for candidate in candidates:
            if has_iconv(candidate):
                return candidate
        return None

    def generate(self):
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._alias_libcjson_pc()

        ncurses_include = os.path.join(
            self.dependencies["ncurses"].package_folder, "include"
        )
        ncurses_libdir = os.path.join(
            self.dependencies["ncurses"].package_folder, "lib"
        )

        tc = CMakeToolchain(self)
        # the toolchain enables CMAKE_FIND_PACKAGE_PREFER_CONFIG, so
        # find_package(Ncurses) resolves to the generated ncurses-config.cmake
        # (imported target ncurses::ncurses) and the in-tree FindNcurses.cmake
        # never runs; patch 0004 maps that target back to NCURSES_FOUND/
        # NCURSES_LIBRARY. The cache entries below cover FindNcurses.cmake
        # should config mode ever be unavailable (its raw find_path()/
        # find_library() calls cannot see a Conan package) and feed the
        # include_directories() call of the curses front-end
        tc.cache_variables["NCURSES_INCLUDE_PATH"] = ncurses_include
        tc.cache_variables["NCURSESW_LIBRARY"] = os.path.join(
            ncurses_libdir, "libncursesw.a"
        )
        tc.cache_variables["NCURSES_LIBRARY"] = os.path.join(
            ncurses_libdir, "libncursesw.a"
        )
        # check_include_files()/check_symbol_exists() only look at
        # CMAKE_REQUIRED_INCLUDES
        tc.cache_variables["CMAKE_REQUIRED_INCLUDES"] = ncurses_include
        # keep the ncurses library directory on the executable link line so
        # probe link steps and bare -l names resolve through it
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = f"-L{ncurses_libdir}"
        # the OHOS sysroot has musl <iconv.h> and iconv_open() in libc (no
        # libiconv needed): point the in-tree FindIconv.cmake at it so the
        # charset plugin and HAVE_ICONV builds do not report "Iconv not found"
        sysroot_include = self._ohos_sysroot_include()
        if sysroot_include:
            tc.cache_variables["ICONV_INCLUDE_PATH"] = sysroot_include
        # cpputest (test_requires): find_package(CppUTest) resolves in config
        # mode under CMAKE_FIND_PACKAGE_PREFER_CONFIG (CMakeDeps target
        # CppUTest::CppUTest), so the in-tree FindCppUTest.cmake never runs
        # and sets no CPPUTEST_* variable; upstream tests/unit/CMakeLists.txt
        # uses ${CPPUTEST_INCLUDE_DIRS} for include_directories() and
        # ${CPPUTEST_LDFLAGS} on the link line of the "tests" binary, so
        # provide both from the package cache
        cpputest_folder = self.dependencies["cpputest"].package_folder
        tc.cache_variables["CPPUTEST_INCLUDE_DIRS"] = os.path.join(
            cpputest_folder, "include"
        )
        cpputest_flags = [f"-L{os.path.join(cpputest_folder, 'lib')}"]
        cpputest_flags.extend(
            f"-l{lib}"
            for lib in self.dependencies["cpputest"].cpp_info.libs
        )
        tc.cache_variables["CPPUTEST_LDFLAGS"] = " ".join(cpputest_flags)
        # build both front-ends and keep the upstream unit test suite
        tc.cache_variables["ENABLE_HEADLESS"] = True
        tc.cache_variables["ENABLE_TESTS"] = True
        # script interpreters (perl/python/...), spell checking and gettext
        # translations are out of scope for this adaptation
        tc.cache_variables["ENABLE_SCRIPTS"] = False
        # the unit tests derive HAVE_<LANG> from the individual switches
        # (tests/unit/CMakeLists.txt), not from ENABLE_SCRIPTS, while the
        # plugin build gates use "ENABLE_SCRIPTS AND ENABLE_<LANG>"
        # (src/plugins/CMakeLists.txt); turn the individual interpreters
        # off too, so that both agree
        tc.cache_variables["ENABLE_PERL"] = False
        tc.cache_variables["ENABLE_PYTHON"] = False
        tc.cache_variables["ENABLE_RUBY"] = False
        tc.cache_variables["ENABLE_LUA"] = False
        tc.cache_variables["ENABLE_TCL"] = False
        tc.cache_variables["ENABLE_GUILE"] = False
        tc.cache_variables["ENABLE_PHP"] = False
        tc.cache_variables["ENABLE_JAVASCRIPT"] = False
        tc.cache_variables["ENABLE_SPELL"] = False
        tc.cache_variables["ENABLE_NLS"] = False
        # upstream sets CMAKE_SKIP_RPATH; on OHOS the shared dependencies
        # live in the package cache and must be located through RPATH. The
        # device cmake (4.1.2, OHOS build) never emits the rpath flags it
        # computes itself (CMAKE_INSTALL_RPATH / CMAKE_BUILD_RPATH /
        # CMAKE_BUILD_WITH_INSTALL_RPATH all verified inert: empty link
        # lines, no DT_RUNPATH in the linked binaries), so the run path is
        # injected as a raw linker flag instead (verified end-to-end:
        # DT_RUNPATH present in the linked binaries)
        rpaths = self._install_rpaths()
        if rpaths:
            rpath_flag = "-Wl,-rpath," + ":".join(rpaths)
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] += " " + rpath_flag
            tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = rpath_flag
            tc.cache_variables["CMAKE_MODULE_LINKER_FLAGS"] = rpath_flag
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # conan's cmake.test() appends cli_args to `cmake --build`, which
        # rejects ctest arguments such as --output-on-failure; the device
        # cmake is no exception, so drive ctest directly in the build folder
        skip_test = self.conf.get("tools.build:skip_test", check_type=bool)
        if can_run(self) and not skip_test:
            env = Environment()
            for libdir in self._host_libdirs():
                env.append_path("LD_LIBRARY_PATH", libdir)
            with env.vars(self).apply():
                self.run("ctest --output-on-failure", cwd=self.build_folder)
        else:
            self.output.warning(
                "cross-build: upstream ctest suite registered but not run"
            )

    def _find_ohos_tool(self, env_name, command, fallback_paths):
        configured = os.environ.get(env_name)
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.exists(configured):
                return configured
        found = shutil.which(command)
        if found:
            return found
        for candidate in fallback_paths:
            if os.path.exists(candidate):
                return candidate
        return None

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        objcopy = self._find_ohos_tool(
            "OHOS_LLVM_OBJCOPY",
            "llvm-objcopy",
            (
                "/data/service/hnp/bin/llvm-objcopy",
                "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
            ),
        )
        signer = self._find_ohos_tool(
            "OHOS_BINARY_SIGN_TOOL",
            "binary-sign-tool",
            (
                "/data/service/hnp/bin/binary-sign-tool",
                "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
            ),
        )
        if not signer:
            raise ConanException(
                "binary-sign-tool is required to package weechat on OHOS"
            )

        targets = []
        for subdir in ("bin", "libexec"):
            directory = os.path.join(self.package_folder, subdir)
            if not os.path.isdir(directory):
                continue
            for name in sorted(os.listdir(directory)):
                path = os.path.join(directory, name)
                if os.path.isfile(path) and self._is_elf(path):
                    targets.append(path)
        for path in glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"),
            recursive=True,
        ):
            if os.path.isfile(path) and self._is_elf(path):
                targets.append(path)

        for path in targets:
            if objcopy:
                self.run(
                    f'{shlex.quote(objcopy)} --remove-section .codesign '
                    f'{shlex.quote(path)} 2>/dev/null || true'
                )
            signed = f"{path}.signed"
            self.run(
                f'{shlex.quote(signer)} sign -inFile {shlex.quote(path)} '
                f'-outFile {shlex.quote(signed)} -selfSign 1'
            )
            shutil.move(signed, path)
            os.chmod(
                path,
                os.stat(path).st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
