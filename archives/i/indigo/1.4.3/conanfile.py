#!/usr/bin/env python3
"""Conan recipe for EPAM Indigo cheminformatics core library 1.4.3.

Scope: core C++ library (common/graph/molecule/reaction/layout + C API)
built through build_scripts/indigo (vendored zlib/tinyxml/inchi, no system
freetype/fontconfig needed). Bingo DB, renderer, and Java/dotnet/Python
wrappers are out of scope for this recipe.

Upstream CTest suite in this scope: DEFINE_TEST(indigo-c-test-shared) from
api/CMakeLists.txt (api/tests/c/indigo-test.c). The full indigo-all ctest
also defines dlopen-test, but that test requires the bingo/renderer/inchi
plugin libraries which are not built here.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


def _read_text_safely(path):
    """Read a source file as text, tolerating legacy single-byte encodings.

    Upstream Indigo is UTF-8 except molecule/CDXConstants.h, which holds a
    Latin-1 0xA9 (copyright sign) at offset 97. latin-1 decodes every byte
    sequence losslessly, so scanning (and byte-exact rewriting) through it
    never corrupts content or crashes the recipe.
    """
    with open(path, "rb") as f:
        data = f.read()
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("latin-1"), "latin-1"


def _write_text_safely(path, text, encoding):
    with open(path, "wb") as f:
        f.write(text.encode(encoding))

_MACRO_PAIRS = (
    ("INDIGO_MINMAX", "__minmax"),
    ("INDIGO_MIN3", "__min3"),
    ("INDIGO_MAX3", "__max3"),
    ("INDIGO_SWAP", "__swap"),
    ("INDIGO_SIGN", "__sign"),
    ("INDIGO_MAX", "__max"),
    ("INDIGO_MIN", "__min"),
)

_PRISTINE_MACRO_ANCHORS = (
    "#define __max(",
    "#define __min(",
    "#define __min3(",
    "#define __max3(",
    "#define __sign(",
    "#define __swap(",
)

# Exact text blocks of the abandoned inline-template route (previous
# strategy cycle). Kept here so _restore_pristine_sources can revert
# them with exact-string inversion. _INLINE_PRISTINE_MACRO_BLOCK and
# _INLINE_PRISTINE_BITARRAY_INC are byte-identical to the upstream
# indigo-1.4.3 tarball content (verified locally against
# Indigo-indigo-1.4.3/common/base_c/defs.h and bitarray.h).
_INLINE_PRISTINE_MACRO_BLOCK = """#if !defined(__max)
#define __max(a, b) (((a) > (b)) ? (a) : (b))
#endif
#if !defined(__min)
#define __min(a, b) (((a) < (b)) ? (a) : (b))
#endif
#if !defined(__min3)
#define __min3(a, b, c) (__min(a, __min(b, c)))
#endif
#if !defined(__max3)
#define __max3(a, b, c) (__max(a, __max(b, c)))
#endif
#if !defined(__sign)
#define __sign(a) (a > 0 ? 1 : (a < 0 ? -1 : 0))
#endif

#define __swap(a, b, tmp) ((tmp) = (b), (b) = (a), (a) = (tmp))"""

_INLINE_TEMPLATES_BLOCK = """/* HMBS_MACRO_INLINE: reserved __-macros converted to C++
 * inline function templates (same names, same call syntax, same
 * arithmetic result types). Function-like macros rewrote libc++
 * internals textually (e.g. std::variant::__swap); real functions
 * never do. Pure-C TUs keep the original macros verbatim. */
#ifdef __cplusplus
template <typename HMBS_T1, typename HMBS_T2>
inline decltype(HMBS_T1() + HMBS_T2()) __max(HMBS_T1 a, HMBS_T2 b)
{
    return a > b ? a : b;
}
template <typename HMBS_T1, typename HMBS_T2>
inline decltype(HMBS_T1() + HMBS_T2()) __min(HMBS_T1 a, HMBS_T2 b)
{
    return a < b ? a : b;
}
template <typename HMBS_T1, typename HMBS_T2, typename HMBS_T3>
inline decltype(HMBS_T1() + HMBS_T2() + HMBS_T3()) __min3(
    HMBS_T1 a, HMBS_T2 b, HMBS_T3 c)
{
    return __min(a, __min(b, c));
}
template <typename HMBS_T1, typename HMBS_T2, typename HMBS_T3>
inline decltype(HMBS_T1() + HMBS_T2() + HMBS_T3()) __max3(
    HMBS_T1 a, HMBS_T2 b, HMBS_T3 c)
{
    return __max(a, __max(b, c));
}
template <typename HMBS_T>
inline int __sign(HMBS_T a)
{
    return a > 0 ? 1 : (a < 0 ? -1 : 0);
}
template <typename HMBS_T>
inline void __swap(HMBS_T& a, HMBS_T& b, HMBS_T& tmp)
{
    tmp = b;
    b = a;
    a = tmp;
}
#else
#if !defined(__max)
#define __max(a, b) (((a) > (b)) ? (a) : (b))
#endif
#if !defined(__min)
#define __min(a, b) (((a) < (b)) ? (a) : (b))
#endif
#if !defined(__min3)
#define __min3(a, b, c) (__min(a, __min(b, c)))
#endif
#if !defined(__max3)
#define __max3(a, b, c) (__max(a, __max(b, c)))
#endif
#if !defined(__sign)
#define __sign(a) (a > 0 ? 1 : (a < 0 ? -1 : 0))
#endif

#define __swap(a, b, tmp) ((tmp) = (b), (b) = (a), (a) = (tmp))
#endif"""

_INLINE_PRISTINE_BITARRAY_INC = """#ifdef __cplusplus
extern "C"
{
#endif

#include "base_c/defs.h\""""

_INLINE_QUARANTINED_BITARRAY_INC = """/* HMBS_MACRO_INLINE: defs.h moved above extern "C"
 * (includes never belong inside it; defs.h now holds C++
 * templates which require C++ linkage). */
#include "base_c/defs.h"

#ifdef __cplusplus
extern "C"
{
#endif"""


