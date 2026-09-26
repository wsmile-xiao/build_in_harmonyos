#!/usr/bin/env python3
"""Conan recipe for libeXaDrums 0.7.0 (OHOS aarch64 adaptation).

Upstream: https://github.com/SpintroniK/libeXaDrums  (BSD-3-Clause)

OHOS adaptations
================
* The library hard-requires ALSA at build AND link time (configure.ac used
  PKG_CHECK_MODULES([alsa]) and Sound/Alsa/Alsa.cpp links against libsndfile-like
  ALSA PCM API).  OHOS has no ALSA and it is not published on ohpcd, so we bundle
  a *static stub* (libasound.a + alsa/asoundlib.h): every snd_* symbol is a no-op,
  snd_pcm_open() succeeds and GetDevices() returns one synthetic device so the
  library links unchanged and the public API is fully usable.  The stub is linked
  INTO libexadrums.so, so consumers never need a system libasound.
* PKG_CHECK_MODULES([alsa]/[tinyxml2]/[minizip]) is removed by a patch; the real
  dependencies (tinyxml2, minizip) are injected through Conan AutotoolsDeps, and
  the ALSA stub through extra_cxxflags/extra_ldflags.
* -lstdc++fs -latomic removed (absent in OHOS clang/libc++).
* alsa dropped from exadrums.pc Requires.private (it is a stub).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain

# ---------------------------------------------------------------------------
# ALSA stub: header + C implementation.  Bundled so the library builds/links on
# OHOS without a real sound backend (audio playback becomes a no-op).
# ---------------------------------------------------------------------------
_ALSA_HEADER = r"""#ifndef ALSA_ASOUNDLIB_H_STUB
#define ALSA_ASOUNDLIB_H_STUB

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

typedef struct _snd_pcm             { int _dummy; } snd_pcm_t;
typedef struct _snd_pcm_hw_params  { int _dummy; } snd_pcm_hw_params_t;
typedef struct _snd_pcm_sw_params  { int _dummy; } snd_pcm_sw_params_t;
typedef struct _snd_pcm_info       { int _dummy; } snd_pcm_info_t;
typedef struct _snd_ctl            { int _dummy; } snd_ctl_t;
typedef struct _snd_ctl_card_info  { int _dummy; } snd_ctl_card_info_t;

typedef enum _snd_pcm_stream {
    SND_PCM_STREAM_PLAYBACK = 0,
    SND_PCM_STREAM_CAPTURE  = 1
} snd_pcm_stream_t;

typedef enum _snd_pcm_format {
    SND_PCM_FORMAT_UNKNOWN = -1,
    SND_PCM_FORMAT_S8      = 0,
    SND_PCM_FORMAT_S16_LE  = 2
} snd_pcm_format_t;

typedef enum _snd_pcm_access {
    SND_PCM_ACCESS_MMAP_INTERLEAVED = 0,
    SND_PCM_ACCESS_RW_INTERLEAVED   = 3
} snd_pcm_access_t;

typedef long          snd_pcm_sframes_t;
typedef unsigned long snd_pcm_uframes_t;

/* card / control */
int  snd_card_next(int *card);
int  snd_ctl_open(snd_ctl_t **handle, const char *name, int mode);
int  snd_ctl_close(snd_ctl_t *handle);
int  snd_ctl_card_info(snd_ctl_t *handle, snd_ctl_card_info_t *info);
const char *snd_ctl_card_info_get_name(snd_ctl_card_info_t *obj);
void snd_ctl_card_info_alloca(snd_ctl_card_info_t **ptr);
int  snd_ctl_pcm_next_device(snd_ctl_t *ctl, int *dev);
int  snd_ctl_pcm_info(snd_ctl_t *ctl, snd_pcm_info_t *info);

