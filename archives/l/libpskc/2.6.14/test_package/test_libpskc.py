#!/usr/bin/env python3
"""Consumer-side check for the packaged libpskc 2.6.14 (R34: real API).

Compiles and runs a small C program against the **packaged** headers and shared
library, then drives the real PSKC document pipeline: parse a KeyContainer from
memory, read its accessors, build it back out to XML, and confirm error paths.

Modeled on upstream's own ``libpskc/tests/tst_*.c`` (that is where the PSKC XML
fixture shape comes from), so the assertions follow upstream semantics rather
than guesses.

Deliberately NOT exercised: ``pskc_sign_x509`` / ``pskc_verify_x509crt``. Those
need **xmlsec1**, which is not published on ohpcd; without it libpskc builds the
non-xmlsec configuration (``USE_XMLSEC`` undefined) and those entry points
return errors. The gap is reported explicitly instead of being papered over —
see notes.md.
"""
import json
import os
import shutil
import subprocess
import sys

# A minimal but *valid* PSKC KeyContainer. Shape taken from upstream's
# tests/tst_accessors.c (namespace + KeyPackage + HOTP algorithm), trimmed to
# what the accessors below read.
PSKC_XML = """<?xml version="1.0" encoding="UTF-8"?>
<KeyContainer Version="1.0" Id="KCID-1"
              xmlns="urn:ietf:params:xml:ns:keyprov:pskc">
  <KeyPackage>
    <DeviceInfo>
      <Manufacturer>TestVendor</Manufacturer>
    </DeviceInfo>
    <Key Id="key-1" Algorithm="urn:ietf:params:xml:ns:keyprov:pskc:hotp">
      <Data>
        <Secret>
          <PlainValue>MTIzNDU2Nzg5MDEyMzQ1Ng==</PlainValue>
        </Secret>
      </Data>
    </Key>
  </KeyPackage>
</KeyContainer>
"""

C_SOURCE = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pskc/pskc.h>

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { \
    printf("FAIL: %s\n", msg); failures++; } } while (0)

/* PSKC document injected by the Python driver (see __PSKC_XML_LITERAL__). */
static const char *PSKC_XML = __PSKC_XML_LITERAL__;

