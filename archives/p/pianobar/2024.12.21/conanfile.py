#!/usr/bin/env python3
"""Conan recipe for pianobar 2024.12.21 on HarmonyOS PC (OHOS aarch64).

pianobar is a free/open-source, console-based client for the Pandora
online radio. Upstream uses a raw Makefile (no configure/CMake) and
pkg-config to discover its dependencies.

Upstream: https://6xq.net/projects/pianobar/
Mirror:   https://github.com/PromyLOPh/pianobar

Build notes:
  - Raw Makefile project: objects are built next to the sources, so the
    build runs with cwd=source_folder (upstream INSTALL flow).
  - Compilers come from Conan conf (tools.build:compiler_executables),
    never from bare $CC/$CFLAGS shell variables (R33).
  - Dependency flags come from PkgConfigDeps output via PKG_CONFIG_PATH
    pointing at the generators folder; pkgconf is provided via
    tool_requires.
  - libao has no Conan recipe in this repo (archives/l/libao/1.2.2 is a
    legacy pre-Conan archive) and is absent from the ohpcd remote, so
    declaring self.requires("libao/...") breaks graph resolution. The
    recipe therefore vendors a minimal OHOS audio shim exposing the
    pkg-config "ao" module and the ao/ao.h API used by src/player.c
    (ao_initialize/shutdown, ao_driver_id, ao_default_driver_id,
    ao_open_live/ao_open_file, ao_play, ao_close). The shim implements
    the "raw" file/pipe driver for real (pianobar --audio-pipe path)
    and a "null" live driver that discards samples: OHOS provides no
    OSS/ALSA/Pulse back end, so even a full libao build could not play
    live audio without an OHOS driver port. The shim is build-private
    (under build_folder/ao-shim) and statically linked; it is not a
    published package and keeps this PR to the single pianobar library.
  - Upstream ships no test suite (no `check` target, no tests/ dir), so
    build() performs no upstream test step. The audit is recorded in
    test_package/MANIFEST.yml and consumer tests in test_package/
    cover both the CLI binary and the libpiano C API.
  - On OHOS the installed CLI binary is self-signed with binary-sign-tool
    (best effort: skipped with a warning when the tools are absent).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

# Vendored OHOS audio shim: public libao header subset used by pianobar.
_AO_H = """\
#ifndef __AO_H__
#define __AO_H__

#ifdef __cplusplus
extern "C" {
#endif

#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include "os_types.h"

#define AO_TYPE_LIVE 1
#define AO_TYPE_FILE 2

#define AO_ENODRIVER 1
#define AO_ENOTFILE 2
#define AO_ENOTLIVE 3
#define AO_EBADOPTION 4
#define AO_EOPENDEVICE 5
#define AO_EOPENFILE 6
#define AO_EFILEEXISTS 7
#define AO_EBADFORMAT 8
#define AO_EFAIL 100

#define AO_FMT_LITTLE 1
#define AO_FMT_BIG 2
#define AO_FMT_NATIVE 4

typedef struct ao_info {
    int type;
    char *name;
    char *short_name;
    char *author;
    char *comment;
    int preferred_byte_format;
    int priority;
    char **options;
    int option_count;
} ao_info;

typedef struct ao_functions ao_functions;
typedef struct ao_device ao_device;

typedef struct ao_sample_format {
    int bits;
    int rate;
    int channels;
    int byte_format;
    char *matrix;
} ao_sample_format;

typedef struct ao_option {
    char *key;
    char *value;
    struct ao_option *next;
} ao_option;

void ao_initialize(void);
void ao_shutdown(void);
int ao_append_global_option(const char *key, const char *value);
int ao_append_option(ao_option **options, const char *key, const char *value);
void ao_free_options(ao_option *options);
ao_device *ao_open_live(int driver_id, ao_sample_format *format,
                        ao_option *option);
ao_device *ao_open_file(int driver_id, const char *filename, int overwrite,
                        ao_sample_format *format, ao_option *option);
int ao_play(ao_device *device, char *output_samples, uint_32 num_bytes);
int ao_close(ao_device *device);
int ao_driver_id(const char *short_name);
int ao_default_driver_id(void);
ao_info *ao_driver_info(int driver_id);
ao_info **ao_driver_info_list(int *driver_count);
const char *ao_file_extension(int driver_id);
int ao_is_big_endian(void);

#ifdef __cplusplus
}
#endif

