#!/usr/bin/env python3
"""Conan recipe for librcc 0.2.13 - Russian Charset Conversion Library.

Upstream: https://github.com/RusXMMS/librcc (tag librcc-0.2.13)
Build system: autotools upstream (configure.ac + Makefile.am, no pre-generated
configure), but the device conan automake package is unusable: every
aclocal/automake binary (including versioned aclocal-1.18/automake-1.18, only
213 bytes) is a shim referencing a missing ``.aclocal-real``/``.automake-real``
target (HMBS hardlink=0/chmod=0), so ``autoreconf -fi`` fails with exit 126
for three consecutive preflight rounds (cp-repair, then ACLOCAL/AUTOMAKE env
override, both ineffective - even versioned binaries are shims).

OHOS adaptation (following the nwipe/gumbo-parser precedent of bypassing the
autotools chain entirely): build() compiles the minimal C sources directly
with the HNP clang (no autoreconf/configure/make, no tool_requires on
automake/autoconf/libtool), using only the mandatory libxml2 dependency.
Feature set mirrors the previous minimal configure flags: no gtk1/glib2/
gtk2/gtk3/bdb/libtranslate, system iconv forced, enca/rcd/guess left
undetected (their support files compile to no-ops without the libs).

- Writable TMPDIR/TMP/TEMP via HMBS injection (device /tmp is read-only
  erofs); only replaces the temp-file root, no test removal.
- Static config.h generated for the minimal feature set (musl/POSIX headers,
  pthread, dlopen, codeset; all optional engines/features left undefined).
- Upstream tests: examples/Makefile.am `test` + `test-russian`
  (cat input-russian.txt | ./example2 [ru]); build() compiles example2
  with the HNP clang and runs both pipes, emitting passed evidence.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.layout import basic_layout


def _writable_tmpdir(conanfile):
    """Reuse HMBS-injected writable tmpdir (device /tmp is read-only erofs)."""
    candidates = []
    for key in ("HMBS_TMPDIR", "HMBS_TMPDIR_RUNTIME"):
        value = os.environ.get(key)
        if value:
            candidates.append(value)
    capabilities = os.environ.get("HMBS_PLATFORM_CAPABILITIES")
    if capabilities:
        try:
            obj = json.loads(capabilities)
            if isinstance(obj, dict):
                for sub in ("tmpdir", "tmpDir", "TMPDIR"):
                    if obj.get(sub):
                        candidates.append(str(obj[sub]))
        except Exception:
            pass
    for key in ("TMPDIR", "TMP", "TEMP"):
        value = os.environ.get(key)
        if value and value != "/tmp" and value not in candidates:
            candidates.append(value)
    fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
    if fallback and fallback not in candidates:
        candidates.append(fallback)
    for base in (getattr(conanfile, "build_folder", None),
                 getattr(conanfile, "source_folder", None)):
        if base:
            candidates.append(os.path.join(str(base), "tmp"))
    for candidate in candidates:
        if not candidate:
            continue
        try:
            os.makedirs(candidate, exist_ok=True)
        except OSError:
            continue
        if not os.path.isdir(candidate):
            continue
        try:
            probe = os.path.join(candidate, ".hmbs_wtest")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("w")
            os.remove(probe)
            return candidate
        except OSError:
            continue
    fallback_dir = os.path.join(str(conanfile.build_folder), "tmp")
    os.makedirs(fallback_dir, exist_ok=True)
    return fallback_dir


def _ensure_tmp_env(conanfile):
    """Redirect temp files off read-only /tmp; pin shell to /bin/sh."""
    tmp = _writable_tmpdir(conanfile)
    for key in ("TMPDIR", "TMP", "TEMP"):
        os.environ[key] = tmp
    os.environ["SHELL"] = "/bin/sh"
    os.environ["CONFIG_SHELL"] = "/bin/sh"
    try:
        os.umask(0o022)
    except Exception:
        pass
    return tmp


# Minimal sources (optional GUI/BDB/translate/aspell units compile to no-ops
# without their libs; engines/external reduced to the always-built western
# module - glib2/libtranslate/BDB paths stay off, same as the previous
# --disable-* configure flags).
_SRC_FILES = [
    "librcc.c", "rcchome.c", "rcclock.c", "rcclocale.c", "lng.c", "opt.c",
    "lngconfig.c", "curconfig.c", "rccconfig.c", "rcclist.c", "rccmutex.c",
    "plugin.c", "rccexternal.c", "rccenca.c", "rccdb4.c", "rccspell.c",
    "engine.c", "rccstring.c", "rccxml.c", "rcciconv.c", "rcctranslate.c",
    "fs.c", "recode.c", "lngrecode.c",
]
_UI_FILES = ["librccui.c", "rccmenu.c", "rccnames.c", "null.c"]
_ENGINE_FILES = ["western.c"]

# Static config.h for the minimal OHOS feature set. Optional engines and
# features (RCD/ENCA/LIBGUESS/BDB/LIBTRANSLATE/ASPELL/GTK*) stay undefined so
# their units compile to stubs. POSIX/musl headers present on the device are
# defined; file-locking probes are left undefined on purpose (rcclock.c falls
# back to best-effort without them - defining them without the syscalls would
# break the link).
_CONFIG_H = """/* Generated by librcc/0.2.13 conanfile: minimal OHOS config. */
#ifndef LIBRCC_CONFIG_H
#define LIBRCC_CONFIG_H
#define HAVE_CODESET 1
#define HAVE_DLFCN_H 1
#define HAVE_DLOPEN 1
#define HAVE_FCNTL_H 1
#define HAVE_ICONV_H 1
#define HAVE_INTTYPES_H 1
#define HAVE_PTHREAD 1
#define HAVE_PWD_H 1
#define HAVE_SIGNAL_H 1
#define HAVE_STRINGS_H 1
#define HAVE_SYS_FILE_H 1
#define HAVE_SYS_SELECT_H 1
#define HAVE_SYS_SOCKET_H 1
#define HAVE_SYS_STAT_H 1
#define HAVE_SYS_TIME_H 1
#define HAVE_SYS_TYPES_H 1
#define HAVE_SYS_UN_H 1
#define HAVE_SYS_WAIT_H 1
#define HAVE_UNISTD_H 1
#define HAVE_STRCASECMP 1
#define HAVE_STRNCASECMP 1
#define HAVE_STRDUP 1
#define HAVE_STRNLEN 1
#define HAVE_NANOSLEEP 1
#define HAVE_USLEEP 1
#define HAVE_FSYNC 1
#define HAVE_FTRUNCATE 1
/* Optional features below stay disabled (minimal OHOS set). */
#undef HAVE_RCD
#undef HAVE_ENCA
#undef HAVE_LIBGUESS
#undef HAVE_DB_H
#undef HAVE_LIBTRANSLATE
#undef HAVE_LIBTRANSLATE_TIMED_TRANSLATE
#undef HAVE_ASPELL
#undef HAVE_LIBCHARSET
#undef HAVE_GTK
#undef HAVE_GTK2
#undef HAVE_GTK3
#undef HAVE_GLIB2
#undef HAVE_FLOCK
#undef HAVE_LOCKF
#endif
"""


# Upstream regression: examples/Makefile.am defines two real test targets
#   test:         cat input-russian.txt | ./example2
#   test-russian: cat input-russian.txt | ./example2 ru
# There is no `make check`/TESTS/ctest, but these two targets are the
# canonical upstream test entries (discovered=2). build() compiles example2
# with the same HNP clang flags, runs both pipes natively, and asserts
# exit 0 + non-empty output with content markers (anti false-pass: empty
# fixture or silent skip must fail, not count as passed).
_HMBS_UPSTREAM_COMMAND = (
    "cat input-russian.txt | ./example2 && "
    "cat input-russian.txt | ./example2 ru "
    "(examples/Makefile.am test/test-russian)"
)


def _hmbs_upstream_marker(result):
    return "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
        result, separators=(",", ":"), ensure_ascii=False)


def _persist_and_emit_upstream(conanfile, result):
    marker = _hmbs_upstream_marker(result)
    try:
        path = os.path.join(str(conanfile.build_folder),
                            "hmbs_upstream_test_result.json")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(
                result, separators=(",", ":"),
                ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001 - evidence must never fail build
        conanfile.output.warning(
            "persist upstream result failed (non-fatal): %s" % exc)
    conanfile.output.highlight(marker)
    print(marker, flush=True)
    return marker


def _run_upstream_examples(conanfile, define_flags, inc_flags,
                           libdir_flags, lib_flags):
    """Compile examples/example2.c and run both upstream test pipes."""
    import subprocess
    src_examples = os.path.join(str(conanfile.source_folder), "examples")
    fixture = os.path.join(src_examples, "input-russian.txt")
    example_src = os.path.join(src_examples, "example2.c")
    if not os.path.isfile(fixture):
        raise Exception("upstream fixture missing: %s" % fixture)
    if os.path.getsize(fixture) == 0:
        raise Exception("upstream fixture is empty: %s" % fixture)
    if not os.path.isfile(example_src):
        raise Exception("upstream example missing: %s" % example_src)
    with open(fixture, "rb") as handle:
        fixture_bytes = handle.read()
    if not fixture_bytes.strip():
        raise Exception("upstream fixture has no content")
    ex_bin = os.path.join(str(conanfile.build_folder), "example2_upstream")
    # Link against the freshly built archive/shared lib in build_folder.
    if getattr(conanfile.options, "shared", False):
        lib_path = os.path.join(str(conanfile.build_folder), "librcc.so")
        lib_arg = '"%s"' % lib_path
    else:
        lib_path = os.path.join(str(conanfile.build_folder), "librcc.a")
        lib_arg = '"%s"' % lib_path
    if not os.path.isfile(lib_path):
        raise Exception("built librcc lib missing for examples: %s" % lib_path)
    compile_script = "set -eu\n"
    compile_script += '"${CC:-clang}" -O2 %s %s -I\"%s\" -I\"%s/src\" "%s" %s -o \"%s\" %s %s\n' % (
        define_flags, inc_flags, str(conanfile.source_folder),
        str(conanfile.source_folder), example_src.replace("\\", "/"),
        lib_arg, ex_bin, libdir_flags, lib_flags)
    compile_script += 'ls -la "%s"\n' % ex_bin
    conanfile.output.info("[hmbs-upstream] compiling example2")
    conanfile.run(compile_script, env="conanbuild")
    if not os.path.isfile(ex_bin):
        raise Exception("example2_upstream binary not produced")
    if os.path.getsize(ex_bin) == 0:
        raise Exception("example2_upstream binary is empty")
    run_env = dict(os.environ)
    tmp = run_env.get("TMPDIR") or _writable_tmpdir(conanfile)
    for key in ("TMPDIR", "TMP", "TEMP"):
        run_env[key] = tmp
    lib_paths = [str(conanfile.build_folder)]
    try:
        for dep in conanfile.dependencies.host.values():
            try:
                for d in dep.cpp_info.libdirs or []:
                    if d and d not in lib_paths:
                        lib_paths.append(d)
            except Exception:
                continue
    except Exception:
        pass
    prev = run_env.get("LD_LIBRARY_PATH", "")
    run_env["LD_LIBRARY_PATH"] = ":".join(lib_paths) + (":" + prev if prev else "")
    cases = [
        ("test", [ex_bin]),
        ("test-russian", [ex_bin, "ru"]),
    ]
    passed = 0
    for name, argv in cases:
        proc = subprocess.run(argv, input=fixture_bytes,
                              capture_output=True, cwd=str(conanfile.build_folder),
                              env=run_env, timeout=60)
        out = (proc.stdout or b"") + (proc.stderr or b"")
        try:
            text = out.decode("utf-8", errors="replace")
        except Exception:
            text = repr(out)
        conanfile.output.info(
            "upstream %s output:\n%s" % (name, text[:4000]))
        if proc.returncode != 0:
            raise Exception(
                "upstream %s failed with code %d output: %s"
                % (name, proc.returncode, text[:2000]))
        if not text.strip():
            raise Exception("upstream %s produced empty output" % name)
        # Content markers: language line + ASCII passthrough lines must survive.
        if ("Current Language" not in text
                and "Unable Detect Language" not in text):
            raise Exception(
                "upstream %s missing language marker" % name)
        if ("Good Morning" not in text and "Guten Abend" not in text
                and "Auf widersehen" not in text):
            raise Exception(
                "upstream %s missing passthrough content" % name)
        passed += 1
    result = {
        "status": "passed",
        "framework": "autotools",
        "command": _HMBS_UPSTREAM_COMMAND,
        "discovered": 2,
        "executed": 2,
        "passed": passed,
        "failed": 0,
        "skipped": 0,
    }
    return result


def _dep_flags(conanfile):
    """Aggregate -I/-L/-l/-D from host deps (libxml2 + transitive)."""
    includes, libdirs, libs, defines = [], [], [], []
    try:
        deps = conanfile.dependencies.host.values()
    except Exception:
        deps = []
    for dep in deps:
        try:
            info = dep.cpp_info
        except Exception:
            continue
        for attr, bucket in (
            ("includedirs", includes), ("libdirs", libdirs),
            ("libs", libs), ("defines", defines),
        ):
            try:
                for value in getattr(info, attr) or []:
                    if value and value not in bucket:
                        bucket.append(value)
            except Exception:
                continue
        try:
            for value in info.system_libs or []:
                if value and value not in libs:
                    libs.append(value)
        except Exception:
            pass
    return includes, libdirs, libs, defines


class LibrccConan(ConanFile):
    name = "librcc"
    version = "0.2.13"
    description = "Russian Charset Conversion Library (RusXMMS recoding/autodetection)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/RusXMMS/librcc"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxml2/2.15.3")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "librcc is only supported on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        _ensure_tmp_env(self)
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _ensure_tmp_env(self)
        from conan.tools.gnu import PkgConfigDeps
        from conan.tools.env import VirtualBuildEnv
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        # Propagate writable tmp root into conanbuild.sh so compiler and
        # test children never fall back to read-only /tmp.
        tmp = _writable_tmpdir(self)
        hmbs_env = Environment()
        hmbs_env.define("TMPDIR", tmp)
        hmbs_env.define("TMP", tmp)
        hmbs_env.define("TEMP", tmp)
        hmbs_env.define("SHELL", "/bin/sh")
        hmbs_env.define("CONFIG_SHELL", "/bin/sh")
        hmbs_env.vars(self, scope="build").save_script("hmbs_env")

    def build(self):
        _ensure_tmp_env(self)
        # Upstream includes "../config.h" from src/; generate it once.
        save(self, os.path.join(self.source_folder, "config.h"), _CONFIG_H)
        includes, libdirs, libs, defines = _dep_flags(self)
        inc_flags = " ".join('-I"%s"' % d for d in includes)
        libdir_flags = " ".join('-L"%s"' % d for d in libdirs)
        # -lxml2 must resolve via aggregated libdirs; pthread/dl/m always.
        link_libs = list(libs)
        for required in ("xml2", "pthread", "dl", "m"):
            if required not in link_libs:
                link_libs.append(required)
        lib_flags = " ".join("-l%s" % lib for lib in link_libs)
        define_flags = " ".join("-D%s" % d for d in defines)
        data_dir = os.path.join(self.package_folder, "lib", "rcc").replace("\\", "/")
        cflags = "-fPIC -O2 -Wall -Wno-deprecated-declarations %s %s -I\"%s\" -I\"%s/src\" -DLIBRCC_DATA_DIR=\\\"%s\\\"" % (
            define_flags, inc_flags, self.source_folder, self.source_folder, data_dir)

        obj_dir = os.path.join(self.build_folder, "objs")
        os.makedirs(obj_dir, exist_ok=True)
        # Compile in one conanbuild shell so CC/clang from the HNP toolchain
        # and TMPDIR/SHELL injection apply; -j1 semantics (one command).
        compile_lines = []
        for src in _SRC_FILES:
            compile_lines.append(
                '"${CC:-clang}" %s -c "%s/src/%s" -o "%s/%s.o"' % (
                    cflags, self.source_folder, src, obj_dir, src))
        for src in _UI_FILES:
            compile_lines.append(
                '"${CC:-clang}" %s -c "%s/ui/%s" -o "%s/ui_%s.o"' % (
                    cflags, self.source_folder, src, obj_dir, src))
        script = "set -eu\n"
        script += "echo \"[hmbs-build] CC=${CC:-clang}\"\n"
        script += "mkdir -p \"%s\"\n" % obj_dir
        for line in compile_lines:
            script += line + "\n"
        src_objs = " ".join('"%s/%s.o"' % (obj_dir, s) for s in _SRC_FILES)
        ui_objs = " ".join('"%s/ui_%s.o"' % (obj_dir, s) for s in _UI_FILES)
        if self.options.shared:
            script += '"${CC:-clang}" -shared -o "%s/librcc.so" %s %s %s\n' % (
                self.build_folder, src_objs, libdir_flags, lib_flags)
            script += '"${CC:-clang}" -shared -o "%s/librccui.so" %s "%s/librcc.so" %s %s\n' % (
                self.build_folder, ui_objs, self.build_folder, libdir_flags, lib_flags)
        else:
            # Static archives; engines stay shared modules (dlopen).
            objs = " ".join('"%s/%s.o"' % (obj_dir, s) for s in _SRC_FILES)
            ui_objs = " ".join('"%s/ui_%s.o"' % (obj_dir, s) for s in _UI_FILES)
            script += 'ar rcs "%s/librcc.a" %s\n' % (self.build_folder, objs)
            script += 'ar rcs "%s/librccui.a" %s\n' % (self.build_folder, ui_objs)
        # Western detection engine (always built, dlopen module).
        script += '"${CC:-clang}" -fPIC -O2 %s %s -I"%s" -I"%s/src" -c "%s/engines/western.c" -o "%s/western_engine.o"\n' % (
            define_flags, inc_flags, self.source_folder, self.source_folder,
            self.source_folder, obj_dir)
        if self.options.shared:
            script += '"${CC:-clang}" -shared -o "%s/western_engine.so" "%s/western_engine.o" "%s/librcc.so" %s %s\n' % (
                self.build_folder, obj_dir, self.build_folder, libdir_flags, lib_flags)
        else:
            script += '"${CC:-clang}" -shared -o "%s/western_engine.so" "%s/western_engine.o" %s %s\n' % (
                self.build_folder, obj_dir, libdir_flags, lib_flags)
        script += 'ls -la "%s"\n' % self.build_folder
        self.run(script, env="conanbuild")
        upstream_result = _run_upstream_examples(
            self, define_flags, inc_flags, libdir_flags, lib_flags)
        _persist_and_emit_upstream(self, upstream_result)

    def package(self):
        _ensure_tmp_env(self)
        if self.options.shared:
            copy(self, "librcc.so", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
            copy(self, "librccui.so", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "librcc.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
            copy(self, "librccui.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "western_engine.so", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib", "rcc", "engines"))
        # Persisted upstream evidence for cache-hit re-emit in test_package.
        # Copy the build-time JSON produced by _run_upstream_examples; if the
        # build folder was cleaned, test_package will hard-fail (no fake
        # evidence) instead of regenerating.
        try:
            copy(self, "hmbs_upstream_test_result.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "lib", "rcc"))
        except Exception as exc:  # noqa: BLE001
            self.output.warning(
                "copy upstream result failed (non-fatal): %s" % exc)
        copy(self, "librcc.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "librccui.h", src=os.path.join(self.source_folder, "ui"),
             dst=os.path.join(self.package_folder, "include"))
        # Minimal librcc.pc from the upstream template (version substituted).
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        prefix = self.package_folder.replace("\\", "/")
        with open(os.path.join(pc_dir, "librcc.pc"), "w", encoding="utf-8", newline="\n") as handle:
            handle.write("prefix=%s\n" % prefix)
            handle.write("exec_prefix=${prefix}\nlibdir=${prefix}/lib\nincludedir=${prefix}/include\n\n")
            handle.write("Name: librcc\nDescription: Encoding Conversion Library\n")
            handle.write("Requires: libxml-2.0\nVersion: 0.2.13\n")
            handle.write("Libs: -L${libdir} -lrcc\nCflags: -I${includedir}\n")

    def package_info(self):
        self.cpp_info.libs = ["rcc", "rccui"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "librcc")
        self.cpp_info.set_property("cmake_target_name", "librcc::librcc")
        self.cpp_info.set_property("pkg_config_name", "librcc")
        self.cpp_info.requires = ["libxml2::libxml2"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
