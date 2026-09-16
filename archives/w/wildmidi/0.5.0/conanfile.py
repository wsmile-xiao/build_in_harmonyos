#!/usr/bin/env python3
"""Conan recipe — wildmidi 0.5.0 (cmake).

WildMIDI: simple MIDI player library with a soft-synth (GUS patch set /
SoundFont2 / built-in OPL3 FM synthesizer).

HarmonyOS adaptation notes:
- Only the library (libWildMidi) is built; the command-line player is
  disabled (WANT_PLAYER=OFF) because OHOS has no ALSA/OSS/SNDIO audio
  stack (the WAV backend of the player is not the deliverable here).
- WANT_ALSA / WANT_OSS / WANT_SNDIO default OFF on non-Linux/BSD
  systems and depend on WANT_PLAYER, so they are inherently off — kept
  explicit below for documentation.
- No external dependencies: the built-in OPL3 FM synthesizer
  (Nuked-OPL3-fast + embedded DMXOPL bank) works without any patch
  files, SF2 support (TinySoundFont) is also embedded.
- The upstream CMakeLists declares cmake_minimum_required(VERSION 3.4)
  which CMake 4.x rejects → CMAKE_POLICY_VERSION_MINIMUM=3.5.
"""
import os
import glob
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class WildmidiConan(ConanFile):
    name = "wildmidi"
    version = "0.5.0"
    description = "Simple MIDI player library with soft-synth (GUS patches, SF2, built-in OPL3)"
    license = "LGPL-3.0-or-later"          # library is LGPL-3.0+ (player GPLv3, not built)
    homepage = "https://github.com/Mindwerks/wildmidi"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wildmidi only supports Linux/OHOS, got {self.settings.os}")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # no external deps: embedded OPL3 synth + TinySoundFont (SF2)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake: 设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK 的 llvm/bin 下只有 llvm-ar，没有 llvm-ranlib，而
        # ohos.toolchain.cmake 把 CMAKE_RANLIB 指向 llvm-ranlib。cmake 造
        # 静态库是 `<AR> qc ... && <RANLIB> <lib>`，于是 .o 全编得动、一造
        # .a 就 ENOENT，报错还不说是哪个程序找不到：
        #   Error running link command: no such file or directory
        # （知识库 E385；brotli/OpenCV/SuiteSparse 同坑）。
        # 返回 "" 表示不覆盖（SDK 自带就用它的）。
        import shutil
        sdk_bin = os.path.normpath(os.path.join(
            toolchain, "..", "..", "..", "llvm", "bin"))
        cand = os.path.join(sdk_bin, "llvm-ranlib")
        if os.path.isfile(cand):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _ohos_arch(self):
        arch_map = {"armv8": "arm64-v8a", "armv7": "armeabi-v7a", "x86": "x86", "x86_64": "x86_64"}
        arch = str(self.settings.arch)
        if arch not in arch_map:
            raise ConanInvalidConfiguration(f"不支持的 OHOS 架构: {arch}")
        return arch_map[arch]

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")
        shared = "ON" if self.options.shared else "OFF"
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH={}".format(self._ohos_arch()),
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            # library only: player needs ALSA/OSS audio backends absent on OHOS
            "-DWANT_PLAYER=OFF",
            "-DWANT_PLAYERSTATIC=OFF",
            "-DWANT_ALSA=OFF",
            "-DWANT_OSS=OFF",
            "-DWANT_SNDIO=OFF",
            "-DWANT_OPENAL=OFF",
            "-DWANT_DEVTEST=OFF",
            "-DBUILD_SHARED_LIBS={}".format(shared),
            # static-only build requires WANT_STATIC=ON, otherwise upstream
            # CMakeLists raises "Neither dynamic nor static library build is
            # selected."
            "-DWANT_STATIC={}".format("OFF" if self.options.shared else "ON"),
            # SF2 support via embedded TinySoundFont (no external deps)
            "-DWANT_SF2=ON",
            # upstream CMakeLists cmake_minimum_required(3.4) < 3.5, CMake 4.x needs this
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            # build upstream test_tokenize (runs on OHOS, links the static lib)
            "-DBUILD_TESTING=ON",
        ])
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs += ' -DCMAKE_RANLIB="{}"'.format(_rl)
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, self.source_folder, defs))
        self.run('cmake --build "{}" -- -j1'.format(bdir))
        # L1: run the upstream unit test natively on the OHOS device.
        # test_tokenize links libwildmidi-static and asserts config-line
        # tokenizing behaviour (quoted paths, empty quotes, comments...).
        self.run('ctest --test-dir "{}" --output-on-failure'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        if self.options.shared:
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue
            # Distinguish the harmless ".codesign section absent" case (typical
            # for fresh builds) from real llvm-objcopy failures. The former
            # must not abort the build; the latter must.
            try:
                proc = subprocess.run(
                    [objcopy, "--remove-section", ".codesign", so],
                    capture_output=True, text=True,
                )
            except FileNotFoundError:
                raise ConanException(
                    f"llvm-objcopy not found at {objcopy} — cannot strip .codesign")
            if proc.returncode != 0:
                stderr = (proc.stderr or "").strip()
                low = stderr.lower()
                if "not found" in low or "no such" in low or "does not exist" in low:
                    self.output.info(
                        f"no .codesign section in {so} (fresh build) — skip strip")
                else:
                    raise ConanException(
                        f"llvm-objcopy failed on {so} (rc={proc.returncode}): {stderr}")
            try:
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))
            except ConanException:
                raise ConanException(
                    f"binary-sign-tool failed while signing {so}")

    def package_info(self):
        self.cpp_info.libs = ["WildMidi"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "WildMidi")
        # exported target: WildMidi::libwildmidi (shared) / WildMidi::libwildmidi-static
        target = "libwildmidi-static" if not self.options.shared else "libwildmidi"
        self.cpp_info.set_property("cmake_target_name", "WildMidi::" + target)
        self.cpp_info.set_property("pkg_config_name", "wildmidi")
        self.cpp_info.system_libs = ["m"]
