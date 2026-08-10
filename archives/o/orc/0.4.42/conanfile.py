#!/usr/bin/env python3
"""Meson-based Conan recipe for orc 0.4.42, the Optimized Inner Loops Runtime Compiler."""

import os

from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class OrcConan(ConanFile):
    name = "orc"
    version = "0.4.42"
    description = "Optimized Inner Loops Runtime Compiler"
    license = "BSD-2-Clause"
    homepage = "https://gitlab.freedesktop.org/gstreamer/orc"
    url = "https://gitlab.freedesktop.org/gstreamer/orc"

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

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["benchmarks"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["hotdoc"] = "disabled"
        tc.project_options["orc-test"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["tools"] = "disabled"
        tc.generate()
        self._inject_windows_c_args()
        self._inject_archive_tools()

    def build(self):
        self._set_ohos_tmpdir()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        self._set_ohos_tmpdir()
        Meson(self).install()

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = libs or ["orc-0.4"]
        self.cpp_info.includedirs = ["include/orc-0.4", "include"]
        self.cpp_info.set_property("cmake_file_name", "orc")
        self.cpp_info.set_property("cmake_target_name", "orc::orc")
        self.cpp_info.set_property("pkg_config_name", "orc-0.4")
        if not self.options.shared:
            self.cpp_info.defines.append("ORC_STATIC_COMPILATION")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _inject_archive_tools(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        archive_tool = compiler_executables.get("ar")
        ranlib_tool = compiler_executables.get("ranlib")

        if not archive_tool:
            c_compiler = compiler_executables.get("c") or ""
            bindir = os.path.dirname(c_compiler)
            for candidate_name in ("llvm-ar", "ar"):
                candidate = os.path.join(bindir, candidate_name) if bindir else ""
                if candidate and os.path.isfile(candidate):
                    archive_tool = candidate
                    break
            if bindir and not ranlib_tool:
                for candidate_name in ("llvm-ranlib", "ranlib"):
                    candidate = os.path.join(bindir, candidate_name)
                    if os.path.isfile(candidate):
                        ranlib_tool = candidate
                        break

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not archive_tool or not os.path.isfile(native_file):
            return

        with open(native_file, encoding="utf-8") as native:
            content = native.read()
        if "\nar =" in content or "[binaries]" not in content:
            return

        insert = "[binaries]\nar = '{}'\n".format(archive_tool.replace("\\", "/"))
        if ranlib_tool:
            insert += "ranlib = '{}'\n".format(ranlib_tool.replace("\\", "/"))
        content = content.replace("[binaries]\n", insert, 1)
        with open(native_file, "w", encoding="utf-8") as native:
            native.write(content)

    def _set_ohos_tmpdir(self):
        if str(self.settings.os) != "OHOS":
            return

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _inject_windows_c_args(self):
        if self.settings.os != "Windows":
            return

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return

        with open(native_file, encoding="utf-8") as native:
            content = native.read()
        option = "'-D_WIN32_WINNT=0x0600'"
        if option in content:
            return

        if "\nc_args = " in content:
            # Preserve Conan's architecture flags while adding the Windows API baseline.
            content = content.replace("\nc_args = ", f"\nc_args = [{option}] + ", 1)
        elif "[built-in options]\n" in content:
            content = content.replace(
                "[built-in options]\n", f"[built-in options]\nc_args = [{option}]\n", 1
            )
        else:
            content += f"\n[built-in options]\nc_args = [{option}]\n"

        with open(native_file, "w", encoding="utf-8") as native:
            native.write(content)
