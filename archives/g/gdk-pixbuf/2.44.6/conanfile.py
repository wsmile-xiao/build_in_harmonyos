#!/usr/bin/env python3
"""Conan recipe - gdk-pixbuf 2.44.6 (Meson)."""

import glob
import json
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GdkPixbufConan(ConanFile):
    name = "gdk-pixbuf"
    version = "2.44.6"
    description = "Image loading and pixel buffer library for GTK applications"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gdk-pixbuf"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires(
            "glib/2.84.0.1", transitive_headers=True, transitive_libs=True
        )
        self.requires(
            "libpng/1.6.58", transitive_headers=True, transitive_libs=True
        )
        self.requires(
            "libjpeg-turbo/3.2.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libtiff/4.7.2", transitive_headers=True, transitive_libs=True
        )
        self.requires(
            "zlib/1.3.1.1", transitive_headers=True, transitive_libs=True
        )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        staged_source = os.path.expanduser(
            "~/Download/gdk-pixbuf-2.44.6.tar.xz"
        )
        if os.path.isfile(staged_source):
            check_sha256(self, staged_source, sources["sha256"])
            unzip(self, staged_source, strip_root=True)
            return
        try:
            get(self, **sources, strip_root=True)
        except Exception as error:
            if not mirror_url:
                raise
            self.output.warning(f"Primary source failed ({error}), trying mirror")
            get(
                self,
                url=mirror_url,
                sha256=sources["sha256"],
                strip_root=True,
            )

    def generate(self):
        PkgConfigDeps(self).generate()
        glib_tools = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(glib_tools)
        self._create_pkg_config_alias(
            "gmodule-2.0.pc", "gmodule-no-export-2.0.pc", "gmodule-no-export-2.0"
        )
        toolchain = MesonToolchain(self)
        toolchain.project_options.update(
            {
                "wrap_mode": "nodownload",
                "default_library": "shared" if self.options.shared else "static",
                "png": "enabled",
                "jpeg": "enabled",
                "tiff": "enabled",
                "gif": "enabled",
                "glycin": "disabled",
                "android": "disabled",
                "others": "disabled",
                "builtin_loaders": ["all"],
                "gio_sniffing": "false",
                "thumbnailer": "disabled",
                "introspection": "disabled",
                "documentation": "false",
                "man": "false",
                "tests": "true",
                "installed_tests": "false",
            }
        )
        toolchain.generate()
        self._inject_meson_tools()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            if self.options.shared and self.settings.os == "OHOS":
                meson.build(target="gdk_pixbuf-2.0")
                self._create_shared_lib_aliases(
                    os.path.join(self.build_folder, "gdk-pixbuf")
                )
            meson.build()
            if cross_building(self):
                self.output.info(
                    "Cross-building: upstream OHOS test binaries are run on device"
                )
            else:
                meson.test()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        if self.settings.os == "OHOS":
            if self.options.shared:
                self._create_shared_lib_aliases(
                    os.path.join(self.package_folder, "lib")
                )
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["gdk_pixbuf-2.0"]
        self.cpp_info.includedirs = ["include/gdk-pixbuf-2.0", "include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = [
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "libpng::libpng",
            "libjpeg-turbo::libjpeg-turbo",
            "libtiff::libtiff",
            "zlib::zlib",
        ]
        self.cpp_info.set_property("cmake_file_name", "gdk-pixbuf")
        self.cpp_info.set_property(
            "cmake_target_name", "gdk-pixbuf::gdk-pixbuf"
        )
        self.cpp_info.set_property("pkg_config_name", "gdk-pixbuf-2.0")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    def _build_environment(self):
        environment = Environment()
        temporary_directory = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary_directory, exist_ok=True)
        environment.define_path("TMPDIR", temporary_directory)
        environment.define_path("TMP", temporary_directory)
        environment.define_path("TEMP", temporary_directory)
        glib_folder = self.dependencies["glib"].package_folder
        environment.prepend_path("PATH", os.path.join(glib_folder, "bin"))
        environment.prepend_path("PATH", self._glib_tools_folder())
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        environment.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder, "gdk-pixbuf")
        )
        user_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
        if os.path.isdir(user_bin):
            environment.prepend_path("PATH", user_bin)
        return environment

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_glib_build_tools(self):
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)

        for tool in ("glib-genmarshal", "glib-mkenums"):
            source = os.path.join(glib_bin, tool)
            if not os.path.isfile(source):
                raise FileNotFoundError(f"GLib build tool is missing: {source}")
            self._build_python_tool_wrapper(tool, source)

        for tool in ("glib-compile-resources", "gobject-query"):
            source = os.path.join(glib_bin, tool)
            if not os.path.isfile(source):
                raise FileNotFoundError(f"GLib build tool is missing: {source}")
            destination = os.path.join(tools_folder, tool)
            shutil.copyfile(source, destination)
            os.chmod(destination, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(destination)
        return tools_folder

    def _build_python_tool_wrapper(self, name, script):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c")
        if not compiler:
            raise RuntimeError("C compiler not found in tools.build:compiler_executables")

        tools_folder = self._glib_tools_folder()
        source = os.path.join(tools_folder, f"{name}-runner.c")
        wrapper = os.path.join(tools_folder, name)
        python = os.path.realpath(sys.executable)
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <unistd.h>\n"
                f"static const char *python_path = {json.dumps(python)};\n"
                f"static const char *script_path = {json.dumps(script)};\n"
                "int main(int argc, char **argv) {\n"
                "    char **args = calloc((size_t)argc + 2, sizeof(char *));\n"
                "    if (!args) return 126;\n"
                "    args[0] = (char *)python_path;\n"
                "    args[1] = (char *)script_path;\n"
                "    for (int i = 1; i < argc; ++i) args[i + 1] = argv[i];\n"
                "    args[argc + 1] = NULL;\n"
                "    execv(python_path, args);\n"
                "    perror(\"execv\");\n"
                "    return 127;\n"
                "}\n"
            )
        with self._build_environment().vars(self).apply():
            self.run(
                f"{shlex.quote(compiler)} {shlex.quote(source)} "
                f"-o {shlex.quote(wrapper)}"
            )
        os.chmod(wrapper, 0o755)
        if self.settings.os == "OHOS":
            self._sign_elf(wrapper)

    def _augment_glib_pkg_config(self, tools_folder):
        pkg_config = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pkg_config):
            raise FileNotFoundError("PkgConfigDeps output is missing: glib-2.0.pc")
        with open(pkg_config, encoding="utf-8") as handle:
            content = handle.read()
        variables = {
            "glib_genmarshal": os.path.join(tools_folder, "glib-genmarshal"),
            "gobject_query": os.path.join(tools_folder, "gobject-query"),
            "glib_mkenums": os.path.join(tools_folder, "glib-mkenums"),
        }
        variable_block = "".join(
            f"{name}={value.replace(os.sep, '/')}\n"
            for name, value in variables.items()
        )
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Libs:") and "-lintl" not in line.split():
                line = line.rstrip("\r\n") + " -lintl\n"
            lines.append(line)
        content = "".join(lines)
        marker = "\nName:"
        if marker not in content:
            raise ValueError("Invalid PkgConfigDeps output: glib-2.0.pc has no Name field")
        content = content.replace(marker, f"\n{variable_block}{marker}", 1)
        with open(pkg_config, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _create_pkg_config_alias(self, source_name, alias_name, package_name):
        source = os.path.join(self.generators_folder, source_name)
        alias = os.path.join(self.generators_folder, alias_name)
        if not os.path.isfile(source):
            raise FileNotFoundError(f"PkgConfigDeps output is missing: {source_name}")
        with open(source, encoding="utf-8") as handle:
            content = handle.read()
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Name:"):
                if package_name == "gmodule-no-export-2.0":
                    lines.append("gmodule_supported=true\n\n")
                lines.append(f"Name: {package_name}\n")
            else:
                lines.append(line)
        with open(alias, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(lines))

    def _inject_meson_tools(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or ""
        compiler_dir = os.path.dirname(compiler) if os.path.sep in compiler else ""

        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if compiler_dir:
            if not ar:
                candidate = os.path.join(compiler_dir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
            if not ranlib:
                candidate = os.path.join(compiler_dir, "llvm-ranlib")
                if os.path.isfile(candidate):
                    ranlib = candidate

        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            candidates = [shutil.which("pkg-config")]
            if compiler_dir:
                candidates.append(os.path.join(compiler_dir, "pkg-config"))
            pkg_config = next(
                (path for path in candidates if path and os.path.isfile(path)), None
            )

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            native_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(native_file):
                continue
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue

            binaries = []
            if ar and "\nar =" not in content:
                binaries.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                binaries.append(f"ranlib = '{ranlib}'")
            if (
                pkg_config
                and "\npkg-config =" not in content
                and "\npkgconfig =" not in content
            ):
                binaries.append(f"pkg-config = '{pkg_config}'")
            glib_compile_resources = os.path.join(
                self._glib_tools_folder(), "glib-compile-resources"
            )
            if (
                os.path.isfile(glib_compile_resources)
                and "\nglib-compile-resources =" not in content
            ):
                binaries.append(
                    f"glib-compile-resources = '{glib_compile_resources}'"
                )
            if not binaries:
                continue
            content = content.replace(
                "[binaries]\n", "[binaries]\n" + "\n".join(binaries) + "\n", 1
            )
            with open(native_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _sign_installed_elfs(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip package signing")
            return

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or ""
        objcopy_candidates = [shutil.which("llvm-objcopy")]
        if compiler and os.path.sep in compiler:
            objcopy_candidates.insert(
                0, os.path.join(os.path.dirname(compiler), "llvm-objcopy")
            )
        objcopy = next(
            (path for path in objcopy_candidates if path and os.path.isfile(path)), None
        )

        patterns = [
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ]
        candidates = []
        for pattern in patterns:
            candidates.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(candidates)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            if objcopy:
                self.run(
                    f"{shlex.quote(objcopy)} --remove-section .codesign "
                    f"{shlex.quote(binary)} 2>/dev/null || true"
                )
            self._sign_elf(binary)

    @staticmethod
    def _create_shared_lib_aliases(libdir):
        versioned = sorted(
            path
            for path in glob.glob(
                os.path.join(libdir, "libgdk_pixbuf-2.0.so.*.*.*")
            )
            if os.path.isfile(path) and not os.path.islink(path)
        )
        if not versioned:
            raise FileNotFoundError(
                f"Versioned gdk-pixbuf shared library is missing in {libdir}"
            )
        source = versioned[-1]
        for name in ("libgdk_pixbuf-2.0.so.0", "libgdk_pixbuf-2.0.so"):
            alias = os.path.join(libdir, name)
            if os.path.lexists(alias):
                os.unlink(alias)
            shutil.copyfile(source, alias)

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS binary signer is missing: {signer}")
        self.run(
            shlex.join(
                [
                    signer,
                    "sign",
                    "-inFile",
                    binary,
                    "-outFile",
                    binary,
                    "-selfSign",
                    "1",
                ]
            )
        )
