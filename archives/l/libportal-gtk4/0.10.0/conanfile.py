#!/usr/bin/env python3
"""Conan recipe — libportal-gtk4 0.10.0 (XDG portal library, GTK4 backend, Meson).

libportal provides GObject-based wrappers around the XDG desktop portal
D-Bus interfaces (org.freedesktop.portal.Desktop): screenshot, file chooser,
notification, settings, openuri, inhibit, etc. The library is a pure
GDBus *client* — the build itself does not need a running session bus.

Adapted to HarmonyOS PC (aarch64). Key configuration:
  - core library (libportal.so) only needs gio-2.0/gio-unix-2.0
  - GTK4 backend enabled (gtk4/4.22.4, broadway flavour — the X11/Wayland
    code paths in portal-gtk4.c are behind GDK_WINDOWING_X11/WAYLAND ifdefs
    and are naturally compiled out); glib pinned to 2.84.0.1.1 to match the
    gtk4 dependency graph exactly (avoids a duplicate glib in the closure)
  - gtk3/qt5/qt6 backends disabled (gtk3 lives in the separate libportal
    package; no qt5/qt6 on OHOS)
  - introspection/vapi/docs disabled (no g-ir-scanner toolchain on OHOS)
  - upstream meson test suite disabled (-Dtests=false): the pytest suite
    needs python-dbus + python-dbusmock + a session bus which OHOS does
    not have (mock-portal environment, see notes.md); L1 coverage is
    provided by test_package
"""
import glob
import os
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibportalConan(ConanFile):
    name = "libportal-gtk4"
    version = "0.10.0"
    description = "libportal-gtk4 — XDG desktop portal library, GTK4 parent-window backend (GIO/GObject wrappers around org.freedesktop.portal.Desktop)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/flatpak/libportal"
    url = "https://github.com/flatpak/libportal"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # Core library: gio-2.0 + gio-unix-2.0 (GDBus client, no runtime bus
        # needed to build). GTK3 backend: gtk+-3.0.
        # Both are propagated to consumers (headers are public).
        # glib: version-pin the whole graph to the gtk4-published revision
        # (libadwaita/1.2.0 pattern). gtk4/4.22.4 already overrides every
        # glib pin (pango/harfbuzz/...) onto 2.84.0.1.1 shared=True; a direct
        # (non-override) root requirement here would conflict with pango's
        # glib/2.84.0.1 because root requirements cannot be overridden.
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("gtk4/4.22.4", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        # copy declared patches (if any) into the exported sources; this
        # package has no platform patches (see notes.md)
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            copy(self, patch["patch_file"], self.recipe_folder, self.export_sources_folder)

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"], sha256=source_data["sha256"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        toolchain = MesonToolchain(self)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["default_library"] = "shared" if self.options.shared else "static"
        # backends: gtk4 required by the task, the rest unavailable/other pkgs
        toolchain.project_options["backend-gtk4"] = "enabled"
        toolchain.project_options["backend-gtk3"] = "disabled"
        toolchain.project_options["backend-qt5"] = "disabled"
        toolchain.project_options["backend-qt6"] = "disabled"
        toolchain.project_options["portal-tests"] = "false"
        # tooling absent on OHOS (g-ir-scanner / vapigen / gi-docgen)
        toolchain.project_options["introspection"] = "false"
        toolchain.project_options["vapi"] = "false"
        toolchain.project_options["docs"] = "false"
        # upstream pytest suite needs python-dbus/dbusmock + a session bus
        # (mock portal environment); OHOS has none — covered by test_package
        toolchain.project_options["tests"] = "false"
        toolchain.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    def build(self):
        # no platform patches needed (see notes.md); no-op if none declared
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # libportal.so (core Xdp* API) + libportal-gtk4.so (XdpGtk4 parent API)
        self.cpp_info.libs = ["portal", "portal-gtk4"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = [
            # gtk4/4.22.4 is a flat package (no components); its implicit
            # component is the package name itself. glib rides the gtk4
            # graph (override pin, not a direct require — see requirements()).
            "gtk4::gtk4",
        ]
        self.cpp_info.set_property("cmake_file_name", "libportal-gtk4")
        self.cpp_info.set_property("cmake_target_name", "libportal-gtk4::libportal-gtk4")
        self.cpp_info.set_property("pkg_config_name", "libportal-gtk4")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── helpers (patterns proven in the accountsservice recipe) ───────────

    def _build_environment(self):
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        # The stock OHOS session LD_LIBRARY_PATH can carry a whitespace-
        # corrupted "/system/lib64" entry ("chipset-pub-sdk:<spaces>/system/
        # lib64"), which makes the dynamic loader miss libc++_shared.so and
        # breaks the ninja --version probe inside meson setup (external
        # shell: /system/lib64 is reached because the shell re-quotes).
        # Prepending a clean /system/lib64 entry is a no-op on a healthy
        # CI worker and fixes the probe on a corrupted session.
        if self.settings.os == "OHOS" and os.path.isdir("/system/lib64"):
            environment.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _append_dependency_pkg_config_paths(self):
        # glib exposes gio-unix-2.0.pc / gtk exposes gdk-3.0.pc etc. only
        # inside the packages' lib/pkgconfig (PkgConfigDeps does not emit
        # these because glib's conan recipe only declares the gio-2.0
        # component; upstream meson dependency('gio-unix-2.0') needs the
        # real .pc on the search path).
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        paths = [self.generators_folder]
        for dependency in self.dependencies.host.values():
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate)
        unique_paths = []
        for path in paths:
            normalized = path.replace("\\", "/")
            if normalized not in unique_paths:
                unique_paths.append(normalized)
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        replacement = "pkg_config_path = [" + ", ".join("'{}'".format(p) for p in unique_paths) + "]"
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _inject_meson_tools(self):
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            import shutil
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (bindir, "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"):
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkg_config or not os.path.isfile(str(pkg_config)):
                pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _augment_glib_pkg_config(self):
        # gnome.mkenums (used for portal-enums.c/h) needs the glib_mkenums /
        # glib_genmarshal / gobject_query pkg-config variables which
        # PkgConfigDeps does not emit; wrap the tools so the conan-installed
        # scripts' __file__ points at bin/ and they can locate their data
        # (accountsservice pattern).
        glib_mkenums = self._create_python_tool_wrapper("glib-mkenums")
        glib_genmarshal = self._create_python_tool_wrapper("glib-genmarshal")
        variables = {
            "glib-2.0": [
                f"glib_mkenums={glib_mkenums}",
                f"glib_genmarshal={glib_genmarshal}",
                "gobject_query=${bindir}/gobject-query",
            ],
        }
        for pc_name, entries in variables.items():
            pc_file = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(pc_file):
                self.output.warning(f"Could not augment missing {pc_name}.pc")
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            inserted = []
            for entry in entries:
                key = entry.split("=", 1)[0] + "="
                if key not in content:
                    inserted.append(entry)
            if inserted:
                addition = "\n" + "\n".join(inserted)
                name_index = content.find("\nName:")
                if name_index >= 0:
                    content = content[:name_index] + addition + content[name_index:]
                else:
                    content = "\n".join(inserted) + "\n" + content
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _create_python_tool_wrapper(self, tool_name):
        tool_path = None
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", tool_name)
            if os.path.isfile(candidate):
                tool_path = candidate
                break
        if not tool_path:
            return f"${{bindir}}/{tool_name}"
        wrapper_path = os.path.join(self.generators_folder, f"{tool_name}-python")
        with open(wrapper_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                f"#!{sys.executable}\n"
                "import runpy\n"
                "import sys\n"
                f"sys.argv = [{tool_path!r}] + sys.argv[1:]\n"
                f"runpy.run_path({tool_path!r}, run_name='__main__')\n"
            )
        os.chmod(wrapper_path, 0o755)
        return wrapper_path.replace("\\", "/")

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_installed_elfs(self):
        import shutil
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
