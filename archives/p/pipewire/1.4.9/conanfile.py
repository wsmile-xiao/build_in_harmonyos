#!/usr/bin/env python3
"""Conan recipe — Meson project (PipeWire 1.4.9)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class PipewireConan(ConanFile):
    name = "pipewire"
    version = "1.4.9"
    description = "PipeWire multimedia server library 1.4.9"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/pipewire/pipewire"
    url = homepage

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: System-name libraries default to static
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Minimal build: core libs + spa + tools + tests, no external deps
        tc.project_options["tests"] = "enabled"
        tc.project_options["pipewire-jack"] = "disabled"
        tc.project_options["pipewire-alsa"] = "disabled"
        tc.project_options["pipewire-v4l2"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["docs"] = "disabled"
        tc.project_options["man"] = "disabled"
        tc.project_options["session-managers"] = "[]"
        tc.project_options["spa-plugins"] = "enabled"
        tc.project_options["alsa"] = "disabled"
        tc.project_options["bluez5"] = "disabled"
        tc.project_options["jack"] = "disabled"
        tc.project_options["dbus"] = "disabled"
        tc.project_options["sndfile"] = "disabled"
        tc.project_options["ffmpeg"] = "disabled"
        tc.project_options["vulkan"] = "disabled"
        tc.project_options["gstreamer"] = "disabled"
        tc.project_options["systemd"] = "disabled"
        tc.project_options["pw-cat"] = "disabled"
        tc.project_options["readline"] = "disabled"
        tc.project_options["udev"] = "disabled"
        tc.project_options["libpulse"] = "disabled"
        tc.project_options["v4l2"] = "disabled"
        tc.project_options["libcamera"] = "disabled"
        tc.project_options["videoconvert"] = "disabled"
        tc.project_options["videotestsrc"] = "disabled"
        tc.project_options["audiotestsrc"] = "disabled"
        tc.project_options["libcanberra"] = "disabled"
        tc.project_options["libusb"] = "disabled"
        tc.project_options["x11"] = "disabled"
        tc.project_options["libffado"] = "disabled"
        tc.project_options["lv2"] = "disabled"
        tc.project_options["raop"] = "disabled"
        tc.project_options["avahi"] = "disabled"
        tc.project_options["snap"] = "disabled"
        tc.project_options["flatpak"] = "disabled"
        tc.project_options["gsettings"] = "disabled"
        tc.project_options["installed_tests"] = "disabled"
        tc.generate()
        # conan MesonToolchain 不把 tools.build:compiler_executables 的 ar/ranlib 写进 native file，
        # meson 便按裸名 llvm-ar 探归档器，而 clang 工具链在 /data/service/hnp/bin，CI worker PATH 上无
        # llvm-ar 时 configure 失败（cairo 1.18.4 / libsigc / pixman / bstring 同一模式）。直接把
        # ar/ranlib 全路径注入 conan_meson_native.ini，不污染 PATH。
        import os as _os
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar = _ce.get("ar"); _rl = _ce.get("ranlib")
        # CI profile 仅提供 c/cpp，未给 ar/ranlib：从 c 编译器同目录推导 llvm-ar/llvm-ranlib 全路径。
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = _os.path.dirname(_cc) if _os.path.sep in _cc else ""
            if _bindir:
                _cand = _os.path.join(_bindir, "llvm-ar")
                if _os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = _os.path.join(_bindir, "llvm-ranlib")
                    if _os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = _os.path.join(self.generators_folder, "conan_meson_native.ini")
        if _ar and _os.path.isfile(_nf):
            with open(_nf) as _f: _c = _f.read()
            if "\nar =" not in _c and "[binaries]" in _c:
                _ins = "[binaries]\nar = '%s'\n" % _ar
                if _rl: _ins += "ranlib = '%s'\n" % _rl
                _c = _c.replace("[binaries]\n", _ins, 1)
                with open(_nf, "w") as _f: _f.write(_c)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["pipewire-0.3"]
        self.cpp_info.system_libs = ["dl", "pthread", "m"]
        # meson installs headers under <prefix>/include/pipewire-0.3/
        # and spa headers under <prefix>/include/spa-0.2/
        self.cpp_info.includedirs = ["include/pipewire-0.3", "include/spa-0.2", "include"]