#endif
"""

_AO_OS_TYPES_H = """\
#ifndef __AO_OS_TYPES_H__
#define __AO_OS_TYPES_H__

#include <stdint.h>

typedef int8_t int_8;
typedef uint8_t uint_8;
typedef int16_t int_16;
typedef uint16_t uint_16;
typedef int32_t int_32;
typedef uint32_t uint_32;

#endif
"""

_AO_SHIM_C = """\
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <ao/ao.h>

struct ao_device {
    int driver_id;
    int is_file;
    FILE *fp;
    int owns_fp;
};

#define AO_SHIM_RAW_ID 0
#define AO_SHIM_NULL_ID 1

static ao_info ao_raw_info = {
    AO_TYPE_FILE, "OHOS raw file output", "raw",
    "pianobar-ohos", "raw/file driver (vendored shim)", AO_FMT_NATIVE,
    10, NULL, 0
};
static ao_info ao_null_info = {
    AO_TYPE_LIVE, "OHOS null live output", "null",
    "pianobar-ohos", "null/live driver, discards samples (vendored shim)",
    AO_FMT_NATIVE, 10, NULL, 0
};
static ao_info *ao_info_list[2] = { &ao_raw_info, &ao_null_info };

void ao_initialize(void) {}
void ao_shutdown(void) {}

int ao_append_global_option(const char *key, const char *value) {
    (void)key; (void)value;
    return 1;
}

int ao_append_option(ao_option **options, const char *key, const char *value) {
    ao_option *opt;
    if (!options || !key || !value)
        return 0;
    opt = (ao_option *)calloc(1, sizeof(*opt));
    if (!opt)
        return 0;
    opt->key = strdup(key);
    opt->value = strdup(value);
    if (!opt->key || !opt->value) {
        free(opt->key);
        free(opt->value);
        free(opt);
        return 0;
    }
    opt->next = *options;
    *options = opt;
    return 1;
}

void ao_free_options(ao_option *options) {
    while (options) {
        ao_option *next = options->next;
        free(options->key);
        free(options->value);
        free(options);
        options = next;
    }
}

int ao_driver_id(const char *short_name) {
    if (!short_name)
        return -1;
    if (strcmp(short_name, "raw") == 0)
        return AO_SHIM_RAW_ID;
    if (strcmp(short_name, "null") == 0)
        return AO_SHIM_NULL_ID;
    /* OHOS has no OSS/ALSA/Pulse back end: map any other live driver
     * name to the null sink so the player pipeline stays functional. */
    return AO_SHIM_NULL_ID;
}

int ao_default_driver_id(void) {
    return AO_SHIM_NULL_ID;
}

ao_device *ao_open_live(int driver_id, ao_sample_format *format,
                        ao_option *option) {
    ao_device *dev;
    (void)option;
    if (!format || format->channels <= 0 || format->rate <= 0)
        return NULL;
    (void)driver_id;
    dev = (ao_device *)calloc(1, sizeof(*dev));
    if (!dev)
        return NULL;
    dev->driver_id = AO_SHIM_NULL_ID;
    dev->is_file = 0;
    dev->fp = NULL;
    dev->owns_fp = 0;
    return dev;
}

ao_device *ao_open_file(int driver_id, const char *filename, int overwrite,
                        ao_sample_format *format, ao_option *option) {
    ao_device *dev;
    FILE *fp = NULL;
    (void)option;
    if (!filename || !format)
        return NULL;
    if (driver_id != AO_SHIM_RAW_ID)
        return NULL;
    if (strcmp(filename, "-") == 0) {
        fp = stdout;
    } else {
        if (!overwrite) {
            FILE *probe = fopen(filename, "rb");
            if (probe) {
                fclose(probe);
                return NULL;
            }
        }
        fp = fopen(filename, "wb");
        if (!fp)
            return NULL;
    }
    dev = (ao_device *)calloc(1, sizeof(*dev));
    if (!dev) {
        if (fp != stdout)
            fclose(fp);
        return NULL;
    }
    dev->driver_id = AO_SHIM_RAW_ID;
    dev->is_file = 1;
    dev->fp = fp;
    dev->owns_fp = (fp != stdout);
    return dev;
}

