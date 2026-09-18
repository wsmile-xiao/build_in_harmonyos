#!/usr/bin/env python3
"""Conan recipe for cursynth 1.5 — GNU cursynth, a polyphonic synthesizer that
runs in the terminal.

cursynth is a single-binary Autotools project.  It bundles RtAudio, RtMidi,
mopo and cJSON as convenience libraries and installs the `cursynth` CLI plus
its patch data files (share/cursynth/patches/*.mite).

Dependencies:
  - ncurses/6.6 (wide-character curses, terminal UI; its recipe builds the
    library static — R26)

OHOS adaptations:
  - patches/ (conandata.yml):
      * config.sub (top level + rtaudio + rtmidi): accept the `linux-ohos`
        triplet (E007 — the 2014-vintage config.sub does not know HarmonyOS).
      * configure (top level + mopo + rtaudio + rtmidi): drop the `umask 077`
        wrapper around the config.status temp-dir creation (E114 — on HMDFS
        the 0700 directory ends up with a mapped uid/setgid combination the
        build user cannot write into, so `subs1.awk: Permission denied`).
      * rtmidi/configure: do not hard-fail when ALSA is missing — fall
        through to RtMidi's no-API build.
      * src/cursynth_gui.cpp: fall back to untranslated strings when NLS is
        off (OHOS ships a <libintl.h> stub without prototypes and no libintl).
  - build-time (see _port_rtaudio_oss below): the bundled rtaudio/RtAudio.cpp
    ships with CRLF line endings, so the patch pipeline's LF-normalised
    unified diff cannot be applied against it (refresh-patch dry-run fails on
    every hunk).  Its OSS back-end is therefore ported in place: compile
    against the classic kernel <sys/soundcard.h> (the bundled back-end was
    written against OSS 4), build without a MIDI API when ALSA is missing,
    and two libc/C++17 portability fixes (pthread_testcancel, abs()).

Runtime notes:
  - OSS is the only audio API that needs no external library on OHOS (no
    ALSA/PulseAudio/JACK).  A system without /dev/dsp reports
    "No audio devices found." and exits 0.
  - NLS is disabled: the terminal UI stays English.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# --------------------------------------------------------------------------
# rtaudio/RtAudio.cpp classic-OSS port (applied at build time, see docstring).
# The back-end was written against the OSS 4 API; classic kernel headers
# (linux/soundcard.h, as shipped with musl based systems) only describe the
# classic ioctl set.  The OSS 4 code paths are kept verbatim behind
# `#ifdef SNDCTL_SYSINFO` and classic-API fallbacks are added in `#else`.
# --------------------------------------------------------------------------
_RTAUDIO_COMPAT_BLOCK = """/* OSS_CLASSIC_COMPAT_APPLIED
 * This back-end was written against the OSS 4 API.  Classic kernel headers
 * (linux/soundcard.h, as shipped with musl based systems) only describe the
 * classic ioctl set, so provide the OSS 4 names used by this file in terms
 * of their classic equivalents.  The PCM_CAP_* values are private to this
 * translation unit: they only appear in the local capability word assembled
 * in the fallback paths below and are never passed to a driver.
 */
