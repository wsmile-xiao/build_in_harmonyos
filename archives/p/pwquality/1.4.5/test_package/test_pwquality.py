#!/usr/bin/env python3
"""Consumer-side check for the packaged pwquality 1.4.5 (R34: real API).

Compiles and runs a small C program against the **packaged** header and shared
library — the same approach this archive uses for other C libraries (cracklib).
Every assertion calls a real API; nothing is inferred from file presence alone.

Exercised (measured function signatures from src/pwquality.h):

* ``pwquality_default_settings()`` → ``pwquality_settings_t *``
* ``pwquality_set_int_value()`` / ``pwquality_get_int_value()`` round-trip
* ``pwquality_read_config()`` — against **the delivered**
  ``etc/security/pwquality.conf`` (shipped but otherwise never read) and against a
  config file this test writes itself (int + string settings + ``dictcheck=0``),
  verifying the parsed values actually take effect
* ``pwquality_set_str_value()`` / ``pwquality_get_str_value()`` round-trip
  (``PWQ_SETTING_BAD_WORDS``)
* the **bad-words check firing** (``PWQ_ERROR_BAD_WORDS``) — an unexercised path
* ``pwquality_check()`` → score >= 0 for a strong password, < 0 (error) plus a
  message from ``pwquality_strerror()`` for one that is too short
* ``pwquality_generate()`` → produces a password that then passes
  ``pwquality_check()`` (a real generate→verify loop)
* ``pwquality_free_settings()``

The CLI tools ``pwscore`` / ``pwmake`` are also executed for real.
"""
import os
import shutil
import subprocess
import sys

C_SOURCE = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pwquality.h>

