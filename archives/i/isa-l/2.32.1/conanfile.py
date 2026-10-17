#!/usr/bin/env python3
"""Conan recipe -- isa-l 2.32.1 (direct compile, no CMake project()).

Intel Intelligent Storage Acceleration Library: CRC, RAID, erasure coding
and compression primitives with aarch64 assembly paths.

OHOS notes:
1. No CMake configure step is executed at all. On some preflight runners
   the profile-pinned compiler /data/service/hnp/bin/clang cannot be
   identified by CMake ("The C compiler identification is unknown" at
   project(), Error 1), and earlier the autotools bootstrap failed for the
   same class of cause (profile-pinned hnp bash inaccessible, m4 Error 127,
   plus read-only /tmp). Both failures live in third-party/configure
   machinery, not in isa-l sources. Following the libe57format precedent,
   the recipe compiles the exact upstream source set directly with a
   verified-working compiler and links the archive itself.
2. Source set, defines and include paths mirror upstream cmake/*.cmake for
   CPU_AARCH64 exactly: base sources + AArch64 .S/.c dispatcher files,
   -Daarch64, lib-private -DISAL_DEPRECATED_INTERNAL, -Iinclude -I. for
   the library (igzip check tests additionally -Iigzip), .S files compiled
   with CC plus -D__ASSEMBLY__. The single SVE-intrinsics TU
   (gf_nvect_dot_prod_sve.c, needs the compiler SVE feature macro for
   <arm_sve.h>) gets -O3 -march=armv8-a+sve per aarch64/Makefile.am.
   Non-AArch64 falls back to the upstream
   CPU_UNDEFINED base-alias sources with no -D flag.
3. The same 17 check programs registered via upstream add_test are built
   (test .c + libisal only, each carries its own main) and executed one by
   one; results are accounted strictly (discovered/executed/passed/failed/
   skipped) and emitted as HMBS_UPSTREAM_TEST_RESULT (dual channel +
   persisted file for test_package re-emission). Nothing is skipped.
4. Toolchain handling: the pinned absolute CC is used only after it passes
   a `--version` probe; otherwise basename/PATH/sibling discovery picks a
   working compiler (ar likewise), every tool invocation goes through
   self.run(env="conanbuild") so hmbs-injected PATH/TMPDIR apply, and a
   minimal compile-link-run smoke test gates the build with an explicit
   environment error when no usable compiler exists.
5. OHOS/musl source fixes (in-recipe, idempotent, no patch files):
   raid_base.c 64-bit word-mask guard extended for libc without __WORDSIZE,
   and the isal_adler32 dispatcher falls back to adler32_base on __OHOS__
   (neon vector path mismatches the bit-exact C reference on device);
   Linux/Apple behavior unchanged, all 17 checks still run.
"""
import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Exact upstream cmake/*.cmake source sets for CPU_AARCH64 (v2.32.1).
_ERASURE_AARCH64 = [
    "erasure_code/ec_base.c",
    "erasure_code/aarch64/ec_aarch64_highlevel_func.c",
    "erasure_code/aarch64/ec_aarch64_dispatcher.c",
    "erasure_code/aarch64/gf_vect_dot_prod_neon.S",
    "erasure_code/aarch64/gf_2vect_dot_prod_neon.S",
    "erasure_code/aarch64/gf_3vect_dot_prod_neon.S",
    "erasure_code/aarch64/gf_4vect_dot_prod_neon.S",
    "erasure_code/aarch64/gf_5vect_dot_prod_neon.S",
    "erasure_code/aarch64/gf_vect_mad_neon.S",
    "erasure_code/aarch64/gf_2vect_mad_neon.S",
    "erasure_code/aarch64/gf_3vect_mad_neon.S",
    "erasure_code/aarch64/gf_4vect_mad_neon.S",
    "erasure_code/aarch64/gf_5vect_mad_neon.S",
    "erasure_code/aarch64/gf_6vect_mad_neon.S",
    "erasure_code/aarch64/gf_vect_mul_neon.S",
    "erasure_code/aarch64/gf_vect_mad_sve.S",
    "erasure_code/aarch64/gf_2vect_mad_sve.S",
    "erasure_code/aarch64/gf_3vect_mad_sve.S",
    "erasure_code/aarch64/gf_4vect_mad_sve.S",
    "erasure_code/aarch64/gf_5vect_mad_sve.S",
    "erasure_code/aarch64/gf_6vect_mad_sve.S",
    "erasure_code/aarch64/gf_vect_mul_sve.S",
    "erasure_code/aarch64/gf_nvect_dot_prod_sve.c",
    "erasure_code/aarch64/ec_multibinary_arm.S",
]
_CRC_AARCH64 = [
    "crc/crc_base.c",
    "crc/crc64_base.c",
    "crc/aarch64/crc_multibinary_arm.S",
    "crc/aarch64/crc_aarch64_dispatcher.c",
    "crc/aarch64/crc16_t10dif_pmull.S",
    "crc/aarch64/crc16_t10dif_copy_pmull.S",
    "crc/aarch64/crc32_ieee_norm_pmull.S",
    "crc/aarch64/crc64_ecma_refl_pmull.S",
    "crc/aarch64/crc64_ecma_norm_pmull.S",
    "crc/aarch64/crc64_iso_refl_pmull.S",
    "crc/aarch64/crc64_iso_norm_pmull.S",
    "crc/aarch64/crc64_jones_refl_pmull.S",
    "crc/aarch64/crc64_jones_norm_pmull.S",
    "crc/aarch64/crc64_rocksoft_refl_pmull.S",
    "crc/aarch64/crc64_rocksoft_norm_pmull.S",
    "crc/aarch64/crc32_iscsi_refl_pmull.S",
    "crc/aarch64/crc32_gzip_refl_pmull.S",
    "crc/aarch64/crc32_iscsi_3crc_fold.S",
    "crc/aarch64/crc32_gzip_refl_3crc_fold.S",
    "crc/aarch64/crc32_iscsi_crc_ext.S",
    "crc/aarch64/crc32_gzip_refl_crc_ext.S",
    "crc/aarch64/crc32_mix_default.S",
    "crc/aarch64/crc32c_mix_default.S",
    "crc/aarch64/crc32_mix_neoverse_n1.S",
    "crc/aarch64/crc32c_mix_neoverse_n1.S",
]
_RAID_AARCH64 = [
    "raid/raid_base.c",
    "raid/aarch64/xor_gen_neon.S",
    "raid/aarch64/pq_gen_neon.S",
    "raid/aarch64/xor_check_neon.S",
    "raid/aarch64/pq_check_neon.S",
    "raid/aarch64/raid_multibinary_arm.S",
    "raid/aarch64/raid_aarch64_dispatcher.c",
]
_IGZIP_AARCH64 = [
    "igzip/igzip.c",
    "igzip/hufftables_c.c",
    "igzip/igzip_base.c",
    "igzip/igzip_icf_base.c",
    "igzip/adler32_base.c",
    "igzip/flatten_ll.c",
    "igzip/encode_df.c",
    "igzip/igzip_icf_body.c",
    "igzip/huff_codes.c",
    "igzip/igzip_inflate.c",
    "igzip/aarch64/igzip_inflate_multibinary_arm64.S",
    "igzip/aarch64/igzip_multibinary_arm64.S",
    "igzip/aarch64/igzip_isal_adler32_neon.S",
    "igzip/aarch64/igzip_multibinary_aarch64_dispatcher.c",
    "igzip/aarch64/igzip_deflate_body_aarch64.S",
    "igzip/aarch64/igzip_deflate_finish_aarch64.S",
    "igzip/aarch64/isal_deflate_icf_body_hash_hist.S",
    "igzip/aarch64/isal_deflate_icf_finish_hash_hist.S",
    "igzip/aarch64/igzip_set_long_icf_fg.S",
    "igzip/aarch64/encode_df.S",
    "igzip/aarch64/isal_update_histogram.S",
    "igzip/aarch64/gen_icf_map.S",
    "igzip/aarch64/igzip_deflate_hash_aarch64.S",
    "igzip/aarch64/igzip_decode_huffman_code_block_aarch64.S",
    "igzip/proc_heap_base.c",
]
_MEM_AARCH64 = [
    "mem/mem_zero_detect_base.c",
    "mem/aarch64/mem_zero_detect_neon.S",
    "mem/aarch64/mem_multibinary_arm.S",
    "mem/aarch64/mem_aarch64_dispatcher.c",
]
_MISC = ["misc/version.c"]

# Upstream CPU_UNDEFINED fallback (base + aliases, no ARCH define).
_BASE_ALIASES = [
    "erasure_code/ec_base.c",
    "erasure_code/ec_base_aliases.c",
    "crc/crc_base.c",
    "crc/crc64_base.c",
    "crc/crc_base_aliases.c",
    "raid/raid_base.c",
    "raid/raid_base_aliases.c",
    "igzip/igzip.c",
    "igzip/hufftables_c.c",
    "igzip/igzip_base.c",
    "igzip/igzip_icf_base.c",
    "igzip/adler32_base.c",
    "igzip/flatten_ll.c",
    "igzip/encode_df.c",
    "igzip/igzip_icf_body.c",
    "igzip/huff_codes.c",
    "igzip/igzip_inflate.c",
    "igzip/igzip_base_aliases.c",
    "igzip/proc_heap_base.c",
    "mem/mem_zero_detect_base.c",
    "mem/mem_zero_detect_base_aliases.c",
    "misc/version.c",
]

# Per-file extra flags mirroring upstream intent:
# - erasure_code/aarch64/Makefile.am builds gf_nvect_dot_prod_sve.c with
#   -O3 ("Ensure SVE intrinsics are compiled with maximum optimization");
# - the TU includes <arm_sve.h>, whose clang guard (#error "SVE support
#   not enabled") requires the compiler's SVE feature macro, enabled here
#   with -march=armv8-a+sve. All functions in the TU carry
#   __attribute__((target("+sve"))) after the in-recipe fix (the 7 upstream
#   `target("+sve+sve2")` wrappers are narrowed to plain `+sve`: the
#   preflight clang grants no `+sve` from the combined spelling, which made
#   the `always_inline` helper illegal to inline; SVE2 is a pure EOR3
#   optimization, correctness is bit-identical), and callers reach them only
#   through the HWCAP-gated aarch64 dispatcher, so non-SVE CPUs are
#   unaffected (same object upstream ships in its aarch64 releases).
_EXTRA_CFLAGS = {
    "erasure_code/aarch64/gf_nvect_dot_prod_sve.c":
        ["-O3", "-march=armv8-a+sve"],
}

# The 17 check programs registered via upstream add_test (name, subdir,
# extra include dirs beyond "include").
_CHECK_TESTS = [
    ("gf_vect_mul_test", "erasure_code", []),
    ("erasure_code_test", "erasure_code", []),
    ("gf_inverse_test", "erasure_code", []),
    ("erasure_code_update_test", "erasure_code", []),
    ("xor_gen_test", "raid", []),
    ("pq_gen_test", "raid", []),
    ("xor_check_test", "raid", []),
    ("pq_check_test", "raid", []),
    ("crc16_t10dif_test", "crc", []),
    ("crc16_t10dif_copy_test", "crc", []),
    ("crc64_funcs_test", "crc", []),
    ("crc32_funcs_test", "crc", []),
    ("igzip_rand_test", "igzip", ["igzip"]),
    ("igzip_wrapper_hdr_test", "igzip", ["igzip"]),
    ("checksum32_funcs_test", "igzip", ["igzip"]),
    ("mem_zero_detect_test", "mem", []),
    ("version_test", "misc", []),
]


class IsalConan(ConanFile):
    name = "isa-l"
    version = "2.32.1"
    description = "Intel Intelligent Storage Acceleration Library (CRC, RAID, erasure coding, compression)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/intel/isa-l"
    url = "https://github.com/intel/isa-l"
    package_type = "library"
    required_conan_version = ">=2.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "isa-l is only supported on Linux/OHOS, not {}".format(self.settings.os)
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        self._ensure_tmp_env()
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmp_env()
        _tmp = self._ensure_tmp_env()
        _hmbs_env = Environment()
        _hmbs_env.define("TMPDIR", _tmp)
        _hmbs_env.define("TMP", _tmp)
        _hmbs_env.define("TEMP", _tmp)
        _hmbs_env.define("SHELL", "/bin/sh")
        _hmbs_env.define("CONFIG_SHELL", "/bin/sh")
        for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK", "HMBS_CAP_LOCAL_MKTEMP",
                   "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD", "HMBS_CAP_SYMLINK",
                   "HMBS_TMPDIR", "HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA",
                   "HMBS_PYTHON3"):
            _v = os.environ.get(_k)
            if _v:
                _hmbs_env.define(_k, _v)
        _hmbs_env.vars(self, scope="build").save_script("hmbs_env")

    def _writable_tmpdir(self):
        _cands = []
        for _k in ("HMBS_TMPDIR", "HMBS_TMPDIR_RUNTIME"):
            _v = os.environ.get(_k)
            if _v:
                _cands.append(_v)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v and _v != "/tmp" and _v not in _cands:
                _cands.append(_v)
        _fb = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if _fb:
            _cands.append(_fb)
        for _base in (getattr(self, "build_folder", None),
                      getattr(self, "base_build_folder", None),
                      getattr(self, "source_folder", None),
                      getattr(self, "base_source_folder", None)):
            if _base:
                _cands.append(os.path.join(str(_base), "tmp"))
        for _c in _cands:
            if not _c:
                continue
            try:
                os.makedirs(_c, exist_ok=True)
            except OSError:
                continue
            if not os.path.isdir(_c):
                continue
            try:
                _probe = os.path.join(_c, ".hmbs_wtest")
                with open(_probe, "w", encoding="utf-8") as _f:
                    _f.write("w")
                os.remove(_probe)
                return _c
            except OSError:
                continue
        try:
            _d = os.path.join(str(self.build_folder), "tmp")
            os.makedirs(_d, exist_ok=True)
            return _d
        except Exception:
            return "/tmp"

    def _ensure_tmp_env(self):
        _tmp = self._writable_tmpdir()
        try:
            os.makedirs(_tmp, exist_ok=True)
        except OSError:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        try:
            os.umask(0o022)
        except Exception:
            pass
        return _tmp

    def _probe_runs(self, exe, args=("--version",)):
        try:
            _r = subprocess.run([exe] + list(args),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                timeout=60)
            return _r.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def _resolve_tool(self, conf_key, short_names):
        """Pinned absolute path only if it actually executes; else PATH."""
        try:
            _pinned = self.conf.get(conf_key, check_type=str)
        except Exception:
            _pinned = None
        if _pinned and os.path.isfile(_pinned) and self._probe_runs(_pinned):
            return _pinned
        if _pinned:
            _base = os.path.basename(_pinned)
            _w = shutil.which(_base)
            if _w and self._probe_runs(_w):
                self.output.warning(
                    "isa-l: pinned {} unusable, using PATH {}".format(_pinned, _w))
                return _w
            _sib_dir = os.path.dirname(_pinned)
            if os.path.isdir(_sib_dir):
                for _n in short_names:
                    _sib = os.path.join(_sib_dir, _n)
                    if os.path.isfile(_sib) and self._probe_runs(_sib):
                        self.output.warning(
                            "isa-l: pinned {} unusable, using sibling {}".format(
                                _pinned, _sib))
                        return _sib
        for _n in short_names:
            _w = shutil.which(_n)
            if _w and self._probe_runs(_w):
                if _pinned:
                    self.output.warning(
                        "isa-l: pinned {} unusable, using PATH {}".format(_pinned, _w))
                return _w
        if _pinned:
            return _pinned
        return short_names[0]

    def _is_aarch64(self):
        return str(self.settings.arch) in ("armv8", "arm64", "aarch64")

    def _lib_sources(self):
        if self._is_aarch64():
            return (_ERASURE_AARCH64 + _CRC_AARCH64 + _RAID_AARCH64
                    + _IGZIP_AARCH64 + _MEM_AARCH64 + _MISC)
        return list(_BASE_ALIASES)

    def _cflags(self):
        _flags = []
        if self._is_aarch64():
            _flags.append("-Daarch64")
        _flags.append("-DISAL_DEPRECATED_INTERNAL")
        if str(self.settings.build_type) == "Debug":
            _flags += ["-O0", "-g"]
        else:
            _flags.append("-O2")
        if self.options.shared or self.options.get_safe("fPIC"):
            _flags.append("-fPIC")
        return _flags

    def _smoke_test(self, cc):
        _tmp = self._ensure_tmp_env()
        _c = os.path.join(_tmp, "hmbs_cc_smoke.c")
        _o = os.path.join(_tmp, "hmbs_cc_smoke")
        with open(_c, "w", encoding="utf-8", newline="\n") as _f:
            _f.write('#include <stdio.h>\nint main(void)'
                     '{printf("hmbs-smoke-%d\\n", 40 + 2);return 0;}\n')
        self.run("{} {} -o {}".format(shlex.quote(cc), shlex.quote(_c),
                                      shlex.quote(_o)),
                 cwd=_tmp, env="conanbuild")
        _out = self.run(_o, cwd=_tmp, env="conanbuild")
        self.output.info("isa-l compiler smoke: {}".format(_out.strip()
                                                           if _out else "rc=0"))

    def _patch_once(self, path, old, new, tag):
        # Idempotent in-place source edit (no patch files): skip when a
        # previous build() already applied it (conan may reuse the source
        # tree across rebuilds), fail closed when neither form is found so
        # unexpected upstream changes surface instead of silently passing.
        with open(path, "r", encoding="utf-8", newline="") as _f:
            _content = _f.read()
        if new in _content:
            self.output.info("isa-l: {} already applied, skipping".format(tag))
            return
        if old not in _content:
            raise ConanException(
                "isa-l: {}: expected pattern not found in {}".format(tag, path))
        with open(path, "w", encoding="utf-8", newline="\n") as _f:
            _f.write(_content.replace(old, new, 1))
        self.output.info("isa-l: {} applied (in-recipe fix)".format(tag))

    def _apply_sve_inline_fix(self):
        # Previous cycle shipped a hand-written unified diff for this file;
        # its hunk header declared +39,13 while the body carries 14 new
        # lines (net +5 over 9 old lines: 7 added comment/attr lines minus
        # 2 removed attr lines), so Conan's patch parser rejected it
        # ("extra lines for hunk no.1", "Failed to parse patch") before any
        # compilation ran. Different route: exact string replacement in place
        # (no hunk counts, immune to CRLF/context drift). Semantics: drop
        # only `always_inline`, keep `target("+sve"/"+sme")` + `inline`, so
        # clang may emit a call when forced inlining is illegal; the
        # HWCAP-gated dispatcher still guards all callers.
        # NOTE (2026-09-17 preflight): the generic _patch_once() helper
        # short-circuits when the NEW string already exists anywhere in the
        # file. For this TU that guard is wrong: the plain
        # `target("+sve")` / `target("+sme")` wrapper attributes already
        # exist 7x, so _patch_once() reported "already applied" and never
        # removed the helper's `always_inline` -- the preflight log still
        # shows `always_inline function ... requires target feature '+sve'`.
        # Hence this method edits the file directly (all occurrences) with
        # its own idempotency check on the OLD strings, not the new ones.
        # Additionally the 7 SVE2 wrappers carry
        # `target("+sve+sve2")` (Apple: `"+sme+sme2"`); the preflight clang
        # compiles the caller `gf_vect_dot_prod_sve2` WITHOUT `+sve`, i.e.
        # it does not grant `+sve` from the combined `"+sve+sve2"` spelling,
        # which is exactly what makes the forced inline illegal. The SVE2
        # wrappers are a pure optimization (EOR3, upstream comment says the
        # compiler generates it automatically); narrowing them to plain
        # `+sve` keeps bit-exact correctness on OHOS while making every
        # caller/callee feature set compatible whatever the inliner does.
        _f = os.path.join(str(self.source_folder),
                          "erasure_code", "aarch64",
                          "gf_nvect_dot_prod_sve.c")
        if not os.path.isfile(_f):
            raise ConanException("isa-l: SVE source missing: {}".format(_f))
        with open(_f, "r", encoding="utf-8", newline="") as _fh:
            _content = _fh.read()
        _orig = _content
        _content = _content.replace(
            '__attribute__((target("+sme"), always_inline))',
            '__attribute__((target("+sme")))')
        _content = _content.replace(
            '__attribute__((target("+sve"), always_inline))',
            '__attribute__((target("+sve")))')
        _content = _content.replace(
            '__attribute__((target("+sve+sve2")))',
            '__attribute__((target("+sve")))')
        _content = _content.replace(
            '__attribute__((target("+sme+sme2")))',
            '__attribute__((target("+sme")))')
        if _content != _orig:
            with open(_f, "w", encoding="utf-8", newline="\n") as _fh:
                _fh.write(_content)
            self.output.info("isa-l: sve-inline+sve2-attr fix applied "
                             "(in-recipe fix)")
            return
        # No change: either already fixed or upstream changed unexpectedly.
        if ('always_inline' in _orig
                or '+sve+sve2' in _orig or '+sme+sme2' in _orig):
            raise ConanException(
                "isa-l: sve-attr fix: old patterns remain but replace failed")
        if ('__attribute__((target("+sve")))' not in _orig
                or 'gf_nvect_dot_prod_sve_unrolled' not in _orig):
            raise ConanException(
                "isa-l: sve-attr fix: expected patterns not found; "
                "upstream file changed?")
        self.output.info("isa-l: sve-inline+sve2-attr already applied, "
                         "skipping")

    def _apply_raid_wordsize_fix(self):
        # raid/raid_base.c selects its 64-bit word masks with
        # "#if __WORDSIZE == 64 || _WIN64 || __x86_64__". musl (OHOS) provides
        # no __WORDSIZE, so LP64 aarch64 wrongly took the 32-bit masks while
        # `unsigned long` is 64-bit: pq_gen_base generated broken Q parity and
        # pq_check_test failed exactly in its end-test section (the single
        # place pairing base-generated parity with the correct neon checker;
        # all ref/neon cross-checks passed). The compiler-predefined
        # __SIZEOF_LONG__ exists on GCC/Clang regardless of libc; extending
        # the guard with it keeps glibc/x86_64 behavior identical and repairs
        # musl/LP64. (ec_base.c carries the same macro name but its fallback
        # is width-independent byte code, so it needs no change.)
        _f = os.path.join(str(self.source_folder), "raid", "raid_base.c")
        if not os.path.isfile(_f):
            raise ConanException("isa-l: raid source missing: {}".format(_f))
        self._patch_once(
            _f,
            "#if __WORDSIZE == 64 || _WIN64 || __x86_64__",
            "#if __WORDSIZE == 64 || _WIN64 || __x86_64__ "
            "|| (defined(__SIZEOF_LONG__) && __SIZEOF_LONG__ == 8)",
            "raid-wordsize")

    def _apply_ohos_adler_fallback(self):
        # True-machine evidence: isal_adler32 via the neon vector path
        # (lengths >= 32) mismatches the bit-exact C reference adler_ref in
        # ~904 sub-cases (e.g. "fail checksum rand 13 = 0xba88733e
        # 0xb7cd733e" with identical low halves), while the <32B scalar path
        # agrees; igzip_rand_test's "incorrect zlib trailer" is the downstream
        # symptom of the same adler defect (deflate/inflate neon round-trips
        # themselves pass). Only this one dispatcher is narrowed to the
        # verified adler32_base on __OHOS__; Linux/Apple behavior is unchanged
        # and all 17 check programs still build and run (nothing skipped).
        _f = os.path.join(str(self.source_folder), "igzip", "aarch64",
                          "igzip_multibinary_aarch64_dispatcher.c")
        if not os.path.isfile(_f):
            raise ConanException(
                "isa-l: adler dispatcher missing: {}".format(_f))
        self._patch_once(
            _f,
            "DEFINE_INTERFACE_DISPATCHER(isal_adler32)\n{\n#if defined(__linux__)",
            "DEFINE_INTERFACE_DISPATCHER(isal_adler32)\n{\n#if defined(__OHOS__)\n"
            "        return adler32_base;\n#elif defined(__linux__)",
            "ohos-adler-base")

    def _apply_ohos_source_fixes(self):
        self._apply_sve_inline_fix()
        self._apply_raid_wordsize_fix()
        self._apply_ohos_adler_fallback()

    def _gen_isal_h(self):
        _h = os.path.join(str(self.build_folder), "isa-l.h")
        _content = (
            "/**\n *  @file isa-l.h\n *  @brief Include for ISA-L library\n"
            " *  Generated from upstream cmake/isa-l.h.in (2.32.1).\n */\n\n"
            "#ifndef _ISAL_H_\n#define _ISAL_H_\n\n"
            "#define ISAL_MAJOR_VERSION 2\n"
            "#define ISAL_MINOR_VERSION 32\n"
            "#define ISAL_PATCH_VERSION 1\n"
            "#define ISAL_MAKE_VERSION(maj, min, patch)"
            "  ((maj) * 0x10000 + (min) * 0x100 + (patch))\n"
            "#define ISAL_VERSION ISAL_MAKE_VERSION(ISAL_MAJOR_VERSION,"
            " ISAL_MINOR_VERSION, ISAL_PATCH_VERSION)\n\n"
            "#include <isa-l/erasure_code.h>\n"
            "#include <isa-l/gf_vect_mul.h>\n"
            "#include <isa-l/raid.h>\n"
            "#include <isa-l/crc.h>\n"
            "#include <isa-l/crc64.h>\n"
            "#include <isa-l/igzip_lib.h>\n"
            "#include <isa-l/mem_routines.h>\n\n"
            "#endif //_ISAL_H_\n")
        with open(_h, "w", encoding="utf-8", newline="\n") as _f:
            _f.write(_content)
        return _h

    def build(self):
        self._ensure_tmp_env()
        self._apply_ohos_source_fixes()
        _cc = self._resolve_tool("tools.build:compiler_executables:c",
                                 ("clang", "cc", "gcc"))
        _ar = self._resolve_tool("tools.build:compiler_executables:ar",
                                 ("llvm-ar", "ar"))
        if not self._probe_runs(_cc):
            raise ConanException(
                "isa-l: no usable C compiler (pinned {!r} failed --version "
                "probe and no PATH compiler runs)".format(_cc))
        self.output.info("isa-l direct compile: CC={} AR={}".format(_cc, _ar))
        self._smoke_test(_cc)
        _src = str(self.source_folder)
        _bf = str(self.build_folder)
        _obj_dir = os.path.join(_bf, "objs")
        _test_dir = os.path.join(_bf, "check_tests")
        os.makedirs(_obj_dir, exist_ok=True)
        os.makedirs(_test_dir, exist_ok=True)
        _flags = " ".join([shlex.quote(x) for x in self._cflags()])
        _inc = "-I{} -I{}".format(shlex.quote(os.path.join(_src, "include")),
                                  shlex.quote(_src))
        _objs = []
        for _rel in self._lib_sources():
            _s = os.path.join(_src, _rel)
            if not os.path.isfile(_s):
                raise ConanException(
                    "isa-l: upstream source missing: {}".format(_rel))
            _o = os.path.join(_obj_dir, _rel.replace("/", "_") + ".o")
            _extra = " -D__ASSEMBLY__" if _rel.endswith(".S") else ""
            _per_file = "".join([" {}".format(shlex.quote(x))
                                 for x in _EXTRA_CFLAGS.get(_rel, [])])
            self.run("{} {} {} {} -c {} -o {}".format(
                shlex.quote(_cc), _flags, _inc,
                (_extra + _per_file).strip(), shlex.quote(_s), shlex.quote(_o)),
                cwd=_bf, env="conanbuild")
            if not os.path.isfile(_o) or os.path.getsize(_o) == 0:
                raise ConanException(
                    "isa-l: empty object for {}".format(_rel))
            _objs.append(_o)
        _lib = os.path.join(_bf, "libisal.so" if self.options.shared
                            else "libisal.a")
        if self.options.shared:
            self.run("{} -shared -o {} {}".format(
                shlex.quote(_cc), shlex.quote(_lib),
                " ".join([shlex.quote(x) for x in _objs])),
                cwd=_bf, env="conanbuild")
        else:
            self.run("{} rcs {} {}".format(
                shlex.quote(_ar), shlex.quote(_lib),
                " ".join([shlex.quote(x) for x in _objs])),
                cwd=_bf, env="conanbuild")
        if not os.path.isfile(_lib) or os.path.getsize(_lib) == 0:
            raise ConanException("isa-l: library artifact empty: {}".format(_lib))
        self._gen_isal_h()
        # Build + run the 17 upstream check programs (ctest-registered set,
        # executed directly since no CMake project() runs here).
        self.output.info("isa-l upstream tests: running 17 ctest-registered "
                         "check programs directly (CMake project() bypassed)")
        _passed = 0
        _failed = 0
        _fail_names = []
        for _name, _sub, _extra_inc in _CHECK_TESTS:
            _tsrc = os.path.join(_src, _sub, _name + ".c")
            if not os.path.isfile(_tsrc):
                raise ConanException(
                    "isa-l: upstream test source missing: {}".format(_tsrc))
            _exe = os.path.join(_test_dir, _name)
            _tinc = _inc + "".join([" -I{}".format(shlex.quote(
                os.path.join(_src, _d))) for _d in _extra_inc])
            self.run("{} {} {} {} {} -o {}".format(
                shlex.quote(_cc), _flags, _tinc, shlex.quote(_tsrc),
                shlex.quote(_lib), shlex.quote(_exe)),
                cwd=_bf, env="conanbuild")
            if not os.path.isfile(_exe) or os.path.getsize(_exe) == 0:
                raise ConanException(
                    "isa-l: empty test binary for {}".format(_name))
            try:
                self.run(_exe, cwd=_test_dir, env="conanbuild")
                _rc = 0
            except Exception:
                _rc = 1
            if _rc == 0:
                _passed += 1
                self.output.info("isa-l check {} PASSED".format(_name))
            else:
                _failed += 1
                _fail_names.append(_name)
                self.output.warning("isa-l check {} FAILED".format(_name))
        _result = {"framework": "check-tests",
                   "command": "run 17 ctest-registered check programs directly",
                   "discovered": len(_CHECK_TESTS),
                   "executed": _passed + _failed,
                   "passed": _passed, "failed": _failed, "skipped": 0}
        if _failed > 0 or _passed + _failed != len(_CHECK_TESTS):
            _result.update({"status": "failed",
                            "reason": "failed: {}".format(_fail_names)})
        else:
            _result.update({"status": "passed"})
        self._emit_upstream_result(_result)
        if _result["status"] != "passed":
            raise ConanException(
                "isa-l upstream tests failed (marker={})".format(_result))

    def _emit_upstream_result(self, result):
        # Dual-channel evidence: output.info plus a stdout-direct print of
        # the same line, then persist to a real file so a later Conan cache
        # hit (build() skipped) can still re-emit from test_package.
        _line = ("HMBS_UPSTREAM_TEST_RESULT="
                 + json.dumps(result, ensure_ascii=False))
        self.output.info(_line)
        try:
            print(_line, flush=True)
        except Exception:
            pass
        try:
            _p = os.path.join(str(self.build_folder), "hmbs_upstream.json")
            with open(_p, "w", encoding="utf-8", newline="\n") as _f:
                _f.write(json.dumps(result, ensure_ascii=False))
        except OSError as _exc:
            self.output.warning(
                "isa-l upstream persist failed: {!r}".format(_exc))

    def package(self):
        self._ensure_tmp_env()
        _libname = "libisal.so" if self.options.shared else "libisal.a"
        copy(self, _libname, src=str(self.build_folder),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", src=os.path.join(str(self.source_folder), "include"),
             dst=os.path.join(self.package_folder, "include", "isa-l"))
        copy(self, "isa-l.h", src=str(self.build_folder),
             dst=os.path.join(self.package_folder, "include"))
        _pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(_pc_dir, exist_ok=True)
        with open(os.path.join(_pc_dir, "libisal.pc"), "w", encoding="utf-8",
                  newline="\n") as _f:
            _f.write("prefix=/\nexec_prefix=${prefix}\n"
                     "libdir=${prefix}/lib\nincludedir=${prefix}/include\n\n"
                     "Name: libisal\nDescription: Intel ISA-L\n"
                     "Version: 2.32.1\nLibs: -L${libdir} -lisal\n"
                     "Cflags: -I${includedir}\n")
        # Persist measured upstream evidence for test_package re-emission.
        try:
            _src = os.path.join(str(self.build_folder), "hmbs_upstream.json")
            if os.path.isfile(_src):
                _res_dir = os.path.join(self.package_folder, "res")
                os.makedirs(_res_dir, exist_ok=True)
                copy(self, "hmbs_upstream.json", src=str(self.build_folder),
                     dst=_res_dir)
                self.output.info("isa-l package: persisted hmbs_upstream.json")
            else:
                self.output.warning(
                    "isa-l package: hmbs_upstream.json not found in build folder")
        except Exception as _exc:
            self.output.warning(
                "isa-l package: persist upstream evidence failed: {!r}".format(_exc))
        # Fail closed: the installed layout must carry the public headers.
        for _hdr in ("isa-l.h", os.path.join("isa-l", "crc.h"),
                     os.path.join("isa-l", "erasure_code.h"),
                     os.path.join("isa-l", "raid.h"),
                     os.path.join("isa-l", "igzip_lib.h"),
                     os.path.join("isa-l", "mem_routines.h")):
            _p = os.path.join(self.package_folder, "include", _hdr)
            if not os.path.isfile(_p):
                raise ConanException(
                    "isa-l package: public header missing: {}".format(_p))

    def package_info(self):
        self.cpp_info.libs = ["isal"]
        self.cpp_info.set_property("pkg_config_name", "libisal")