#ifndef SNDCTL_SYSINFO
  #define PCM_CAP_OUTPUT 0x0001
  #define PCM_CAP_INPUT  0x0002
  #define PCM_CAP_DUPLEX 0x0004

  /* OSS 4 hint for the "other endian" 16 bit format; the classic headers
     only define AFMT_S16_NE. */
  #ifndef AFMT_S16_OE
    #if AFMT_S16_NE == AFMT_S16_LE
      #define AFMT_S16_OE AFMT_S16_BE
    #else
      #define AFMT_S16_OE AFMT_S16_LE
    #endif
  #endif
  /* 24/32-bit and float formats were introduced by OSS 4; mark them
     unsupported (a zero bit never matches a device capability mask). */
  #ifndef AFMT_S24_NE
    #define AFMT_S24_NE 0
    #define AFMT_S24_OE 0
  #endif
  #ifndef AFMT_S24_LE
    #define AFMT_S24_LE 0
    #define AFMT_S24_BE 0
  #endif
  #ifndef AFMT_S32_NE
    #define AFMT_S32_NE 0
    #define AFMT_S32_OE 0
  #endif
  #ifndef AFMT_S32_LE
    #define AFMT_S32_LE 0
    #define AFMT_S32_BE 0
  #endif
  #ifndef AFMT_FLOAT
    #define AFMT_FLOAT 0
  #endif
  /* OSS 4 renamed DSP_RESET to DSP_HALT. */
  #ifndef SNDCTL_DSP_HALT
    #define SNDCTL_DSP_HALT SNDCTL_DSP_RESET
  #endif

  /* Descriptor of the single classic device node, matching the fields this
     file reads from the OSS 4 oss_audioinfo structure. */
  struct OssClassicAudioInfo {
    const char* devnode;
    const char* name;
    unsigned int caps;          /* private PCM_CAP_* bits */
    int max_channels;
    unsigned long iformats;     /* AFMT_* mask */
    int nrates;
    int rates[32];
    int min_rate;
    int max_rate;
  };
#endif
"""

_CLASSIC_GET_DEVICE_COUNT = """#else
  /* Classic OSS has no enumeration ioctl; probe the default device node. */
  int fd = open( "/dev/dsp", O_WRONLY | O_NONBLOCK, 0 );
  if ( fd == -1 ) return 0;
  close( fd );
  return 1;
#endif"""

_CLASSIC_GET_DEVICE_INFO = """#else
  /* Classic kernel OSS header: single device node, no OSS 4 info ioctls. */
  if ( device != 0 ) {
    errorText_ = "RtApiOss::getDeviceInfo: device ID is invalid!";
    error( RtError::INVALID_USE );
    return info;
  }

  int fd = open( "/dev/dsp", O_WRONLY | O_NONBLOCK, 0 );
  if ( fd == -1 ) {
    errorText_ = "RtApiOss::getDeviceInfo: error opening '/dev/dsp'.";
    error( RtError::WARNING );
    return info;
  }

  OssClassicAudioInfo ainfo;
  ainfo.devnode = "/dev/dsp";
  ainfo.name = "default";
  ainfo.caps = PCM_CAP_OUTPUT;
  ainfo.max_channels = 2;
  ainfo.iformats = 0;
  ainfo.nrates = 0;
  ainfo.min_rate = 8000;
  ainfo.max_rate = 48000;

  int caps = 0;
  if ( ioctl( fd, SNDCTL_DSP_GETCAPS, &caps ) != -1 && ( caps & DSP_CAP_DUPLEX ) )
    ainfo.caps |= PCM_CAP_INPUT | PCM_CAP_DUPLEX;

  int channels = 2;
  if ( ioctl( fd, SNDCTL_DSP_CHANNELS, &channels ) != -1 && channels > 0 )
    ainfo.max_channels = channels;

  int fmts = 0;
  if ( ioctl( fd, SNDCTL_DSP_GETFMTS, &fmts ) != -1 )
    ainfo.iformats = (unsigned long) fmts;

  /* The classic API has no rate table; validate each standard rate by
     programming it and reading it back. */
  for ( unsigned int k = 0; k < MAX_SAMPLE_RATES && ainfo.nrates < 32; k++ ) {
    int rate = SAMPLE_RATES[k];
    if ( ioctl( fd, SNDCTL_DSP_SPEED, &rate ) != -1 && rate == (int) SAMPLE_RATES[k] )
      ainfo.rates[ainfo.nrates++] = SAMPLE_RATES[k];
  }
  close( fd );
#endif"""