int main(void)
{
    pskc_rc rc;
    pskc_t *container = NULL;

    /* --- version API (real calls, mirroring upstream tests/tst_basic.c) --
     * Implementation (global.c:143):
     *   return (!req_version || strverscmp(req_version, PSKC_VERSION) <= 0)
     *          ? PSKC_VERSION : NULL;
     * so a *lower* requirement succeeds ("0" <= "2.6.14" -> non-NULL) while a
     * higher/incomparable one fails ("999.999", "UNKNOWN" -> NULL).
     * An earlier draft asserted the opposite for "0" and was wrong. */
    CHECK(pskc_check_version(PSKC_VERSION) != NULL, "check_version(PSKC_VERSION)");
    CHECK(pskc_check_version(NULL) != NULL, "check_version(NULL)");
    CHECK(pskc_check_version("999.999") == NULL, "check_version(999.999) should be NULL");
    CHECK(pskc_check_version("0") != NULL, "check_version(0) should succeed (lower req)");
    CHECK(pskc_check_version("UNKNOWN") == NULL, "check_version(UNKNOWN) should be NULL");

    /* --- global init / log hook ---------------------------------------- */
    rc = pskc_global_init();
    CHECK(rc == PSKC_OK, "pskc_global_init");

    /* --- init + parse the real document -------------------------------- */
    rc = pskc_init(&container);
    CHECK(rc == PSKC_OK && container != NULL, "pskc_init");

    /* ARGUMENT ORDER — verified against the shipped header, do NOT "fix" it.
     *
     *   include/pskc/container.h:47
     *   extern PSKCAPI int pskc_parse_from_memory (pskc_t * container,
     *                                              size_t len, const char *buffer);
     *
     * i.e. (container, len, buffer) — the length comes BEFORE the buffer.
     * Compiling this call with ``-Wall -Wextra -Werror`` against the packaged
     * header produces zero diagnostics; swapping to (container, buffer, len)
     * yields two hard errors:
     *   error: incompatible pointer to integer conversion passing 'const char *'
     *          to parameter of type 'size_t' [-Wint-conversion]
     *   note: passing argument to parameter 'len' here   (container.h:48)
     *   error: incompatible integer to pointer conversion passing 'unsigned long'
     *          to parameter of type 'const char *' [-Wint-conversion]
     * So this order is the correct one. */
    rc = pskc_parse_from_memory(container, strlen(PSKC_XML), PSKC_XML);
    if (rc != PSKC_OK)
    {
        printf("FAIL: pskc_parse_from_memory rc=%d\n", rc);
        failures++;
    }
    else
    {
        const char *v = pskc_get_version(container);
        const char *id = pskc_get_id(container);
        pskc_key_t *key;

        printf("  parsed: version=%s id=%s\n",
               v ? v : "(null)", id ? id : "(null)");
        CHECK(v != NULL && strcmp(v, "1.0") == 0, "pskc_get_version == 1.0");
        CHECK(id != NULL && strcmp(id, "KCID-1") == 0, "pskc_get_id == KCID-1");

        key = pskc_get_keypackage(container, 0);
        CHECK(key != NULL, "pskc_get_keypackage(0)");

        /* serialise back out to XML — real round-trip through libxml2.
         * Measured signature (include/pskc/container.h:91):
         *   int pskc_output(pskc_t *, pskc_output_formats_t, char **out, size_t *len);
         * This API has NO pskc_output_t / pskc_output_init / pskc_output_done. */
        {
            char *out = NULL;
            size_t outlen = 0;
            rc = pskc_output(container, PSKC_OUTPUT_XML, &out, &outlen);
            CHECK(rc == PSKC_OK, "pskc_output(XML)");
            CHECK(out != NULL, "pskc_output produced a buffer");
            CHECK(out != NULL && outlen > 0, "pskc_output reported a length");
            CHECK(out != NULL && strstr(out, "KeyContainer") != NULL,
                  "round-trip XML contains KeyContainer");
            if (out)
            {
                printf("  round-trip XML length=%zu\n", outlen);
                pskc_free(out);
            }
        }

        /* upstream-documented error case (tests/tst_basic.c:115):
         *   pskc_output(NULL, 42, NULL, NULL) == PSKC_UNKNOWN_OUTPUT_FORMAT */
        rc = pskc_output(NULL, (pskc_output_formats_t) 42, NULL, NULL);
        CHECK(rc == PSKC_UNKNOWN_OUTPUT_FORMAT,
              "pskc_output(invalid format) == PSKC_UNKNOWN_OUTPUT_FORMAT");
    }

    /* --- error path: malformed XML must be rejected -------------------- */
    {
        pskc_t *bad = NULL;
        rc = pskc_init(&bad);
        CHECK(rc == PSKC_OK, "pskc_init(bad)");
        /* Same argument order as above: (container, len, buffer) — 20 bytes
         * then the buffer, per include/pskc/container.h:47. */
        rc = pskc_parse_from_memory(bad, 20, "<not-a-pskc-docute/>");
        CHECK(rc != PSKC_OK, "malformed XML must not parse as PSKC_OK");
        printf("  malformed input rejected with rc=%d\n", rc);
        pskc_done(bad);
    }

    pskc_done(container);
    pskc_global_done();

    if (failures) { printf("FAILURES: %d\n", failures); return 1; }
    printf("OK\n");
    return 0;
}
"""


def find_tool(*names):
    """Resolve a tool by name on PATH, or accept an existing absolute path."""
    for n in names:
        if not n:
            continue
        # An existing absolute/relative path wins (CI exports e.g.
        # CC=/data/service/hnp/bin/clang, whose directory is NOT on PATH).
        if os.path.sep in n:
            if os.path.isfile(n) and os.access(n, os.X_OK):
                return n
            continue
        p = shutil.which(n)
        if p:
            return p
    return None


# Absolute fallbacks: the CI sandbox does not put the HNP toolchain dir on PATH,
# and it exports CC as a *bare* name ("clang"), which subprocess cannot exec.
CC_CANDIDATES = (
    "/data/service/hnp/bin/clang",
    "/data/service/hnp/bin/gcc",
    "/storage/Users/currentUser/usr/local/bin/clang",
    "/usr/bin/clang",
    "/usr/bin/gcc",
    "/usr/bin/cc",
)


def find_cc():
    """Locate a usable C compiler, tolerating an unusable ``CC``.

    Measured on CI (#10423, same pattern here): ``CC`` is exported as the bare
    word ``clang`` while ``/data/service/hnp/bin`` is absent from ``PATH``, so
    honouring ``os.environ["CC"]`` verbatim aborts with
        FileNotFoundError: [Errno 2] No such file or directory: 'clang'
    CC is therefore only used when it actually resolves; otherwise a real
    interpreter is found by name or by absolute path.
    """
    return find_tool(os.environ.get("CC"), "clang", "gcc", "cc", *CC_CANDIDATES)


def compile_env(pkg_libdirs):
    """Environment for the *compile/link* step — packaged libs must not leak in.

    Measured on CI (#10440, build #49233): the test_package runs the script with
    ``env="conanrun"``, so ``LD_LIBRARY_PATH`` contains the packaged dependency
    lib dirs, including libxml2/2.15.3.1's ``lib``.  The OHOS SDK's ``lld`` is
    itself a dynamic executable linked against ``libxml2.so.16`` and resolves it
    through its own ``$ORIGIN/../lib`` RUNPATH.  Having *another* same-soname
    ``libxml2.so.16`` earlier on ``LD_LIBRARY_PATH`` **shadows** the SDK's copy,
    so the linker dies before doing any work:

        Error relocating .../native/llvm/bin/lld: xmlFreeDoc: symbol not found
        ("xmlSetGenericErrorFunc"/"xmlReadMemory"/... likewise)
        clang-15: error: unable to execute command: No such file or directory
        clang-15: error: linker command failed due to signal

    Reproduced locally by putting a same-named, symbol-less ``libxml2.so.16`` on
    LD_LIBRARY_PATH while invoking the SDK clang — identical message.

    The compile step does not need LD_LIBRARY_PATH at all: the packaged headers
    and libraries are addressed explicitly via -I/-L below.  So the packaged lib
    dirs are dropped from LD_LIBRARY_PATH *for this subprocess only*; the runtime
    step below re-adds them deliberately (that is where they are required).
    """
    env = dict(os.environ)
    drop = [os.path.abspath(d) for d in pkg_libdirs if d]
    kept = []
    for entry in env.get("LD_LIBRARY_PATH", "").split(os.pathsep):
        if not entry:
            continue
        if any(os.path.abspath(entry) == d for d in drop):
            continue
        kept.append(entry)
    if kept:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(kept)
    else:
        env.pop("LD_LIBRARY_PATH", None)
    return env


def main():
    pkg = sys.argv[1]
    # Optional: libxml2's runtime lib directory (passed by the test_package
    # conanfile) so the consumer program can resolve the dependency .so.
    libxml2_libdir = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("LIBXML2_LIBDIR")
    inc = os.path.join(pkg, "include")
    lib = os.path.join(pkg, "lib")

    # --- packaged artifacts ------------------------------------------------
    header = os.path.join(inc, "pskc", "pskc.h")
    if not os.path.isfile(header):
        print(f"FAIL: pskc/pskc.h not found at {header}", file=sys.stderr)
        return 1
    sos = [n for n in os.listdir(lib) if n.startswith("libpskc.so")]
    if not sos:
        print(f"FAIL: libpskc.so not found under {lib}", file=sys.stderr)
        return 1
    pc = os.path.join(lib, "pkgconfig", "libpskc.pc")
    if not os.path.isfile(pc):
        print(f"FAIL: libpskc.pc not found at {pc}", file=sys.stderr)
        return 1

    # pkg-config contract must hold (module name "libpskc", -lpskc)
    pkgconfig = find_tool("pkg-config")
    if pkgconfig:
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = os.path.join(lib, "pkgconfig")
        res = subprocess.run([pkgconfig, "--modversion", "libpskc"],
                             capture_output=True, env=env, timeout=60)
        ver = res.stdout.decode().strip()
        assert res.returncode == 0 and ver == "2.6.14", (res.returncode, ver, res.stderr)
        res = subprocess.run([pkgconfig, "--libs", "libpskc"],
                             capture_output=True, env=env, timeout=60)
        assert "-lpskc" in res.stdout.decode(), res.stdout
        print(f"  pkg-config: libpskc {ver} (-lpskc present)")

    cc = find_cc()
    if not cc:
        print("FAIL: no C compiler found (tried CC=$CC, PATH, and absolute "
              f"fallbacks {CC_CANDIDATES})", file=sys.stderr)
        return 1

    workdir = os.path.join(os.path.dirname(os.path.abspath(pkg)), "_libpskc_test")
    os.makedirs(workdir, exist_ok=True)
    src = os.path.join(workdir, "consumer.c")
    exe = os.path.join(workdir, "consumer")
    # Inject the PSKC fixture as a C string literal. json.dumps produces an
    # escaping that is valid C for this content (quotes/backslashes/newlines),
    # so the document travels in the source itself and needs no runtime file IO.
    c_literal = json.dumps(PSKC_XML)
    source_text = C_SOURCE.replace("__PSKC_XML_LITERAL__", c_literal)
    assert "__PSKC_XML_LITERAL__" not in source_text, "fixture placeholder not substituted"
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(source_text)
    res = subprocess.run([cc, "-O1", f"-I{inc}", src, f"-L{lib}", "-lpskc",
                          f"-Wl,-rpath,{lib}", "-o", exe],
                         capture_output=True, timeout=300,
                         env=compile_env([lib, libxml2_libdir]))
    if res.returncode != 0:
        print("FAIL: compiling the consumer program failed:\n"
              + (res.stdout + res.stderr).decode(errors="ignore"), file=sys.stderr)
        return 1
    print("  consumer program compiled against the packaged header+library")

    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = lib + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    # libxml2 is needed at runtime by the packaged library
    if libxml2_libdir:
        env["LD_LIBRARY_PATH"] = libxml2_libdir + os.pathsep + env["LD_LIBRARY_PATH"]
    res = subprocess.run([exe], capture_output=True, env=env, timeout=180)
    out = (res.stdout + res.stderr).decode(errors="ignore")
    print("\n".join("  " + ln for ln in out.strip().splitlines()))
    if res.returncode != 0:
        print("FAIL: consumer program reported failures", file=sys.stderr)
        return 1

    print(f"libpskc 2.6.14 consumer API: PASS ({pkg})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
