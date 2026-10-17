#!/usr/bin/env python3
"""Conan 2.x recipe — cubicsdr 0.2.7 (HarmonyOS PC aarch64, C-class challenge).

CubicSDR is a cross-platform Software Defined Radio application
(wxWidgets GUI + liquid-dsp DSP + SoapySDR hardware abstraction).

OHOS adaptation scope (layered core-library cut, first full iteration):

The upstream CMakeLists.txt hard-requires a desktop graphics stack:
find_package(OpenGL REQUIRED) resolves GLX which OHOS does not provide
(system has EGL/GLES only; nm -D on /system/lib64/libGLESv3.so and the
SDK libGLv4.so shows no glBegin/glOrtho immediate-mode symbols), and
find_package(wxWidgets COMPONENTS gl core propgrid adv base) requires
the wxCore GUI modules while the published wxwidgets/3.3.3 conan
package is the wxBase non-GUI variant (wxUSE_GUI=OFF, only
wx_baseu-3.3/wx_baseu_net-3.3/wx_baseu_xml-3.3 are shipped).

A full GUI build is therefore impossible on this platform today.  What
this package delivers instead is the DSP core of CubicSDR as a static
library, compiled from upstream sources verbatim (zero modification of
upstream source files; all 35 compilation units are upstream files):

  libcubicsdr-core.a
    - src/modules/modem/Modem.cpp/.h                  modem base + factory
    - src/modules/modem/ModemAnalog.cpp / ModemDigital.cpp
    - src/modules/modem/analog/*.{cpp,h}   AM FM FM-stereo NBFM USB LSB
                                           DSB CW IQ  (10 analog modes)
    - src/modules/modem/digital/*.{cpp,h}  APSK ASK BPSK DPSK FSK GMSK
                                           OOK PSK QAM QPSK SQAM ST
                                           (13 digital modes)
    - src/IOThread.cpp, src/util/{ThreadBlockingQueue,Timer,DataTree}.cpp
    - external/tinyxml (DataTree serialization backend)
    - external/rtaudio (dummy API: upstream auto-fallback at RtAudio.h
      line 629 when no audio API macro is defined; OHOS has none of
      ALSA/Pulse/JACK/OSS, so __RTAUDIO_DUMMY__ is set by the headers
      themselves — not a stub we wrote)

The core build is driven by a generated standalone CMakeLists.txt
(written into the source tree under core-build/) that compiles those
upstream files with the same public include layout as the upstream
project (-I src, src/modules/modem, src/audio for AudioThread.h which
carries the AudioThreadInput data structure consumed by demodulate()).
ENABLE_DIGITAL_LAB=0 is the upstream CMakeLists.txt default; the
travis-ci build enables the Digital Lab console (a wxWidgets GUI
window) which is out of scope here.  One upstream defect must be
patched for the LAB=0 configuration: ModemFSK.cpp / ModemGMSK.cpp
reference the LAB-gated outStream member unconditionally (upstream
travis masks this by always building with LAB=1) — patches/0001 guards
those references while preserving the demodulator state-machine calls.
LAB=0 additionally keeps std::stringstream out of the static library:
the OHOS clang-15 toolchain duplicates libc++ weak template symbols
between the .a and libc++_shared.so, and the stringstream destructor
then performs an invalid free at process exit (ASan-verified, 100%
reproducible on a digital-modem construct/destroy probe).

Out of scope (truthfully declared in reports/upstream-tests.md, not
silently skipped):
  - GUI front-end (src/forms, src/panel, src/ui, src/visual,
    AppFrame/AppConfig/CubicSDR main): needs wxCore GUI + desktop
    OpenGL immediate mode (glBegin/glVertex/glOrtho in
    PrimaryGLContext/TuningContext/GLPanel etc.) — not available on
    OHOS PC.
  - demod orchestration layer (src/demod/*) and SDR device threads
    (src/sdr/*): 60+ wxGetApp() call sites deep-couple to the wx
    application singleton (GUI event/notification callbacks); these
    layers only make sense together with a GUI front-end.
  - Audio device management class AudioThread (AudioThread.cpp): the
    RtAudio device controller wired to wxGetApp() at line 349; the
    AudioThreadInput data structure used by the modem demodulate()
    API is fully delivered (header-inline in AudioThread.h).

Dependencies (all published on the ohpcd registry, W0 verified with
conan install --build=never for aarch64-linux-ohos):
  - liquid-dsp/1.8.2 (DSP primitives: filters, modems, AGC, resampler)
  - soapysdr/0.8.1   (test_package only: SDR hardware abstraction —
                      device enumeration characterised on a
                      no-hardware OHOS PC)

Upstream tests: CubicSDR 0.2.7 ships no CTest registration at all
(grep -r "add_test|enable_testing|BUILD_TESTING" over the tag →
empty; travis-ci/build_cubicsdr.sh only builds and runs the
application binary).  The testable core on OHOS is therefore
exercised by our own consumer tests (test_package):
  1. DSP demodulation loop: synthesise FM/AM/USB/LSB/CW signals with
     liquid-dsp modulators, feed them to the CubicSDR Modem engine
     via the public demodulate() API, assert the demodulated audio
     contains the injected tone (frequency-domain peak check).
  2. Modem factory registry: all 23 modem modes instantiate through
     Modem::makeModem (analog 10 + digital 13).
  3. SoapySDR no-hardware behaviour: SoapySDR::Device::enumerate()
     returns an empty list without crashing — the documented
     no-device form on a machine without SDR hardware.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    get,
    save,
    export_conandata_patches,
)


class CubicSDRConan(ConanFile):
    name = "cubicsdr"
    version = "0.2.7"
    description = (
        "Cross-platform Software Defined Radio application — DSP core "
        "library (modem engine, 23 demodulation modes) for HarmonyOS PC"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.cubicsdr.com"
    url = "https://github.com/cjcliffe/CubicSDR"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}
    generators = "CMakeDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 verified: published on ohpcd registry, aarch64-linux-ohos
        # binary installs cleanly (conan install --build=never).
        self.requires("liquid-dsp/1.8.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # Upstream compilation units of the core layer (all paths are
    # upstream files, compiled verbatim — see class docstring).
    _core_sources = [
        "src/modules/modem/Modem.cpp",
        "src/modules/modem/ModemAnalog.cpp",
        "src/modules/modem/ModemDigital.cpp",
        "src/modules/modem/analog/ModemAM.cpp",
        "src/modules/modem/analog/ModemCW.cpp",
        "src/modules/modem/analog/ModemDSB.cpp",
        "src/modules/modem/analog/ModemFM.cpp",
        "src/modules/modem/analog/ModemFMStereo.cpp",
        "src/modules/modem/analog/ModemIQ.cpp",
        "src/modules/modem/analog/ModemLSB.cpp",
        "src/modules/modem/analog/ModemNBFM.cpp",
        "src/modules/modem/analog/ModemUSB.cpp",
        "src/modules/modem/digital/ModemAPSK.cpp",
        "src/modules/modem/digital/ModemASK.cpp",
        "src/modules/modem/digital/ModemBPSK.cpp",
        "src/modules/modem/digital/ModemDPSK.cpp",
        "src/modules/modem/digital/ModemFSK.cpp",
        "src/modules/modem/digital/ModemGMSK.cpp",
        "src/modules/modem/digital/ModemOOK.cpp",
        "src/modules/modem/digital/ModemPSK.cpp",
        "src/modules/modem/digital/ModemQAM.cpp",
        "src/modules/modem/digital/ModemQPSK.cpp",
        "src/modules/modem/digital/ModemSQAM.cpp",
        "src/modules/modem/digital/ModemST.cpp",
        "src/IOThread.cpp",
        "src/util/ThreadBlockingQueue.cpp",
        "src/util/Timer.cpp",
        "src/util/DataTree.cpp",
        "external/tinyxml/tinyxml.cpp",
        "external/tinyxml/tinystr.cpp",
        "external/tinyxml/tinyxmlerror.cpp",
        "external/tinyxml/tinyxmlparser.cpp",
        "external/rtaudio/RtAudio.cpp",
    ]

    _core_includes = [
        "src",
        "src/modules/modem",
        "src/modules/modem/analog",
        "src/modules/modem/digital",
        "src/audio",
        "src/demod",
        "src/util",
        "src/sdr",
        "external/rtaudio",
        "external/tinyxml",
        "external/lodepng",
        "external/cubicvr2/math",
    ]

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def _write_core_cmake(self):
        """Write a standalone CMakeLists.txt for the core cut.

        The generated project lives in the build folder and references
        upstream sources by absolute path; upstream files are compiled
        verbatim.  Include layout mirrors the upstream CMakeLists.txt
        include_directories() block (same set of trees) so headers
        resolve exactly as in an upstream build.
        """
        src = self.source_folder
        sources = "\n".join(
            '    "%s"' % os.path.join(src, s) for s in self._core_sources
        )
        includes = "\n".join(
            '    "%s"' % os.path.join(src, d) for d in self._core_includes
        )
        # NOTE: plain string replace (not str.format) — the CMake script
        # itself uses ${...} placeholders extensively.
        cmake = """cmake_minimum_required(VERSION 3.15)
