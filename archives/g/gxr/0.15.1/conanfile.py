#!/usr/bin/env python3
"""Conan recipe for gxr 0.15.1 on HarmonyOS PC (Meson)."""

import glob
import os
import shlex
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    save,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GxrConan(ConanFile):
    name = "gxr"
    version = "0.15.1"
    description = "GLib/GObject abstraction for OpenXR and OpenVR APIs"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xrdesktop/gxr"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "gulkan/0.15.1", transitive_headers=True, transitive_libs=True
        )
        self.requires(
            "gtk/3.24.43", transitive_headers=True, transitive_libs=True
        )
        self.requires(
            "glib/2.84.0.1", transitive_headers=True, transitive_libs=True
        )
        self.requires(
            "json-glib/1.10.6", transitive_headers=True, transitive_libs=True
        )
        self.requires(
            "harfbuzz/14.2.0.1.1.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("pkgconf/3.0.5")
        self.tool_requires("glslang/vulkan-sdk-1.3.290.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._write_gdk_pkg_config_alias()

        toolchain = MesonToolchain(self)
        toolchain.project_options.update(
            {
                "api_doc": False,
                "backends": [],
                "default_library": (
                    "shared" if bool(self.options.shared) else "static"
                ),
                "introspection": False,
                "wrap_mode": "nodownload",
            }
        )
        pkgconf_folder = self.dependencies.build["pkgconf"].package_folder
        pkgconf = self._find_runnable_tool(
            ("pkgconf", "pkg-config"),
            os.path.join(pkgconf_folder, "bin", "pkgconf"),
        )
        if pkgconf:
            toolchain.binaries["pkg-config"] = pkgconf
        glslang_folder = self.dependencies.build["glslang"].package_folder
        glslang = self._find_runnable_tool(
            ("glslangValidator",),
            os.path.join(glslang_folder, "bin", "glslangValidator"),
        )
        if glslang:
            toolchain.binaries["glslangValidator"] = glslang
        resource_compiler = self._prepare_resource_compiler()
        toolchain.binaries["glib-compile-resources"] = resource_compiler
        self._set_binutils(toolchain)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info(
                "Cross-building: the library, examples, upstream tests, and "
                "consumer are compiled; runtime assertions execute whenever "
                "the target can run"
            )
        else:
            # CI builds natively on HarmonyOS, so Meson's test process needs
            # the shared libraries supplied by Conan host requirements.
            with VirtualRunEnv(self).vars().apply():
                if str(self.settings.os) == "OHOS":
                    runtime = Environment()
                    runtime_dir = self._prepare_native_test_runtime()
                    if runtime_dir:
                        runtime.prepend_path("LD_LIBRARY_PATH", runtime_dir)
                    with runtime.vars(self).apply():
                        meson.test()
                else:
                    meson.test()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        Meson(self).install()
        rm(
            self,
            "*",
            os.path.join(self.package_folder, "bin"),
            recursive=True,
        )
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        self._self_sign_elfs()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gxr")
        self.cpp_info.set_property("cmake_target_name", "gxr::gxr")
        self.cpp_info.set_property("pkg_config_name", "gxr-0.15")
        self.cpp_info.libs = ["gxr-0.15"]
        self.cpp_info.includedirs = [os.path.join("include", "gxr-0.15")]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl"]

    def _write_gdk_pkg_config_alias(self):
        """Expose gtk's GDK implementation under upstream's gdk-3.0 name."""
        pc_path = os.path.join(self.generators_folder, "gdk-3.0.pc")
        with open(pc_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "Name: GDK\n"
                "Description: GDK 3 provided by the Conan gtk package\n"
                "Version: 3.24.43\n"
                "Requires: gtk+-3.0\n"
                "Libs:\n"
                "Cflags:\n"
            )

    def _set_binutils(self, toolchain):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or ""
        bindir = os.path.dirname(compiler) if os.sep in compiler else ""
        if not bindir:
            return
        for key, names in (
            ("ar", ("llvm-ar", "ar")),
            ("ranlib", ("llvm-ranlib", "ranlib")),
        ):
            for name in names:
                candidate = os.path.join(bindir, name)
                if os.path.isfile(candidate):
                    toolchain.binaries[key] = candidate
                    break

    def _prepare_resource_compiler(self):
        """Prepare a runnable GLib resource compiler for the build machine."""
        glib = self.dependencies["glib"]
        packaged = os.path.join(
            glib.package_folder, "bin", "glib-compile-resources"
        )
        if not os.path.isfile(packaged):
            raise RuntimeError(f"GLib resource compiler missing: {packaged}")

        if cross_building(self):
            resource_compiler = self._find_runnable_tool(
                ("glib-compile-resources",), packaged
            )
            if not resource_compiler:
                raise RuntimeError("No runnable glib-compile-resources found")
            return resource_compiler

        tools_folder = os.path.join(self.build_folder, "conan-native-tools")
        os.makedirs(tools_folder, exist_ok=True)
        staged = os.path.join(tools_folder, "glib-compile-resources")
        shutil.copyfile(packaged, staged)
        os.chmod(staged, 0o755)
        if str(self.settings.os) == "OHOS":
            self._resign_ohos_elf(staged)

        wrapper = staged + ".sh"
        glib_libdir = os.path.join(glib.package_folder, "lib")
        save(
            self,
            wrapper,
            "#!/bin/sh\n"
            f"LD_LIBRARY_PATH={shlex.quote(glib_libdir)}"
            "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\n"
            "export LD_LIBRARY_PATH\n"
            f"exec {shlex.quote(staged)} \"$@\"\n",
        )
        os.chmod(wrapper, 0o755)
        return wrapper

    def _prepare_native_test_runtime(self):
        """Provide a freshly signed JSON-GLib SONAME for native OHOS tests."""
        json_glib = self.dependencies["json-glib"]
        shared = json_glib.options.get_safe("shared")
        if shared is not None and not bool(shared):
            return None
        packaged = os.path.join(
            json_glib.package_folder, "lib", "libjson-glib-1.0.so.0"
        )
        if not os.path.lexists(packaged):
            raise RuntimeError(f"JSON-GLib runtime library missing: {packaged}")
        source = os.path.realpath(packaged)
        package_root = os.path.realpath(json_glib.package_folder)
        if (
            not os.path.isfile(source)
            or os.path.commonpath((source, package_root)) != package_root
        ):
            raise RuntimeError(f"Unsafe JSON-GLib runtime library: {packaged}")

        runtime_dir = tempfile.mkdtemp(
            prefix="gxr-native-runtime-", dir=self.build_folder
        )
        staged = os.path.join(runtime_dir, "libjson-glib-1.0.so.0")
        if os.path.lexists(staged):
            os.remove(staged)
        shutil.copyfile(source, staged)
        os.chmod(staged, 0o755)
        self._resign_ohos_elf(staged)
        return runtime_dir

    def _resign_ohos_elf(self, path):
        """Force re-sign a task-private ELF for the HarmonyOS loader."""
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or ""
        compiler_dir = os.path.dirname(compiler) if os.sep in compiler else ""
        objcopy_candidates = (
            os.path.join(compiler_dir, "llvm-objcopy") if compiler_dir else "",
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        )
        objcopy = next(
            (item for item in objcopy_candidates if os.path.isfile(item)), None
        )
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy_dir = os.path.dirname(os.path.realpath(objcopy)) if objcopy else ""
        readelf_candidates = (
            os.path.join(compiler_dir, "llvm-readelf") if compiler_dir else "",
            os.path.join(objcopy_dir, "llvm-readelf") if objcopy_dir else "",
            "/data/service/hnp/bin/llvm-readelf",
            shutil.which("llvm-readelf") or "",
            shutil.which("readelf") or "",
        )
        readelf = next(
            (item for item in readelf_candidates if os.path.isfile(item)), None
        )
        if not objcopy or not readelf or not os.path.isfile(signer):
            raise RuntimeError("OHOS ELF signing tools are required")

        temporary = path + ".unsigned"
        if os.path.lexists(temporary):
            raise RuntimeError(f"Stale ELF signing output beside: {path}")
        try:
            shutil.copyfile(path, temporary)
            stripped = subprocess.run(
                [objcopy, "--remove-section", ".codesign", temporary],
                capture_output=True,
                timeout=60,
                check=False,
            )
            if stripped.returncode != 0:
                raise RuntimeError(f"Failed to strip old ELF signature: {path}")
            result = subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    temporary,
                    "-outFile",
                    temporary,
                    "-selfSign",
                    "1",
                ],
                capture_output=True,
                timeout=60,
                check=False,
            )
            if result.returncode != 0 or not os.path.isfile(temporary):
                raise RuntimeError(f"Failed to self-sign OHOS ELF: {path}")
            sections = subprocess.run(
                [readelf, "-SW", temporary],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if sections.returncode != 0 or sections.stdout.count(".codesign") != 1:
                raise RuntimeError(f"Invalid signed OHOS ELF: {path}")
            os.chmod(temporary, 0o755)
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.remove(temporary)

    def _self_sign_elfs(self):
        if str(self.settings.os) != "OHOS":
            return
        targets = glob.glob(os.path.join(self.package_folder, "lib", "*.so*"))
        targets.extend(
            glob.glob(os.path.join(self.package_folder, "bin", "*"))
        )
        signed = 0
        for path in targets:
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            self._resign_ohos_elf(path)
            signed += 1
        self.output.info(f"self-signed {signed} ELF file(s) in package")

    @staticmethod
    def _find_runnable_tool(names, packaged_candidate):
        candidates = []
        for name in names:
            candidate = shutil.which(name, path=os.defpath)
            if candidate:
                candidates.append(candidate)
        candidates.append(packaged_candidate)
        for candidate in candidates:
            if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
                continue
            if GxrConan._tool_runs(candidate):
                return candidate
        return None

    @staticmethod
    def _tool_runs(candidate, env=None):
        if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
            return False
        try:
            result = subprocess.run(
                [candidate, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
                env=env,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0
