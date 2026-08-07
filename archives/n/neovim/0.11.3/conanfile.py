#!/usr/bin/env python3
"""Conan recipe for a Neovim 0.11.3 headless spike on OHOS.

This first spike intentionally uses Neovim's bundled dependency build where
possible.  The goal is to isolate whether the nvim binary itself can be built,
signed, and run in headless mode on OHOS before splitting every dependency into
separate Conan packages for the Path B Vusted chain.
"""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
    save,
)
from conan.tools.layout import basic_layout


class NeovimConan(ConanFile):
    name = "neovim"
    version = "0.11.3"
    description = "Hyperextensible Vim-based text editor, packaged for headless smoke testing"
    license = "Apache-2.0"
    homepage = "https://neovim.io/"
    url = "https://github.com/neovim/neovim"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libiconv/1.17")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        user_toolchains = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain",
            default=[],
            check_type=list,
        )
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(user_toolchains)
        if ndk:
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
        candidates.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"
                )
            )
        )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _compiler_path(self, language):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        candidate = compiler_executables.get(language, "")
        if candidate and os.path.isfile(candidate):
            return candidate
        fallback = "clang++" if language == "cpp" else "clang"
        return shutil.which(fallback) or fallback

    def _find_tool(self, name):
        candidates = [
            os.environ.get(name.upper().replace("-", "_"), ""),
            shutil.which(name) or "",
            os.path.join("/data/service/hnp/bin", name),
            os.path.join("/storage/Users/currentUser/usr/local/bin", name),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _sign_elf_tree(self, *roots):
        signer = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        if not signer or not objcopy:
            self.output.warning("OHOS signing tools not found; skipping ELF signing")
            return

        seen = set()
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for path in glob.glob(os.path.join(root, "**", "*"), recursive=True):
                if path in seen or os.path.islink(path) or not os.path.isfile(path):
                    continue
                seen.add(path)
                if not self._looks_like_elf(path):
                    continue
                self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true')
                self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')

    def _looks_like_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _build_flags(self):
        build_type = str(self.settings.build_type)
        toolchain = self._ohos_toolchain()
        ar = self._find_tool("llvm-ar") or self._find_tool("ar")
        ranlib = self._find_tool("llvm-ranlib") or self._find_tool("ranlib")
        strip = self._find_tool("llvm-strip") or self._find_tool("strip")
        iconv_flags = self._iconv_flags()
        platform_flags = []
        if toolchain:
            platform_flags.append(f'-DCMAKE_TOOLCHAIN_FILE="{toolchain}"')
        else:
            platform_flags.extend(
                [
                    f'-DCMAKE_C_COMPILER="{self._compiler_path("c")}"',
                    f'-DCMAKE_CXX_COMPILER="{self._compiler_path("cpp")}"',
                    "-DCMAKE_SYSTEM_NAME=Linux",
                    "-DCMAKE_SYSTEM_PROCESSOR=aarch64",
                ]
            )
        if ar:
            platform_flags.append(f'-DCMAKE_AR="{ar}"')
        if ranlib:
            platform_flags.append(f'-DCMAKE_RANLIB="{ranlib}"')
        if strip:
            platform_flags.append(f'-DCMAKE_STRIP="{strip}"')
        bundled_flags = self._bundled_dependency_flags()
        return {
            "cmake_extra": " ".join(
                platform_flags
                + iconv_flags
                + bundled_flags
                + [
                    f"-DCMAKE_BUILD_TYPE={build_type}",
                    f'-DCMAKE_INSTALL_PREFIX="{self.package_folder}"',
                    "-DENABLE_LIBINTL=OFF",
                    "-DENABLE_LTO=OFF",
                    "-DENABLE_WASMTIME=OFF",
                    "-DCI_BUILD=OFF",
                ]
            ),
            "deps_cmake": " ".join(
                platform_flags
                + [
                    f"-DCMAKE_BUILD_TYPE={build_type}",
                    "-DENABLE_WASMTIME=OFF",
                    "-DUSE_BUNDLED_GETTEXT=OFF",
                    "-DUSE_BUNDLED_LIBICONV=OFF",
                ]
            ),
        }

    def _bundled_dependency_flags(self):
        deps_prefix = os.path.join(self.source_folder, ".deps", "usr")
        deps_include = os.path.join(deps_prefix, "include")
        deps_lib = os.path.join(deps_prefix, "lib")
        return [
            f'-DLUV_INCLUDE_DIR="{deps_include}"',
            f'-DLUV_LIBRARY="{os.path.join(deps_lib, "libluv.a")}"',
            f'-DLIBUV_INCLUDE_DIR="{deps_include}"',
            f'-DLIBUV_LIBRARY="{os.path.join(deps_lib, "libuv.a")}"',
            f'-DLPEG_LIBRARY="{os.path.join(deps_lib, "liblpeg.a")}"',
            f'-DTREESITTER_INCLUDE_DIR="{deps_include}"',
            f'-DTREESITTER_LIBRARY="{os.path.join(deps_lib, "libtree-sitter.a")}"',
            f'-DUNIBILIUM_INCLUDE_DIR="{deps_include}"',
            f'-DUNIBILIUM_LIBRARY="{os.path.join(deps_lib, "libunibilium.a")}"',
            f'-DUTF8PROC_INCLUDE_DIR="{deps_include}"',
            f'-DUTF8PROC_LIBRARY="{os.path.join(deps_lib, "libutf8proc.a")}"',
            f'-DLUAJIT_INCLUDE_DIR="{os.path.join(deps_include, "luajit-2.1")}"',
            f'-DLUAJIT_LIBRARY="{os.path.join(deps_lib, "libluajit-5.1.a")}"',
        ]

    def _iconv_flags(self):
        iconv = self.dependencies["libiconv"].cpp_info
        flags = []
        if iconv.includedirs:
            flags.append(f'-DICONV_INCLUDE_DIR="{iconv.includedirs[0]}"')
        iconv_library = self._dependency_library(iconv, "iconv")
        charset_library = self._dependency_library(iconv, "charset")
        if iconv_library:
            flags.append(f'-DICONV_LIBRARY="{iconv_library}"')
        if charset_library:
            flags.append(f'-DCHARSET_LIBRARY="{charset_library}"')
        return flags

    def _dependency_library(self, cpp_info, name):
        candidates = []
        for libdir in cpp_info.libdirs:
            candidates.extend(
                [
                    os.path.join(libdir, f"lib{name}.a"),
                    os.path.join(libdir, f"lib{name}.so"),
                    os.path.join(libdir, f"{name}.lib"),
                ]
            )
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        return ""

    def _patch_bundled_deps(self):
        deps_txt = os.path.join(self.source_folder, "cmake.deps/deps.txt")
        replace_in_file(
            self,
            deps_txt,
            "https://github.com/",
            "https://gh-proxy.com/https://github.com/",
        )

        luajit_cmake = os.path.join(self.source_folder, "cmake.deps/cmake/BuildLuajit.cmake")
        replace_in_file(
            self,
            luajit_cmake,
            "CC=${DEPS_C_COMPILER} PREFIX=${DEPS_INSTALL_DIR}",
            'CC=${DEPS_C_COMPILER} "TARGET_AR=${CMAKE_AR} rcus" '
            '"TARGET_STRIP=${CMAKE_STRIP}" PREFIX=${DEPS_INSTALL_DIR}',
        )

        find_iconv = os.path.join(self.source_folder, "cmake/FindIconv.cmake")
        replace_in_file(
            self,
            find_iconv,
            "if(ICONV_LIBRARY)\n  target_link_libraries(iconv INTERFACE ${ICONV_LIBRARY})\nendif()\n",
            "if(ICONV_LIBRARY)\n  target_link_libraries(iconv INTERFACE ${ICONV_LIBRARY})\nendif()\n"
            "if(CHARSET_LIBRARY)\n  target_link_libraries(iconv INTERFACE ${CHARSET_LIBRARY})\nendif()\n",
        )

        main_cmake = os.path.join(self.source_folder, "src/nvim/CMakeLists.txt")
        replace_in_file(
            self,
            main_cmake,
            "  if(WIN32)\n    target_link_libraries(nlua0 PUBLIC ${LUAJIT_LIBRARY})\n  endif()\n",
            "  if(WIN32 OR CMAKE_SYSTEM_NAME MATCHES \"OHOS|HarmonyOS\")\n"
            "    target_link_libraries(nlua0 PUBLIC ${LUAJIT_LIBRARY})\n"
            "  endif()\n",
        )

        libuv_patch = os.path.join(
            self.source_folder,
            "cmake.deps/cmake/PatchLibuvOhos.cmake",
        )
        save(
            self,
            libuv_patch,
            r'''
if(NOT DEFINED SOURCE_DIR)
  message(FATAL_ERROR "SOURCE_DIR is required")
endif()

set(internal_h "${SOURCE_DIR}/src/unix/internal.h")
file(READ "${internal_h}" internal_content)
string(REPLACE
  "#if defined(__linux__) || (defined(__FreeBSD__) && __FreeBSD_version >= 1301000)"
  "#if (defined(__linux__) && !defined(__OHOS__)) || (defined(__FreeBSD__) && __FreeBSD_version >= 1301000)"
  internal_content
  "${internal_content}")
file(WRITE "${internal_h}" "${internal_content}")

set(core_c "${SOURCE_DIR}/src/unix/core.c")
file(READ "${core_c}" core_content)
string(REPLACE
  "#ifdef __linux__\n  cpu_set_t set;"
  "#if defined(__linux__) && !defined(__OHOS__)\n  cpu_set_t set;"
  core_content
  "${core_content}")
file(WRITE "${core_c}" "${core_content}")

set(udp_c "${SOURCE_DIR}/src/unix/udp.c")
file(READ "${udp_c}" udp_content)
string(REPLACE
  "#if defined(__linux__) || defined(__FreeBSD__) || defined(__APPLE__)"
  "#if (defined(__linux__) && !defined(__OHOS__)) || defined(__FreeBSD__) || defined(__APPLE__)"
  udp_content
  "${udp_content}")
string(REPLACE
  "#if defined(__linux__) || defined(__FreeBSD__) || defined(__APPLE__) || \\\n  (defined(__sun__) && defined(MSG_WAITFORONE)) || defined(__QNX__)"
  "#if (defined(__linux__) && !defined(__OHOS__)) || defined(__FreeBSD__) || defined(__APPLE__) || \\\n  (defined(__sun__) && defined(MSG_WAITFORONE)) || defined(__QNX__)"
  udp_content
  "${udp_content}")
file(WRITE "${udp_c}" "${udp_content}")

set(cmake_lists "${SOURCE_DIR}/CMakeLists.txt")
file(READ "${cmake_lists}" cmake_content)
string(REPLACE
  "if(APPLE OR CMAKE_SYSTEM_NAME MATCHES \"Android|Linux\")"
  "if(APPLE OR CMAKE_SYSTEM_NAME MATCHES \"Android|Linux|HarmonyOS\")"
  cmake_content
  "${cmake_content}")
string(REPLACE
  "if(CMAKE_SYSTEM_NAME STREQUAL \"Linux\")"
  "if(CMAKE_SYSTEM_NAME MATCHES \"Linux|HarmonyOS\")"
  cmake_content
  "${cmake_content}")
file(WRITE "${cmake_lists}" "${cmake_content}")
'''.lstrip(),
        )

        libuv_cmake = os.path.join(self.source_folder, "cmake.deps/cmake/BuildLibuv.cmake")
        replace_in_file(
            self,
            libuv_cmake,
            "  DOWNLOAD_DIR ${DEPS_DOWNLOAD_DIR}/libuv\n",
            "  DOWNLOAD_DIR ${DEPS_DOWNLOAD_DIR}/libuv\n"
            "  PATCH_COMMAND ${CMAKE_COMMAND} -DSOURCE_DIR=<SOURCE_DIR> "
            "-P ${CMAKE_CURRENT_LIST_DIR}/PatchLibuvOhos.cmake\n",
        )

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("This spike recipe is intended for OHOS only")
        self._patch_bundled_deps()

        flags = self._build_flags()
        make_args = (
            f'USE_BUNDLED=1 CMAKE_BUILD_TYPE="{self.settings.build_type}" '
            f'CMAKE_EXTRA_FLAGS=\'{flags["cmake_extra"]}\' '
            f'DEPS_CMAKE_FLAGS=\'{flags["deps_cmake"]}\''
        )
        build_env = "CMAKE_BUILD_PARALLEL_LEVEL=1"

        self.run(f"{build_env} make -j1 deps {make_args}", cwd=self.source_folder)
        self._sign_elf_tree(
            os.path.join(self.source_folder, ".deps", "usr", "bin"),
            os.path.join(self.source_folder, ".deps", "usr", "lib"),
        )

        self.run(f"{build_env} make -j1 nvim {make_args}", cwd=self.source_folder)
        self._sign_elf_tree(
            os.path.join(self.source_folder, "build", "bin"),
            os.path.join(self.source_folder, "build", "lib"),
        )

        runtime = os.path.join(self.source_folder, "runtime")
        nvim = os.path.join(self.source_folder, "build", "bin", "nvim")
        self.run(f'VIMRUNTIME="{runtime}" "{nvim}" --version', cwd=self.source_folder)
        self.run(
            f'VIMRUNTIME="{runtime}" "{nvim}" --headless -u NONE -i NONE '
            f"'+lua print(vim.version().major)' +qa",
            cwd=self.source_folder,
        )

    def package(self):
        self.run('cmake --install "build"', cwd=self.source_folder)
        self._sign_elf_tree(
            os.path.join(self.package_folder, "bin"),
            os.path.join(self.package_folder, "lib"),
            os.path.join(self.package_folder, "lib64"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        runtime = os.path.join(self.package_folder, "share", "nvim", "runtime")
        self.runenv_info.define_path("VIMRUNTIME", runtime)
        self.runenv_info.define_path("NVIM_RUNTIME", runtime)