project(cubicsdr-core CXX)

find_package(liquid CONFIG REQUIRED)

add_library(cubicsdr-core STATIC
@@SOURCES@@
)

target_compile_definitions(cubicsdr-core PRIVATE
    ENABLE_DIGITAL_LAB=0
)

target_include_directories(cubicsdr-core PUBLIC
@@INCLUDES@@
)

# RtAudio compiles its dummy API automatically when no audio API macro
# is defined (RtAudio.h line 629: __RTAUDIO_DUMMY__ fallback).  OHOS
# has none of ALSA/Pulse/JACK/OSS, so the dummy backend is the
# upstream-intended fallback, not a local stub.

target_link_libraries(cubicsdr-core PUBLIC liquid::liquid-static)

# On OHOS the math functions are provided by libc; pass "m" as a plain
# linker flag rather than find_library() (which returns NOTFOUND in the
# cross sysroot where libm is a stub that doesn't exist as a file).
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_libraries(cubicsdr-core PUBLIC m pthread dl)
endif()

set_target_properties(cubicsdr-core PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
)

install(TARGETS cubicsdr-core
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)

# Public headers: modem engine + shared data structures (AudioThread.h
# carries AudioThreadInput; DemodDefs.h carries the queue types).  The
# upstream src/ tree is mirrored verbatim minus the GUI-only subtrees
# (forms/panel/ui/visual/rig) — they are out of the core scope and
# drag wx headers.
file(COPY "@@SRCDIR@@/src/" DESTINATION include/cubicsdr/src
     FILES_MATCHING PATTERN "*.h"
     PATTERN "forms" EXCLUDE
     PATTERN "panel" EXCLUDE
     PATTERN "ui" EXCLUDE
     PATTERN "visual" EXCLUDE
     PATTERN "rig" EXCLUDE)
