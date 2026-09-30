import os
from shlex import quote as shell_quote

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class VkeybdConan(ConanFile):
    """vkeybd — X11/Tk virtual MIDI keyboard (tiwai/vkeybd).

    Upstream is a 2007-era hand-written Makefile project producing two binaries:

      * ``vkeybd``  — Tcl/Tk GUI that emits MIDI events to a sequencer backend.
      * ``sftovkb`` — pure-C SoundFont (SF2) -> vkeybd preset-list converter.

    Every adaptation is a **command-line Makefile override**; upstream source is
    never edited. Three measured facts drive them (all verified on device
    3QC0124C11000071, clang 15 aarch64-unknown-linux-ohos):

    1. The Makefile hardcodes ``TCL_VERSION = 8.4`` and an X11R6 prefix
       (``XLIB = -L/usr/X11R6/lib``, ``XINC = -I/usr/X11R6/include``). Neither
       exists on OHOS, and tk has no 8.6 release published at all, so the only
       coherent available pair is tcl/tk 9.0.3.2. The published tcl/tk packages
       export sonames ``tcl9.0`` / ``tcl9tk9.0``, not ``-ltcl8.4`` / ``-ltk8.4``,
       so TCLLIB/TKLIB are redirected to the real sonames.

    2. The AWE and MIDI backends ``#include <linux/soundcard.h>`` (the Linux OSS
       ioctl interface, absent from OHOS) and are genuinely unportable, so
       ``USE_AWE``/``USE_MIDI`` are switched off. The ALSA backend needs only
       ``alsa/asoundlib.h`` and is retained — this is a *declared degradation*
       (see notes.md), never a silent drop.

    3. CFLAGS is deliberately **not** overridden: the Makefile derives the
       ``-DVKB_TCLFILE`` / ``-DVKBLIB_DIR`` / ``-DVKB_USE_ALSA`` defines inside
       it. Instead the individual knobs it composes CFLAGS from (COPTFLAGS and
       the per-dependency include vars) are set, so those defines survive.
    """

    name = "vkeybd"
    version = "0.1.18d"
    license = "GPL-2.0-or-later"
    url = "https://github.com/tiwai/vkeybd"
    description = "X11/Tk virtual MIDI keyboard driving the ALSA sequencer"
    topics = ("x11", "midi", "alsa", "tcl", "tk", "audio")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # conandata holds a flat sources block; the explicit `filename` is what
        # lets get() recognise the codeload tarball as gzip. Without it the URL
        # has no .tar.gz suffix and get() guesses zip -> BadZipFile.
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("tcl/9.0.3.2", transitive_headers=True, transitive_libs=True)
        self.requires("tk/9.0.3.2", transitive_headers=True, transitive_libs=True)
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("alsa-lib/1.2.16")

    @property
    def _data_dir(self):
        return os.path.join(self.package_folder, "share", "vkeybd")

    def _make_args(self):
        tcl = self.dependencies["tcl"].cpp_info
        tk = self.dependencies["tk"].cpp_info
        x11 = self.dependencies["libx11"].cpp_info
        alsa = self.dependencies["alsa-lib"].cpp_info

        # COPTFLAGS: the Makefile's own CFLAGS base. Include dirs go here so the
        # -D defines the Makefile appends to CFLAGS are preserved (see class doc).
        incs = []
        for dep in ("tcl", "tk", "libx11", "alsa-lib"):
            incs.extend("-I%s" % d for d in self.dependencies[dep].cpp_info.includedirs)
        coptflags = " ".join(["-O2", "-fPIC", "-Wall"] + incs)

        # NOTE: every assignment is shell-quoted. A make variable assignment
        # passed unquoted ("COPTFLAGS=-O2 -fPIC -I/a -I/b") is word-split by the
        # shell, so make receives a bare "-fPIC" and friends as options and dies
        # with "make: invalid option -- /".
        def q(name, value):
            return shell_quote("{0}={1}".format(name, value))

        return [
            q("COPTFLAGS", coptflags),
            # Real sonames: published tcl/tk ship tcl9.0 / tcl9tk9.0.
            q("TCLLIB", "-ltcl9.0"),
            q("TKLIB", "-ltcl9tk9.0"),
            q("TCLINC", ""),
            q("TKINC", ""),
            # X11R6 does not exist on OHOS; the -L paths come from LDFLAGS below.
            q("XLIB", "-lX11"),
            q("XINC", ""),
            # ALSA is the only retained backend (AWE/MIDI need <linux/soundcard.h>).
            q("USE_AWE", "0"),
            q("USE_MIDI", "0"),
            q("USE_ALSA", "1"),
            q("USE_LASH", "0"),
            # Command-line EXTRALIB wins over the Makefile's `+=` lines, so both
            # the ALSA library and -ldl (upstream adds it unconditionally) are set.
            q("EXTRALIB", "-lasound -ldl"),
            q("LDFLAGS", " ".join(
                "-L" + d for d in (tcl.libdirs[0], tk.libdirs[0],
                                   x11.libdirs[0], alsa.libdirs[0]))),
            # vkeybd reads its Tk script from the compiled-in absolute path, so
            # VKBLIB_DIR must point at this package's data dir.
            q("VKBLIB_DIR", self._data_dir),
        ]

    def generate(self):
        # No toolchain helper: upstream is a bare Makefile, so every compiler
        # and linker flag travels through the make command line (see _make_args).
        self.output.info("vkeybd: pure Makefile project — flags passed via make vars")

    def build(self):
        args = self._make_args()
        # The Makefile lives in the source folder; with basic_layout(src_folder)
        # Conan runs commands in the build root, so make must be pointed at it.
        self.run("make -C {0} vkeybd sftovkb {1}".format(
            self.source_folder, " ".join(args)), env="conanbuild")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        datadir = self._data_dir
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(datadir, exist_ok=True)

        for binary in ("vkeybd", "sftovkb"):
            self.run("install -m 755 {0} {1}".format(
                os.path.join(self.source_folder, binary),
                os.path.join(bindir, binary)), env="conanbuild")

        # Runtime data the Tk script loads: the script itself, the preset list,
        # and the locale keymaps.
        for f in ("vkeybd.tcl", "vkeybd.list", "vkeybdmap", "vkeybdmap-de",
                  "vkeybdmap-es", "vkeybdmap-fr"):
            src = os.path.join(self.source_folder, f)
            if os.path.isfile(src):
                copy(self, f, src=self.source_folder, dst=datadir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # vkeybd resolves its Tk script through the compiled-in VKBLIB_DIR and
        # Tcl/Tk init scripts through the standard env vars of those packages.
        self.runenv_info.define("VKEYBD_DATADIR", self._data_dir)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl"]
