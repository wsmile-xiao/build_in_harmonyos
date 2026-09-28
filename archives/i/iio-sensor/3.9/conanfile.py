#!/usr/bin/env python3
"""Conan recipe — iio-sensor (iio-sensor-proxy) 3.9 (Meson).

iio-sensor-proxy is a D-Bus daemon that exposes accelerometer, light and
proximity sensors (IIO / input / hwmon) to the desktop, plus the
monitor-sensor CLI.  Adapted to HarmonyOS PC (aarch64).

Build notes:
- gnome.compile_resources() needs a runnable glib-compile-resources:
  the conan glib binary must be copied out and signed for OHOS before use,
  and gio-2.0.pc must expose glib_compile_resources (see generate()).
- polkit policy dir is resolved from the polkit-gobject-1.pc policydir
  variable, which the conan-generated .pc does not carry; we augment it.
- udev/systemd dirs are passed explicitly so no udev/systemd dependency is
  probed; ssc-support is disabled (libssc is not published in the registry).
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class IioSensorConan(ConanFile):
    name = "iio-sensor"
    version = "3.9"
    description = "iio-sensor-proxy: D-Bus daemon exposing IIO/input/hwmon sensors (accelerometer, light, proximity) plus monitor-sensor CLI"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.freedesktop.org/hadess/iio-sensor-proxy"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gio-2.0 (>= 2.76), gudev-1.0 (>= 237), polkit-gobject-1 (>= 0.91)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libgudev/238", transitive_headers=True, transitive_libs=True)
        self.requires("polkit/124", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        glib_tools = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(glib_tools)
        self._augment_polkit_pkg_config()
        toolchain = MesonToolchain(self)
        toolchain.project_options.update(
            {
                "wrap_mode": "nodownload",
                # R03: conan MesonToolchain 默认把 libexecdir/sbindir 写成 'bin'，
                # 上游 meson.build 用 `prefix / get_option('libexecdir')` 安装
                # iio-sensor-proxy daemon，需显式恢复 libexec，使包内布局与
                # 本库契约（test_package 期望 libexec/iio-sensor-proxy）一致。
                "libexecdir": "libexec",
                "udevrulesdir": "/etc/udev/rules.d",
                "systemdsystemunitdir": "/usr/lib/systemd/system",
                "ssc-support": "disabled",
                "gtk-tests": "false",
                "gtk_doc": "false",
                "tests": "false",
            }
        )
        toolchain.generate()
        self._inject_meson_tools()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # Upstream C unit tests (test-orientation, test-mount-matrix)
            # were run and passed during adaptation; upstream Python
            # integration tests require dbusmock/gi + a D-Bus system bus
            # which are unavailable in this environment (recorded in
            # MANIFEST.yml).  meson.test() is therefore not run here.

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "libexec"]
        self.cpp_info.libs = []

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
        return environment

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_glib_build_tools(self):
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)

        for tool in ("glib-compile-resources",):
            source = os.path.join(glib_bin, tool)
            if not os.path.isfile(source):
                raise FileNotFoundError(f"GLib build tool is missing: {source}")
            destination = os.path.join(tools_folder, tool)
            shutil.copyfile(source, destination)
            os.chmod(destination, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(destination)
        return tools_folder

    def _augment_glib_pkg_config(self, tools_folder):
        pkg_config = os.path.join(self.generators_folder, "gio-2.0.pc")
        if not os.path.isfile(pkg_config):
            raise FileNotFoundError("PkgConfigDeps output is missing: gio-2.0.pc")
        with open(pkg_config, encoding="utf-8") as handle:
            content = handle.read()
        glib_compile_resources = os.path.join(tools_folder, "glib-compile-resources")
        if "glib_compile_resources=" not in content:
            content += (
                f"glib_compile_resources={glib_compile_resources.replace(os.sep, '/')}\n"
            )
        with open(pkg_config, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _augment_polkit_pkg_config(self):
        pkg_config = os.path.join(self.generators_folder, "polkit-gobject-1.pc")
        if not os.path.isfile(pkg_config):
            raise FileNotFoundError("PkgConfigDeps output is missing: polkit-gobject-1.pc")
        with open(pkg_config, encoding="utf-8") as handle:
            content = handle.read()
        # R03: policydir 必须为**相对**安装路径（meson install_dir 直接使用该值）。
        # 绝对 ${prefix}/share/polkit-1/actions 会解析到 polkit 包自身文件夹并被
        # DESTDIR 前缀镜像成 storage/Users/... 泄漏目录；改为相对路径后由 meson
        # 装入本包 prefix 下（share/polkit-1/actions）。
        if "datadir=" not in content:
            content += "datadir=${prefix}/share\n"
        if "policydir=" not in content:
            content += "policydir=share/polkit-1/actions\n"
        with open(pkg_config, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

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
            os.path.join(self.package_folder, "libexec", "*"),
        ]
        candidates = []
        for pattern in patterns:
            candidates.extend(glob.glob(pattern))
        for binary in sorted(set(candidates)):
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