int ao_play(ao_device *device, char *output_samples, uint_32 num_bytes) {
    size_t wrote;
    if (!device || (!output_samples && num_bytes != 0))
        return 0;
    if (num_bytes == 0)
        return 1;
    if (!device->is_file || !device->fp)
        return 1; /* null live sink: discard */
    wrote = fwrite(output_samples, 1, (size_t)num_bytes, device->fp);
    return (wrote == (size_t)num_bytes) ? 1 : 0;
}

int ao_close(ao_device *device) {
    if (!device)
        return 0;
    if (device->is_file && device->fp && device->owns_fp)
        fclose(device->fp);
    free(device);
    return 0;
}

ao_info *ao_driver_info(int driver_id) {
    if (driver_id == AO_SHIM_RAW_ID)
        return &ao_raw_info;
    if (driver_id == AO_SHIM_NULL_ID)
        return &ao_null_info;
    return NULL;
}

ao_info **ao_driver_info_list(int *driver_count) {
    if (driver_count)
        *driver_count = 2;
    return ao_info_list;
}

const char *ao_file_extension(int driver_id) {
    if (driver_id == AO_SHIM_RAW_ID)
        return "raw";
    return NULL;
}

int ao_is_big_endian(void) {
    const int x = 1;
    return (*(const char *)&x == 0) ? 1 : 0;
}
"""

_AO_PC = """\
prefix={prefix}
exec_prefix=${{prefix}}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: ao
Description: OHOS vendored libao shim (raw file + null live drivers)
Version: 1.2.2
Libs: -L${{libdir}} -lao
Cflags: -I${{includedir}}
"""


class PianobarConan(ConanFile):
    name = "pianobar"
    version = "2024.12.21"
    description = "Console-based client for the Pandora online radio"
    license = "MIT"
    homepage = "https://6xq.net/projects/pianobar/"
    url = "https://github.com/PromyLOPh/pianobar"
    topics = ("pandora", "radio", "audio", "cli")

    # Mixed tool+library package (bin/pianobar CLI plus lib/libpiano.a C API):
    # "application" would make CMakeDeps drop cpp_info.libs so consumers
    # linking pianobar::piano get no -lpiano (every Piano* symbol undefined
    # while transitive deps still resolve). "library" keeps both bin and
    # lib propagation (precedent: a52dec/0.7.4 ships bin tools + liba52
    # with package_type="library").
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pianobar is supported only on Linux/OHOS, got %s"
                % self.settings.os
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "OHOS builds require armv8/aarch64"
            )

    def requirements(self):
        # INSTALL deps: libcurl>=7.32.0, gcrypt (blowfish),
        # json-c, ffmpeg>=5.1 (mov demuxer/aac decoder/http/volume).
        # NOTE: upstream also needs libao, but libao has no Conan recipe
        # in this repo and is absent from the ohpcd remote; it is provided
        # as a build-private vendored shim (see _compile_ao_shim) so the
        # dependency graph resolves.
        # transitive_* propagates headers/libs to the libpiano consumer
        # test in test_package.
        self.requires("curl/8.15.0", transitive_headers=True,
                      transitive_libs=True)
        self.requires("json-c/0.18", transitive_headers=True,
                      transitive_libs=True)
        self.requires("libgcrypt/1.12.2", transitive_headers=True,
                      transitive_libs=True)
        self.requires("ffmpeg/7.1.5", transitive_headers=True,
                      transitive_libs=True)
        # Graph fix (preflight 2026-09-14): curl/8.15.0 requires
        # openssl/3.5.6.1 (OHOS FD_SET portability fix) while ffmpeg/7.1.5
        # still pins openssl/3.5.6 -> "Version conflict" at graph compute.
        # Patch-level bump is API-compatible, so force the higher version
        # for the whole graph. override=True only pins the version, it does
        # not add a new direct link for the application package.
        self.requires("openssl/3.5.6.1", override=True)

    def build_requirements(self):
        # Upstream Makefile shells out to $(PKG_CONFIG) for every dep.
        self.tool_requires("pkgconf/3.0.5")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def _compilers(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c", "clang")
        ar = executables.get("ar", "llvm-ar")
        return cc, ar

    def _ao_shim_prefix(self):
        return os.path.join(self.build_folder, "ao-shim")

    def _write_ao_shim(self):
        prefix = self._ao_shim_prefix()
        inc = os.path.join(prefix, "include", "ao")
        src = os.path.join(prefix, "src")
        lib = os.path.join(prefix, "lib")
        pc = os.path.join(prefix, "lib", "pkgconfig")
        for d in (inc, src, lib, pc):
            os.makedirs(d, exist_ok=True)
        with open(os.path.join(inc, "ao.h"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(_AO_H)
        with open(os.path.join(inc, "os_types.h"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(_AO_OS_TYPES_H)
        with open(os.path.join(src, "ao_shim.c"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(_AO_SHIM_C)
        with open(os.path.join(pc, "ao.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(_AO_PC.format(prefix=prefix))
        return prefix

    def _compile_ao_shim(self, cc, ar):
        prefix = self._write_ao_shim()
        inc = os.path.join(prefix, "include")
        src = os.path.join(prefix, "src", "ao_shim.c")
        obj = os.path.join(prefix, "src", "ao_shim.o")
        lib = os.path.join(prefix, "lib", "libao.a")
        self.output.info("pianobar: building vendored ao shim")
        self.run(
            "\"%s\" -c -O2 -I\"%s\" \"%s\" -o \"%s\"" % (cc, inc, src, obj),
            cwd=self.build_folder,
        )
        self.run(
            "\"%s\" rcs \"%s\" \"%s\"" % (ar, lib, obj),
            cwd=self.build_folder,
        )
        return prefix

    def _build_environment(self):
        env = Environment()
        # Writable scratch dir under the build folder (device TMPDIR may
        # live on a read-only/HMDFS mount).
        tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        # PkgConfigDeps writes one .pc per dependency into the generators
        # folder; point pkg-config there plus the vendored ao shim
        # (plus any pre-existing entries).
        pc_path = (os.path.join(self._ao_shim_prefix(), "lib", "pkgconfig")
                   + os.pathsep + self.generators_folder)
        prev_pc = os.environ.get("PKG_CONFIG_PATH", "")
        if prev_pc:
            pc_path = pc_path + os.pathsep + prev_pc
        env.define("PKG_CONFIG_PATH", pc_path)
        env.define("PKG_CONFIG", "pkgconf")
        return env

    def build(self):
        apply_conandata_patches(self)
        cc, ar = self._compilers()
        self.output.info("pianobar build: CC=%s AR=%s" % (cc, ar))
        build_env = self._build_environment()
        with VirtualBuildEnv(self).vars().apply(), build_env.vars(self).apply():
            # Vendored ao shim must exist before pkg-config probes "ao".
            self._compile_ao_shim(cc, ar)
            self.run("pkgconf --modversion ao", cwd=self.build_folder)
            # Upstream INSTALL flow, single job (R9).
            self.run("make clean", cwd=self.source_folder, ignore_errors=True)
            # json-c headers live in <package>/include/json-c/ (json.h,
            # json_object.h, ...), but this repo's json-c recipe exposes only
            # top-level include/ via PkgConfigDeps, so upstream
            # `#include <json.h>` fails. Pass the subdir explicitly via
            # command-line CFLAGS (minimal, pianobar-local; json-c recipe
            # untouched to keep single-library PR).
            json_inc = self.dependencies["json-c"].cpp_info.includedirs[0]
            json_cflags = "-I%s -I%s" % (
                json_inc, os.path.join(json_inc, "json-c"))
            self.output.info("pianobar build: json-c CFLAGS=%s" % json_cflags)
            self.run(
                "make -j1 PKG_CONFIG=pkgconf CC=\"%s\" CFLAGS=\"-O2 -DNDEBUG %s\""
                % (cc, json_cflags),
                cwd=self.source_folder,
            )
            # The default (DYNLINK=0) build links libpiano objects straight
            # into the binary; archive a static libpiano.a by hand so the
            # C API can be packaged and consumer-tested. No symlinks are
            # created (HMDFS may not support them).
            objs = []
            libpiano_dir = os.path.join(self.source_folder, "src", "libpiano")
            for fname in ("crypt.o", "piano.o", "request.o", "response.o",
                          "list.o"):
                obj = os.path.join(libpiano_dir, fname)
                if not os.path.isfile(obj):
                    raise ConanInvalidConfiguration(
                        "expected libpiano object missing: %s" % obj
                    )
                objs.append("\"%s\"" % obj)
            self.run(
                "\"%s\" rcs \"%s\" %s"
                % (ar, os.path.join(self.source_folder, "libpiano.a"),
                   " ".join(objs)),
                cwd=self.source_folder,
            )

    def _sign_binary(self, binary):
        """Self-sign an OHOS CLI binary (best effort, never fatal)."""
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        signer = shutil.which("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "OHOS signing tools not found "
                "(llvm-objcopy=%s, binary-sign-tool=%s); shipping unsigned"
                % (objcopy, signer)
            )
            return
        self.run("\"%s\" --remove-section .codesign \"%s\""
                 % (objcopy, binary), ignore_errors=True)
        signed = binary + ".signed"
        self.run("\"%s\" sign -inFile \"%s\" -outFile \"%s\" -selfSign 1"
                 % (signer, binary, signed))
        os.replace(signed, binary)
        os.chmod(binary, 0o755)

    def package(self):
        build_env = self._build_environment()
        with VirtualBuildEnv(self).vars().apply(), build_env.vars(self).apply():
            # Upstream install target honors PREFIX/DESTDIR.
            self.run(
                "make install PREFIX=/ DESTDIR=\"%s\"" % self.package_folder,
                cwd=self.source_folder,
            )
        # Static libpiano C API + public header (Debian splits this as
        # libpiano; here it ships with the tool package).
        # Fail fast (instead of a confusing downstream 'piano.h/config.h
        # file not found' in consumers) if the upstream layout ever changes.
        for _hdr in (os.path.join(self.source_folder, "src", "libpiano",
                                  "piano.h"),
                     os.path.join(self.source_folder, "src", "config.h")):
            if not os.path.isfile(_hdr):
                raise ConanInvalidConfiguration(
                    "expected upstream header missing: %s" % _hdr)
        copy(self, "libpiano.a",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "piano.h",
             src=os.path.join(self.source_folder, "src", "libpiano"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        # Upstream src/libpiano/piano.h does `#include "../config.h"`, so any
        # consumer including <piano.h> needs that file at <prefix>/config.h
        # (i.e. include/../config.h). Ship the static upstream src/config.h
        # there; it only adds version/feature macros (plus ffmpeg version
        # headers already covered by the ffmpeg component requires below).
        copy(self, "config.h",
             src=os.path.join(self.source_folder, "src"),
             dst=self.package_folder,
             keep_path=False)
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        if str(self.settings.os) == "OHOS":
            self._sign_binary(
                os.path.join(self.package_folder, "bin", "pianobar"))

    def package_info(self):
        self.cpp_info.libs = ["piano"]
        # Transitive headers/libs for CMake consumers: test_libpiano.c
        # includes <gcrypt.h> (also via piano.h) and libpiano.a references
        # curl/json-c/gcrypt/libav* symbols. Without this, CMakeDeps
        # consumers of pianobar::piano get no transitive includes/libs
        # (preflight: fatal error: 'gcrypt.h' file not found).
        self.cpp_info.requires = [
            # NOTE: entries are "<conan-package>::<component>" using the
            # recipe reference name, NOT the CMake target name: this repo's
            # curl recipe declares cmake_target_name=CURL::libcurl, but the
            # requires entry must stay "curl::..." (preflight: package_info()
            # rejects 'CURL::' as "not a direct requirement of the recipe").
            "curl::curl",
            "json-c::json-c",
            "libgcrypt::libgcrypt",
            "ffmpeg::avformat",
            "ffmpeg::avcodec",
            "ffmpeg::avfilter",
            "ffmpeg::avutil",
        ]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            # pthread symbols live in musl libc on OHOS; -lpthread is kept
            # for Linux compatibility (upstream links it unconditionally).
            self.cpp_info.system_libs = ["pthread", "m"]
        self.cpp_info.set_property("cmake_file_name", "pianobar")
        self.cpp_info.set_property("cmake_target_name", "pianobar::piano")
        self.cpp_info.set_property("pkg_config_name", "libpiano")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
