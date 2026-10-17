#!/usr/bin/env python3
"""Conan recipe — libfaketime 0.9.11 (plain Makefile, LD_PRELOAD interposer).

libfaketime is a preloaded shared object that rewrites the result of the libc
time/pthread "deadline" APIs, plus a `faketime` wrapper that sets LD_PRELOAD for
one command. Upstream ships no configure, uses `CC ?= gcc`, and installs through
the root Makefile (src + man + doc).

OHOS notes:
  - The library binds its interposers to glibc symbol-version nodes through
    `__asm__(".symver ..., sym@GLIBC_2.x")` plus src/libfaketime.map. musl has no
    symbol versioning and the OHOS clang assembler frontend rejects `.symver`
    without a `@` tag, so both halves need porting (patches 0001/0002).
  - The OHOS replacement for that version script is *generated* in build()
    instead of being added by a patch: the repo's own `refresh-patch --auto`
    regenerates one patch per existing source file and silently drops
    new-file hunks, which would leave the recipe pointing at a script nobody
    creates. Upstream's glibc-facing src/libfaketime.map stays untouched.
  - `bin/faketime` resolves the library from the compile-time PREFIX, so build
    and install must agree on PREFIX=<package_folder>.
  - The upstream Makefile only special-cases Darwin/SunOS; OHOS falls into the
    generic branch, so no platform switch patch is needed there.
"""
import os
import platform

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout

# The OHOS clang wrapper injects -Wl,--code-sign / -fuse-ld=lld into every
# command line, which -Wunused-command-line-argument turns into an error under
# the project's -Werror. The remaining two flags silence clang-only diagnostics
# on upstream sources. FAKE_RANDOM/FAKE_PID are opt-in upstream features that
# the snippet suite of this very release drives.
COMPILE_FLAGS = " ".join([
    "-Wno-error=unused-command-line-argument",
    "-Wno-self-assign",
    "-Wno-error=unused-but-set-variable",
    "-DFAKE_RANDOM",
    "-DFAKE_PID",
])

# Linker script used in place of upstream's src/libfaketime.map on musl/OHOS:
# glibc version nodes do not exist there, so only the "hide the internal
# variants" half of the original script is kept.
VERSION_SCRIPT_NAME = "libfaketime.map.ohos"
VERSION_SCRIPT = """\
# OHOS/musl has no symbol versioning (glibc's GLIBC_2.x version nodes do not
# exist), so a version script that binds our interposers to GLIBC_* nodes makes
# ld.lld fail with "symbol ...@@ has undefined version". Keep only the
# hidden-symbol part of the original script.
{
  local:
    timer_settime_*;
    timer_gettime_*;
    pthread_cond_timedwait_*;
    pthread_cond_init_*;
    pthread_cond_destroy_*;
};
"""


