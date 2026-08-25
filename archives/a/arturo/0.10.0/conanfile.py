#!/usr/bin/env python3
"""Conan recipe for Arturo 0.10.0 (full build) for HarmonyOS PC (arm64).

Arturo is a programming language and bytecode VM built with Nim.
Nim compiler is pulled via tool_requires("nim/2.2.8") — no system PATH dependency.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    copy,
)
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class ArturoConan(ConanFile):
    name = "arturo"
    version = "0.10.0"
    description = "Arturo Programming Language + Bytecode VM compiler"
    license = "MIT"
    homepage = "https://arturo-lang.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")
        self.requires("openssl/3.5.6.1.1")
        self.requires("sqlite3/3.49.1")
        self.requires("pcre/8.45")

    def build_requirements(self):
        self.tool_requires("nim/2.2.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # Dependency helpers
    # ------------------------------------------------------------------

    def _get_deps_include_dir(self):
        """Collect dependency include directories from Conan dependencies."""
        deps_inc = os.path.join(self.build_folder, "deps_prefix", "include")
        os.makedirs(deps_inc, exist_ok=True)
        for dep_name, dep in self.dependencies.items():
            if dep.cpp_info:
                for inc in dep.cpp_info.includedirs:
                    if os.path.isdir(inc):
                        for item in os.listdir(inc):
                            s = os.path.join(inc, item)
                            d = os.path.join(deps_inc, item)
                            if os.path.isdir(s):
                                shutil.copytree(s, d, dirs_exist_ok=True)
                            else:
                                shutil.copy2(s, d)
        return deps_inc

    def _get_deps_lib_dir(self):
        """Collect dependency library directories from Conan dependencies."""
        deps_lib = os.path.join(self.build_folder, "deps_prefix", "lib")
        os.makedirs(deps_lib, exist_ok=True)
        for dep_name, dep in self.dependencies.items():
            if dep.cpp_info:
                for lib_name in dep.cpp_info.libs:
                    for libpath in dep.cpp_info.libdirs:
                        for ext in (".a", ".so"):
                            fname = f"lib{lib_name}{ext}"
                            s = os.path.join(libpath, fname)
                            if os.path.exists(s):
                                shutil.copy2(s, os.path.join(deps_lib, fname))
        return deps_lib

    def _replace_bundled_libs(self, src_dir):
        """Replace bundled OpenSSL and PCRE static libraries with Conan-managed versions."""
        ossl_dest = os.path.join(src_dir, "src/deps/openssl/linux/arm64")
        pcre_dest = os.path.join(src_dir, "src/deps/pcre/linux/arm64")

        for dep_name, dep in self.dependencies.items():
            dep_short = str(dep_name).split("/")[0].lower()
            self.output.info(
                f"Processing dep: {dep_name} (short={dep_short}), "
                f"libdirs={dep.cpp_info.libdirs}, libs={dep.cpp_info.libs}"
            )

            if dep_short == "openssl" and os.path.isdir(ossl_dest):
                for libpath in dep.cpp_info.libdirs:
                    if os.path.isdir(libpath):
                        for fname in os.listdir(libpath):
                            if fname.endswith(".a") and (
                                "ssl" in fname or "crypto" in fname
                            ):
                                s = os.path.join(libpath, fname)
                                shutil.copy2(s, os.path.join(ossl_dest, fname))
                                self.output.info(
                                    f"Replaced {fname} with OHOS version from {s}"
                                )

            elif dep_short == "pcre" and os.path.isdir(pcre_dest):
                for libpath in dep.cpp_info.libdirs:
                    if os.path.isdir(libpath):
                        for fname in os.listdir(libpath):
                            if fname.endswith(".a") and "pcre" in fname:
                                s = os.path.join(libpath, fname)
                                shutil.copy2(s, os.path.join(pcre_dest, fname))
                                self.output.info(
                                    f"Replaced {fname} with OHOS version from {s}"
                                )

    # ------------------------------------------------------------------
    # Conan lifecycle
    # ------------------------------------------------------------------

    def generate(self):
        """Generate build environment — Nim paths from tool_requires."""
        nim_dep = self.dependencies.build["nim"]
        nim_lib = nim_dep.cpp_info.libdirs[0]
        nim_bin_dir = nim_dep.cpp_info.bindirs[0]

        deps_inc = self._get_deps_include_dir()
        deps_lib = self._get_deps_lib_dir()

        env = Environment()
        env.define("NIM_LIB_PATH", nim_lib)
        env.define("DEPS_INCLUDE_DIR", deps_inc)
        env.define("DEPS_LIB_DIR", deps_lib)
        env.define("NIM_BIN", os.path.join(nim_bin_dir, "nim"))
        # Ensure nim binary dir is in PATH for inner gorgeEx calls in build.nims
        env.define("PATH", nim_bin_dir)
        env.vars(self).save_script("arturo_build_env")

    def build(self):
        apply_conandata_patches(self)

        # R32: Support both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        src_dir = self.source_folder

        # Nim binary and stdlib from tool_requires("nim/2.2.8")
        nim_dep = self.dependencies.build["nim"]
        nim_bin = os.path.join(nim_dep.cpp_info.bindirs[0], "nim")
        nim_lib = nim_dep.cpp_info.libdirs[0]

        # Replace bundled OpenSSL/PCRE with Conan-managed versions
        self._replace_bundled_libs(src_dir)

        # Build using Nim build system.
        nim_flags = [
            f'--lib:"{nim_lib}"',
            f'--path:"{nim_lib}"',
            f'--path:"{nim_lib}/core"',
            f'--path:"{nim_lib}/deprecated/pure"',
            f'--path:"{nim_lib}/experimental"',
            f'--path:"{nim_lib}/impure"',
            f'--path:"{nim_lib}/impure/nre/private"',
            f'--path:"{nim_lib}/packages/docutils"',
            f'--path:"{nim_lib}/posix"',
            f'--path:"{nim_lib}/pure"',
            f'--path:"{nim_lib}/pure/collections"',
            f'--path:"{nim_lib}/pure/concurrency"',
            f'--path:"{nim_lib}/pure/includes"',
            f'--path:"{nim_lib}/pure/ioselects"',
            f'--path:"{nim_lib}/pure/unidecode"',
            f'--path:"{nim_lib}/std"',
            f'--path:"{nim_lib}/std/private"',
            f'--path:"{nim_lib}/system"',
            f'--path:"{nim_lib}/system/mm"',
            f'--path:"{nim_lib}/wrappers"',
            f'--path:"{nim_lib}/wrappers/linenoise"',
            f'--cc:clang',
        ]
        nim_flags_str = " ".join(nim_flags)

        self.run(
            f'"{nim_bin}" {nim_flags_str} "{src_dir}/build.nims" build '
            f"--mode:full --os:linux --arch:arm64 --log",
            cwd=src_dir,
        )

        # Sign the binary (HarmonyOS requirement)
        sign_tool = os.environ.get("SIGN_TOOL") or shutil.which("binary-sign-tool")
        if sign_tool and os.path.exists(sign_tool):
            self.run(
                f'"{sign_tool}" sign -inFile "{src_dir}/bin/arturo" '
                f'-outFile "{src_dir}/bin/arturo" -selfSign 1',
                cwd=src_dir,
            )

    def package(self):
        copy(
            self,
            "arturo",
            src=os.path.join(self.source_folder, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