_CLASSIC_PROBE_DEVICE_OPEN = """#else
  /* Classic kernel OSS header: single default device node. */
  if ( device != 0 ) {
    errorText_ = "RtApiOss::probeDeviceOpen: device ID is invalid!";
    return FAILURE;
  }

  OssClassicAudioInfo ainfo;
  ainfo.devnode = "/dev/dsp";
  ainfo.name = "default";
  ainfo.caps = PCM_CAP_OUTPUT;
  ainfo.max_channels = 2;
  ainfo.iformats = 0;
  ainfo.nrates = 0;
  ainfo.min_rate = 8000;
  ainfo.max_rate = 48000;

  int result = 0;
  int probefd = open( "/dev/dsp", O_WRONLY | O_NONBLOCK, 0 );
  if ( probefd != -1 ) {
    int caps = 0;
    if ( ioctl( probefd, SNDCTL_DSP_GETCAPS, &caps ) != -1 && ( caps & DSP_CAP_DUPLEX ) )
      ainfo.caps |= PCM_CAP_INPUT | PCM_CAP_DUPLEX;
    close( probefd );
  }
#endif"""


def _find(lines, marker, start=0):
    for i in range(start, len(lines)):
        if marker in lines[i]:
            return i
    raise ConanInvalidConfiguration(f"cursynth: RtAudio.cpp marker not found: {marker}")


def _port_rtaudio_oss(source_folder):
    """Apply the classic-OSS port to rtaudio/RtAudio.cpp (idempotent)."""
    path = os.path.join(source_folder, "rtaudio", "RtAudio.cpp")
    with open(path, encoding="utf-8", errors="surrogateescape", newline="") as f:
        src = f.read()
    if "OSS_CLASSIC_COMPAT_APPLIED" in src and '#include <sys/soundcard.h>' in src:
        return
    assert '#include "soundcard.h"' in src
    src = src.replace('#include "soundcard.h"', '#include <sys/soundcard.h>')

    # OHOS musl provides no pthread cancellation point; make it a no-op
    # (same approach as the merged zam-plugins RtAudio port — R8 libc probe
    # exception, justified in the PR description).
    src = src.replace(
        "// Static variable definitions.",
        "// Static variable definitions.\n"
        "#ifdef __OHOS__\n"
        "#define pthread_testcancel() ((void)0)\n"
        "#endif\n", 1)
    assert "#define pthread_testcancel() ((void)0)" in src

    # c++17/libc++: abs(unsigned) is ambiguous; srate/sampleRate are small
    # numbers well within int range, make the subtraction signed again.
    src = src.replace("abs( srate - sampleRate )", "abs( srate - (int) sampleRate )")
    assert "abs( srate - (int) sampleRate )" in src

    lines = src.split("\n")

    anchor = _find(lines, "static void *ossCallbackHandler(void * ptr);")
    g0 = _find(lines, "RtApiOss :: getDeviceCount")
    g_body = _find(lines, 'int mixerfd = open( "/dev/mixer", O_RDWR, 0 );', g0)
    g_ret = _find(lines, "  return sysinfo.numaudios;", g0)
    assert lines[g_ret + 1].strip() == "}"
    d0 = _find(lines, "RtApiOss :: getDeviceInfo")
    d_mix = _find(lines, 'int mixerfd = open( "/dev/mixer", O_RDWR, 0 );', d0)
    d_shared = _find(lines, "  // Probe channels", d0)
    assert lines[d_shared - 1].strip() == "" and lines[d_shared - 2].strip() == "}"
    p0 = _find(lines, "RtApiOss :: probeDeviceOpen", d0)
    p_mix = _find(lines, 'int mixerfd = open( "/dev/mixer", O_RDWR, 0 );', p0)
    p_shared = _find(lines, "  int flags = 0;", p0)
    assert lines[p_shared - 1].strip() == ""

    inserts = [
        (p_shared - 1, _CLASSIC_PROBE_DEVICE_OPEN.split("\n")),
        (p_mix, ["#ifdef SNDCTL_SYSINFO"]),
        (d_shared - 1, _CLASSIC_GET_DEVICE_INFO.split("\n")),
        (d_mix, ["#ifdef SNDCTL_SYSINFO"]),
        (g_ret + 1, _CLASSIC_GET_DEVICE_COUNT.split("\n")),
        (g_body, ["#ifdef SNDCTL_SYSINFO"]),
        (anchor, _RTAUDIO_COMPAT_BLOCK.split("\n") + [""]),
    ]
    for pos, block in sorted(inserts, key=lambda t: -t[0]):
        lines[pos:pos] = block

    out = "\n".join(lines)
    if src.count("\r\n") >= src.count("\n") // 2 and src.count("\r\n") > 0:
        # RtAudio.cpp ships with CRLF line endings; re-normalise the whole
        # file to CRLF so only the real content changes differ from upstream.
        out = out.replace("\r\n", "\n").replace("\n", "\r\n")
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(out)


