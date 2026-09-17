#!/usr/bin/env python3
"""Conan recipe for audiocd 26.04.3 on HarmonyOS PC.

audiocd (the audiocd-kio tarball from KDE Gear 26.04.3) is the KDE audio CD
ripping stack: upstream ships the audiocd:// KIO worker (kio_audiocd), the
KCM settings module (kcmaudiocd) and the reusable audiocdplugins encoder
library with its encoder plugins (wav/cda, flac, vorbis, lame, opus).

OHOS-specific adaptations (see patches/0001-ohos-adaptation.patch):
  - The KIO worker (audiocd.cpp) and the KCM module (kcmaudiocd/) are trimmed
    from the build: KF6::KIO / KF6::KCMUtils / KF6::Solid are not published to
    the ohpcd conan registry, and the worker's ripping core requires raw
    optical-drive access (cdparanoia cdda_* on a /dev/sr0 style device node)
    which does not exist on HarmonyOS PC (no optical drives).
  - The delivered artifacts on this platform are the audiocdplugins shared
    library (AudioCDEncoder base class + plugin loader) and the encoder
    plugins, which embedding applications use directly.
  - The encoder plugin ABI keeps the upstream create_audiocd_encoders symbol,
    but the sink type changes from KIO::WorkerBase to a self-contained
    AudioCDDataSink abstract interface (only data(const QByteArray&) is ever
    called by the encoders upstream).
  - KProcess (KCoreAddons) usage in the lame/opus encoder wrappers is ported
    to plain QProcess with explicit program/argument lists, dropping the
    KCoreAddons link requirement for those plugins.
  - The cdparanoia dependency (unpublished on ohpcd) is dropped: the only
    remaining consumer of its header needs the two fixed CD-DA frame-size
    constants, which now live in the self-contained audiocdcdio.h
    (identical Red Book values).
  - KCDDB include form switched from <KCDDB/CDInfo> to <kcddb/CDInfo> because
    the published libkcddb package installs the CamelCase forwarding headers
    under kcddb/ (KDEInstallDirs single-dir layout, libkcddb 26.04.3
    precedent).
  - Upstream registers no test suite (no tests/, autotests/ or add_test()
    anywhere in the tarball); consumer-side verification is provided by
    test_package (encoder round trips: wav/cda header+data via the sink,
    plugin discovery, KCDDB CDInfo fill-in).
  - Dependencies: qtbase/6.11.1 (Qt6 Core/Widgets/Network via KCddb6),
    kconfig/6.26.0, kcoreaddons/6.26.0, ki18n/6.26.0, kwidgetsaddons/6.26.0,
    libkcddb/26.04.3, flac/1.5.0, libvorbis/1.3.7 (pulls libogg),
    lame/3.100, opus/1.5.2, ecm/6.26.0 (build tool).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in the KDE platform list).
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake created manually because qtbase and the KF6
    packages use cmake_find_mode=none, so CMakeDeps does not add their
    lib/cmake builddirs to CMAKE_PREFIX_PATH.
  - Linker flags pin -Wl,-z,max-page-size=0x1000: the default lld 0x10000
    page size can place .dynsym/.dynstr into separate high-address RW LOAD
    segments which the OHOS musl loader refuses to mmap (dlopen fails with
    "Permission denied"); the 4K layout loads fine.
  - No post-install patchelf sweep on the produced libraries: the OHOS
    patchelf rewrites the program headers into that same rejected
    multi-RW-LOAD layout (verified: 4-LOAD 27KB libaudiocdplugins.so ->
    patchelf --replace-needed -> 7-LOAD 198KB, dlopen Permission denied).
    Absolute-path DT_NEEDED entries are left in place instead (libkcddb
    26.04.3 precedent, whose published package keeps cache-absolute
    DT_NEEDED entries and passes CI).
"""
import glob
import shutil
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class AudiocdConan(ConanFile):
    name = "audiocd"
    version = "26.04.3"
    description = "KDE audio CD ripping stack - audiocdplugins encoder library with wav/flac/vorbis/lame/opus encoder plugins (KIO worker and KCM trimmed on OHOS)"
    license = "GPL-2.0-or-later AND GFDL-1.2-or-later"
    homepage = "https://invent.kde.org/multimedia/audiocd"
    url = "https://download.kde.org/stable/release-service/26.04.3/src/audiocd-kio-26.04.3.tar.xz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("ki18n/6.26.0")
        self.requires("kwidgetsaddons/6.26.0")
        self.requires("libkcddb/26.04.3")
        # encoder plugin codecs
        self.requires("flac/1.5.0")
        self.requires("libvorbis/1.3.7")
        self.requires("lame/3.100")
        self.requires("opus/1.5.2")
        # flac/1.5.0 pins libogg/1.3.5 while libvorbis/1.3.7 pins libogg/1.3.6;
        # force the newer one for the whole graph (libogg has a stable C ABI,
        # the FLAC package links fine against 1.3.6).
        self.requires("libogg/1.3.6", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Skip translation catalog generation: the CI worker's msgfmt
        # (gettext 0.22.5 in /usr/local) fails to load its own libintl.so.8
        # (alkimia 8.2.1 recipe precedent).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        # OHOS loader workaround: the default lld max-page-size of 0x10000
        # places .dynsym/.dynstr into separate high-address RW LOAD segments;
        # the OHOS musl loader refuses to mmap that layout ("Permission
        # denied"). Pinning the page size to 0x1000 restores the regular
        # 4-LOAD layout that loads fine (verified with a dlopen probe).
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_MODULE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
        # KF6DocTools is optional upstream; never pull it (unpublished)
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "TRUE"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so the
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ...) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        # Help the Module-mode finders (FindFLAC / FindOggVorbis, and the
        # Cdparanoia/worker parts are trimmed) locate the conan-provided
        # codec libraries and headers.
        flac = self.dependencies.get("flac")
        if flac and flac.package_folder:
            tc.variables["FLAC_INCLUDE_DIR"] = os.path.join(
                flac.package_folder, "include"
            )
            flac_lib = None
            for cand in (
                os.path.join(flac.package_folder, "lib", "libFLAC.so"),
                os.path.join(flac.package_folder, "lib", "libFLAC.a"),
            ):
                if os.path.exists(cand):
                    flac_lib = cand
                    break
            if flac_lib:
                tc.variables["FLAC_LIBRARY"] = flac_lib
        vorbis = self.dependencies.get("libvorbis")
        if vorbis and vorbis.package_folder:
            tc.variables["VORBIS_INCLUDE_DIR"] = os.path.join(
                vorbis.package_folder, "include"
            )
            for var, lib in (
                ("VORBIS_LIBRARY", "libvorbis.so"),
                ("VORBISFILE_LIBRARY", "libvorbisfile.so"),
                ("VORBISENC_LIBRARY", "libvorbisenc.so"),
            ):
                cand = os.path.join(vorbis.package_folder, "lib", lib)
                cand_a = cand[:-3] + ".a"
                for c in (cand, cand_a):
                    if os.path.exists(c):
                        tc.variables[var] = c
                        break
        ogg = self.dependencies.get("libogg")
        if ogg and ogg.package_folder:
            tc.variables["OGG_INCLUDE_DIR"] = os.path.join(
                ogg.package_folder, "include"
            )
            for cand in (
                os.path.join(ogg.package_folder, "lib", "libogg.so"),
                os.path.join(ogg.package_folder, "lib", "libogg.a"),
            ):
                if os.path.exists(cand):
                    tc.variables["OGG_LIBRARY"] = cand
                    break
        # HAVE_LIBVORBISENC2: the upstream FindOggVorbis module runs
        # check_library_exists(vorbis vorbis_bitrate_addblock) which links a
        # test program; the cross-link fails resolving the transitive
        # libogg dependency (no rpath), not because the symbol is missing.
        # vorbis_bitrate_addblock exists since libvorbis 1.1 (2004) and is
        # exported by the conan libvorbis 1.3.7 package (nm -D verified), so
        # pin the result.
        tc.variables["HAVE_LIBVORBISENC2"] = "1"

        tc.generate()

        # qtbase and the KF6/libkcddb packages use cmake_find_mode=none, so
        # CMakeDeps doesn't generate conan_cmakedeps_paths.cmake. Create it
        # manually to add their lib/cmake dirs to CMAKE_PREFIX_PATH
        # (libkcddb 26.04.3 / alkimia 8.2.1 recipe precedent).
        lines = []
        for dep_name in (
            "qtbase",
            "kconfig",
            "kcoreaddons",
            "ki18n",
            "kwidgetsaddons",
            "libkcddb",
            "flac",
            "libvorbis",
            "libogg",
            "lame",
            "opus",
        ):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                pkg = dep.package_folder
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
                for libdir in ("lib", "lib64"):
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/{libdir}")'
                    )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")'
                )
                bindir = os.path.join(pkg, "bin")
                if os.path.isdir(bindir):
                    lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{bindir}")')
        if ecm:
            ecm_pkg = ecm.package_folder
            ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PROGRAM_PATH "{ecm_pkg}/bin")')
        # KCddb6 exports its own cmake config under lib/cmake/KCddb6
        kcddb = self.dependencies.get("libkcddb")
        if kcddb and kcddb.package_folder:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{kcddb.package_folder}/lib/cmake/KCddb6")'
            )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            lines.append(
                f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase.package_folder}/lib")'
            )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        # Host tools shipped by the conan packages (kconfig_compiler from
        # kconfig, moc/uic/rcc from qtbase) are OHOS binaries: they need the
        # compatible libc++_shared from /system/lib64 plus the dependency
        # lib dirs on LD_LIBRARY_PATH (kconfig 6.26.0 / libkcddb 26.04.3
        # recipe precedent).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own AudioCdPlugins cmake config; the
        # library is the consumable deliverable. Use cmake_find_mode=none so
        # CMakeDeps does not shadow the upstream-installed configs.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["audiocdplugins"]