int main(int argc, char **argv)
{
    const char *pkg = argv[1];
    const char *workdir = argv[2];   /* scratch dir, set by test_pwquality.py */
    int failures = 0;

    /* --- default settings ------------------------------------------------ */
    pwquality_settings_t *pwq = pwquality_default_settings();
    if (!pwq) { printf("FAIL: pwquality_default_settings returned NULL\n"); return 1; }

    /* --- int setting round-trip ----------------------------------------- */
    if (pwquality_set_int_value(pwq, PWQ_SETTING_MIN_LENGTH, 12) != 0) {
        printf("FAIL: set MIN_LENGTH\n"); failures++;
    }
    int minlen = 0;
    if (pwquality_get_int_value(pwq, PWQ_SETTING_MIN_LENGTH, &minlen) != 0 || minlen != 12) {
        printf("FAIL: get MIN_LENGTH = %d (expected 12)\n", minlen); failures++;
    } else {
        printf("  MIN_LENGTH round-trip = %d\n", minlen);
    }

    /* --- dictionary check needs an EXTERNAL dictionary ------------------ */
    /* pwquality's dict_check calls cracklib's FascistCheck, which needs a
     * compiled dictionary (pw_dict.pwd/.pwi) installed at runtime. The cracklib
     * package in this archive ships only headers+libs (no dictionary), so with
     * dict_check enabled a check fails with PWQ_ERROR_CRACKLIB_CHECK (-22) and
     * pwquality_generate cascades to PWQ_ERROR_GENERATION_FAILED (-24).
     * That is an environmental data dependency, not a library defect, so this
     * is asserted explicitly and then dict_check is turned OFF for the
     * functional checks below. */
    char buf[256];
    void *aux = NULL;
    int with_dict = pwquality_check(pwq, "Str0ng!Password#2024", NULL, "alice", &aux);
    if (with_dict == PWQ_ERROR_CRACKLIB_CHECK) {
        pwquality_strerror(buf, sizeof(buf), with_dict, aux);
        printf("  dict_check=1 -> PWQ_ERROR_CRACKLIB_CHECK (no dictionary "
               "installed; expected in this environment)\n");
    } else if (with_dict >= 0) {
        printf("  dict_check=1 -> score %d (a dictionary IS available)\n", with_dict);
    } else {
        pwquality_strerror(buf, sizeof(buf), with_dict, aux);
        printf("FAIL: dict_check=1 gave unexpected %d: %s\n", with_dict, buf);
        failures++;
    }
    if (pwquality_set_int_value(pwq, PWQ_SETTING_DICT_CHECK, 0) != 0) {
        printf("FAIL: could not disable dict_check\n"); failures++;
    }

    /* --- a strong password passes (dictionary check off) ---------------- */
    aux = NULL;
    int score = pwquality_check(pwq, "Str0ng!Password#2024", NULL, "alice", &aux);
    if (score < 0) {
        pwquality_strerror(buf, sizeof(buf), score, aux);
        printf("FAIL: strong password rejected: score=%d msg=%s\n", score, buf);
        failures++;
    } else {
        printf("  strong password score = %d\n", score);
    }

    /* --- a too-short password is rejected with a message ---------------- */
    aux = NULL;
    int bad = pwquality_check(pwq, "ab", NULL, "alice", &aux);
    if (bad >= 0) {
        printf("FAIL: 'ab' unexpectedly accepted (score=%d)\n", bad);
        failures++;
    } else {
        pwquality_strerror(buf, sizeof(buf), bad, aux);
        if (strlen(buf) == 0) {
            printf("FAIL: strerror produced an empty message\n"); failures++;
        } else {
            printf("  short password rejected: %s\n", buf);
        }
    }

    /* --- generate then verify (real generate->check loop) --------------- */
    char *generated = NULL;
    int rc = pwquality_generate(pwq, 64, &generated);
    if (rc != 0 || !generated) {
        printf("FAIL: pwquality_generate rc=%d\n", rc); failures++;
    } else {
        printf("  generated password length = %zu\n", strlen(generated));
        aux = NULL;
        int gscore = pwquality_check(pwq, generated, NULL, "alice", &aux);
        if (gscore < 0) {
            pwquality_strerror(buf, sizeof(buf), gscore, aux);
            printf("FAIL: generated password rejected: %s\n", buf);
            failures++;
        } else {
            printf("  generated password verifies, score = %d\n", gscore);
        }
        free(generated);
    }

    pwquality_free_settings(pwq);

    /* --- pwquality_read_config(): the DELIVERED conf (shipped, never read) --- */
    /* etc/security/pwquality.conf is packaged but nothing exercises it; reading
     * it must succeed (rc == 0). It is comment-only, so it changes nothing —
     * the point is that the parser accepts the shipped file as-is. */
    char cfgpath[1200];
    snprintf(cfgpath, sizeof(cfgpath), "%s/etc/security/pwquality.conf", pkg);
    pwquality_settings_t *pwq_c = pwquality_default_settings();
    if (!pwq_c) { printf("FAIL: default_settings for config test\n"); failures++; }
    else {
        aux = NULL;
        int rv_cfg = pwquality_read_config(pwq_c, cfgpath, &aux);
        if (rv_cfg != 0) {
            pwquality_strerror(buf, sizeof(buf), rv_cfg, aux);
            printf("FAIL: read_config(delivered conf) rc=%d: %s\n", rv_cfg, buf);
            failures++;
        } else {
            printf("  read_config accepted the delivered etc/security/pwquality.conf\n");
        }
        pwquality_free_settings(pwq_c);
    }

    /* --- read_config() with real settings: parsed values must take effect --- */
    /* Write our own conf, then prove the parser applied it (int + string). */
    snprintf(cfgpath, sizeof(cfgpath), "%s/test_pwquality.conf", workdir);
    FILE *cf = fopen(cfgpath, "w");
    if (!cf) { printf("FAIL: cannot write %s\n", cfgpath); failures++; }
    else {
        fprintf(cf, "# written by the test_package consumer check\n");
        fprintf(cf, "minlen = 20\n");
        fprintf(cf, "badwords = mybadword\n");
        fclose(cf);

        pwquality_settings_t *pwq_r = pwquality_default_settings();
        if (!pwq_r) { printf("FAIL: default_settings for read_config test\n"); failures++; }
        else {
            aux = NULL;
            int rv_r = pwquality_read_config(pwq_r, cfgpath, &aux);
            if (rv_r != 0) {
                pwquality_strerror(buf, sizeof(buf), rv_r, aux);
                printf("FAIL: read_config(custom conf) rc=%d: %s\n", rv_r, buf);
                failures++;
            } else {
                int got_min = -1;
                if (pwquality_get_int_value(pwq_r, PWQ_SETTING_MIN_LENGTH, &got_min) != 0
                    || got_min != 20) {
                    printf("FAIL: conf minlen not applied (got %d, want 20)\n", got_min);
                    failures++;
                } else {
                    printf("  conf file applied: minlen = %d\n", got_min);
                }
                const char *got_bw = NULL;
                if (pwquality_get_str_value(pwq_r, PWQ_SETTING_BAD_WORDS, &got_bw) != 0
                    || got_bw == NULL || strcmp(got_bw, "mybadword") != 0) {
                    printf("FAIL: conf badwords not applied (got %s)\n",
                           got_bw ? got_bw : "(null)");
                    failures++;
                } else {
                    printf("  conf file applied: badwords = %s\n", got_bw);
                }
            }
            pwquality_free_settings(pwq_r);
        }
    }

    /* --- string setting round-trip (set/get BAD_WORDS) --------------------- */
    pwquality_settings_t *pwq_s = pwquality_default_settings();
    if (!pwq_s) { printf("FAIL: default_settings for str round-trip\n"); failures++; }
    else {
        if (pwquality_set_str_value(pwq_s, PWQ_SETTING_BAD_WORDS, "alpha-beta") != 0) {
            printf("FAIL: set_str_value(BAD_WORDS)\n"); failures++;
        } else {
            const char *rt = NULL;
            if (pwquality_get_str_value(pwq_s, PWQ_SETTING_BAD_WORDS, &rt) != 0
                || rt == NULL || strcmp(rt, "alpha-beta") != 0) {
                printf("FAIL: str round-trip got %s\n", rt ? rt : "(null)");
                failures++;
            } else {
                printf("  BAD_WORDS str round-trip = %s\n", rt);
            }
        }
        pwquality_free_settings(pwq_s);
    }

    /* --- the bad-words CHECK actually fires (differential, unexercised) ---- */
    /* Same password + same settings, only badwords differs, so any difference
     * in the verdict is attributable to the bad-words path. dict_check is off
     * because no dictionary is shipped (that path is covered above). */
    pwquality_settings_t *pwq_b = pwquality_default_settings();
    if (!pwq_b) { printf("FAIL: default_settings for badwords check\n"); failures++; }
    else {
        pwquality_set_int_value(pwq_b, PWQ_SETTING_DICT_CHECK, 0);
        pwquality_set_int_value(pwq_b, PWQ_SETTING_MIN_LENGTH, 8);
        const char *pw_with_word = "mysecretpassword42";   /* contains "password" */

        aux = NULL;
        int without_bw = pwquality_check(pwq_b, pw_with_word, NULL, "alice", &aux);
        if (without_bw < 0) {
            pwquality_strerror(buf, sizeof(buf), without_bw, aux);
            printf("FAIL: baseline password rejected before badwords set: %s\n", buf);
            failures++;
        }
        if (pwquality_set_str_value(pwq_b, PWQ_SETTING_BAD_WORDS, "password") != 0) {
            printf("FAIL: set badwords for the check\n"); failures++;
        } else {
            aux = NULL;
            int with_bw = pwquality_check(pwq_b, pw_with_word, NULL, "alice", &aux);
            if (with_bw != PWQ_ERROR_BAD_WORDS) {
                pwquality_strerror(buf, sizeof(buf), with_bw, aux);
                printf("FAIL: bad-words check did not fire (rc=%d: %s)\n",
                       with_bw, buf);
                failures++;
            } else {
                printf("  bad-words check fired: PWQ_ERROR_BAD_WORDS for a "
                       "password containing the configured word\n");
            }
        }
        pwquality_free_settings(pwq_b);
    }

    (void)pkg;
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
        # An absolute/relative path that exists wins (CI exports e.g.
        # CC=/data/service/hnp/bin/clang, which is NOT on PATH).
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

    Measured on CI (#10423): ``CC`` is exported as the bare word ``clang`` while
    ``/data/service/hnp/bin`` is absent from ``PATH``. Using ``os.environ["CC"]``
    verbatim therefore aborted with
        FileNotFoundError: [Errno 2] No such file or directory: 'clang'
    so CC is only honoured when it actually resolves, and a real interpreter is
    otherwise located by name or by absolute path.
    """
    return find_tool(os.environ.get("CC"), "clang", "gcc", "cc", *CC_CANDIDATES)


def main():
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    lib = os.path.join(pkg, "lib")

    # --- packaged artifacts ------------------------------------------------
    header = os.path.join(inc, "pwquality.h")
    if not os.path.isfile(header):
        print(f"FAIL: pwquality.h not found at {header}", file=sys.stderr)
        return 1
    sos = [n for n in os.listdir(lib) if n.startswith("libpwquality.so")]
    if not sos:
        print(f"FAIL: libpwquality.so not found under {lib}", file=sys.stderr)
        return 1
    pc = os.path.join(lib, "pkgconfig", "pwquality.pc")
    if not os.path.isfile(pc):
        print(f"FAIL: pwquality.pc not found at {pc}", file=sys.stderr)
        return 1
    # pkg-config contract: the .pc must be usable
    pkgconfig = find_tool("pkg-config")
    if pkgconfig:
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = os.path.join(lib, "pkgconfig")
        res = subprocess.run([pkgconfig, "--modversion", "pwquality"],
                             capture_output=True, env=env, timeout=60)
        ver = res.stdout.decode().strip()
        assert res.returncode == 0 and ver == "1.4.5", (res.returncode, ver)
        res = subprocess.run([pkgconfig, "--libs", "pwquality"],
                             capture_output=True, env=env, timeout=60)
        assert "-lpwquality" in res.stdout.decode(), res.stdout
        print(f"  pkg-config: pwquality {ver} (-lpwquality present)")

    cc = find_cc()
    if not cc:
        print("FAIL: no C compiler found (tried CC=$CC, PATH, and absolute "
              f"fallbacks {CC_CANDIDATES})", file=sys.stderr)
        return 1

    workdir = os.path.join(os.path.dirname(os.path.abspath(pkg)), "_pwq_test")
    os.makedirs(workdir, exist_ok=True)
    src = os.path.join(workdir, "consumer.c")
    exe = os.path.join(workdir, "consumer")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(C_SOURCE)

    rpath = lib
    compile_cmd = [cc, "-O1", f"-I{inc}", src, f"-L{lib}", "-lpwquality",
                   f"-Wl,-rpath,{rpath}", "-o", exe]
    res = subprocess.run(compile_cmd, capture_output=True, timeout=300)
    if res.returncode != 0:
        print("FAIL: compiling the consumer program failed:\n"
              + (res.stdout + res.stderr).decode(errors="ignore"), file=sys.stderr)
        return 1
    print("  consumer program compiled against the packaged header+library")

    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = lib + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    res = subprocess.run([exe, pkg, workdir], capture_output=True, env=env,
                         timeout=180)
    out = (res.stdout + res.stderr).decode(errors="ignore")
    print("\n".join("  " + ln for ln in out.strip().splitlines()))
    if res.returncode != 0:
        print("FAIL: consumer program reported failures", file=sys.stderr)
        return 1

    # --- CLI tools: run them for real --------------------------------------
    for tool in ("pwscore", "pwmake"):
        path = os.path.join(pkg, "bin", tool)
        if not os.path.isfile(path):
            print(f"FAIL: {tool} missing from {pkg}/bin", file=sys.stderr)
            return 1

    # pwscore: a password shorter than the minimum length fails the LENGTH check,
    # which runs before the dictionary check — a real code path needing no
    # dictionary. (measured: "The password is shorter than 8 characters", rc=1)
    score_exe = os.path.join(pkg, "bin", "pwscore")
    res = subprocess.run([score_exe], input=b"ab\n", capture_output=True,
                         env=env, timeout=120)
    out = (res.stdout + res.stderr).decode(errors="ignore")
    assert "shorter than" in out, f"pwscore length check missing: {out!r}"
    assert res.returncode == 1, (res.returncode, out)
    print("  pwscore: length check fired ('shorter than ...'), dictionary not needed")

    # pwscore with a length-compliant password proceeds to the DICTIONARY check.
    # Without an installed dictionary that must fail with the cracklib error —
    # pinned explicitly so the environmental gap is documented rather than
    # silently tolerated.
    res = subprocess.run([score_exe], input=b"Str0ng!Password#2024\n",
                         capture_output=True, env=env, timeout=120)
    out = (res.stdout + res.stderr).decode(errors="ignore")
    if "pw_dict" in out or "dictionary" in out.lower():
        print("  pwscore: long password -> dictionary-check failure "
              "(no dictionary installed; environmental, as documented)")
    else:
        scored = res.stdout.decode().strip()
        assert scored.isdigit(), (scored, out)
        print(f"  pwscore: long password scored {scored}")

    # pwmake: the usage paths (wrong arg count / non-numeric) need no dictionary.
    make_exe = os.path.join(pkg, "bin", "pwmake")
    for bad_args, want_rc in (([], 3), (["abc"], 4)):
        res = subprocess.run([make_exe, *bad_args], capture_output=True,
                             env=env, timeout=120)
        out = (res.stdout + res.stderr).decode(errors="ignore")
        assert "Usage:" in out, f"pwmake {bad_args} expected usage, got {out!r}"
        assert res.returncode == want_rc, (bad_args, res.returncode, want_rc)
    print("  pwmake: usage paths verified (no args -> rc=3, non-numeric -> rc=4)")

    # pwmake with an entropy count generates a password, but generation verifies
    # candidates through the dictionary check, so it needs the dictionary too.
    res = subprocess.run([make_exe, "64"], capture_output=True, env=env, timeout=120)
    made = res.stdout.decode(errors="ignore").strip()
    err = res.stderr.decode(errors="ignore")
    if made:
        assert len(made) >= 8, f"pwmake produced too-short output: {made!r}"
        print(f"  pwmake 64 produced a {len(made)}-char password")
    else:
        assert "pw_dict" in err or "dictionary" in err.lower(), err
        print("  pwmake 64 -> generation blocked by the missing dictionary "
              "(environmental, as documented)")

    print(f"pwquality 1.4.5 consumer API: PASS ({pkg})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