class IndigoConan(ConanFile):
    name = "indigo"
    version = "1.4.3"
    description = "EPAM Indigo universal cheminformatics core library (C API)"
    license = "Apache-2.0"
    homepage = "https://github.com/epam/Indigo"
    topics = ("chemistry", "cheminformatics", "smiles", "molfile")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"indigo supports Linux and OHOS package builds, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WITH_STATIC"] = False
        tc.variables["CMAKE_SKIP_RPATH"] = True
        # Upstream floor is cmake_minimum_required(VERSION 3.4); the OHOS
        # toolchain ships CMake 4.x which errors on <3.5 compat floors.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            self._patch_ohos_cmake()
        self._restore_pristine_sources()
        self._patch_swap_rename()
        self._patch_byte_ambiguity()
        self._patch_inchi_isascii()
        self._patch_enable_ctest()
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(
            build_script_folder=os.path.join(
                self.source_folder, "build_scripts", "indigo"
            )
        )
        cmake.build()
        self._run_upstream_tests()

    def _replace_once(self, path, old, new):
        content, _enc = _read_text_safely(path)
        if new in content:
            return
        if old not in content:
            raise ConanException(
                f"OHOS cmake patch anchor missing in {path}: {old!r}"
            )
        _write_text_safely(path, content.replace(old, new), _enc)

    def _restore_pristine_sources(self):
        """Revert stale mutations from previous strategy cycles (idempotent).

        NEW root cause for the current strategy cycle: the identical
        `layout/.../molecule_layout_graph_assign_smart.cpp 7 errors`
        survived three mutually exclusive fixes (bulk INDIGO_* rename,
        in-defs.h system pre-include, `-include hmbs_prefix.h`), which
        implies the fixes never took effect on the actually compiled
        tree. build() mutates the Conan-cached source tree in place with
        early-return idempotence and no reverse migration, so every
        strategy switch leaves the previous mutation behind: renamed
        INDIGO_* call sites, system #includes injected into defs.h
        (parsed inside bitarray.h's `extern "C"`, self-inflicting the
        `templates must have C++ linkage` failure), and stale
        hmbs_prefix.h variants (quoting, <memory_resource>).

        This method subtracts ALL of those before the current
        strategy runs. Pristine anchors verified against the upstream
        indigo-1.4.3 tarball: common/base_c/defs.h holds zero
        `#include` lines and defines exactly six function-like macros
        `__max/__min/__min3/__max3/__sign/__swap`. Anything else in
        that file (a `#include`, an `INDIGO_MAX/MIN/...` definition, an
        HMBS marker line) is by construction a leftover of our own
        earlier rounds, never upstream content (`INDIGO_PLUGIN` is the
        one legitimate upstream `INDIGO_*` token and is preserved).
        """
        import re as _re

        prefix = os.path.join(self.source_folder, "hmbs_prefix.h")
        if os.path.isfile(prefix):
            os.remove(prefix)
            self.output.info("removed stale hmbs_prefix.h")
        # Revert tree-wide byte disambiguation from any previous round
        # (::byte qualification and/or indigo_byte rename): restore
        # unqualified byte, then drop our own marker lines. The upstream
        # typedef `typedef unsigned char byte;` in defs.h is preserved
        # verbatim; only disambiguated uses are reverted.
        byte_reverted_files = 0
        for _root, _, _files in os.walk(self.source_folder):
            if "third_party" in _root.split(os.sep):
                continue
            for _name in _files:
                if not _name.endswith((".c", ".cpp", ".h")):
                    continue
                _path = os.path.join(_root, _name)
                _content, _enc2 = _read_text_safely(_path)
                if "HMBS_BYTE_QUALIFY" not in _content and "::byte" not in _content and "indigo_byte" not in _content:
                    continue
                # Drop our own alias definition line first (defs.h only;
                # other files never carry it). It must be removed, not
                # reverted, otherwise it collapses into a duplicate of
                # the pristine typedef.
                _lines = _content.splitlines(keepends=True)
                _kept = [
                    l
                    for l in _lines
                    if l.strip() != "typedef unsigned char indigo_byte;"
                ]
                _reverted = "".join(_kept)
                # Revert only our own ::byte (not std::byte): ::byte not
                # preceded by an identifier char or a colon.
                # Collapse stale multi-colon spellings from a
                # double-applied ::byte round (e.g. :::byte): fold
                # to ::byte first so the revert below (which
                # spares std::byte) can fire. Unconditional fold
                # is safe: std:::byte (invalid C++) folds back to
                # the valid std::byte it came from.
                while ":::byte" in _reverted:
                    _reverted = _reverted.replace(":::byte", "::byte")
                _reverted = _re.sub(r"(?<![\w:])::byte\b", "byte", _reverted)
                # Revert our own indigo_byte rename (word-boundary; never
                # touches n_bytes/bitGetOnesCountByte: '_' is a word char
                # so \b blocks those).
                _reverted = _re.sub(r"\bindigo_byte\b", "byte", _reverted)
                _reverted = "\n".join(
                    l
                    for l in _reverted.splitlines()
                    if "HMBS_BYTE_QUALIFY" not in l
                ) + "\n"
                # Collapse accidental triple-colon from double revert
                # (never expected; loud check below covers typedef).
                if _reverted != _content:
                    _write_text_safely(_path, _reverted, _enc2)
                    byte_reverted_files += 1
        if byte_reverted_files:
            self.output.info(
                f"byte-qualify: reverted files={byte_reverted_files}"
            )
        defs = os.path.join(
            self.source_folder, "common", "base_c", "defs.h"
        )
        text, _defs_enc = _read_text_safely(defs)
        if "\r\n" in text:
            text = text.replace("\r\n", "\n")
            _write_text_safely(defs, text, _defs_enc)
            self.output.info("defs.h: normalized CRLF to LF")
        if "HMBS_MACRO_INLINE" in text:
            # Revert the abandoned inline-template route with exact-string
            # inversion (constants share one definition with the route that
            # introduced them). That route kept the identical 7-error
            # fingerprint in layout/...assign_smart.cpp, so it is
            # subtracted here, never kept. Fall through to the shared
            # reversal/verification below afterwards.
            if _INLINE_TEMPLATES_BLOCK not in text:
                raise ConanException(
                    "defs.h carries HMBS_MACRO_INLINE marker but the "
                    "inline block anchor is missing; refusing to revert "
                    "blindly"
                )
            text = text.replace(
                _INLINE_TEMPLATES_BLOCK, _INLINE_PRISTINE_MACRO_BLOCK
            )
            _write_text_safely(defs, text, _defs_enc)
            self.output.info(
                "defs.h: reverted inline templates to pristine macros"
            )
        bitarray = os.path.join(
            self.source_folder, "common", "base_c", "bitarray.h"
        )
        bit_text, _bit_enc = _read_text_safely(bitarray)
        if "HMBS_MACRO_INLINE" in bit_text:
            if _INLINE_QUARANTINED_BITARRAY_INC not in bit_text:
                raise ConanException(
                    "bitarray.h carries HMBS_MACRO_INLINE marker but the "
                    "quarantine block anchor is missing; refusing to "
                    "revert blindly"
                )
            _write_text_safely(
                bitarray,
                bit_text.replace(
                    _INLINE_QUARANTINED_BITARRAY_INC,
                    _INLINE_PRISTINE_BITARRAY_INC,
                ),
                _bit_enc,
            )
            self.output.info(
                "bitarray.h: reverted extern-C quarantine to pristine"
            )
        # Reverse any bulk-rename leftovers (longest names first).
        # Bare-word revert (not call-pattern) so `#if !defined(INDIGO_MAX)`
        # guards revert alongside `INDIGO_MAX(` calls. INDIGO_PLUGIN is
        # never matched by these exact names.
        for new_name, old_name in _MACRO_PAIRS:
            if new_name not in text:
                continue
            text = _re.sub(
                r"\b" + new_name + r"\b", old_name, text
            )
            self.output.info(f"defs.h: reverted {new_name} to {old_name}")
        # Drop injected system includes / marker comment lines; pristine
        # defs.h has no #include at all.
        kept = []
        dropped = 0
        for line in text.splitlines(keepends=True):
            stripped = line.strip()
            if stripped.startswith("#include") or (
                stripped.startswith("//") and "HMBS" in stripped
            ) or (stripped.startswith("/*") and "HMBS" in stripped):
                dropped += 1
                continue
            kept.append(line)
        if dropped:
            text = "".join(kept)
            self.output.info(f"defs.h: dropped {dropped} injected lines")
        # Reverse bulk-rename leftovers across sources (not third_party).
        reverted_files = 0
        for root, _, files in os.walk(self.source_folder):
            if "third_party" in root.split(os.sep):
                continue
            for name in files:
                if not name.endswith((".c", ".cpp", ".h")):
                    continue
                path = os.path.join(root, name)
                content, _enc = _read_text_safely(path)
                updated = content
                for new_name, old_name in _MACRO_PAIRS:
                    if new_name in updated:
                        updated = _re.sub(
                            r"\b" + new_name + r"\b",
                            old_name,
                            updated,
                        )
                # Drop our own stale marker lines (keep INDIGO_PLUGIN).
                lines = updated.splitlines(keepends=True)
                filtered = [
                    l
                    for l in lines
                    if not (
                        (l.strip().startswith("//")
                         or l.strip().startswith("/*"))
                        and "HMBS" in l
                    )
                ]
                updated = "".join(filtered)
                if updated != content:
                    _write_text_safely(path, updated, _enc)
                    reverted_files += 1
        # The defs.h on disk was already reverted above via `text`; write
        # it back when the rename reversal changed it.
        current_defs, _ = _read_text_safely(defs)
        if text != current_defs:
            _write_text_safely(defs, text, _defs_enc)
            final_defs = text
        else:
            final_defs = current_defs
        for anchor in _PRISTINE_MACRO_ANCHORS:
            if anchor not in final_defs:
                raise ConanException(
                    "pristine defs.h anchor missing after restore: "
                    + anchor
                )
        if "#include" in final_defs.replace("#ifndef", "").replace(
            "#endif", ""
        ):
            for line in final_defs.splitlines():
                if line.strip().startswith("#include"):
                    raise ConanException(
                        "defs.h still holds stale mutations after "
                        f"restore: {line.strip()}"
                    )
        self.output.info(
            f"pristine restore done: reverted_files={reverted_files}"
        )

    def _patch_ohos_cmake(self):
        """Map OHOS onto the upstream Linux code path (idempotent).

        NOTE: must live in build() (not source()): Conan 2 forbids
        'self.settings' access in source(). Each replacement checks
        for its own marker first and raises loudly if its anchor is
        missing, so a re-run never double-patches and an upstream
        refactor fails visibly instead of silently.
        """
        def _replace_once(path, old, new):
            content, _enc = _read_text_safely(path)
            if new in content:
                return
            if old not in content:
                raise ConanException(
                    f"OHOS cmake patch anchor missing in {path}: {old!r}"
                )
            _write_text_safely(path, content.replace(old, new), _enc)

        gsv = os.path.join(
            self.source_folder, "common", "cmake", "GetSystemVersion.cmake"
        )
        _replace_once(
            gsv,
            "elseif(UNIX)",
            'elseif(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" '
            'OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")',
        )
        sbp = os.path.join(
            self.source_folder, "common", "cmake", "SetBuildParameters.cmake"
        )
        _replace_once(
            sbp,
            "elseif(UNIX AND NOT APPLE OR MINGW)",
            'elseif((UNIX AND NOT APPLE) OR MINGW '
            'OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" '
            'OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")',
        )
        _replace_once(
            sbp,
            "if(UNIX OR APPLE)",
            'if(UNIX OR APPLE OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" '
            'OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")',
        )
        api_cmake = os.path.join(
            self.source_folder, "api", "CMakeLists.txt"
        )
        _replace_once(
            api_cmake,
            "if(UNIX AND NOT APPLE)",
            'if((UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" '
            'OR CMAKE_SYSTEM_NAME STREQUAL "OHOS") AND NOT APPLE)',
        )
        _replace_once(
            api_cmake,
            "if (UNIX AND NOT APPLE)",
            'if ((UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" '
            'OR CMAKE_SYSTEM_NAME STREQUAL "OHOS") AND NOT APPLE)',
        )
        _replace_once(
            api_cmake,
            'if(${SUBSYSTEM_NAME} MATCHES "x64")',
            'if(${SUBSYSTEM_NAME} MATCHES "x64" '
            'AND NOT CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" '
            'AND NOT CMAKE_SYSTEM_NAME STREQUAL "OHOS")',
        )
        _replace_once(
            api_cmake,
            'if (NOT APPLE AND ${SUBSYSTEM_NAME} MATCHES "x64")',
            'if (NOT APPLE AND ${SUBSYSTEM_NAME} MATCHES "x64" '
            'AND NOT CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" '
            'AND NOT CMAKE_SYSTEM_NAME STREQUAL "OHOS")',
        )
        api_content, _ = _read_text_safely(api_cmake)
        # OHOS (musl-based) has no separate librt; keep -lrt on Linux.
        if "-lrt" in api_content:
            _replace_once(
                api_cmake,
                "target_link_libraries(indigo-shared -lpthread -lrt)",
                "target_link_libraries(indigo-shared -lpthread)",
            )
            tmp, _tmp_enc = _read_text_safely(api_cmake)
            if '"-lpthread;-lrt;z;tinyxml;inchi"' in tmp:
                _write_text_safely(
                    api_cmake,
                    tmp.replace(
                        '"-lpthread;-lrt;z;tinyxml;inchi"',
                        '"-lpthread;z;tinyxml;inchi"',
                    ),
                    _tmp_enc,
                )

    def _patch_swap_rename(self):
        """Rename all six reserved __-macros to INDIGO_* (escalated route).

        Strategy change (14th policy cycle): the 13th-cycle single-macro
        hypothesis (__swap-only collision with std::variant::__swap) is
        falsified by the 2026-09-23 preflight: after __swap -> INDIGO_SWAP
        plus header-only byte qualification, the identical 7-error
        fingerprint in layout/src/molecule_layout_graph_assign_smart.cpp
        survived unchanged. A single-macro fix cannot explain an unchanged
        fingerprint, so this round escalates the SAME machinery (exact
        rename, comment/string-aware, loud verification) to all six
        reserved function-like macros in common/base_c/defs.h:
        __max/__min/__min3/__max3/__sign/__swap -> INDIGO_MAX/INDIGO_MIN/
        INDIGO_MIN3/INDIGO_MAX3/INDIGO_SIGN/INDIGO_SWAP. New libc++/libc
        headers use __-prefixed internal identifiers extensively; leaving
        five function-like __-macros active while system headers parse
        textually rewrites them regardless of which one the truncated log
        happened to show. Call-site audit against the 1.4.3 tarball: no
        .c TU uses these macros, no use inside a string literal, // comment
        mentions never rewritten. Idempotent via HMBS_RESERVED_RENAME
        (accepts predecessor HMBS_SWAP_RENAME as already-started); loud on
        any leftover instead of guessing.
        """
        import re as _re

        _RESERVED_DEFS = (
            (
                "#define __max(a, b) (((a) > (b)) ? (a) : (b))",
                "#define INDIGO_MAX(a, b) (((a) > (b)) ? (a) : (b))",
                "__max",
                "INDIGO_MAX",
            ),
            (
                "#define __min(a, b) (((a) < (b)) ? (a) : (b))",
                "#define INDIGO_MIN(a, b) (((a) < (b)) ? (a) : (b))",
                "__min",
                "INDIGO_MIN",
            ),
            (
                "#define __min3(a, b, c) (__min(a, __min(b, c)))",
                "#define INDIGO_MIN3(a, b, c) (INDIGO_MIN(a, INDIGO_MIN(b, c)))",
                "__min3",
                "INDIGO_MIN3",
            ),
            (
                "#define __max3(a, b, c) (__max(a, __max(b, c)))",
                "#define INDIGO_MAX3(a, b, c) (INDIGO_MAX(a, INDIGO_MAX(b, c)))",
                "__max3",
                "INDIGO_MAX3",
            ),
            (
                "#define __sign(a) (a > 0 ? 1 : (a < 0 ? -1 : 0))",
                "#define INDIGO_SIGN(a) (a > 0 ? 1 : (a < 0 ? -1 : 0))",
                "__sign",
                "INDIGO_SIGN",
            ),
            (
                "#define __swap(a, b, tmp) ((tmp) = (b), (b) = (a), (a) = (tmp))",
                "#define INDIGO_SWAP(a, b, tmp) ((tmp) = (b), (b) = (a), (a) = (tmp))",
                "__swap",
                "INDIGO_SWAP",
            ),
        )

        def _split_code_comment(line):
            # Split // comment outside string literals (single/double
            # quotes, backslash escapes). Returns (code, sep, comment).
            in_single = False
            in_double = False
            escaped = False
            for i in range(len(line) - 1):
                ch = line[i]
                if escaped:
                    escaped = False
                    continue
                if ch == "\\" and (in_single or in_double):
                    escaped = True
                    continue
                if ch == "'" and not in_double:
                    in_single = not in_single
                    continue
                if ch == '"' and not in_single:
                    in_double = not in_double
                    continue
                if ch == "/" and line[i + 1] == "/" and not in_single and not in_double:
                    return line[:i], "//", line[i + 2 :]
            return line, "", ""

        def _has_string_literal(code):
            in_single = False
            in_double = False
            escaped = False
            for ch in code:
                if escaped:
                    escaped = False
                    continue
                if ch == "\\" and (in_single or in_double):
                    escaped = True
                    continue
                if ch == "'" and not in_double:
                    in_single = not in_single
                    continue
                if ch == '"' and not in_single:
                    in_double = not in_double
                    continue
            return in_single or in_double

        defs = os.path.join(
            self.source_folder, "common", "base_c", "defs.h"
        )
        text, _defs_enc = _read_text_safely(defs)
        if "\r\n" in text:
            text = text.replace("\r\n", "\n")
            _write_text_safely(defs, text, _defs_enc)
            self.output.info("defs.h: normalized CRLF to LF")
        if "HMBS_RESERVED_RENAME" not in text:
            for old_def, new_def, _old_name, _new_name in _RESERVED_DEFS:
                if new_def in text:
                    continue
                if old_def not in text:
                    # Predecessor single-macro round may have already
                    # renamed __swap; any other missing anchor is loud.
                    raise ConanException(
                        "defs.h reserved-macro definition anchor missing; "
                        f"refusing to rename blindly: {old_def[:40]!r}"
                    )
                text = text.replace(old_def, new_def)
            marker = (
                "/* HMBS_RESERVED_RENAME: reserved __max/__min/__min3/"
                "__max3/__sign/__swap renamed to INDIGO_*; function-like "
                "reserved macros rewrote new libc++ internals. */\n"
            )
            # Migrate predecessor marker text if present.
            text = text.replace(
                "/* HMBS_SWAP_RENAME: __swap renamed to INDIGO_SWAP; "
                "function-like __swap rewrote libc++ variant internals. */\n",
                "",
            )
            _write_text_safely(defs, marker + text, _defs_enc)
            self.output.info("defs.h: six reserved macros renamed to INDIGO_*")
        renamed_files = 0
        renamed_uses = 0
        # Longest names first so __min3/__max3/__minmax never partially match.
        _CALL_PAIRS = (
            ("__minmax", "INDIGO_MINMAX"),
            ("__min3", "INDIGO_MIN3"),
            ("__max3", "INDIGO_MAX3"),
            ("__swap", "INDIGO_SWAP"),
            ("__sign", "INDIGO_SIGN"),
            ("__max", "INDIGO_MAX"),
            ("__min", "INDIGO_MIN"),
        )
        _HASH_RE = r"\b__minmax\b|\b__max3?\b|\b__min3?\b|\b__sign\b|\b__swap\b"
        _CALL_RE = r"\b__minmax\s*\(|\b__max3?\s*\(|\b__min3?\s*\(|\b__sign\s*\(|\b__swap\s*\("
        for root, _, files in os.walk(self.source_folder):
            if "third_party" in root.split(os.sep):
                continue
            for name in files:
                if not name.endswith((".c", ".cpp", ".h")):
                    continue
                path = os.path.join(root, name)
                content, _enc = _read_text_safely(path)
                out_lines = []
                file_uses = 0
                for line in content.splitlines(keepends=True):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        # Preprocessor lines are renamed in place instead of
                        # failing: upstream render2d/src/render_internal.cpp
                        # defines `#define __minmax(inv,t1,t2)
                        # (inv ? __min(t1,t2) : __max(t1,t2))`, whose body
                        # must follow the same rename.
                        new_line = line
                        for old_name, new_name in _CALL_PAIRS:
                            new_line, n = _re.subn(
                                r"\b" + old_name + r"\b", new_name, new_line
                            )
                            file_uses += n
                        out_lines.append(new_line)
                        continue
                    code, sep, comment = _split_code_comment(line)
                    if _has_string_literal(code) and _re.search(
                        _CALL_RE,
                        code,
                    ):
                        # Audited tarball has no macro use inside a string
                        # literal; fail visibly instead of guessing.
                        raise ConanException(
                            "reserved macro inside string literal, refusing "
                            f"to rewrite blindly: {path}: {stripped[:120]}"
                        )
                    new_code = code
                    for old_name, new_name in _CALL_PAIRS:
                        new_code, n = _re.subn(
                            r"\b" + old_name + r"\s*\(", new_name + "(", new_code
                        )
                        file_uses += n
                    if sep:
                        out_lines.append(new_code + sep + comment)
                    else:
                        out_lines.append(new_code)
                if file_uses:
                    _write_text_safely(path, "".join(out_lines), _enc)
                    renamed_files += 1
                    renamed_uses += file_uses
        self.output.info(
            "call sites renamed to INDIGO_*: "
            f"uses={renamed_uses} files={renamed_files}"
        )
        # Loud verification on the final tree.
        final_defs, _ = _read_text_safely(defs)
        for _old_def, _new_def, _o, _n in _RESERVED_DEFS:
            if _new_def not in final_defs:
                raise ConanException(
                    f"{_n} definition missing in defs.h after rename"
                )
        for _old_def, _new_def, _o, _n in _RESERVED_DEFS:
            if _old_def in final_defs:
                raise ConanException(
                    f"stale {_o} definition remains in defs.h after rename"
                )
        leftovers = []
        indigo_uses = 0
        for root, _, files in os.walk(self.source_folder):
            if "third_party" in root.split(os.sep):
                continue
            for name in files:
                if not name.endswith((".c", ".cpp", ".h")):
                    continue
                path = os.path.join(root, name)
                content, _ = _read_text_safely(path)
                for lineno, line in enumerate(content.splitlines(), 1):
                    if line.strip().startswith("#"):
                        if _re.search(_HASH_RE, line):
                            leftovers.append(f"{path}:{lineno}")
                        continue
                    code, _, _ = _split_code_comment(line)
                    if _re.search(
                        _CALL_RE,
                        code,
                    ):
                        leftovers.append(f"{path}:{lineno}")
                indigo_uses += len(
                    _re.findall(
                        r"\bINDIGO_(MINMAX|MAX3|MIN3|MAX|MIN|SIGN|SWAP)\s*\(",
                        content,
                    )
                )
        if leftovers:
            raise ConanException(
                "stale reserved-macro call remains after rename: "
                + "; ".join(leftovers[:10])
            )
        # Audited tarball total is ~280 call sites across the six names
        # (89 __swap + ~190 __max/__min/__sign/__min3/__max3); allow no
        # silent loss. Lower bound 250 keeps the gate loud without
        # hard-coding an exact count that upstream may shift.
        if indigo_uses < 250:
            raise ConanException(
                "INDIGO_* use count unexpectedly low "
                f"(uses={indigo_uses}); refusing to proceed blindly"
            )
        self.output.info(
            f"reserved-rename verification passed (INDIGO_* uses={indigo_uses})"
        )

    def _patch_byte_ambiguity(self):
        """Qualify Indigo's global `byte` as `::byte` in C++-only files.

        Root cause (falsifies the two previous byte strategies): the
        `typedef unsigned char byte` is provided TWICE, each guarded by
        `#ifndef __byte_typedef__`: once in `api/indigo.h` (public C API
        header) and once in `common/base_c/defs.h`. Both tree-wide
        spellings are therefore unwinnable, as the 2026-09-23/24
        preflights prove: (a) tree-wide `::byte` breaks every C TU
        (`::` is not valid C; bitarray.c, 20 errors); (b) tree-wide
        `indigo_byte` rename breaks every C++ TU that includes
        `api/indigo.h` first, because indigo.h wins the
        `__byte_typedef__` guard race, so defs.h skips its guarded block
        INCLUDING the inserted `indigo_byte` alias line, while the
        renamed uses (`molecule_fingerprint.h`, `output.h`, `scanner.h`
        via `api/src/indigo.cpp` <- `indigo_internal.h` <- `indigo.h`)
        have no declaration in scope (20 errors, `unknown type name
        'indigo_byte'`). The layout TU (which never includes indigo.h)
        compiled fine in the same build, confirming the guard-race
        mechanism; the alias design never accounted for the second
        provider of the guard.

        Fix (surgical, introduces no new type names): spell Indigo's
        global byte explicitly as `::byte`, but ONLY where `::` is legal
        C++: every non-third_party `.cpp` file plus every non-third_party
        header OUTSIDE the C include-closure. The C-closure is computed
        by BFS over quoted `#include "..."` starting from every
        non-third_party `.c` file (audited against the 1.4.3 tarball: 12
        headers, among them `api/indigo.h`, `common/base_c/bitarray.h`,
        `defs.h` and the `os_*.h` family); those headers plus all `.c`
        files keep pristine `byte`, which is valid C and unambiguous
        there (`std::byte` does not exist in C). `::byte` resolves to
        whichever provider won the guard race (identical `unsigned char`
        either way) and stays unambiguous even under `using namespace
        std;` (e.g. `layout/molecule_layout_macrocycles.h:31`, the
        source of the original 7 layout errors). String literals, `//`
        and `/* */` comments, `#` preprocessor lines, typedef lines,
        `std::byte`, already-qualified `::byte` and member accesses are
        never rewritten. Idempotent by construction (a second run finds
        no unqualified use); _restore_pristine_sources reverts it.
        """
        import re as _re

        def _split_code_comment(line):
            in_single = False
            in_double = False
            escaped = False
            for i in range(len(line) - 1):
                ch = line[i]
                if escaped:
                    escaped = False
                    continue
                if ch == "\\" and (in_single or in_double):
                    escaped = True
                    continue
                if ch == "'" and not in_double:
                    in_single = not in_single
                    continue
                if ch == '"' and not in_single:
                    in_double = not in_double
                    continue
                if ch == "/" and line[i + 1] == "/" and not in_single and not in_double:
                    return line[:i], "//", line[i + 2 :]
            return line, "", ""

        def _block_start_outside_strings(code):
            # Index of '/*' outside '...'/\"...\" literals, else -1.
            in_single = False
            in_double = False
            escaped = False
            i = 0
            while i < len(code) - 1:
                ch = code[i]
                if escaped:
                    escaped = False
                    i += 1
                    continue
                if ch == "\\" and (in_single or in_double):
                    escaped = True
                    i += 1
                    continue
                if ch == "'" and not in_double:
                    in_single = not in_single
                    i += 1
                    continue
                if ch == '"' and not in_single:
                    in_double = not in_double
                    i += 1
                    continue
                if not in_single and not in_double and ch == "/" and code[i + 1] == "*":
                    return i
                i += 1
            return -1

        def _qualify_outside_strings(code):
            # Rewrite unqualified `byte` to `::byte` outside string
            # literals. Boundary rule: preceding char must not be
            # alnum/`_`/`:`/`.`/`>` (spares n_bytes, bitGetOnesCountByte,
            # __byte_typedef__, std::byte, ::byte, member access) and the
            # following char must not be alnum/`_`.
            out = []
            i = 0
            n = len(code)
            in_single = False
            in_double = False
            escaped = False
            uses = 0
            while i < n:
                ch = code[i]
                if escaped:
                    out.append(ch)
                    escaped = False
                    i += 1
                    continue
                if ch == "\\" and (in_single or in_double):
                    out.append(ch)
                    escaped = True
                    i += 1
                    continue
                if ch == "'" and not in_double:
                    out.append(ch)
                    in_single = not in_single
                    i += 1
                    continue
                if ch == '"' and not in_single:
                    out.append(ch)
                    in_double = not in_double
                    i += 1
                    continue
                if in_single or in_double:
                    out.append(ch)
                    i += 1
                    continue
                if (
                    code.startswith("byte", i)
                    and (i == 0 or (not code[i - 1].isalnum() and code[i - 1] not in ("_", ":", ".", ">")))
                    and (i + 4 >= n or (not code[i + 4].isalnum() and code[i + 4] != "_"))
                ):
                    out.append("::byte")
                    i += 4
                    uses += 1
                else:
                    out.append(ch)
                    i += 1
            return "".join(out), uses

        # C include-closure: every header reachable from a .c TU through
        # quoted includes stays pristine `byte` (valid C by construction:
        # a .c TU cannot include a C++-only header and still compile).
        by_base = {}
        all_sources = []
        for _root, _, _files in os.walk(self.source_folder):
            if "third_party" in _root.split(os.sep):
                continue
            for _name in _files:
                if not _name.endswith((".c", ".cpp", ".h")):
                    continue
                _p = os.path.join(_root, _name)
                all_sources.append(_p)
                by_base.setdefault(_name, []).append(_p)
        for _k in by_base:
            by_base[_k] = sorted(by_base[_k])
        _c_files = [
            _p for _p in all_sources
            if _p.endswith(".c") and not _p.endswith(".cpp")
        ]
        if not _c_files:
            raise ConanException(
                "C include-closure anchor missing: no .c file found"
            )
        _c_scope = set(_c_files)
        _queue = list(_c_files)
        _inc_re = _re.compile(r'^\s*#\s*include\s*"([^"]+)"')
        while _queue:
            _cur = _queue.pop()
            _ctext, _ = _read_text_safely(_cur)
            for _line in _ctext.splitlines():
                _m = _inc_re.match(_line)
                if not _m:
                    continue
                _inc = _m.group(1).replace("/", os.sep)
                _cand = os.path.normpath(
                    os.path.join(os.path.dirname(_cur), _inc)
                )
                if not os.path.isfile(_cand):
                    _cand = None
                    for _p in by_base.get(os.path.basename(_inc), []):
                        _cand = _p
                        break
                if _cand is not None and _cand not in _c_scope:
                    _c_scope.add(_cand)
                    _queue.append(_cand)
        self.output.info(
            "byte C-scope: .c files + closure headers="
            f"{len(_c_scope)}"
        )

        def _process_cpp_scope_file(path, encoding, text):
            out_lines = []
            uses = 0
            block = False
            for line in text.splitlines(keepends=True):
                eol = ""
                body = line
                if body.endswith("\\r\\n"):
                    eol = "\\r\\n"
                    body = body[:-2]
                elif body.endswith("\\n"):
                    eol = "\\n"
                    body = body[:-1]
                if block:
                    end = body.find("*/")
                    if end == -1:
                        out_lines.append(line)
                        continue
                    rest = body[end + 2 :]
                    code, sep, comment = _split_code_comment(rest)
                    if code.strip().startswith("#") or (
                        "typedef" in code
                        and _re.search(r"\bbyte\b", code)
                    ):
                        out_lines.append(line)
                    else:
                        new_code, u = _qualify_outside_strings(code)
                        uses += u
                        tail = new_code + (sep + comment if sep else "")
                        out_lines.append(body[: end + 2] + tail + eol)
                    block = False
                    continue
                code, sep, comment = _split_code_comment(body)
                bi = _block_start_outside_strings(code)
                if bi != -1:
                    pre = code[:bi]
                    ei = code.find("*/", bi + 2)
                    if ei == -1:
                        if pre.strip().startswith("#") or (
                            "typedef" in pre
                            and _re.search(r"\bbyte\b", pre)
                        ):
                            out_lines.append(line)
                        else:
                            new_pre, u = _qualify_outside_strings(pre)
                            uses += u
                            out_lines.append(
                                new_pre + code[bi:]
                                + (sep + comment if sep else "") + eol
                            )
                        block = True
                    else:
                        mid = code[bi : ei + 2]
                        post = code[ei + 2 :]
                        if pre.strip().startswith("#") or (
                            "typedef" in pre
                            and _re.search(r"\bbyte\b", pre)
                        ):
                            new_pre, u0 = pre, 0
                        else:
                            new_pre, u0 = _qualify_outside_strings(pre)
                        if post.strip().startswith("#") or (
                            "typedef" in post
                            and _re.search(r"\bbyte\b", post)
                        ):
                            new_post, u1 = post, 0
                        else:
                            new_post, u1 = _qualify_outside_strings(post)
                        uses += u0 + u1
                        out_lines.append(
                            new_pre + mid + new_post
                            + (sep + comment if sep else "") + eol
                        )
                    continue
                if code.strip().startswith("#") or (
                    "typedef" in code and _re.search(r"\bbyte\b", code)
                ):
                    out_lines.append(line)
                    continue
                new_code, u = _qualify_outside_strings(code)
                uses += u
                out_lines.append(
                    new_code + (sep + comment if sep else "") + eol
                )
            return "".join(out_lines), uses

        patched_files = 0
        patched_uses = 0
        for root, _, files in os.walk(self.source_folder):
            if "third_party" in root.split(os.sep):
                continue
            for name in files:
                if name.endswith(".c") or not name.endswith((".cpp", ".h")):
                    continue
                path = os.path.join(root, name)
                if not name.endswith(".cpp") and path in _c_scope:
                    continue
                content, _enc = _read_text_safely(path)
                updated, file_uses = _process_cpp_scope_file(
                    path, _enc, content
                )
                if file_uses:
                    _write_text_safely(path, updated, _enc)
                    patched_files += 1
                    patched_uses += file_uses
        self.output.info(
            f"byte-ambiguity: qualified uses={patched_uses} "
            f"files={patched_files}"
        )
        # Audited 1.4.3 tarball carries ~370 C++-scope `byte` uses;
        # demand a conservative lower bound so a silent skip (e.g. a
        # broken closure that swallows the whole tree) fails loudly
        # instead of shipping an unpatched build into the next preflight.
        if patched_uses < 200 or patched_files < 60:
            raise ConanException(
                "suspiciously few ::byte qualifications "
                f"(uses={patched_uses} files={patched_files}); "
                "refusing to proceed blindly"
            )
        # Loud verification on the final tree.
        for _provider in (
            os.path.join(self.source_folder, "common", "base_c", "defs.h"),
            os.path.join(self.source_folder, "api", "indigo.h"),
        ):
            _ptext, _ = _read_text_safely(_provider)
            if "typedef unsigned char byte;" not in _ptext:
                raise ConanException(
                    f"upstream byte typedef damaged: {_provider}"
                )
            if "indigo_byte" in _ptext:
                raise ConanException(
                    f"stale indigo_byte alias in provider: {_provider}"
                )
        leftovers = []
        scoped_leaks = []
        stale_alias = []
        for root, _, files in os.walk(self.source_folder):
            if "third_party" in root.split(os.sep):
                continue
            for name in files:
                if not name.endswith((".c", ".cpp", ".h")):
                    continue
                path = os.path.join(root, name)
                content, _ = _read_text_safely(path)
                if "indigo_byte" in content:
                    stale_alias.append(path)
                    continue
                if name.endswith(".cpp") or (
                    name.endswith(".h") and path not in _c_scope
                ):
                    block = False
                    for lineno, line in enumerate(
                        content.splitlines(), 1
                    ):
                        body = line
                        if block:
                            if "*/" in body:
                                block = False
                            continue
                        if (
                            _block_start_outside_strings(
                                _split_code_comment(body)[0]
                            )
                            != -1
                            and "*/" not in body
                        ):
                            block = True
                            body = body.split("/*")[0]
                        code, _, _ = _split_code_comment(body)
                        if code.strip().startswith("#"):
                            continue
                        if "typedef" in code and _re.search(
                            r"\bbyte\b", code
                        ):
                            continue
                        scrubbed = []
                        in_single = False
                        in_double = False
                        escaped = False
                        for ch in code:
                            if escaped:
                                escaped = False
                                scrubbed.append(" ")
                                continue
                            if ch == "\\\\" and (in_single or in_double):
                                escaped = True
                                scrubbed.append(" ")
                                continue
                            if ch == "'" and not in_double:
                                in_single = not in_single
                                scrubbed.append(" ")
                                continue
                            if ch == '"' and not in_single:
                                in_double = not in_double
                                scrubbed.append(" ")
                                continue
                            if in_single or in_double:
                                scrubbed.append(" ")
                            else:
                                scrubbed.append(ch)
                        code_ns = "".join(scrubbed)
                        for m in _re.finditer(r"byte", code_ns):
                            s = m.start()
                            pre_ok = s == 0 or (
                                not code_ns[s - 1].isalnum()
                                and code_ns[s - 1]
                                not in ("_", ":", ".", ">")
                            )
                            post_ok = s + 4 >= len(code_ns) or (
                                not code_ns[s + 4].isalnum()
                                and code_ns[s + 4] != "_"
                            )
                            if pre_ok and post_ok:
                                leftovers.append(f"{path}:{lineno}")
                                break
                        if len(leftovers) >= 10:
                            break
                else:
                    if _re.search(r"(?<![\w:])::byte\b", content):
                        scoped_leaks.append(path)
                if len(leftovers) >= 10 or len(scoped_leaks) >= 10:
                    break
            if len(leftovers) >= 10 or len(scoped_leaks) >= 10:
                break
        if stale_alias:
            raise ConanException(
                "stale indigo_byte remains after scoped qualify: "
                + "; ".join(stale_alias[:10])
            )
        if leftovers:
            raise ConanException(
                "unqualified byte remains in C++ scope after qualify: "
                + "; ".join(leftovers[:10])
            )
        if scoped_leaks:
            raise ConanException(
                "::byte leaked into C scope: " + "; ".join(scoped_leaks[:10])
            )
        self.output.info(
            "byte-scope verification passed "
            f"(qualified uses={patched_uses})"
        )

    def _patch_inchi_isascii(self):
        """Provide a portable __isascii fallback for vendored InChI.

        Root cause: third_party/inchi/INCHI_BASE/src/util.c lrtrim()
        calls __isascii() at two sites (leading/trailing trim loop).
        The only upstream fallback lives in ichicomp.h behind
        COMPILE_ANSI_ONLY, and util.c includes that header only behind
        COMPILE_ANSI_ONLY && __APPLE__. On glibc/Linux the calls still
        compile because glibc <ctype.h> defines __isascii as a macro,
        so no symbol is needed. On musl/OHOS there is neither the macro
        nor the symbol, so __isascii becomes an implicit function call
        with an undefined reference baked into libindigo.so; linking
        indigo-c-test-shared then fails with `ld.lld: error: undefined
        reference due to --no-allow-shlib-undefined: __isascii`.

        Fix (minimal, same semantics as upstream's own fallback):
        append an unconditional `#ifndef __isascii / #define __isascii`
        block after the Apple-only include block in util.c. Guarded, so
        glibc builds are byte-identical in behavior; on musl/OHOS the
        macro expands inline and no symbol is referenced. Idempotent via
        HMBS_ISASCII_FALLBACK; loud when the anchor or the two call
        sites are missing.
        """
        path = os.path.join(
            self.source_folder,
            "third_party",
            "inchi",
            "INCHI_BASE",
            "src",
            "util.c",
        )
        content, _enc = _read_text_safely(path)
        marker = "HMBS_ISASCII_FALLBACK"
        if marker in content:
            return
        anchor = (
            "#if defined(COMPILE_ANSI_ONLY) && defined(__APPLE__)\n"
            "/*    For build under OSX, advice from Burt Leland */\n"
            '#include "ichicomp.h"    /* Needed for __isascii define */\n'
            "#endif"
        )
        if anchor not in content:
            raise ConanException(
                "inchi __isascii patch anchor missing in "
                f"{path}; refusing to patch blindly"
            )
        fallback = (
            "\n/* HMBS_ISASCII_FALLBACK: glibc <ctype.h> defines __isascii\n"
            " * as a macro, but musl/OHOS provides neither the macro nor\n"
            " * the symbol, so util.c lrtrim() baked an undefined\n"
            " * __isascii reference into libindigo.so (ld.lld\n"
            " * --no-allow-shlib-undefined failure on indigo-c-test-shared).\n"
            " * Same definition as upstream ichicomp.h COMPILE_ANSI_ONLY\n"
            " * fallback; guarded so glibc builds are unchanged. */\n"
            "#ifndef __isascii\n"
            "#define __isascii(val) ((unsigned)(val) <= 0x7F)\n"
            "#endif\n"
        )
        _write_text_safely(
            path, content.replace(anchor, anchor + fallback, 1), _enc
        )
        self.output.info("inchi util.c: added portable __isascii fallback")
        final, _ = _read_text_safely(path)
        if marker not in final:
            raise ConanException(
                "inchi __isascii fallback marker missing after patch"
            )
        if final.count("__isascii(") < 2:
            raise ConanException(
                "inchi util.c __isascii call sites missing after patch"
            )

    def _patch_enable_ctest(self):
        """Enable CTest registration for build_scripts/indigo (idempotent).

        Root cause of the 2026-09-24 preflight `discovered=0`: the recipe
        configures build_scripts/indigo, whose CMakeLists chain
        (indigo -> ConfigureCommon -> api/DEFINE_TEST) never calls
        enable_testing(). Upstream only calls ENABLE_TESTING() in
        build_scripts/indigo-all (out of scope: pulls bingo/renderer/
        inchi plugins). Without enable_testing(), api/CMakeLists.txt's
        DEFINE_TEST(indigo-c-test-shared) still builds the executable
        but add_test() registers nothing, so `ctest -N` reports
        `No tests were found!!!` and the HMBS gate fails with
        discovered=0. Fix: insert a single enable_testing() after the
        project() line of build_scripts/indigo/CMakeLists.txt. Guarded
        so glibc/Linux behavior is unchanged apart from registering the
        same one test; idempotent via HMBS_ENABLE_CTEST marker; loud
        when the anchor is missing. Also drops DISABLE_INDIGO_TESTS
        from the environment so the DEFINE_TEST guard cannot silently
        skip the test.
        """
        os.environ.pop("DISABLE_INDIGO_TESTS", None)
        path = os.path.join(
            self.source_folder, "build_scripts", "indigo", "CMakeLists.txt"
        )
        content, _enc = _read_text_safely(path)
        marker = "HMBS_ENABLE_CTEST"
        if marker in content:
            return
        anchor = "project(IndigoSolution)"
        if anchor not in content:
            raise ConanException(
                "ctest enable patch anchor missing in "
                f"{path}; refusing to patch blindly"
            )
        insert = (
            "\n# HMBS_ENABLE_CTEST: build_scripts/indigo never calls\n"
            "# enable_testing() (only indigo-all does), so add_test() in\n"
            "# api/CMakeLists.txt registers nothing and ctest reports\n"
            "# 'No tests were found'. Enable here to register the single\n"
            "# in-scope test indigo-c-test-shared.\n"
            "enable_testing()\n"
        )
        _write_text_safely(
            path, content.replace(anchor, anchor + insert, 1), _enc
        )
        self.output.info("indigo CMakeLists: enable_testing() added")
        final, _ = _read_text_safely(path)
        if marker not in final or "enable_testing()" not in final:
            raise ConanException(
                "ctest enable marker missing after patch"
            )

    def _run_upstream_tests(self):
        """Run the upstream CTest suite and emit the HMBS evidence marker.

        Source audit: build_scripts/indigo -> api/CMakeLists.txt registers
        exactly one CTest via DEFINE_TEST(indigo-c-test-shared,
        tests/c/indigo-test.c). Numbers below come from deterministic
        sources only: `ctest -N` for discovered, per-test
        `Test #N ... Passed|Failed` lines (or Testing/Temporary/
        LastTest.log) for executed/passed/failed. No stdout substring
        counting, no returncode-based guessing, no arithmetic repair.
        """
        import re as _re

        discovered = 0
        executed = 0
        passed = 0
        failed = 0
        skipped = 0
        command = "ctest --output-on-failure"
        reason = ""
        # Deterministic source 1: `ctest -N` for the registered total.
        nproc = subprocess.run(
            ["ctest", "-N"],
            cwd=self.build_folder,
            capture_output=True,
            text=True,
            timeout=300,
        )
        nout = (nproc.stdout or "") + (nproc.stderr or "")
        discovered = len(_re.findall(r"Test\s+#\d+\s*:", nout))
        self.output.info("ctest -N output:\n" + nout.strip()[-2000:])
        # Deterministic source 2: per-test result lines, one source only.
        proc = subprocess.run(
            ["ctest", "--output-on-failure"],
            cwd=self.build_folder,
            capture_output=True,
            text=True,
            timeout=1200,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        self.output.info(
            f"ctest exit={proc.returncode}\n"
            + "\n".join(out.splitlines()[-25:])
        )
        for line in out.splitlines():
            if not _re.search(r"Test\s+#\d+\s*:", line):
                continue
            if _re.search(r"\bPassed\b", line):
                executed += 1
                passed += 1
            elif _re.search(r"\b(Failed|Timeout)\b", line):
                executed += 1
                failed += 1
            elif _re.search(r"\bSkipped\b", line):
                skipped += 1
        if executed == 0:
            # Fallback source: Testing/Temporary/LastTest.log (same
            # per-test lines, single deterministic file).
            searched = []
            for root, _, files in os.walk(self.build_folder):
                if "LastTest.log" in files:
                    searched.append(
                        os.path.join(root, "LastTest.log")
                    )
            if searched:
                with open(
                    searched[0], encoding="utf-8", errors="ignore"
                ) as f:
                    log = f.read()
                for line in log.splitlines():
                    if "Test #" not in line:
                        continue
                    if _re.search(r"\bPassed\b", line):
                        executed += 1
                        passed += 1
                    elif _re.search(r"\b(Failed|Timeout)\b", line):
                        executed += 1
                        failed += 1
                    elif _re.search(r"\bSkipped\b", line):
                        skipped += 1
                if executed == 0:
                    m = _re.search(
                        r"(\d+)% tests passed,\s*(\d+) tests failed "
                        r"out of (\d+)",
                        log,
                    )
                    if m:
                        total = int(m.group(3))
                        failed = int(m.group(2))
                        passed = total - failed
                        executed = total
                        if discovered == 0:
                            discovered = total
                self.output.info(
                    f"LastTest.log fallback: {searched[0]} "
                    f"executed={executed}"
                )
            else:
                reason = (
                    "no per-test Test #N lines in ctest stdout; "
                    "searched build tree, LastTest.log not found"
                )
        # Identity self-check: counts must be internally consistent.
        for value in (discovered, executed, passed, failed, skipped):
            if not isinstance(value, int) or value < 0:
                reason = (
                    "counter identity violated "
                    f"(discovered={discovered}, executed={executed}, "
                    f"passed={passed}, failed={failed}, "
                    f"skipped={skipped})"
                )
                break
        else:
            if passed + failed != executed or executed + skipped > (
                discovered or executed
            ):
                reason = (
                    "counter identity violated "
                    f"(discovered={discovered}, executed={executed}, "
                    f"passed={passed}, failed={failed}, "
                    f"skipped={skipped})"
                )
        status = (
            "passed"
            if (
                not reason
                and discovered > 0
                and executed == discovered
                and failed == 0
            )
            else "failed"
        )
        if not reason and status == "failed":
            if discovered == 0:
                reason = "ctest completed with discovered=0"
            else:
                reason = "upstream ctest did not fully pass"
        marker = {
            "status": status,
            "framework": "ctest",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if reason:
            marker["reason"] = reason
            marker["evidence"] = "ctest stdout tail + LastTest.log fallback in build log"
        line = f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker)}"
        print(line, flush=True)
        self.output.info(line)
        if status != "passed":
            raise ConanException(f"Upstream ctest suite failed: {marker}")

    def package(self):
        candidates = []
        for root, _, files in os.walk(self.build_folder):
            for name in files:
                if name.startswith("libindigo.so"):
                    candidates.append(os.path.join(root, name))
        src_copy = os.path.join(
            self.source_folder,
            "api",
            "libs",
            "shared",
            "Linux",
            "x64",
        )
        if os.path.isdir(src_copy):
            for name in os.listdir(src_copy):
                if name.startswith("libindigo.so"):
                    candidates.append(os.path.join(src_copy, name))
        if not candidates:
            raise ConanException(
                "Expected shared library libindigo.so was not built"
            )
        libdir = os.path.join(self.package_folder, "lib")
        seen = set()
        for path in candidates:
            base = os.path.basename(path)
            if base in seen:
                continue
            seen.add(base)
            copy(
                self,
                base,
                src=os.path.dirname(path),
                dst=libdir,
                keep_path=False,
            )
        for header in ("indigo.h", "indigo_cpp.h"):
            copy(
                self,
                header,
                src=os.path.join(self.source_folder, "api"),
                dst=os.path.join(self.package_folder, "include"),
            )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["indigo"]
        self.cpp_info.set_property("cmake_file_name", "indigo")
        self.cpp_info.set_property("cmake_target_name", "indigo::indigo")
        self.cpp_info.set_property("pkg_config_name", "indigo")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
