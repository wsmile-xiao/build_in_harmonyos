#!/usr/bin/env python3
"""Conan recipe — libevdev 1.13.4 (Meson, OHOS PC / aarch64).

libevdev is a wrapper library around the kernel evdev interface; it is the
base of the input stack consumed by libinput.  1.13.4 is the Debian
bookworm版本,作为积分赛依赖任务提交(仓库已有 1.13.3 / 1.13.7,本配方
构建要点与其保持一致,见 notes.md)。

与 1.13.7 相比的唯一源码差异是 1 个 portability 补丁:
meson.build 中 cc.find_library('m'/'rt') 改为 required:false(musl 无
独立 librt;见 conandata.yml)。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibevdevConan(ConanFile):
    name = "libevdev"
    version = "1.13.4"
    description = "Handler library for evdev events"
    license = "MIT"
    homepage = "https://www.freedesktop.org/wiki/Software/libevdev/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"],
            sha256=source_data.get("sha256", ""), strip_root=True)

    def generate(self):
        self._ensure_tmpdir()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["tests"] = "disabled"
        tc.project_options["documentation"] = "disabled"
        tc.project_options["tools"] = "enabled"
        tc.generate()
        self._inject_ar_ranlib()

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        self._create_harmonyos_headers()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        if self.options.shared and self.settings.os == "OHOS":
            self._create_shared_lib_aliases()

    def package_info(self):
        self.cpp_info.libs = ["evdev"]
        self.cpp_info.includedirs = ["include/libevdev-1.0"]
        self.cpp_info.system_libs = ["m", "rt"]
        self.cpp_info.set_property("pkg_config_name", "libevdev")
        self.cpp_info.set_property("cmake_file_name", "libevdev")

    # ── Helper methods(与 main 上 1.13.7 配方一致)────────────────

    def _ensure_tmpdir(self):
        # HarmonyOS 的 /tmp 是只读 erofs(E002)— 指到可写目录
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp"
        )
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _inject_ar_ranlib(self):
        """Set AR/RANLIB env vars from the Conan profile's compiler_executables."""
        compiler_executables = (
            self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            or {}
        )
        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if not ar:
            cc = compiler_executables.get("c") or ""
            if cc:
                ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        if not ranlib:
            cc = compiler_executables.get("c") or ""
            if cc:
                ranlib = os.path.join(os.path.dirname(cc), "llvm-ranlib")
        if ar:
            os.environ["AR"] = ar
        if ranlib:
            os.environ["RANLIB"] = ranlib

    def _create_harmonyos_headers(self):
        """Create harmonyos header symlinks for meson's host_machine.system().

        Meson maps OHOS to 'harmonyos' for host_machine.system().
        libevdev's meson.build looks for include/linux/{system}/input.h.
        Since HarmonyOS uses the Linux kernel, we symlink the Linux UAPI headers.
        """
        harmonyos_dir = os.path.join(
            self.source_folder, "include", "linux", "harmonyos"
        )
        if not os.path.exists(harmonyos_dir):
            os.makedirs(harmonyos_dir, exist_ok=True)
            input_h = os.path.join(harmonyos_dir, "input.h")
            input_ec_h = os.path.join(harmonyos_dir, "input-event-codes.h")
            if not os.path.exists(input_h):
                os.symlink("../linux/input.h", input_h)
            if not os.path.exists(input_ec_h):
                os.symlink(
                    "../linux/input-event-codes.h", input_ec_h
                )

    def _create_shared_lib_aliases(self):
        """Ensure libevdev.so symlinks exist in the package (HMDFS safety)."""
        libdir = os.path.join(self.package_folder, "lib")
        for src, dst in [
            ("libevdev.so.2.3.0", "libevdev.so.2"),
            ("libevdev.so.2", "libevdev.so"),
        ]:
            src_path = os.path.join(libdir, src)
            dst_path = os.path.join(libdir, dst)
            if os.path.exists(src_path) and not os.path.exists(dst_path):
                os.symlink(src, dst_path)
