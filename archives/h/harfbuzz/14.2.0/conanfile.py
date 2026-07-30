#!/usr/bin/env python3
"""Conan recipe for HarfBuzz 14.2.0 (Meson)."""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class HarfbuzzConan(ConanFile):
    name = "harfbuzz"
    version = "14.2.0"
    description = "OpenType text shaping engine"
    license = "MIT"
    homepage = "https://harfbuzz.github.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("freetype/2.14.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_tool(self, tool, llvm=True):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c", "")
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        compiler_name = os.path.basename(compiler_path)
        version_suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
            else ""
        )

        candidates = [compiler_executables.get(tool)]
        if compiler_dir:
            if llvm:
                candidates.extend(
                    [
                        os.path.join(
                            compiler_dir, f"llvm-{tool}{version_suffix}"
                        ),
                        os.path.join(compiler_dir, f"llvm-{tool}"),
                    ]
                )
            candidates.append(os.path.join(compiler_dir, tool))
        if llvm and version_suffix:
            candidates.append(f"llvm-{tool}{version_suffix}")
        if llvm:
            candidates.append(f"llvm-{tool}")
        candidates.append(tool)

        for candidate in candidates:
            if candidate:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved

        raise ConanInvalidConfiguration(
            f"required build tool was not found: {tool}"
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        toolchain.project_options.update(
            {
                "libdir": "lib",
                "glib": "disabled",
                "gobject": "disabled",
                "cairo": "disabled",
                "chafa": "disabled",
                "png": "disabled",
                "zlib": "disabled",
                "icu": "disabled",
                "graphite": "disabled",
                "graphite2": "disabled",
                "freetype": "enabled",
                "fontations": "disabled",
                "raster": "disabled",
                "vector": "enabled",
                "gpu": "disabled",
                "gpu_demo": "disabled",
                "subset": "enabled",
                "tests": "enabled",
                "introspection": "disabled",
                "docs": "disabled",
                "utilities": "disabled",
                "benchmark": "disabled",
            }
        )
        toolchain.generate()

        if self.settings.os in ("Linux", "OHOS"):
            # MesonToolchain omits archive tools. Use the same resolver as the
            # test and signing tools so clang-15 also selects llvm-*-15.
            ar = self._resolve_tool("ar")
            ranlib = self._resolve_tool("ranlib")

            native_file = os.path.join(
                self.generators_folder, "conan_meson_native.ini"
            )
            if os.path.isfile(native_file):
                with open(native_file, encoding="utf-8") as handle:
                    content = handle.read()
                if "\nar =" not in content and "[binaries]" in content:
                    archive_tools = (
                        "[binaries]\nar = '{}'\nranlib = '{}'\n".format(
                            ar, ranlib
                        )
                    )
                    content = content.replace("[binaries]\n", archive_tools, 1)
                    with open(native_file, "w", encoding="utf-8") as handle:
                        handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if self.settings.os in ("Linux", "OHOS"):
            # OHOS Python's posix_spawn does not resolve bare tool names.
            test_env = Environment()
            test_env.define("NM", self._resolve_tool("nm"))
            test_env.define("OBJDUMP", self._resolve_tool("objdump"))
            with test_env.vars(self).apply():
                meson.test()
        else:
            meson.test()

    def package(self):
        Meson(self).install()
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_libraries = glob.glob(
            os.path.join(libdir, "**", "*.so"), recursive=True
        )
        shared_libraries += glob.glob(
            os.path.join(libdir, "**", "*.so.*"), recursive=True
        )
        objcopy = self._resolve_tool("objcopy")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        for library in sorted(set(shared_libraries)):
            if os.path.islink(library):
                continue
            remove_codesign = shlex.join(
                [objcopy, "--remove-section", ".codesign", library]
            )
            self.run(
                # A library that has not been signed yet has no .codesign section.
                f"{remove_codesign} 2>/dev/null || true"
            )
            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        library,
                        "-outFile",
                        library,
                        "-selfSign",
                        "1",
                    ]
                )
            )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "harfbuzz")

        core = self.cpp_info.components["harfbuzz"]
        core.libs = ["harfbuzz"]
        core.includedirs = ["include/harfbuzz"]
        core.requires = ["freetype::freetype"]
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            core.system_libs = ["pthread", "m"]
        core.set_property("cmake_target_name", "harfbuzz::harfbuzz")
        core.set_property("pkg_config_name", "harfbuzz")

        subset = self.cpp_info.components["subset"]
        subset.libs = ["harfbuzz-subset"]
        subset.includedirs = ["include/harfbuzz"]
        subset.requires = ["harfbuzz"]
        subset.set_property("cmake_target_name", "harfbuzz::subset")
        subset.set_property("pkg_config_name", "harfbuzz-subset")

        vector = self.cpp_info.components["vector"]
        vector.libs = ["harfbuzz-vector"]
        vector.includedirs = ["include/harfbuzz"]
        vector.requires = ["harfbuzz"]
        vector.set_property("cmake_target_name", "harfbuzz::vector")
        vector.set_property("pkg_config_name", "harfbuzz-vector")
