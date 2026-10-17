#!/usr/bin/env python3
"""Apply additive HarmonyOS compatibility transforms to a GCC source tree."""

import shutil
import sys
from pathlib import Path


def inject_ohos_triplet(script_path):
    path = Path(script_path)
    content = path.read_text(encoding="utf-8", errors="surrogateescape")
    marker = "# HarmonyOS triplet compatibility (Conan recipe)"
    if marker in content:
        return
    newline = content.find("\n")
    if newline < 0:
        return
    snippet = """
{marker}
case "$1" in
  aarch64-linux-ohos | aarch64-unknown-linux-ohos | none-unknown-linux-ohos)
    echo aarch64-unknown-linux-ohos
    exit 0
    ;;
esac
""".format(marker=marker)
    path.write_text(
        content[: newline + 1] + snippet + content[newline + 1 :],
        encoding="utf-8",
        errors="surrogateescape",
    )


def prepare(source, ohos_header):
    for filename in ("config.sub", "configfsf.sub"):
        for script in source.rglob(filename):
            inject_ohos_triplet(script)

    for configure in source.rglob("configure"):
        content = configure.read_text(
            encoding="utf-8", errors="surrogateescape"
        )
        updated = content.replace("umask 077", "umask 022")
        if updated != content:
            configure.write_text(
                updated, encoding="utf-8", errors="surrogateescape"
            )

    config_gcc = source / "gcc" / "config.gcc"
    config_content = config_gcc.read_text(encoding="utf-8")
    replacements = (
        (
            "    *-*-*musl*)\n",
            "    *-*-*musl* | *-*-*ohos*)\n",
        ),
        (
            '\ttmake_file="${tmake_file} aarch64/t-aarch64 aarch64/t-aarch64-linux"\n'
            '\ttm_defines="${tm_defines}  TARGET_DEFAULT_ASYNC_UNWIND_TABLES=1"\n',
            '\ttmake_file="${tmake_file} aarch64/t-aarch64 aarch64/t-aarch64-linux"\n'
            '\tcase $target in\n'
            '\t*-*-linux-ohos*) tm_file="${tm_file} ohos.h" ;;\n'
            '\tesac\n'
            '\ttm_defines="${tm_defines}  TARGET_DEFAULT_ASYNC_UNWIND_TABLES=1"\n',
        ),
        (
            "*-linux-musl*)\n\ttmake_file=\"${tmake_file} t-musl\"\n",
            "*-linux-musl* | *-linux-ohos*)\n\ttmake_file=\"${tmake_file} t-musl\"\n",
        ),
        (
            "*-*-linux*android*|*-*-linux*uclibc*|*-*-linux*musl*)\n",
            "*-*-linux*android*|*-*-linux*uclibc*|*-*-linux*musl*|*-*-linux*ohos*)\n",
        ),
    )
    for old, new in replacements:
        if old not in config_content:
            raise RuntimeError(
                "GCC 16.1.0 OHOS source transform no longer matches config.gcc"
            )
        config_content = config_content.replace(old, new, 1)
    config_gcc.write_text(config_content, encoding="utf-8")

    shutil.copy2(ohos_header, source / "gcc" / "config" / "ohos.h")

    # libgccjit-specific fixes for the HarmonyOS C++ runtime (libc++):
    #
    # 1) jit-target.h used std::_Hash_bytes, a libstdc++-private hash
    #    function that libc++ does not provide.  Replace it with a
    #    portable FNV-1a 64-bit hash with identical bucket behaviour.
    jit_target = source / "gcc" / "jit" / "jit-target.h"
    jit_content = jit_target.read_text(encoding="utf-8")
    hash_old = (
        "static size_t hash_cstr (const char *s)\n"
        "{\n"
        "  const size_t seed = 0;\n"
        "  return std::_Hash_bytes (s, std::strlen (s), seed);\n"
        "}"
    )
    hash_new = (
        "static size_t hash_cstr (const char *s)\n"
        "{\n"
        "  /* FNV-1a 64-bit: std::_Hash_bytes is libstdc++-private and\n"
        "     is not provided by the HarmonyOS libc++ runtime.  */\n"
        "  size_t h = 14695981039346656037ULL;\n"
        "  for (const unsigned char *p = (const unsigned char *) s; *p; ++p)\n"
        "    {\n"
        "      h ^= *p;\n"
        "      h *= 1099511628211ULL;\n"
        "    }\n"
        "  return h;\n"
        "}"
    )
    if hash_old not in jit_content:
        raise RuntimeError(
            "GCC 16.1.0 jit-target.h hash_cstr pattern no longer matches"
        )
    jit_target.write_text(
        jit_content.replace(hash_old, hash_new, 1), encoding="utf-8"
    )

    # 2) GCC's system.h maps abort() to fancy_abort(); libc++ headers
    #    (e.g. <functional> with exceptions disabled) call std::abort()
    #    directly, so the macro rewrite produced std::fancy_abort() which
    #    does not exist.  Make fancy_abort visible in namespace std.
    system_h = source / "gcc" / "system.h"
    system_content = system_h.read_text(encoding="utf-8")
    sys_old = (
        "extern void fancy_abort (const char *, int, const char *)\n"
        "\t\t\t\t\t ATTRIBUTE_NORETURN ATTRIBUTE_COLD;\n"
        "#define abort() fancy_abort (__FILE__, __LINE__, __FUNCTION__)"
    )
    sys_new = (
        "extern void fancy_abort (const char *, int, const char *)\n"
        "\t\t\t\t\t ATTRIBUTE_NORETURN ATTRIBUTE_COLD;\n"
        "#define abort() fancy_abort (__FILE__, __LINE__, __FUNCTION__)\n"
        "\n"
        "/* HarmonyOS ships libc++ rather than libstdc++; libc++ headers\n"
        "   call std::abort () directly (for example in <functional> when\n"
        "   exceptions are disabled), which the abort() macro above would\n"
        "   rewrite into std::fancy_abort ().  Make fancy_abort visible in\n"
        "   namespace std so that rewrite compiles.  */\n"
        "#ifdef __cplusplus\n"
        "namespace std { using ::fancy_abort; }\n"
        "#endif"
    )
    if sys_old not in system_content:
        raise RuntimeError(
            "GCC 16.1.0 system.h fancy_abort pattern no longer matches"
        )
    system_h.write_text(
        system_content.replace(sys_old, sys_new, 1), encoding="utf-8"
    )

    # 3) Make array_slice constructors constexpr so the global targetm
    #    object (struct gcc_target targetm in config/aarch64/aarch64.cc)
    #    can be statically initialized again.
    #
    #    gcc_target contains an array_slice member (attribute_table), whose
    #    ctors are not constexpr; with clang this forces targetm into .bss
    #    with dynamic initialization through .init_array.  Other translation
    #    units run their own dynamic init earlier in .init_array (for example
    #    jit/jit-builtins.cc builds builtin_data[], whose DEF_C99_BUILTIN
    #    entries evaluate targetm.libc_has_function() at init time).  At that
    #    point targetm is still all-zero, so the hook pointer is NULL and
    #    calling it SIGSEGVs.  With constexpr ctors clang emits targetm as
    #    plain initialized data, ready before any dynamic initializer runs.
    vec_h = source / "gcc" / "vec.h"
    vec_content = vec_h.read_text(encoding="utf-8")
    vec_old = (
        "  array_slice () : m_base (nullptr), m_size (0) {}\n"
        "\n"
        "  template<typename OtherT>\n"
        "  array_slice (array_slice<OtherT> other)\n"
        "    : m_base (other.m_base), m_size (other.m_size) {}\n"
        "\n"
        "  array_slice (iterator base, unsigned int size)\n"
        "    : m_base (base), m_size (size) {}\n"
        "\n"
        "  template<size_t N>\n"
        "  array_slice (T (&array)[N]) : m_base (array), m_size (N) {}\n"
        "\n"
        "  template<typename OtherT>\n"
        "  array_slice (const vec<OtherT> &v)\n"
        "    : m_base (v.address ()), m_size (v.length ()) {}\n"
        "\n"
        "  template<typename OtherT>\n"
        "  array_slice (vec<OtherT> &v)\n"
        "    : m_base (v.address ()), m_size (v.length ()) {}\n"
        "\n"
        "  template<typename OtherT, typename A>\n"
        "  array_slice (const vec<OtherT, A, vl_embed> *v)\n"
        "    : m_base (v ? v->address () : nullptr), m_size (v ? v->length () : 0) {}\n"
        "\n"
        "  template<typename OtherT, typename A>\n"
        "  array_slice (vec<OtherT, A, vl_embed> *v)\n"
        "    : m_base (v ? v->address () : nullptr), m_size (v ? v->length () : 0) {}"
    )
    vec_new = (
        "  constexpr array_slice () : m_base (nullptr), m_size (0) {}\n"
        "\n"
        "  template<typename OtherT>\n"
        "  constexpr array_slice (array_slice<OtherT> other)\n"
        "    : m_base (other.m_base), m_size (other.m_size) {}\n"
        "\n"
        "  constexpr array_slice (iterator base, unsigned int size)\n"
        "    : m_base (base), m_size (size) {}\n"
        "\n"
        "  template<size_t N>\n"
        "  constexpr array_slice (T (&array)[N]) : m_base (array), m_size (N) {}\n"
        "\n"
        "  template<typename OtherT>\n"
        "  constexpr array_slice (const vec<OtherT> &v)\n"
        "    : m_base (v.address ()), m_size (v.length ()) {}\n"
        "\n"
        "  template<typename OtherT>\n"
        "  constexpr array_slice (vec<OtherT> &v)\n"
        "    : m_base (v.address ()), m_size (v.length ()) {}\n"
        "\n"
        "  template<typename OtherT, typename A>\n"
        "  constexpr array_slice (const vec<OtherT, A, vl_embed> *v)\n"
        "    : m_base (v ? v->address () : nullptr), m_size (v ? v->length () : 0) {}\n"
        "\n"
        "  template<typename OtherT, typename A>\n"
        "  constexpr array_slice (vec<OtherT, A, vl_embed> *v)\n"
        "    : m_base (v ? v->address () : nullptr), m_size (v ? v->length () : 0) {}"
    )
    if vec_old not in vec_content:
        raise RuntimeError(
            "GCC 16.1.0 vec.h array_slice ctor block no longer matches"
        )
    vec_h.write_text(vec_content.replace(vec_old, vec_new, 1), encoding="utf-8")

    # 4) HarmonyOS rejects dlopen() of an unsigned shared object with
    #    EPERM (E077).  libgccjit JIT-compiles code into a temporary
    #    fake.so and dlopens it; that file is unsigned, so the runtime
    #    load fails with "Permission denied".  Sign fake.so in place
    #    before dlopen when a signer is supplied through the
    #    OHOS_JIT_SIGNER environment variable (set by the recipe).
    jit_playback = source / "gcc" / "jit" / "jit-playback.cc"
    playback_content = jit_playback.read_text(encoding="utf-8")
    dlopen_old = (
        "#else\n"
        "  const char *error = NULL;\n"
        "  /* Clear any existing error.  */\n"
        "  dlerror ();\n"
        "\n"
        "  handle = dlopen (m_tempdir->get_path_so_file (),\n"
        "\t\t   RTLD_NOW | RTLD_LOCAL);\n"
    )
    dlopen_new = (
        "#else\n"
        "  const char *error = NULL;\n"
        "  /* Clear any existing error.  */\n"
        "  dlerror ();\n"
        "\n"
        "  /* HarmonyOS requires a signed ELF before dlopen (E077);\n"
        "     the freshly-linked fake.so is unsigned, so sign it in\n"
        "     place when a signer is configured via OHOS_JIT_SIGNER.  */\n"
        "  {\n"
        "    const char *signer = getenv (\"OHOS_JIT_SIGNER\");\n"
        "    if (signer && *signer)\n"
        "      {\n"
        "\tconst char *so = m_tempdir->get_path_so_file ();\n"
        "\tchar cmd[4096];\n"
        "\tsnprintf (cmd, sizeof (cmd),\n"
        "\t\t  \"'%s' sign -inFile '%s' -outFile '%s.signed' \"\n"
        "\t\t  \"-selfSign 1 && mv -f '%s.signed' '%s'\",\n"
        "\t\t  signer, so, so, so, so);\n"
        "\tif (system (cmd) != 0)\n"
        "\t  add_error (NULL, \"OHOS JIT signing failed for %s\", so);\n"
        "      }\n"
        "  }\n"
        "\n"
        "  handle = dlopen (m_tempdir->get_path_so_file (),\n"
        "\t\t   RTLD_NOW | RTLD_LOCAL);\n"
    )
    if dlopen_old not in playback_content:
        raise RuntimeError(
            "GCC 16.1.0 jit-playback.cc dlopen block no longer matches"
        )
    jit_playback.write_text(
        playback_content.replace(dlopen_old, dlopen_new, 1),
        encoding="utf-8",
    )


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: prepare_ohos_sources.py SOURCE_FOLDER OHOS_HEADER"
        )
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