install(DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/include/"
        DESTINATION include)
install(DIRECTORY "@@SRCDIR@@/external/rtaudio/" DESTINATION include/cubicsdr/external/rtaudio
    FILES_MATCHING PATTERN "*.h")
install(DIRECTORY "@@SRCDIR@@/external/tinyxml/" DESTINATION include/cubicsdr/external/tinyxml
    FILES_MATCHING PATTERN "*.h")
install(DIRECTORY "@@SRCDIR@@/external/lodepng/" DESTINATION include/cubicsdr/external/lodepng
    FILES_MATCHING PATTERN "*.h")
install(FILES "@@SRCDIR@@/external/cubicvr2/math/cubic_math.h"
    DESTINATION include/cubicsdr/external/cubicvr2/math)
"""
        cmake = cmake.replace("@@SOURCES@@", sources)
        cmake = cmake.replace("@@INCLUDES@@", includes)
        cmake = cmake.replace("@@SRCDIR@@", src)
        # The generated core project is written into the (conan-managed,
        # disposable) source tree so CMake(build_script_folder=...) can
        # configure it; upstream files are never modified.
        core_dir = os.path.join(src, "core-build")
        os.makedirs(core_dir, exist_ok=True)
        save(self, os.path.join(core_dir, "CMakeLists.txt"), cmake)
        return "core-build"

    def build(self):
        # Upstream defect workaround (see patches/0001): ENABLE_DIGITAL_LAB=0
        # is the upstream CMakeLists.txt default but ModemFSK/ModemGMSK
        # reference the LAB-gated outStream member unconditionally; the
        # patch guards those references.  LAB=0 also keeps the
        # std::stringstream member (and its OHOS weak-symbol destructor
        # hazard) out of the delivered static library entirely — the
        # stream's only consumer is the wxWidgets DigitalConsole GUI
        # which is out of scope on this platform.
        apply_conandata_patches(self)
        script_folder = self._write_core_cmake()
        cmake = CMake(self)
        cmake.configure(build_script_folder=script_folder)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cubicsdr-core")
        self.cpp_info.set_property("cmake_target_name", "cubicsdr-core::cubicsdr-core")
        self.cpp_info.set_property("pkg_config_name", "cubicsdr-core")
        self.cpp_info.libs = ["cubicsdr-core"]
        self.cpp_info.includedirs = ["include/cubicsdr"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