/* pcm info */
void snd_pcm_info_alloca(snd_pcm_info_t **ptr);
void snd_pcm_info_set_device(snd_pcm_info_t *obj, unsigned int val);
void snd_pcm_info_set_subdevice(snd_pcm_info_t *obj, unsigned int val);
void snd_pcm_info_set_stream(snd_pcm_info_t *obj, snd_pcm_stream_t val);

/* pcm */
int  snd_pcm_open(snd_pcm_t **pcm, const char *name, snd_pcm_stream_t stream, int mode);
int  snd_pcm_close(snd_pcm_t *pcm);
int  snd_pcm_drain(snd_pcm_t *pcm);
int  snd_pcm_drop(snd_pcm_t *pcm);
int  snd_pcm_prepare(snd_pcm_t *pcm);
int  snd_pcm_resume(snd_pcm_t *pcm);
int  snd_pcm_start(snd_pcm_t *pcm);
snd_pcm_sframes_t snd_pcm_writei(snd_pcm_t *pcm, const void *buffer, snd_pcm_uframes_t size);
snd_pcm_stream_t snd_pcm_stream(snd_pcm_t *pcm);

/* hw params */
void snd_pcm_hw_params_alloca(snd_pcm_hw_params_t **ptr);
int  snd_pcm_hw_params_any(snd_pcm_t *pcm, snd_pcm_hw_params_t *params);
int  snd_pcm_hw_params_set_rate_resample(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, unsigned int val);
int  snd_pcm_hw_params_set_access(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, snd_pcm_access_t val);
int  snd_pcm_hw_params_set_format(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, snd_pcm_format_t val);
int  snd_pcm_hw_params_set_channels(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, unsigned int val);
int  snd_pcm_hw_params_set_rate_near(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, unsigned int *val, int *dir);
int  snd_pcm_hw_params_set_buffer_time_near(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, unsigned int *val, int *dir);
int  snd_pcm_hw_params_get_buffer_size(snd_pcm_hw_params_t *params, snd_pcm_uframes_t *val);
int  snd_pcm_hw_params_set_period_time_near(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, unsigned int *val, int *dir);
int  snd_pcm_hw_params_get_period_size(snd_pcm_hw_params_t *params, snd_pcm_uframes_t *val, int *dir);
int  snd_pcm_hw_params(snd_pcm_t *pcm, snd_pcm_hw_params_t *params);

/* sw params */
void snd_pcm_sw_params_alloca(snd_pcm_sw_params_t **ptr);
int  snd_pcm_sw_params_current(snd_pcm_t *pcm, snd_pcm_sw_params_t *params);
int  snd_pcm_sw_params_set_start_threshold(snd_pcm_t *pcm, snd_pcm_sw_params_t *params, snd_pcm_uframes_t val);
int  snd_pcm_sw_params_set_avail_min(snd_pcm_t *pcm, snd_pcm_sw_params_t *params, snd_pcm_uframes_t val);
int  snd_pcm_sw_params(snd_pcm_t *pcm, snd_pcm_sw_params_t *params);

const char *snd_strerror(int errnum);

#ifdef __cplusplus
}
#endif

#endif /* ALSA_ASOUNDLIB_H_STUB */
"""

_ALSA_STUB_C = r"""#include "alsa/asoundlib.h"
#include <stdlib.h>
#include <string.h>

static const char STUB_NAME[] = "OHOS ALSA Stub";
static const char STUB_ERR[]  = "OHOS ALSA stub";

void snd_pcm_hw_params_alloca(snd_pcm_hw_params_t **ptr){ *ptr = (snd_pcm_hw_params_t*)calloc(1, sizeof(snd_pcm_hw_params_t)); }
void snd_pcm_sw_params_alloca(snd_pcm_sw_params_t **ptr){ *ptr = (snd_pcm_sw_params_t*)calloc(1, sizeof(snd_pcm_sw_params_t)); }
void snd_pcm_info_alloca(snd_pcm_info_t **ptr){ *ptr = (snd_pcm_info_t*)calloc(1, sizeof(snd_pcm_info_t)); }
void snd_ctl_card_info_alloca(snd_ctl_card_info_t **ptr){ *ptr = (snd_ctl_card_info_t*)calloc(1, sizeof(snd_ctl_card_info_t)); }

