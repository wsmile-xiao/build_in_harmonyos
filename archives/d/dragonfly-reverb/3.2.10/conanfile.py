#!/usr/bin/env python3
"""Conan recipe for dragonfly-reverb 3.2.10 (LV2 DSP only).

Dragonfly Reverb is a bundle of free audio reverb effects. On OHOS we build
only the LV2 DSP plugins (no GUI) because OpenGL/X11/JACK are not available.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file


class DragonflyReverbConan(ConanFile):
    name = "dragonfly-reverb"
    version = "3.2.10"
    description = "Free audio reverb effect plugins (LV2 DSP only on OHOS)"
    license = "GPL-3.0-or-later"
    homepage = "https://michaelwillis.github.io/dragonfly-reverb/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "*.ttl",
            os.path.join(self.recipe_folder, "lv2"),
            os.path.join(self.export_sources_folder, "lv2"),
            keep_path=True,
        )

    def source(self):
        get(self, **self.conan_data["sources"]["dragonfly-reverb"], strip_root=True)
        dpf_dir = os.path.join(self.source_folder, "dpf")
        if not os.path.isfile(os.path.join(dpf_dir, "Makefile.base.mk")):
            get(
                self,
                **self.conan_data["sources"]["dpf"],
                destination=dpf_dir,
                strip_root=True,
            )

    def build(self):
        apply_conandata_patches(self)

        # OHOS lld 交叉编译下符号导出不稳定：version-script 的 global 强制导出
        # 解析不可靠（#11664 失败），-Wl,-E 依赖 visibility("default") 亦不稳定
        # （#12873 通过、#13413 失败）。改用 lld 的 --export-dynamic-symbol 按符号名
        # 显式强制导出，独立于 visibility 与 version-script 解析，最可靠。
        # 其余符号靠 DPF 的 -fvisibility=hidden 保持不导出，等价于原 local:* 效果。
        # 仅替换 --version-script=... 子串，原行 -Wl, 前缀保留，最终为
        # -Wl,--export-dynamic-symbol=lv2_descriptor。
        plugins_mk = os.path.join(self.source_folder, "dpf", "Makefile.plugins.mk")
        replace_in_file(
            self,
            plugins_mk,
            "--version-script=$(DPF_PATH)/utils/symbols/lv2.version",
            "--export-dynamic-symbol=lv2_descriptor",
        )

        for name in (
            "DragonflyEarlyReflections",
            "DragonflyHallReverb",
            "DragonflyPlateReverb",
            "DragonflyRoomReverb",
        ):
            os.makedirs(os.path.join(self.source_folder, "build", name), exist_ok=True)
            os.makedirs(os.path.join(self.source_folder, "bin", f"{name}.lv2"), exist_ok=True)
        os.makedirs(os.path.join(self.source_folder, "build", "common", "kiss_fft"), exist_ok=True)
        os.makedirs(os.path.join(self.source_folder, "build", "common", "freeverb"), exist_ok=True)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        self._ensure_lld_dependencies(cc)

        self.run(
            f'make CC="{cc}" CXX="{cxx}" AR="{ar}" '
            "CROSS_COMPILING=true HAVE_DGL=false UI_TYPE=none "
            "FORCE_NATIVE_AUDIO_FALLBACK=true SKIP_STRIPPING=true -j1",
            cwd=self.source_folder,
        )

    def _ensure_lld_dependencies(self, cc):
        """Ensure lld (OHOS SDK linker) can find its shared-lib dependencies.

        The OHOS SDK's lld binary depends on libxml2.so.16. Some CI runners
        don't have this library in the default linker search path, causing
        lld to fail at startup with "Error loading shared library
        libxml2.so.16". We locate the library within the SDK directory tree
        and prepend its directory to LD_LIBRARY_PATH.
        """
        if self.settings.os != "OHOS":
            return

        # Build candidate lib directories from the compiler path and SDK layout
        cc_bin = os.path.dirname(os.path.realpath(cc))
        candidate_dirs = [
            os.path.join(cc_bin, "..", "lib"),
            "/data/service/hnp/lib",
        ]
        candidate_dirs.extend(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
        )

        lib_dirs = []
        for d in candidate_dirs:
            d = os.path.normpath(d)
            if d in lib_dirs or not os.path.isdir(d):
                continue
            # Prefer directories that actually contain libxml2
            if glob.glob(os.path.join(d, "libxml2.so*")):
                lib_dirs.insert(0, d)
            else:
                lib_dirs.append(d)

        if not lib_dirs:
            return

        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = (
            ":".join(lib_dirs) + (f":{existing}" if existing else "")
        )
        self.output.info(
            f"LD_LIBRARY_PATH set for lld dependencies: {os.environ['LD_LIBRARY_PATH']}"
        )

    def package(self):
        src = self.source_folder
        bin_dir = os.path.join(src, "bin")
        copy(self, "*.so", bin_dir, os.path.join(self.package_folder, "lib", "lv2"), keep_path=True)
        copy(
            self,
            "*.ttl",
            os.path.join(self.export_sources_folder, "lv2"),
            os.path.join(self.package_folder, "lib", "lv2"),
            keep_path=True,
        )
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib/lv2"]
        self.cpp_info.resdirs = ["lib/lv2"]
