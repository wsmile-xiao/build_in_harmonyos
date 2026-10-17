#!/usr/bin/env python3
"""Conan recipe - libhandy 1.8.3 (Meson, GTK3 widget library).

libhandy provides additional GTK3 UI widgets (HdyWindow, HdyLeaflet, ...).
It is a hard dependency of evince >= 48 (the GNOME document viewer).

Build notes (OHOS aarch64):
- Meson + gnome.compile_resources / gnome.mkenums_simple need the GLib
  build tools (glib-compile-resources / glib-mkenums) from the glib package.
  glib-mkenums is a python script -> wrapped via a zero-compile sh launcher
  (the CI worker's SDK lld lacks libxml2.so.16, so avoid linking any ELF).
- fribidi is included as <fribidi.h>: fix the generated fribidi.pc Cflags.
- introspection / vapi / glade_catalog are disabled (their deps are not in
  the registry and are unused by consumers here).
- OHOS shared-library build misses the SONAME/linker aliases -> copy them.
"""
import glob
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


class LibhandyConan(ConanFile):
    name = "libhandy"
    version = "1.8.3"
    description = "Additional GTK3 UI widgets for adaptive applications"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libhandy"
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
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("fribidi/1.0.16", transitive_headers=True, transitive_libs=True)
        self.requires("harfbuzz/14.2.0.1.1.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        staged_source = os.path.expanduser("~/Download/libhandy-1.8.3.tar.xz")
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
            get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_fribidi_pc()
        tools_folder = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(tools_folder)
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "default_library": "shared" if self.options.shared else "static",
            "introspection": "disabled",
            "vapi": "false",
            "glade_catalog": "disabled",
            "gtk_doc": "false",
            "tests": "false",
            "examples": "false",
        })
        tc.generate()
        self._inject_meson_tools(tools_folder)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if not cross_building(self):
                meson.test()
            else:
                self.output.info("Cross-building: skipping upstream tests on host")

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        if self.settings.os == "OHOS":
            if self.options.shared:
                self._create_shared_lib_aliases(os.path.join(self.package_folder, "lib"))
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["handy-1"]
        self.cpp_info.includedirs = ["include/libhandy-1", "include"]
        self.cpp_info.set_property("pkg_config_name", "libhandy-1")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── helpers ────────────────────────────────────────────────────────────
    def _build_environment(self):
        environment = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        for name in ("TMPDIR", "TMP", "TEMP"):
            environment.define_path(name, tmp)
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        environment.prepend_path("PATH", glib_bin)
        environment.prepend_path("PATH", self._glib_tools_folder())
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
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
        for tool in ("glib-mkenums",):
            source = os.path.join(glib_bin, tool)
            if not os.path.isfile(source):
                raise FileNotFoundError(f"GLib build tool missing: {source}")
            self._build_python_tool_wrapper(tool, source)
        for tool in ("glib-compile-resources",):
            source = os.path.join(glib_bin, tool)
            if not os.path.isfile(source):
                raise FileNotFoundError(f"GLib build tool missing: {source}")
            destination = os.path.join(tools_folder, tool)
            shutil.copyfile(source, destination)
            os.chmod(destination, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(destination)
        return tools_folder

    def _build_python_tool_wrapper(self, name, script):
        # zero-compile sh launcher: the CI worker SDK lld may lack
        # libxml2.so.16, so any link step can crash. Wrapper simply execs
        # python on the glib script with absolute paths, no ELF produced.
        tools_folder = self._glib_tools_folder()
        wrapper = os.path.join(tools_folder, name)
        python = os.path.realpath(sys.executable)
        q = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#!/bin/sh\nexec {} {} \"$@\"\n".format(q(python), q(script)))
        os.chmod(wrapper, 0o755)

    def _fix_fribidi_pc(self):
        pc = os.path.join(self.generators_folder, "fribidi.pc")
        if not os.path.isfile(pc):
            return
        text = open(pc, encoding="utf-8").read()
        if "/fribidi" in text.split("Cflags:", 1)[-1]:
            return
        for old, new in (
            ('Cflags: -I"${includedir}"', 'Cflags: -I"${includedir}" -I"${includedir}/fribidi"'),
            ("Cflags: -I${includedir}", "Cflags: -I${includedir} -I${includedir}/fribidi"),
        ):
            if old in text:
                text = text.replace(old, new, 1)
                break
        open(pc, "w", encoding="utf-8", newline="\n").write(text)

    def _augment_glib_pkg_config(self, tools_folder):
        pkg_config = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pkg_config):
            raise FileNotFoundError("PkgConfigDeps output is missing: glib-2.0.pc")
        with open(pkg_config, encoding="utf-8") as handle:
            content = handle.read()
        variables = {
            "glib_mkenums": os.path.join(tools_folder, "glib-mkenums"),
        }
        variable_block = "".join(
            f"{name}={value.replace(os.sep, '/')}\n"
            for name, value in variables.items()
        )
        # Append -lintl to Libs (needed for bindtextdomain/bind_textdomain_codeset)
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

    def _inject_meson_tools(self, tools_folder):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = ce.get("c") or ""
        compiler_dir = os.path.dirname(compiler) if os.path.sep in compiler else ""

        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
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

        glib_compile_resources = os.path.join(tools_folder, "glib-compile-resources")
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
            if os.path.isfile(glib_compile_resources) and "\nglib-compile-resources =" not in content:
                binaries.append(f"glib-compile-resources = '{glib_compile_resources}'")
            if not binaries:
                continue
            content = content.replace(
                "[binaries]\n", "[binaries]\n" + "\n".join(binaries) + "\n", 1
            )
            with open(native_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _create_shared_lib_aliases(self, libdir):
        versioned = sorted(
            path
            for path in glob.glob(os.path.join(libdir, "libhandy-1.so.*.*.*"))
            if os.path.isfile(path) and not os.path.islink(path)
        )
        if not versioned:
            return
        source = versioned[-1]
        for name in ("libhandy-1.so.0", "libhandy-1.so"):
            alias = os.path.join(libdir, name)
            if os.path.lexists(alias):
                os.unlink(alias)
            shutil.copyfile(source, alias)

    def _sign_installed_elfs(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip package signing")
            return
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        candidates = [shutil.which("llvm-objcopy")]
        if cc and os.path.sep in cc:
            candidates.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates if p and os.path.isfile(p)), None)
        patterns = [
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ]
        cands = []
        for pattern in patterns:
            cands.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(cands)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            if objcopy:
                self.run(
                    f"{shlex.quote(objcopy)} --remove-section .codesign "
                    f"{shlex.quote(binary)} 2>/dev/null || true"
                )
            self._sign_elf(binary)

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS binary signer is missing: {signer}")
        self.run(
            shlex.join([
                signer, "sign", "-inFile", binary,
                "-outFile", binary, "-selfSign", "1",
            ])
        )
