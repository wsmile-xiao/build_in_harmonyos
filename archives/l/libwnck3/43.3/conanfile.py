#!/usr/bin/env python3
"""Conan recipe for libwnck 43.3 on HarmonyOS PC.

The published GTK 3 package uses its Broadway display backend and therefore
does not export GDK-X11 or Cairo-Xlib.  libwnck remains a real X11/EWMH client:
the portability layer built here talks to an X server through libX11 and turns
X pixmaps into Cairo image surfaces.  GTK widgets can simultaneously render
through Broadway without removing libwnck window-management behaviour.
"""

import os
import platform
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools import gnu
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class Libwnck3Conan(ConanFile):
    name = "libwnck3"
    version = "43.3"
    description = "Window navigator construction kit for X11 desktop integration"
    license = "LGPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libwnck"
    url = "https://gitlab.gnome.org/GNOME/libwnck"
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
        for dependency in ("glib", "gtk", "cairo"):
            try:
                self.options[dependency].shared = True
            except Exception as exc:
                self.output.info(f"shared option not set for {dependency}: {exc}")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libwnck supports Linux and OHOS, not {self.settings.os}"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "libwnck 43.3 upstream always builds a shared library"
            )

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxres/1.2.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxi/6.1.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pkg_config = gnu.PkgConfigDeps(self)
        pkg_config.set_property("glib", "pkg_config_name", "glib-2.0")
        pkg_config.set_property("gtk", "pkg_config_name", "gtk+-3.0")
        pkg_config.set_property("cairo", "pkg_config_name", "cairo")
        pkg_config.set_property("libx11", "pkg_config_name", "x11")
        pkg_config.set_property("libxres", "pkg_config_name", "xres")
        pkg_config.set_property("libxi", "pkg_config_name", "xi")
        pkg_config.generate()

        tools_folder = self._prepare_glib_tools()
        self._augment_glib_pc(tools_folder)

        toolchain = MesonToolchain(self)
        toolchain.project_options.update({
            "wrap_mode": "nodownload",
            "startup_notification": "disabled",
            "introspection": "disabled",
            "gtk_doc": False,
            "install_tools": False,
            "x11_compat": True,
        })
        toolchain.generate()
        self._ensure_ohos_cross_file()
        self._inject_build_tools(tools_folder)

        environment = Environment()
        environment.prepend_path("PATH", tools_folder)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        environment.vars(self).save_script("libwnck_build_env")

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            meson.test()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._sanitize_pkg_config()
        if str(self.settings.os) == "OHOS":
            self._resign_package_shared_libraries()

    def package_info(self):
        self.cpp_info.libs = ["wnck-3"]
        self.cpp_info.includedirs = ["include/libwnck-3.0", "include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libwnck3")
        self.cpp_info.set_property("cmake_target_name", "libwnck3::libwnck3")
        self.cpp_info.set_property("pkg_config_name", "libwnck-3.0")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "native-tools")

    def _inject_build_tools(self, tools_folder):
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = next(
                (
                    candidate
                    for candidate in (
                        "/usr/bin/pkg-config",
                        "/usr/bin/pkgconf",
                        shutil.which("pkg-config"),
                        shutil.which("pkgconf"),
                    )
                    if candidate and os.path.isfile(candidate)
                ),
                "/usr/bin/pkg-config",
            )
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        archiver = compiler_executables.get("ar") or ""
        if not archiver:
            compiler = (
                compiler_executables.get("c")
                or compiler_executables.get("cpp")
                or ""
            )
            compiler_folder = os.path.dirname(compiler) if compiler else ""
            candidate = os.path.join(compiler_folder, "llvm-ar")
            if compiler_folder and os.path.isfile(candidate):
                archiver = candidate
        if str(self.settings.os) == "OHOS" and (
            not archiver or not os.path.isfile(archiver)
        ):
            raise ConanException(
                "OHOS llvm-ar could not be resolved next to the configured "
                f"compiler: {compiler_executables.get('c')!r}"
            )
        cross_file = os.path.join(self.generators_folder, "conan_meson_cross.ini")
        if not os.path.isfile(cross_file):
            raise ConanException("Meson cross file was not generated")
        with open(cross_file, encoding="utf-8") as handle:
            content = handle.read()
        binaries = {
            "pkg-config": os.path.abspath(str(pkg_config)),
            "ar": os.path.abspath(str(archiver)) if archiver else "",
            "glib-compile-resources": os.path.join(
                tools_folder, "glib-compile-resources"
            ),
            "glib-mkenums": os.path.join(tools_folder, "glib-mkenums"),
            "glib-genmarshal": os.path.join(tools_folder, "glib-genmarshal"),
        }
        entries = "".join(
            f"{name} = '{path}'\n"
            for name, path in binaries.items()
            if path and f"\n{name} =" not in content
        )
        if entries:
            content = content.replace("[binaries]\n", "[binaries]\n" + entries, 1)
        with open(cross_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _ensure_ohos_cross_file(self):
        if str(self.settings.os) != "OHOS":
            return
        cross_file = os.path.join(self.generators_folder, "conan_meson_cross.ini")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.isfile(cross_file) or not os.path.isfile(native_file):
            return

        build_cpu = platform.machine().lower()
        if build_cpu in ("amd64", "x86_64"):
            build_family = "x86_64"
        elif build_cpu in ("arm64", "aarch64"):
            build_family = "aarch64"
        else:
            build_family = build_cpu
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read().rstrip()
        content = content.replace(
            "[properties]\n", "[properties]\nneeds_exe_wrapper = true\n", 1
        )
        content += (
            "\n\n[build_machine]\n"
            "system = 'linux'\n"
            f"cpu_family = '{build_family}'\n"
            f"cpu = '{build_cpu}'\n"
            "endian = 'little'\n"
            "\n[host_machine]\n"
            "system = 'harmonyos'\n"
            "cpu_family = 'aarch64'\n"
            "cpu = 'armv8'\n"
            "endian = 'little'\n"
        )
        os.replace(native_file, cross_file)
        with open(cross_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _prepare_glib_tools(self):
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")

        for name in ("glib-mkenums", "glib-genmarshal"):
            source = os.path.join(glib_bin, name)
            if not os.path.isfile(source):
                raise ConanException(f"GLib build tool missing: {source}")
            wrapper = os.path.join(tools_folder, name)
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    "#!/bin/sh\nexec env -u LD_LIBRARY_PATH "
                    f"{shlex.quote(os.path.realpath(sys.executable))} "
                    f"{shlex.quote(source)} \"$@\"\n"
                )
            os.chmod(wrapper, 0o755)

        compiled_tool = os.path.join(glib_bin, "glib-compile-resources")
        if not os.path.isfile(compiled_tool):
            raise ConanException(f"glib-compile-resources missing: {compiled_tool}")
        private_tool = os.path.join(tools_folder, "glib-compile-resources.bin")
        shutil.copyfile(compiled_tool, private_tool)
        os.chmod(private_tool, 0o755)
        if str(self.settings.os) == "OHOS":
            self._resign_ohos_elf(private_tool)

        runtime_libdirs = []
        for dependency in self.dependencies.host.values():
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            libdir = os.path.join(package_folder, "lib")
            if os.path.isdir(libdir) and libdir not in runtime_libdirs:
                runtime_libdirs.append(libdir)
        runtime_path = ":".join(runtime_libdirs)

        machine = platform.machine().lower()
        if machine in ("aarch64", "arm64"):
            command = (
                "exec env LD_LIBRARY_PATH="
                f"{shlex.quote(runtime_path)}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}} "
                f"{shlex.quote(private_tool)} \"$@\""
            )
        else:
            qemu = os.getenv("LIBWNCK_QEMU", "") or shutil.which("qemu-aarch64")
            qemu_root = os.getenv("LIBWNCK_QEMU_ROOT", "") or os.path.expanduser(
                "~/.local/share/ohpcd/alpine-aarch64-3.24.0"
            )
            qemu_shim = os.getenv("LIBWNCK_QEMU_SHIM", "") or os.path.expanduser(
                "~/.local/share/ohpcd/libwnck-qemu-runtime-shim.so"
            )
            if (
                qemu
                and os.path.isfile(qemu)
                and os.path.isdir(qemu_root)
                and os.path.isfile(qemu_shim)
            ):
                qemu_runtime = ":".join(
                    runtime_libdirs
                    + [os.path.join(qemu_root, "lib"), os.path.join(qemu_root, "usr", "lib")]
                )
                command = (
                    f"exec {shlex.quote(qemu)} -L {shlex.quote(qemu_root)} "
                    f"-E LD_PRELOAD={shlex.quote(qemu_shim)} "
                    f"-E LD_LIBRARY_PATH={shlex.quote(qemu_runtime)} "
                    f"{shlex.quote(private_tool)} \"$@\""
                )
            else:
                host_tool = "/usr/bin/glib-compile-resources"
                if not os.path.isfile(host_tool):
                    host_tool = shutil.which("glib-compile-resources") or ""
                if not host_tool:
                    raise ConanException(
                        "Conan glib-compile-resources needs an AArch64 runner, and no "
                        "isolated host fallback is available"
                    )
                self.output.warning(
                    "AArch64 runner unavailable; using isolated host "
                    "glib-compile-resources fallback"
                )
                command = (
                    "exec env -u LD_LIBRARY_PATH "
                    f"{shlex.quote(host_tool)} \"$@\""
                )
        wrapper = os.path.join(tools_folder, "glib-compile-resources")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(f"#!/bin/sh\n{command}\n")
        os.chmod(wrapper, 0o755)
        return tools_folder

    def _resign_ohos_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanException(f"HarmonyOS binary signer missing: {signer}")

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = (
            compiler_executables.get("c")
            or compiler_executables.get("cpp")
            or ""
        )
        compiler_folder = os.path.dirname(compiler) if compiler else ""
        objcopy = next(
            (
                candidate
                for candidate in (
                    os.path.join(compiler_folder, "llvm-objcopy"),
                    shutil.which("llvm-objcopy"),
                )
                if candidate and os.path.isfile(candidate)
            ),
            None,
        )
        if objcopy:
            self.run(
                f"{shlex.quote(objcopy)} --remove-section .codesign "
                f"{shlex.quote(binary)} 2>/dev/null || true"
            )
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

    def _resign_package_shared_libraries(self):
        libdir = os.path.join(self.package_folder, "lib")
        targets = []
        for root, _, filenames in os.walk(libdir):
            for filename in filenames:
                if ".so" not in filename:
                    continue
                target = os.path.join(root, filename)
                if os.path.isfile(target) and not os.path.islink(target):
                    targets.append(target)
        if not targets:
            raise ConanException("No packaged libwnck shared library found to sign")
        for target in sorted(targets):
            self._resign_ohos_elf(target)
        self.output.info(
            f"Re-signed {len(targets)} packaged libwnck shared library file(s)"
        )

    def _augment_glib_pc(self, tools_folder):
        path = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(path):
            raise ConanException("PkgConfigDeps did not generate glib-2.0.pc")
        content = open(path, encoding="utf-8").read()
        variables = (
            f"glib_mkenums={os.path.join(tools_folder, 'glib-mkenums')}\n"
            f"glib_genmarshal={os.path.join(tools_folder, 'glib-genmarshal')}\n"
        )
        if "glib_mkenums=" not in content:
            content = content.replace("\nName:", "\n" + variables + "\nName:", 1)
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Libs:") and "-lintl" not in line.split():
                line = line.rstrip("\r\n") + " -lintl\n"
            lines.append(line)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(lines))

    def _build_environment(self):
        environment = Environment()
        environment.prepend_path("PATH", self._glib_tools_folder())
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        return environment

    def _sanitize_pkg_config(self):
        pc = os.path.join(self.package_folder, "lib", "pkgconfig", "libwnck-3.0.pc")
        if not os.path.isfile(pc):
            raise ConanException("libwnck-3.0.pc was not installed")
        content = open(pc, encoding="utf-8").read()
        content = content.replace("Requires.private:  x11  xres", "Requires.private: x11 xres")
        with open(pc, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