class CursynthConan(ConanFile):
    name = "cursynth"
    version = "1.5"
    description = "GNU cursynth - polyphonic MIDI synthesizer that runs in the terminal"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/cursynth/"
    url = ""  # CI fills

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.6")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cursynth is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # In-source build: the top Makefile installs `patches_DATA =
        # patches/*.mite` whose glob only resolves inside the source tree
        # (out-of-source builds fail with "No rule to make target
        # 'patches/*.mite'"); same workaround as the alpine 2.26 port.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # CRLF + LF-normalised patches do not mix: port RtAudio.cpp before the
        # (LF-based) patches are applied.  Idempotent.
        _port_rtaudio_oss(self.source_folder)
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsDeps: feed -I/-L/-l from ncurses into configure/make
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # OSS is the only audio API that needs no external library
            # (ALSA / PulseAudio / JACK do not exist on OHOS)
            "--with-oss",
            # OHOS has no libintl: build without message catalogues
            "--disable-nls",
            # E007: config.sub is patched to accept linux-ohos; build == host
            # keeps configure in native mode so its run tests are meaningful
            "--build=aarch64-unknown-linux-ohos",
            "--host=aarch64-unknown-linux-ohos",
        ])
        # NOTE: do NOT pass env= to tc.generate() — it *replaces* the whole
        # toolchain environment (losing CC/CXX/CFLAGS).  The CONFIG_SHELL/SHELL
        # routing is done with command-line assignments in build() instead,
        # which win over the profile [buildenv].
        tc.generate()

    def build(self):
        # §12.38①/E386: the profile [buildenv] points CONFIG_SHELL/SHELL at
        # the hnp bash whose getcwd() hangs on HMDFS build directories
        # ("working directory cannot be determined").  The buildenv script
        # aggregates after the toolchain env, so the override must happen on
        # the command line of each invocation (akku 1.1.0 precedent).
        # ac_cv_func_malloc/realloc_0_nonnull: AC_FUNC_MALLOC runs a test
        # program whose outcome differs between workers (some CI sandboxes
        # refuse to exec freshly built unsigned conftests), flipping config.h
        # into `#define malloc rpl_malloc` which breaks the libc++ headers.
        # Pin the correct values so configure is deterministic everywhere.
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            configure_path = os.path.join(self.build_folder, "configure")
        self.run(
            f'ac_cv_func_malloc_0_nonnull=yes ac_cv_func_realloc_0_nonnull=yes '
            f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh "{configure_path}" '
            f"--prefix=/ "
            f"'--bindir=${{prefix}}/bin' "
            f"'--sbindir=${{prefix}}/bin' "
            f"'--libdir=${{prefix}}/lib' "
            f"'--includedir=${{prefix}}/include' "
            f"'--oldincludedir=${{prefix}}/include' "
            f"--with-oss --disable-nls "
            f"--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos",
            env="conanbuild",
        )
        autotools = Autotools(self)
        # R9: single job - parallel make hits the HMDFS jobserver fifo EPERM (E074)
        autotools.make(args=["-j1", "MAKEINFO=true", "SHELL=/bin/sh"])
        # Upstream ships no automated tests (no TESTS/check_PROGRAMS in the
        # tarball); run the hook anyway so the build stays verifiable where a
        # suite is added.  MAKEINFO=true: texinfo is not available.
        autotools.make(target="check", args=["MAKEINFO=true", "SHELL=/bin/sh"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true", "SHELL=/bin/sh"])

    def package_info(self):
        # Standalone binary, no library info
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