class LibfaketimeConan(ConanFile):
    name = "libfaketime"
    version = "0.9.11"
    description = "Library and wrapper to fake the system time seen by a process, via LD_PRELOAD"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/wolfcw/libfaketime"
    url = "https://github.com/wolfcw/libfaketime"
    topics = ("time", "clock", "preload", "testing")
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # datefudge/1.27 (merged, same wall) shows the variable that decides
        # whether a worker honours the preload is the *injection target*, not
        # the object: its notes.md records that the worker's system Perl is not
        # intercepted while a repository-published Conan perl is. Declare such a
        # `date` so the probe can try it as a second target. test-only, so it
        # stays out of the package requirements and out of the package_id.
        if str(self.settings.os) == "OHOS":
            self.test_requires("coreutils/9.10")

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfaketime needs a glibc/musl ELF platform, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def _make_vars(self):
        return (
            f'CC="{self._compiler_c()}" '
            f'PREFIX="{self.package_folder}" '
            'LIBDIRNAME="/lib/faketime" '
            f'VERSION_SCRIPT={VERSION_SCRIPT_NAME} '
            f'FAKETIME_COMPILE_CFLAGS="{COMPILE_FLAGS}"'
        )

    def generate(self):
        env = Environment()
        env.define("CC", self._compiler_c())
        env.vars(self).save_script("conanbuild_cc")

    def build(self):
        apply_conandata_patches(self)
        # The Makefile links with `--version-script=<name>` relative to src/,
        # so the generated script has to sit next to the sources.
        save(self, os.path.join(self.source_folder, "src", VERSION_SCRIPT_NAME),
             VERSION_SCRIPT)
        vars_ = self._make_vars()
        self.run(f'make -j1 {vars_}', cwd=self.source_folder)
        # Upstream test entry: root `test` builds src then runs `make -C test all`
        # (timetest + the testframe functional suites + test.sh scenarios).
        lib, bindir = self._select_preload_pair()
        test_env = self._preload_env_var(lib)
        path_prefix = (bindir + ":") if bindir else ""
        self._with_hnp_perl(f'{test_env}make -j1 {vars_} test',
                            cwd=self.source_folder, path_prefix=path_prefix)
        self._with_hnp_perl(f'{test_env}make -j1 {vars_} snippets',
                            cwd=os.path.join(self.source_folder, "test"),
                            path_prefix=path_prefix)

    def _preload_env_var(self, lib):
        # Upstream's test drivers preload "../src/libfaketime.so.1", i.e. a path
        # relative to the current directory, and musl's loader *silently*
        # ignores an LD_PRELOAD entry it cannot honour (no diagnostic, exit
        # status 0) -- so a suite that "passes" may have measured real time
        # throughout. FAKETIME_TESTLIB is upstream's own escape hatch
        # (test/functests/common.inc, test.sh, test_variable_data.sh,
        # test_constructors.sh, randomtest.sh); the probe below hands it the
        # absolute path of the one object this loader actually accepts.
        return f'FAKETIME_TESTLIB="{lib}" '

    def _can_run_ohos_binaries(self):
        # datefudge/1.27 guard: only claim the Conan coreutils binaries when this
        # machine can actually exec OHOS aarch64 ELFs.
        return str(self.settings.os) == "OHOS" and platform.machine().lower() in (
            "aarch64", "arm64")

    def _coreutils_bin(self):
        if not self._can_run_ohos_binaries():
            return ""
        return os.path.join(
            self.dependencies.test["coreutils"].package_folder, "bin")

    def _select_preload_pair(self):
        # Return the (library, target-bindir) pair this loader really honours.
        #
        # musl's loader drops an LD_PRELOAD entry it cannot honour without any
        # diagnostic and without a non-zero exit status, so every time-faking
        # assertion silently measures real time while the suite still reports
        # success. Probe once, loudly, before 31+ assertions depend on it.
        #
        # Five CI rounds moved the *object* (absolute path, chmod 0755, a copy
        # this process created itself, that copy self-signed, a copy under
        # $TMPDIR) against the worker's system `date`; none was ever mapped
        # (empty loader stderr, and a deliberately unparseable FAKETIME was
        # accepted without complaint, which a loaded libfaketime never is).
        # The merged datefudge/1.27 precedent says the decisive variable is the
        # *target* -- system programs are not intercepted, repository-published
        # Conan binaries are (knowledge base E502/E465). So each object rung is
        # now probed against both targets, cheapest first, and the winning pair
        # is handed to the suites: FAKETIME_TESTLIB plus a PATH prefix that
        # makes `date` resolve to that same target. Nothing is hidden either
        # way -- if no pair works, the build fails right after the evidence dump.
        src = os.path.join(self.source_folder, "src")
        cu = self._coreutils_bin()
        ladder = [
            'SRC="%s"' % src,
            'lib="$SRC/libfaketime.so.1"',
            'pair="$SRC/.lft-preload-pair"',
            'c1="$SRC/lft-check.so"',
            'cu="%s"' % cu,
            'fake() {',
            '  out=$(LD_PRELOAD="$1" FAKETIME=1 FAKETIME_FMT=%s "$2" +%s 2>/dev/null)',
            '  [ x"$out" = x1 ]',
            '}',
            'try() {',
            '  if fake "$1" "$2"; then',
            '    echo "  $4 -> VIABLE lib=$1 target=$2 prepend=$3"',
            '    printf \'%s\\n%s\\n\' "$1" "$3" > "$pair"',
            '    exit 0',
            '  fi',
            '  echo "  $4 -> not faked"',
            '}',
            'sign() { env -u LD_LIBRARY_PATH "$@"; }',
            'rung() {',
            '  try "$1" date           ""   "$2 / system date"',
            '  if [ -n "$cu" ]; then',
            '    try "$1" "$cu/date" "$cu" "$2 / coreutils date"',
            '  fi',
            '}',
            'rm -f "$pair"',
            'echo "  TMPDIR      : ${TMPDIR:-unset}  $(ls -ld ${TMPDIR:-/nonexistent} 2>&1 | head -1)"',
            'echo "  coreutils   : $(ls -l "$cu/date" 2>&1 | head -1)"',
            'echo "libfaketime preload self-check (object rung x injection target)"',
            'run=$(timeout 20 "$SRC"/faketime 1 date +%s 2>&1 | head -2)',
            'echo "  wrapper control (sets LD_PRELOAD itself): $run"',
            'rung "$lib" "r1 as built"',
            'echo "  r2 chmod 0755 the build-tree objects (E543)"',
            'chmod 0755 "$SRC/libfaketime.so.1" "$SRC/libfaketimeMT.so.1" "$SRC/faketime" 2>&1',
            'rung "$lib" "r2 as built after chmod"',
            'echo "  r3 a fresh copy created by this process"',
            'rm -f "$c1"',
            'cp "$lib" "$c1" 2>&1',
            'chmod 0755 "$c1" 2>&1',
            'echo "  $(ls -ld "$c1" 2>&1)"',
            'rung "$c1" "r3 owned copy"',
            'echo "  r4 self-sign that copy (XPM, same treatment package() gives)"',
            'sign llvm-objcopy --remove-section .codesign "$c1" 2>/dev/null || true',
            'sg=$(sign binary-sign-tool sign -inFile "$c1" -outFile "$c1" -selfSign 1 2>&1 | tail -1)',
            'echo "  $sg"',
            'rung "$c1" "r4 owned copy after self-sign"',
            'echo "  r5 a copy under $TMPDIR (possibly another mount)"',
            't="${TMPDIR:-/data/local/tmp}"',
            'c2="$t/lft-check.so"',
            'rm -f "$c2"',
            'cp "$lib" "$c2" 2>&1 && chmod 0755 "$c2" 2>&1',
            'sign llvm-objcopy --remove-section .codesign "$c2" 2>/dev/null || true',
            'sign binary-sign-tool sign -inFile "$c2" -outFile "$c2" -selfSign 1 >/dev/null 2>&1 || true',
            'echo "  $(ls -ld "$c2" 2>&1)"',
            'rung "$c2" "r5 tmpdir copy"',
            'echo "  every rung failed: dumping evidence"',
            'echo "  uid            : $(id -u 2>&1)"',
            'echo "  shell exe      : $(readlink -f /proc/$$/exe 2>&1)"',
            'echo "  cwd            : $(pwd 2>&1)"',
            'echo "  PATH           : $PATH"',
            'echo "  machine        : $(uname -m)"',
            'echo "  dynamic loader : $(ls /lib/ld-musl* 2>&1)"',
            'echo "  preload objects: $(ls -l "$lib" "$c1" 2>&1)"',
            'echo "  codesign sect  : $(readelf -S "$lib" 2>&1 | grep -c codesign)"',
            'echo "  lib NEEDED     : $(readelf -d "$lib" 2>&1 | grep NEEDED | tr -s " ")"',
            'err=$(LD_PRELOAD="$lib" FAKETIME=1 FAKETIME_FMT=%s date +%s 2>&1 >/dev/null)',
            'echo "  loader stderr  : $err"',
            'mnt=$(grep storage /proc/self/mounts 2>&1 | head -2 | tr -s " " | cut -c1-160)',
            'echo "  storage mount  : $mnt"',
            'echo "  candidates (elf type / result):"',
            'for c in date /usr/bin/date /bin/date /system/bin/date "$cu/date"; do',
            '  p=$(command -v "$c" 2>&1)',
            '  r=$(LD_PRELOAD="$lib" FAKETIME=1 FAKETIME_FMT=%s "$c" +%s 2>&1)',
            '  ty=$(readelf -h "$p" 2>/dev/null | sed -n "s/^ *Type: //p" | tr -s " ")',
            '  echo "   $c -> $p type=$ty result=$r"',
            'done',
            'for tt in date "$cu/date"; do',
            '  mp=$(LD_PRELOAD="$lib" FAKETIME=1 "$tt" 2>&1 | head -2)',
            '  echo "  mapped at all? (a loaded libfaketime complains about the '
            'unparseable FAKETIME, an ignored preload does not) target=$tt -> $mp"',
            'done',
            'exit 1',
        ]
        self._with_hnp_perl("\n".join(ladder), cwd=self.source_folder)
        marker = os.path.join(src, ".lft-preload-pair")
        lib = ""
        bindir = ""
        if os.path.isfile(marker):
            with open(marker, encoding="utf-8") as handle:
                lines = [line.strip() for line in handle.read().splitlines()]
            if len(lines) >= 2:
                lib, bindir = lines[0], lines[1]
        if not lib or not os.path.isfile(lib):
            raise Exception(
                "libfaketime: this loader honours no LD_PRELOAD object against "
                "either injection target (worker system `date` and the Conan "
                "coreutils `date`) -- see the rung matrix and evidence above, "
                "the upstream functional suites would silently measure real time")
        return lib, bindir

    def _with_hnp_perl(self, command, cwd, path_prefix=""):
        # test/functests/test_exclude_mono.sh needs a perl whose Time::HiRes
        # exposes clock_gettime(); the HNP perl does, a user-local build of the
        # same version may not. Prepending the HNP dir is a no-op where the
        # PATH perl already works.
        # The suite needs perl (HNP) and a `date` to inject into. Keep that
        # ordering pinned so the probe's verdict cannot drift with the caller's
        # PATH -- and put the pair the probe selected *first*, otherwise a
        # "coreutils date" verdict is undone by /usr/bin/date (toybox) shadowing
        # it and the suites silently run against the target that was rejected.
        self.run(f'PATH="{path_prefix}/data/service/hnp/bin:/usr/bin:/bin:$PATH" '
                 f'{command}', cwd=cwd)

    def package(self):
        vars_ = self._make_vars()
        self.run(f'make {vars_} DESTDIR="" install', cwd=self.source_folder)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # E543: HMDFS hands out 0660 by default, which execve()/the loader reject.
        os.chmod(os.path.join(self.package_folder, "bin", "faketime"), 0o755)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS XPM requires self-signed ELF. The hnp tools resolve libc++
        # from their own location, so the LD_LIBRARY_PATH the ohos-aarch64
        # profile buildenv prepends has to be dropped for them to run.
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        lib = os.path.join(self.package_folder, "lib", "faketime")
        for f in (os.path.join(self.package_folder, "bin", "faketime"),
                  os.path.join(lib, "libfaketime.so.1"),
                  os.path.join(lib, "libfaketimeMT.so.1")):
            if not os.path.isfile(f) or not self._is_elf(f):
                continue
            self.run(f'env -u LD_LIBRARY_PATH {objcopy} '
                     f'--remove-section .codesign "{f}" 2>/dev/null || true')
            self.run(f'env -u LD_LIBRARY_PATH {signer} '
                     f'sign -inFile "{f}" -outFile "{f}" -selfSign 1')

    def package_info(self):
        # Nothing is ever linked against this package: it is an LD_PRELOAD
        # payload without headers or import library. Consumers read the paths
        # published below (see test_package).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        lib = os.path.join(self.package_folder, "lib", "faketime")
        self.cpp_info.set_property("user:preload_lib", os.path.join(lib, "libfaketime.so.1"))
        self.cpp_info.set_property("user:preload_lib_mt", os.path.join(lib, "libfaketimeMT.so.1"))
        self.cpp_info.set_property("user:faketime_cli",
                                   os.path.join(self.package_folder, "bin", "faketime"))
