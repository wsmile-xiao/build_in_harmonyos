#!/usr/bin/env python3
"""Conan recipe — libaccounts-glib 1.27 (Meson).

libaccounts-glib is the GLib-based core of the accounts-sso (Single Sign-On)
project. It provides a C API for managing online account information via
GLib/GObject, with SQLite-backed storage and libxml2 for XML parsing.

Adapted to HarmonyOS PC (aarch64). All features (library + tools) are built
without trimming. See notes.md for platform adaptation details.
"""
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibAccountsGlibConan(ConanFile):
    name = "libaccounts-glib"
    version = "1.27"
    description = "GLib-based library for managing online account information (accounts-sso project)"
    license = "LGPL-2.1"
    homepage = "https://gitlab.com/accounts-sso/libaccounts-glib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3", transitive_headers=True, transitive_libs=True)
        self.requires("sqlite3/3.49.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # check is only needed to build the upstream test suite (tests/meson.build)
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._create_glib_pkg_config_aliases()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        self._inject_archive_tools()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = ["accounts-glib"]
        self.cpp_info.requires = ["glib2::glib2", "libxml2::libxml2", "sqlite3::sqlite3"]
        self.cpp_info.includedirs = ["include", "include/libaccounts-glib"]
        self.cpp_info.set_property("pkg_config_name", "libaccounts-glib")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    # ── glib2 pkg-config alias helpers (adapted from vips recipe) ──

    def _create_glib_pkg_config_aliases(self):
        """Create gio-2.0.pc, gobject-2.0.pc, gio-unix-2.0.pc aliases from
        the single glib-2.0.pc that PkgConfigDeps generates for glib2, and
        inject glib_genmarshal / gdbus_codegen variables pointing to staged
        copies of the glib tools."""
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()

        # Inject missing tool variables
        for variable, executable in {
            "glib_genmarshal": "glib-genmarshal",
            "glib_mkenums": "glib-mkenums",
            "gdbus_codegen": "gdbus-codegen",
        }.items():
            if not re.search(rf"^{variable}=", content, flags=re.M):
                tool = self._stage_glib_tool(content, executable)
                content = content.replace(
                    "\nName:",
                    f"\n{variable}={tool}\nName:",
                    1,
                )

        with open(glib_pc, "w", encoding="utf-8") as target:
            target.write(content)

        # Create alias .pc files for gio-2.0, gobject-2.0
        for filename, name in {
            "gio-2.0.pc": "gio-2.0",
            "gobject-2.0.pc": "gobject-2.0",
        }.items():
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            with open(os.path.join(self.generators_folder, filename), "w", encoding="utf-8") as target:
                target.write(alias)

        # Create gio-unix-2.0.pc with correct Cflags for gio-unix-2.0 includes
        prefix_match = re.search(r"^prefix=(.+)$", content, flags=re.M)
        prefix = prefix_match.group(1).strip() if prefix_match else "${pcfiledir}"
        gio_unix_pc = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        with open(gio_unix_pc, "w", encoding="utf-8") as target:
            target.write(
                f"prefix={prefix}\n"
                f"includedir=${{prefix}}/include\n\n"
                f"Name: gio-unix-2.0\n"
                f"Description: unix specific headers for glib I/O library\n"
                f"Version: 2.88.0\n"
                f"Requires: gobject-2.0 gio-2.0\n"
                f"Cflags: -I${{includedir}}/gio-unix-2.0\n"
            )

    def _inject_archive_tools(self):
        """Inject ar/ranlib paths into meson native.ini to fix 'Unknown
        linker(s)' error when AR env var points to llvm-ar not on PATH."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or (os.path.join(bindir, "ar") if bindir else "")
        ranlib = executables.get("ranlib") or (os.path.join(bindir, "llvm-ranlib") if bindir else "")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        if not ar:
            ar = shutil.which("ar") or shutil.which("llvm-ar")
        if not ar:
            raise ConanInvalidConfiguration("Meson needs ar for libaccounts-glib")
        with open(native_file, encoding="utf-8") as native:
            content = native.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        tools = f"[binaries]\nar = '{ar}'\n"
        if ranlib and os.path.isfile(ranlib):
            tools += f"ranlib = '{ranlib}'\n"
        with open(native_file, "w", encoding="utf-8") as native:
            native.write(content.replace("[binaries]\n", tools, 1))

    def _stage_glib_tool(self, pc_content, executable):
        """Copy a glib tool (glib-genmarshal, gdbus-codegen) from the glib2
        conan package to the generators folder and return its path.

        For Python-based tools (gdbus-codegen, glib-mkenums), create a shell
        wrapper that sets PYTHONPATH to find the glib codegen module."""
        prefix_match = re.search(r"^prefix=(.+)$", pc_content, flags=re.M)
        if not prefix_match:
            return f"${{bindir}}/{executable}"
        prefix = prefix_match.group(1).strip()
        source = os.path.join(prefix, "bin", executable)
        if not os.path.isfile(source):
            return f"${{bindir}}/{executable}"

        # Check if it's a Python script
        is_python = False
        with open(source, encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
            if "python" in first_line:
                is_python = True

        if is_python:
            return self._build_python_wrapper(executable, prefix, source)
        else:
            target = os.path.join(self.generators_folder, executable)
            shutil.copyfile(source, target)
            os.chmod(target, 0o755)
            return target

    def _build_python_wrapper(self, executable, glib_prefix, script_path):
        """Create a shell wrapper for a Python-based glib tool that sets
        PYTHONPATH to include the glib codegen module directory."""
        codegen_dir = os.path.join(glib_prefix, "share", "glib-2.0")
        wrapper = os.path.join(self.generators_folder, executable)
        python = shutil.which("python3") or sys.executable
        with open(wrapper, "w", encoding="utf-8") as w:
            w.write(
                "#!/data/service/hnp/bin/bash\n"
                f"export PYTHONPATH={codegen_dir}:$PYTHONPATH\n"
                f'exec {python} "{script_path}" "$@"\n'
            )
        os.chmod(wrapper, 0o755)
        return wrapper