int snd_card_next(int *card){ if (*card >= 0) *card = -1; return 0; }

int snd_ctl_open(snd_ctl_t **handle, const char *name, int mode){ (void)name; (void)mode; *handle = (snd_ctl_t*)calloc(1, 1); return 0; }
int snd_ctl_close(snd_ctl_t *handle){ free(handle); return 0; }
int snd_ctl_card_info(snd_ctl_t *handle, snd_ctl_card_info_t *info){ (void)handle; (void)info; return 0; }
const char *snd_ctl_card_info_get_name(snd_ctl_card_info_t *obj){ (void)obj; return STUB_NAME; }
int snd_ctl_pcm_next_device(snd_ctl_t *ctl, int *dev){ (void)ctl; if (*dev >= 0) *dev = -1; return 0; }
int snd_ctl_pcm_info(snd_ctl_t *ctl, snd_pcm_info_t *info){ (void)ctl; (void)info; return 0; }

void snd_pcm_info_set_device(snd_pcm_info_t *obj, unsigned int val){ (void)obj; (void)val; }
void snd_pcm_info_set_subdevice(snd_pcm_info_t *obj, unsigned int val){ (void)obj; (void)val; }
void snd_pcm_info_set_stream(snd_pcm_info_t *obj, snd_pcm_stream_t val){ (void)obj; (void)val; }

int snd_pcm_open(snd_pcm_t **pcm, const char *name, snd_pcm_stream_t stream, int mode){ (void)name; (void)stream; (void)mode; *pcm = (snd_pcm_t*)calloc(1, 1); return 0; }
int snd_pcm_close(snd_pcm_t *pcm){ free(pcm); return 0; }
int snd_pcm_drain(snd_pcm_t *pcm){ (void)pcm; return 0; }
int snd_pcm_drop(snd_pcm_t *pcm){ (void)pcm; return 0; }
int snd_pcm_prepare(snd_pcm_t *pcm){ (void)pcm; return 0; }
int snd_pcm_resume(snd_pcm_t *pcm){ (void)pcm; return 0; }
int snd_pcm_start(snd_pcm_t *pcm){ (void)pcm; return 0; }
snd_pcm_sframes_t snd_pcm_writei(snd_pcm_t *pcm, const void *buffer, snd_pcm_uframes_t size){ (void)pcm; (void)buffer; return (snd_pcm_sframes_t)size; }
snd_pcm_stream_t snd_pcm_stream(snd_pcm_t *pcm){ (void)pcm; return SND_PCM_STREAM_PLAYBACK; }

int snd_pcm_hw_params_any(snd_pcm_t *pcm, snd_pcm_hw_params_t *params){ (void)pcm; (void)params; return 0; }
int snd_pcm_hw_params_set_rate_resample(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, unsigned int val){ (void)pcm; (void)params; (void)val; return 0; }
int snd_pcm_hw_params_set_access(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, snd_pcm_access_t val){ (void)pcm; (void)params; (void)val; return 0; }
int snd_pcm_hw_params_set_format(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, snd_pcm_format_t val){ (void)pcm; (void)params; (void)val; return 0; }
int snd_pcm_hw_params_set_channels(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, unsigned int val){ (void)pcm; (void)params; (void)val; return 0; }
int snd_pcm_hw_params_set_rate_near(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, unsigned int *val, int *dir){ (void)pcm; (void)params; (void)val; (void)dir; return 0; }
int snd_pcm_hw_params_set_buffer_time_near(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, unsigned int *val, int *dir){ (void)pcm; (void)params; (void)val; (void)dir; return 0; }
int snd_pcm_hw_params_get_buffer_size(snd_pcm_hw_params_t *params, snd_pcm_uframes_t *val){ (void)params; *val = 4096; return 0; }
int snd_pcm_hw_params_set_period_time_near(snd_pcm_t *pcm, snd_pcm_hw_params_t *params, unsigned int *val, int *dir){ (void)pcm; (void)params; (void)val; (void)dir; return 0; }
int snd_pcm_hw_params_get_period_size(snd_pcm_hw_params_t *params, snd_pcm_uframes_t *val, int *dir){ (void)params; (void)dir; *val = 1024; return 0; }
int snd_pcm_hw_params(snd_pcm_t *pcm, snd_pcm_hw_params_t *params){ (void)pcm; (void)params; return 0; }

