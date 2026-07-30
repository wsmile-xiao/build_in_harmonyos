#!/usr/bin/env python3
"""Conan recipe - aravis 0.8.36 (Meson)."""
import glob
import json
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class AravisConan(ConanFile):
    name = "aravis"
    version = "0.8.36"
    description = "Vision library for GenICam based cameras"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/AravisProject/aravis"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
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
        self.requires("glib/2.84.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmpdir()
        PkgConfigDeps(self).generate()
        self._patch_glib_pkg_config_variables()
        self._create_glib_pkg_config_aliases()
        self._patch_gio_pkg_config_variables()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["viewer"] = "disabled"
        tc.project_options["gst-plugin"] = "disabled"
        tc.project_options["usb"] = "disabled"
        tc.project_options["packet-socket"] = "disabled"
        tc.project_options["tests"] = "true"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["documentation"] = "disabled"
        tc.generate()
        self._inject_ar_ranlib()

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if self.options.shared and self.settings.os == "OHOS":
            self._create_shared_lib_aliases(os.path.join(self.build_folder, "src"))
        old_loader_path = self._configure_test_loader_path()
        try:
            meson.test()
        finally:
            self._restore_loader_path(old_loader_path)

    def package(self):
        Meson(self).install()
        if self.options.shared and self.settings.os == "OHOS":
            self._create_shared_lib_aliases(os.path.join(self.package_folder, "lib"))
            self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = ["aravis-0.8"]
        self.cpp_info.requires = ["glib::glib", "libxml2::libxml2", "zlib::zlib"]
        self.cpp_info.includedirs = ["include/aravis-0.8", "include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "aravis")
        self.cpp_info.set_property("cmake_target_name", "aravis::aravis")
        self.cpp_info.set_property("pkg_config_name", "aravis-0.8")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _inject_ar_ranlib(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if not ar:
            cc = compiler_executables.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insertion = "[binaries]\nar = '{}'\n".format(ar)
                if ranlib:
                    insertion += "ranlib = '{}'\n".format(ranlib)
                content = content.replace("[binaries]\n", insertion, 1)
                with open(native_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _ensure_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _create_glib_pkg_config_aliases(self):
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        aliases = {
            "gio-2.0.pc": "gio-2.0",
            "gobject-2.0.pc": "gobject-2.0",
            "gmodule-2.0.pc": "gmodule-2.0",
            "gthread-2.0.pc": "gthread-2.0",
        }
        for filename, name in aliases.items():
            alias_path = os.path.join(self.generators_folder, filename)
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            with open(alias_path, "w", encoding="utf-8") as target:
                target.write(alias)

    def _patch_glib_pkg_config_variables(self):
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        variables = {
            "glib_genmarshal": self._stage_glib_tool("glib-genmarshal"),
            "gobject_query": self._stage_glib_tool("gobject-query"),
            "glib_mkenums": self._stage_glib_tool("glib-mkenums"),
        }
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        for variable, value in variables.items():
            if re.search(rf"^{re.escape(variable)}=", content, flags=re.M):
                content = re.sub(
                    rf"^{re.escape(variable)}=.*$",
                    f"{variable}={value}",
                    content,
                    flags=re.M,
                )
            else:
                content = f"{variable}={value}\n" + content
        with open(glib_pc, "w", encoding="utf-8") as target:
            target.write(content)

    def _patch_gio_pkg_config_variables(self):
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if not os.path.isfile(gio_pc):
            return
        variables = {
            "gio": self._stage_glib_tool("gio"),
            "gio_querymodules": self._stage_glib_tool("gio-querymodules"),
            "glib_compile_schemas": self._stage_glib_tool("glib-compile-schemas"),
            "glib_compile_resources": self._stage_glib_tool("glib-compile-resources"),
            "gdbus": self._stage_glib_tool("gdbus"),
            "gdbus_codegen": self._stage_glib_tool("gdbus-codegen"),
            "gresource": self._stage_glib_tool("gresource"),
            "gsettings": self._stage_glib_tool("gsettings"),
        }
        with open(gio_pc, encoding="utf-8") as source:
            content = source.read()
        for variable, value in variables.items():
            if re.search(rf"^{re.escape(variable)}=", content, flags=re.M):
                content = re.sub(
                    rf"^{re.escape(variable)}=.*$",
                    f"{variable}={value}",
                    content,
                    flags=re.M,
                )
            else:
                content = f"{variable}={value}\n" + content
        with open(gio_pc, "w", encoding="utf-8") as target:
            target.write(content)

    def _stage_glib_tool(self, name):
        source = os.path.join(self.dependencies["glib"].package_folder, "bin", name)
        tools_dir = os.path.join(self.build_folder, ".glib-tools")
        os.makedirs(tools_dir, exist_ok=True)
        target = os.path.join(tools_dir, name)
        if os.path.isfile(source) and not os.path.isfile(target):
            shutil.copy2(source, target)
            os.chmod(target, 0o755)
        if os.path.isfile(target):
            with open(target, "rb") as handle:
                first_line = handle.readline(128)
            if b"python" in first_line and self.settings.os == "OHOS":
                return self._build_python_tool_wrapper(name, target)
        return target

    def _build_python_tool_wrapper(self, name, script):
        tools_dir = os.path.join(self.build_folder, ".glib-tools")
        wrapper = os.path.join(tools_dir, f"{name}-runner")
        if os.path.isfile(wrapper):
            return wrapper
        cc = self.conf.get("tools.build:compiler_executables", default={}) or {}
        compiler = cc.get("c")
        if not compiler:
            raise RuntimeError("C compiler not found in tools.build:compiler_executables")
        source = os.path.join(tools_dir, f"{name}-runner.c")
        python = os.path.realpath(sys.executable)
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <unistd.h>\n"
                f"static const char *python_path = {json.dumps(python)};\n"
                f"static const char *script_path = {json.dumps(script)};\n"
                "int main(int argc, char **argv) {\n"
                "    char **args = (char **)calloc((size_t)argc + 2, sizeof(char *));\n"
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
        self.run(f'"{compiler}" "{source}" -o "{wrapper}"')
        os.chmod(wrapper, 0o755)
        return wrapper

    def _configure_test_loader_path(self):
        libdirs = [os.path.join(self.build_folder, "src")]
        for dependency in self.dependencies.values():
            libdirs.extend(dependency.cpp_info.libdirs)
        current = os.environ.get("LD_LIBRARY_PATH")
        if current:
            libdirs.append(current)
        os.environ["LD_LIBRARY_PATH"] = ":".join(self._unique(libdirs))
        return current

    @staticmethod
    def _restore_loader_path(value):
        if value is None:
            os.environ.pop("LD_LIBRARY_PATH", None)
        else:
            os.environ["LD_LIBRARY_PATH"] = value

    @staticmethod
    def _unique(items):
        seen = set()
        result = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def _create_shared_lib_aliases(self, libdir):
        versioned = sorted(
            path for path in glob.glob(os.path.join(libdir, "libaravis-0.8.so.*"))
            if os.path.isfile(path)
        )
        if not versioned:
            return
        source = versioned[-1]
        for name in ("libaravis-0.8.so.0", "libaravis-0.8.so"):
            target = os.path.join(libdir, name)
            if not os.path.exists(target):
                shutil.copy2(source, target)

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_objects += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_objects:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise FileNotFoundError(f"Required OHOS signing tool is missing: {tool}")
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=shared_object
            ))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=shared_object
            ))