int snd_pcm_sw_params_current(snd_pcm_t *pcm, snd_pcm_sw_params_t *params){ (void)pcm; (void)params; return 0; }
int snd_pcm_sw_params_set_start_threshold(snd_pcm_t *pcm, snd_pcm_sw_params_t *params, snd_pcm_uframes_t val){ (void)pcm; (void)params; (void)val; return 0; }
int snd_pcm_sw_params_set_avail_min(snd_pcm_t *pcm, snd_pcm_sw_params_t *params, snd_pcm_uframes_t val){ (void)pcm; (void)params; (void)val; return 0; }
int snd_pcm_sw_params(snd_pcm_t *pcm, snd_pcm_sw_params_t *params){ (void)pcm; (void)params; return 0; }

const char *snd_strerror(int errnum){ (void)errnum; return STUB_ERR; }
"""


_OHOS_TRIPLET = "aarch64-unknown-linux-ohos"


def _prepare_autotools_env():
    """Point the autoconf-family env vars at what is actually on PATH.

    The automake/libtool scripts installed into the Conan cache hardcode
    absolute paths for autoconf/autom4te/sed (baked in at *their* build
    time), which do not exist on the OHOS worker.  Expose the real tools
    via the documented env vars so the aclocal/automake/libtoolize wrappers
    do not try to exec a stale path.  Same preparation as the
    abiword-plugin-* recipes (argp-standalone precedent).
    """
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


class LibexadrumsConan(ConanFile):
    name = "libexadrums"
    version = "0.7.0"
    description = "eXaDrums software drum module library (OHOS stubbed ALSA)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/SpintroniK/libeXaDrums"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        # Source requires C++20; override the profile default (c++17).
        self.settings.compiler.cppstd = "20"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libexadrums is only supported on Linux/OHOS, not {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require arch=armv8")

    def requirements(self):
        self.requires("tinyxml2/11.0.0")
        self.requires("minizip/1.3.1")

    def build_requirements(self):
        # The upstream GitHub-archive tarball ships no generated `configure`
        # (git snapshots never contain autoreconf products), so build() must
        # bootstrap it.  configure.ac uses both LT_INIT (-> needs libtoolize)
        # and AM_INIT_AUTOMAKE (-> needs aclocal), i.e. the full autoreconf
        # chain, not just autoconf.
        #
        # CI worker (USER=100) resolves neither: /data/service/hnp/bin ships
        # only the autoconf family (autoreconf/autoconf/autoheader/autom4te,
        # no aclocal / no libtoolize), and the host-installed copies under
        # $HOME/usr/local/bin are invisible/broken from the CI sandbox.  The
        # build then dies in autoreconf with
        #   Can't exec "aclocal": No such file or directory
        #   autoreconf: error: aclocal failed with exit status: 2
        # (CI run #60012; reproduced locally as "Permission denied" with the
        # usr/local/bin PATH entry removed — aclocal there is a host symlink).
        #
        # Pull automake + libtool in as tool_requires (both published on
        # ohpcd, same convention as the abiword-plugin-* / audispd /
        # babeltrace recipes) and let VirtualBuildEnv below put their bin/
        # directories on the conanbuild PATH.  tool_requires resolve against
        # the *build* profile, so conan create needs both -pr:h and -pr:b.
        self.tool_requires("automake/1.18")
        # NOTE: libtool must be >= 2.5.4.1.  The published libtool/2.5.4
        # package relocates libtoolize's pkgdatadir into
        # share/libtool-conan/{build-aux,libltdl,m4} (relative symlinks), but
        # that tree is EMPTY in the 2.5.4 binary package, so autoreconf dies
        # with
        #   libtoolize: error: $pkgauxdir is not a directory:
        #     '<...>/libtool/2.5.4/p/share/libtool-conan/build-aux'
        # 2.5.4.1 is the re-published fix for exactly this (its
        # share/libtool-conan carries the three working symlinks).
        self.tool_requires("libtool/2.5.4.1")

    def layout(self):
        # In-tree build: keep source and build in the same folder so the raw
        # autoreconf/./configure/make chain (and the patched configure.ac) all
        # run where configure.ac actually lives.  basic_layout would split them
        # and leave the build folder empty.
        self.folders.source = ""
        self.folders.build = ""
        self.folders.generators = "conan"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @property
    def _ohos_tmpdir(self):
        """Writable temp dir for the whole build.

        OHOS mounts /tmp on a *read-only* erofs partition, and the CI worker's
        sandbox HOME has no `tmp` subdir (only the interactive HOME does).
        mksh (/system/bin/sh) writes here-document temp files to $TMPDIR and
        *silently falls back to /tmp* when $TMPDIR is unset or is not an
        existing directory, which killed configure with (CI run #60094):

          ./configure[1903]: can't create temporary file /tmp/shXXXXXX.tmp:
                             Read-only file system
          sed: conftest.cpp: No such file or directory
          configure: error: C++ compiler cannot create executables

        Anchoring the path inside the build folder is safe: that tree is
        always writable (autoreconf.log / configure.log are written there).
        """
        return os.path.join(self.build_folder, ".ohos-tmp")

    def generate(self):
        _prepare_autotools_env()
        # Inject the tool_requires (automake/libtool) bin directories into the
        # conanbuild environment.  Without this the autoreconf chain above
        # cannot find aclocal/libtoolize on the CI worker's clean PATH, even
        # though the packages are in the dependency graph (CI run #60012).
        VirtualBuildEnv(self).generate()

        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel") and configure then aborts with
        #   configure: error: cannot guess build type; you must specify one
        # Pass the triplet explicitly so the config.guess probe is never used
        # (config.sub understands *-linux-ohos; same as the abiword-plugin-* /
        # argp-standalone recipes).  build() passes the same value to the
        # hand-rolled `sh ./configure` below — AutotoolsToolchain.configure_args
        # are NOT applied there (we cannot use Autotools.configure() because
        # the generated ./configure is a shebang script that HMFS refuses to
        # exec directly).
        tc.configure_args.extend([
            f"--build={_OHOS_TRIPLET}",
            f"--host={_OHOS_TRIPLET}",
            "--disable-dependency-tracking",
        ])
        # ALSA stub include + lib, linked statically into libexadrums.
        stub_inc = os.path.join(self.build_folder, "alsa_stub", "include")
        stub_lib = os.path.join(self.build_folder, "alsa_stub", "lib")
        tc.extra_cxxflags.append(f"-I{stub_inc}")
        tc.extra_ldflags.append(f"-L{stub_lib}")
        tc.extra_ldflags.append("-lasound")
        # Embed an RPATH for every dependency lib dir so the built libexadrums.so
        # can locate its shared dependencies (minizip/tinyxml2) at load time
        # without LD_LIBRARY_PATH.  This is what makes the library self-contained
        # for the test_package (framework sets CMAKE_SKIP_RPATH) and for real
        # OHOS consumers that link it.
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                tc.extra_ldflags.append(f"-Wl,-rpath,{libdir}")
        # libc++ 15 is stricter than gcc/libstdc++ about transitive includes: a
        # number of upstream headers use std::string / std::move / std::unique_ptr
        # / std::find_if / ... without including the owning <string> / <utility> /
        # <memory> / <algorithm> / ..., which compiled fine on the original
        # toolchain but fails here.  Force-include the common STL headers in every
        # translation unit instead of patching dozens of files for the same issue.
        for _h in ("string", "utility", "memory", "algorithm", "functional",
                   "iterator", "cstdint", "type_traits", "initializer_list",
                   "array", "tuple", "cstddef"):
            tc.extra_cxxflags.append(f"-include {_h}")
        tc.generate()

        # Redirect every temp file into the build folder (see _ohos_tmpdir).
        # The previous version pointed TMPDIR at $HOME/tmp, which does NOT
        # exist on the CI worker, so mksh silently fell back to the read-only
        # /tmp and configure died with "C++ compiler cannot create
        # executables" (CI run #60094; reproduced locally by giving the build
        # a HOME without a tmp/ subdir).  Create the dir here, i.e. before the
        # first shell of build() runs.
        tmpdir = self._ohos_tmpdir
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        # zsh (the CI entry shell) uses TMPPREFIX rather than TMPDIR for its
        # here-documents, so pin both and no shell flavour can fall back to /tmp.
        env.define("TMPPREFIX", os.path.join(tmpdir, "sh"))
        # configure's conftest binaries (and the test_package binary) link the
        # shared libminizip/libtinyxml2/libexadrums, so the loader needs
        # LD_LIBRARY_PATH pointed at the dependency lib dirs at runtime.
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_tmpdir")

    def _run(self, cmd, log_name):
        log_path = os.path.join(self.build_folder, log_name)
        try:
            self.run(f"{cmd} > {log_path} 2>&1")
        except Exception:
            with open(log_path, "r", errors="replace") as fh:
                tail = fh.read()[-5000:]
            raise ConanException(f"FAILED: {cmd}\n--- {log_name} (tail) ---\n{tail}")

    def _build_alsa_stub(self):
        compiler_exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_exes.get("c") or "clang"
        ar = compiler_exes.get("ar") or "llvm-ar"
        stub_inc = os.path.join(self.build_folder, "alsa_stub", "include")
        stub_lib = os.path.join(self.build_folder, "alsa_stub", "lib")
        os.makedirs(os.path.join(stub_inc, "alsa"), exist_ok=True)
        os.makedirs(stub_lib, exist_ok=True)
        with open(os.path.join(stub_inc, "alsa", "asoundlib.h"), "w") as fh:
            fh.write(_ALSA_HEADER)
        with open(os.path.join(self.build_folder, "alsa_stub", "asound_stub.c"), "w") as fh:
            fh.write(_ALSA_STUB_C)
        # self.run() auto-applies the aggregated conanbuild env, which defines
        # TMPDIR/TMPPREFIX pointing at the writable build-folder temp dir
        # (see _ohos_tmpdir).  No explicit env= needed.
        self.run(
            f"{cc} -c {os.path.join(self.build_folder, 'alsa_stub', 'asound_stub.c')} "
            f"-I{stub_inc} -o {os.path.join(stub_lib, 'asound_stub.o')}"
        )
        self.run(
            f"{ar} rcs {os.path.join(stub_lib, 'libasound.a')} "
            f"{os.path.join(stub_lib, 'asound_stub.o')}"
        )

    def _bypass_mktemp_tmpdir(self):
        """E114: replace autoconf's `mktemp -d` temp dir with a plain mkdir one.

        On HMDFS the directory `mktemp -d` creates comes out as drwx--S---
        (2700 + setgid): *nobody* can create files inside it, not even its
        owner, and chmod cannot relax it.  The generated `config.status`
        bootstraps its scratch dir that way, so configure succeeds and then
        dies immediately in the next step (CI run #60712):

            configure: creating ./config.status
            ./config.status[1027]: can't create ./confkioDMa/subs1.awk:
                                   Permission denied
            config.status: error: could not setup config files machinery

        The offending block is baked into the generated `configure` (and is
        copied verbatim into the `config.status` it emits), so patching
        `configure` here — after autoreconf, before it is run — fixes both
        at once.  `tmp` is pointed at a directory we create ourselves with
        os.makedirs (a plain mkdir, not mktemp) and the `mkdir` fallback is
        neutralised.  Knowledge entry E114; same fix as archives/r/rsync.
        """
        configure = os.path.join(self.build_folder, "configure")
        if not os.path.isfile(configure):
            configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            self.output.warning("E114 bypass: no generated ./configure found")
            return False

        # /storage/... (HMDFS) and the read-only /tmp are both unsuitable; the
        # recipe-owned build-folder scratch dir is writable and per-build unique.
        fixed_dir = os.path.join(self._ohos_tmpdir, "conf-tmp")
        os.makedirs(fixed_dir, exist_ok=True)

        with open(configure, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        patched = content
        for old, new in (
            ('`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`', fixed_dir),
            ("tmp=./conf$$-$RANDOM", f"tmp={fixed_dir}"),
            ('(umask 077 && mkdir "$tmp")', "true"),
        ):
            patched = patched.replace(old, new)
        if patched == content:
            self.output.warning(
                "E114 bypass: autoconf temp-dir bootstrap not found in configure; "
                "leaving it untouched"
            )
            return False

        mode = os.stat(configure).st_mode
        with open(configure, "w", encoding="utf-8") as fh:
            fh.write(patched)
        os.chmod(configure, mode & 0o7777)
        self.output.info(f"E114 bypass: config.status scratch dir -> {fixed_dir}")
        return True

    def build(self):
        _prepare_autotools_env()
        self._build_alsa_stub()
        apply_conandata_patches(self)

        # configure.ac declares AC_CONFIG_MACRO_DIRS([m4]) but the GitHub
        # archive ships no m4/ directory (it is a build-time artifact), which
        # makes aclocal -I m4 warn.  Create it so the macro dir exists.
        os.makedirs(os.path.join(self.source_folder, "m4"), exist_ok=True)

        # OHOS build-folder exec quirk: the generated ./configure (and by
        # extension config.status/install-sh/libtool that configure spawns) cannot
        # be exec'd directly from this filesystem — running it as `./configure`
        # yields "Permission denied".  Re-exec through /system/bin/sh and
        # propagate CONFIG_SHELL/SHELL so the generated Makefile invokes every
        # sub-script via that shell too (read+interpret, no exec bit needed).
        sh = "/system/bin/sh"
        # Repeat TMPDIR/TMPPREFIX inline, on top of the conanbuild env, so the
        # configure sub-shell can never fall back to the read-only /tmp (see
        # _ohos_tmpdir).
        tmpdir = self._ohos_tmpdir
        os.makedirs(tmpdir, exist_ok=True)
        sh_env = (f"CONFIG_SHELL={sh} SHELL={sh} "
                  f"TMPDIR={tmpdir} TMPPREFIX={tmpdir}/sh")

        self._run("autoreconf -fiv", "autoreconf.log")
        # E114: patch the just-generated ./configure so the config.status it
        # emits uses a plain-mkdir scratch dir instead of mktemp's unusable
        # drwx--S--- one (see _bypass_mktemp_tmpdir).
        self._bypass_mktemp_tmpdir()
        # Must mirror AutotoolsToolchain's configure_args by hand: Autotools
        # .configure() would exec ./configure, which HMFS refuses (see above),
        # so the triplet / dependency-tracking flags have to be repeated here.
        configure_args = [
            f"--build={_OHOS_TRIPLET}",
            f"--host={_OHOS_TRIPLET}",
            "--disable-dependency-tracking",
            f"--prefix={self.package_folder}",
        ]
        if self.options.shared:
            configure_args += ["--enable-shared", "--disable-static"]
        else:
            configure_args += ["--disable-shared", "--enable-static"]
        self._run(f"{sh_env} {sh} ./configure " + " ".join(configure_args), "configure.log")
        # R9: single job — parallel make can hit HMDFS jobserver fifo EPERM.
        self._run(f"{sh_env} make -j1", "make.log")

    def package(self):
        sh = "/system/bin/sh"
        tmpdir = self._ohos_tmpdir
        os.makedirs(tmpdir, exist_ok=True)
        # install-sh / libtool are shell scripts too: they need the writable
        # TMPDIR for their here-documents (see _ohos_tmpdir).
        sh_env = (f"CONFIG_SHELL={sh} SHELL={sh} "
                  f"TMPDIR={tmpdir} TMPPREFIX={tmpdir}/sh")
        self._run(f"{sh_env} make install", "install.log")

        # Install the ALSA stub header so the public API (Alsa.h / AlsaParams.h
        # #include <alsa/asoundlib.h>) stays self-contained on OHOS.
        stub_inc = os.path.join(self.build_folder, "alsa_stub", "include")
        copy(self, "asoundlib.h",
             os.path.join(stub_inc, "alsa"),
             os.path.join(self.package_folder, "include", "alsa"))

        # Upstream only installs the Api/* public headers under pkgincludedir.
        # Ship the full source header tree as well so internal API headers
        # (notably Sound/Alsa/Alsa.h, needed by consumers/tests to reach the
        # bundled ALSA stub) are available with their relative includes intact.
        copy(self, "*.h", self.source_folder,
             os.path.join(self.package_folder, "include", "libexadrums"))

        # Remove libtool wrappers.
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

        self._materialize_soname_aliases()

    def _materialize_soname_aliases(self):
        """Replace the SONAME alias symlinks under lib/ with real files.

        libtool's install produces the standard three-name layout
            libexadrums.so -> libexadrums.so.2 -> libexadrums.so.2.0.0
        where both .so (devel name) and .so.2 (SONAME) are *symlinks*.

        On OHOS that is fatal at load time: the ELF NEEDED entry records the
        SONAME (libexadrums.so.2), and when the loader opens that name and
        lands on a symlink it gets EACCES on a filesystem/domain without
        symlink resolution; musl only continues searching on ENOENT/ENOTDIR,
        so it fails immediately instead of falling back to the real file:

            Error loading shared library libexadrums.so.2: (needed by ...)
            Error relocating ...: symbol not found          -> rc=127

        (knowledge entries E316 / E492; every one of the 30+ dependency
        packages already in the local Conan cache ships materialized files
        and zero symlinks under lib/.)  Same fix as
        archives/l/libkysdk-base/3.0.1.3:_materialize_soname_aliases:
        copy2 follows the link to the real ELF (preserving the mode bits),
        then os.replace atomically swaps the symlink for the copy.
        """
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for name in sorted(os.listdir(lib_dir)):
            path = os.path.join(lib_dir, name)
            if not os.path.islink(path):
                continue
            entity = os.path.realpath(path)
            if not os.path.isfile(entity):
                continue
            tmp = path + ".entity"
            shutil.copy2(entity, tmp)
            os.replace(tmp, path)
            self.output.info(f"materialized SONAME alias: lib/{name}")

    def package_info(self):
        self.cpp_info.libs = ["exadrums"]
        # Propagate the real dependencies so consumers (and the test_package
        # run environment) pull in minizip/tinyxml2 lib dirs at link + runtime.
        self.cpp_info.requires = ["minizip::minizip", "tinyxml2::tinyxml2"]
        # Alsa.h / AlsaParams.h still #include <alsa/asoundlib.h>; ship the stub
        # header so consumers compile without a system ALSA.
        self.cpp_info.includedirs = ["include"]
