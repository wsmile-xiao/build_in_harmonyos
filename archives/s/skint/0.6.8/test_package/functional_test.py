#!/usr/bin/env python3
"""skint 0.6.8 — packaged-artifact functional + HarmonyOS runtime checks.

Drives the *installed* `skint` binary from the Conan package.  Every case
prints `[PASS] <id>` or `[FAIL] <id> <detail>` and the script ends with a
machine readable `RESULT: passed=<n> failed=<n>` line.

Groups
  F1..F21  documented interpreter surface: SRFI-176 version banner, help,
           `-e`/`-l`/`-s`/`-p`/REPL modes, R7RS evaluation (numbers, strings,
           vectors, records), proper tail recursion, call/cc, multiple
           values, dynamic-wind, file ports, error reporting, exit status.
  H1..H4   HarmonyOS specific runtime behaviour:
             H1 subprocess creation through the musl `system()` -> /bin/sh
                path (`(skint hidden)` %system)
             H2 file round-trip inside the OHOS application sandbox (HMDFS)
             H3 real `(command-line)` argv of the installed binary
             H4 the SRFI tree resolved out of the packaged prefix through
                SKINT_LIBDIRS (nothing to do with the build tree)

Stdlib only, so the same file runs on the HarmonyOS CI worker.
"""
import argparse
import os
import subprocess
import sys
import tempfile


class Harness(object):
    def __init__(self, binary, libdir, workdir):
        self.binary = binary
        self.libdir = libdir
        self.workdir = workdir

    def run(self, args, stdin=None, env_extra=None, cwd=None, timeout=300):
        env = dict(os.environ)
        if self.libdir:
            env["SKINT_LIBDIRS"] = self.libdir
        if env_extra:
            env.update(env_extra)
        payload = stdin.encode("utf-8") if isinstance(stdin, str) else stdin
        proc = subprocess.run([self.binary] + list(args), input=payload,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              env=env, cwd=cwd or self.workdir, timeout=timeout)
        return proc.returncode, proc.stdout.decode("utf-8", "replace")

    def write(self, name, text):
        path = os.path.join(self.workdir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def read(self, path):
        if not os.path.isabs(path):
            path = os.path.join(self.workdir, path)
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()


def _short(text, limit=180):
    text = " | ".join(text.strip().splitlines())
    return text[:limit]


# ── F: documented interpreter surface ─────────────────────────────────────
def f01_version(h):
    rc, out = h.run(["-V"])
    return (rc == 0 and '(version "0.6.8")' in out and "skint-0.6.8" in out,
            "rc=%d %s" % (rc, _short(out)))


def f02_help(h):
    rc, out = h.run(["-h"])
    ok = rc == 0 and "usage: skint" in out and "--eval" in out and "--version" in out
    return ok, "rc=%d %s" % (rc, _short(out))


def f03_eval_arithmetic(h):
    rc, out = h.run(["-e", "(+ 1 2)"])
    return rc == 0 and out.strip().endswith("3"), "rc=%d out=%r" % (rc, _short(out))


def f04_eval_data(h):
    rc, out = h.run(["-e", '(list 1 "two" \'three 4.5)'])
    return (rc == 0 and '(1 "two" three 4.5)' in out,
            "rc=%d out=%r" % (rc, _short(out)))


def f05_script_mode(h):
    path = h.write("f05.scm", '(display (string-append "script-" "ok"))\n(newline)\n')
    rc, out = h.run(["-s", path])
    return rc == 0 and "script-ok" in out, "rc=%d out=%r" % (rc, _short(out))


def f06_load_then_eval(h):
    path = h.write("f06.scm", "(define (answer) 42)\n")
    rc, out = h.run(["-l", path, "-e", "(answer)"])
    return rc == 0 and out.strip().endswith("42"), "rc=%d out=%r" % (rc, _short(out))


def f07_r7rs_base(h):
    prog = ("(let loop ((i 0) (acc (list)))"
            "  (if (= i 5) (reverse acc) (loop (+ i 1) (cons i acc))))")
    rc, out = h.run(["-e", prog])
    rc2, out2 = h.run(["-e", "(map (lambda (x) (* x x)) (list 1 2 3))"])
    ok = rc == 0 and "(0 1 2 3 4)" in out and rc2 == 0 and "(1 4 9)" in out2
    return ok, "loop=%r map=%r" % (_short(out), _short(out2))


def f08_numbers(h):
    prog = ("(list (quotient 7 2) (remainder 7 2) (floor 2.7) (expt 2 10) "
            "(number->string 255 16) (< 1 2))")
    rc, out = h.run(["-e", prog])
    ok = rc == 0 and "(3 1 2.0 1024 \"ff\" #t)" in out
    return ok, "rc=%d out=%r" % (rc, _short(out))


def f09_strings_chars(h):
    prog = ('(list (string-append "a" "b") (string-length "abc") '
            '(char->integer #\\A) (list->string (reverse (string->list "abc"))))')
    rc, out = h.run(["-e", prog])
    ok = rc == 0 and '("ab" 3 65 "cba")' in out
    return ok, "rc=%d out=%r" % (rc, _short(out))


def f10_vectors_bytevectors(h):
    prog = ('(let ((v (make-vector 3 0))) (vector-set! v 1 7) '
            '(list (vector-ref v 1) (vector-length v) '
            '(bytevector-u8-ref (bytevector 1 2 3) 2)))')
    rc, out = h.run(["-e", prog])
    ok = rc == 0 and "(7 3 3)" in out
    return ok, "rc=%d out=%r" % (rc, _short(out))


def f11_tail_recursion(h):
    prog = "(let loop ((i 0)) (if (= i 200000) i (loop (+ i 1))))"
    rc, out = h.run(["-e", prog])
    return rc == 0 and out.strip().endswith("200000"), "rc=%d out=%r" % (rc, _short(out))


def f12_call_cc(h):
    prog = "(call-with-current-continuation (lambda (k) (+ 1 (k 42))))"
    rc, out = h.run(["-e", prog])
    return rc == 0 and out.strip().endswith("42"), "rc=%d out=%r" % (rc, _short(out))


def f13_multiple_values(h):
    prog = "(call-with-values (lambda () (values 1 2)) +)"
    rc, out = h.run(["-e", prog])
    return rc == 0 and out.strip().endswith("3"), "rc=%d out=%r" % (rc, _short(out))


def f14_dynamic_wind(h):
    prog = ('(let ((log (list)))'
            ' (dynamic-wind'
            '  (lambda () (set! log (cons "in" log)))'
            '  (lambda () (set! log (cons "body" log)))'
            '  (lambda () (set! log (cons "out" log))))'
            ' (reverse log))')
    rc, out = h.run(["-e", prog])
    ok = rc == 0 and '("in" "body" "out")' in out
    return ok, "rc=%d out=%r" % (rc, _short(out))


def f15_file_ports(h):
    prog = ('(let ((p "f15-io.txt"))'
            ' (if (file-exists? p) (delete-file p))'
            ' (call-with-output-file p (lambda (out) (write (list 1 2 3) out)))'
            ' (let ((data (call-with-input-file p (lambda (in) (read in)))))'
            '  (list (file-exists? p) data)))')
    rc, out = h.run(["-e", prog])
    ok = rc == 0 and "(#t (1 2 3))" in out
    return ok, "rc=%d out=%r" % (rc, _short(out))


def f16_error_reporting(h):
    rc, out = h.run(["-e", '(error "boom" 1 2)'])
    ok = rc != 0 and "boom" in out
    return ok, "rc=%d out=%r" % (rc, _short(out))


def f17_exit_status(h):
    rc, out = h.run(["-e", "(exit 5)"])
    return rc == 5, "rc=%d out=%r" % (rc, _short(out))


def f18_program_mode(h):
    path = h.write("f18.scm",
                   '(import (scheme base) (scheme write))\n'
                   '(display "program-mode")\n(newline)\n')
    rc, out = h.run(["-p", path])
    return rc == 0 and "program-mode" in out, "rc=%d out=%r" % (rc, _short(out))


def f19_repl_stdin(h):
    rc, out = h.run([], stdin="(+ 40 2)\n")
    ok = rc == 0 and "42" in out
    return ok, "rc=%d out=%r" % (rc, _short(out))


def f20_features(h):
    prog = '(if (memq (quote r7rs) (features)) "r7rs-on" "r7rs-off")'
    rc, out = h.run(["-e", prog])
    return rc == 0 and "r7rs-on" in out, "rc=%d out=%r" % (rc, _short(out))


def f21_records(h):
    prog = ('(begin'
            ' (define-record-type point (make-point x y) point?'
            '   (x point-x) (y point-y))'
            ' (let ((p (make-point 3 4)))'
            '  (list (point? p) (point-x p) (point-y p)'
            '        (assoc 2 (list (cons 1 "a") (cons 2 "b"))))))')
    rc, out = h.run(["-e", prog])
    ok = rc == 0 and "(#t 3 4 (2 . \"b\"))" in out
    return ok, "rc=%d out=%r" % (rc, _short(out))


# ── H: HarmonyOS specific runtime behaviour ───────────────────────────────
def h01_subprocess_spawn(h):
    """musl system() -> /bin/sh must exist and exec a real child on OHOS."""
    target = os.path.join(h.workdir, "h01-spawned.txt")
    prog = ('(begin (import (skint hidden))'
            ' (exit (%system "echo skint-ohos-ok > ' + target + '")))')
    rc, out = h.run(["-q", "-e", prog])
    body = h.read(target) if os.path.exists(target) else ""
    ok = rc == 0 and body.strip() == "skint-ohos-ok"
    return ok, "exit=%d body=%r out=%r" % (rc, body.strip(), _short(out))


def h02_sandbox_filesystem(h):
    """write/read/delete inside the OHOS sandbox (HMDFS) must round-trip."""
    prog = ('(let ((p "h02-roundtrip.txt"))'
            ' (if (file-exists? p) (delete-file p))'
            ' (call-with-output-file p'
            '  (lambda (out) (display "ohos-hmdfs" out) (newline out)))'
            ' (let ((txt (call-with-input-file p (lambda (in) (read-line in)))))'
            '  (delete-file p)'
            '  (list txt (file-exists? p))))')
    rc, out = h.run(["-e", prog])
    ok = rc == 0 and '("ohos-hmdfs" #f)' in out
    return ok, "rc=%d out=%r" % (rc, _short(out))


def h03_command_line_argv(h):
    """`(command-line)` must expose the real installed argv on OHOS."""
    path = h.write("h03-argv.scm", "(write (command-line))\n(newline)\n")
    rc, out = h.run(["-s", path, "alpha", "beta"])
    ok = (rc == 0 and "h03-argv.scm" in out
          and '"alpha"' in out and '"beta"' in out)
    return ok, "rc=%d out=%r" % (rc, _short(out))


def h04_packaged_srfi_tree(h):
    """SRFI modules must resolve from the packaged prefix via SKINT_LIBDIRS."""
    empty = tempfile.mkdtemp(prefix="skint-nowhere-")
    prog = ('(begin (import (srfi 1))'
            ' (list (fold + 0 (list 1 2 3))'
            '       (length (delete-duplicates (list 1 1 2 3 3)))))')
    rc, out = h.run(["-q", "-e", prog], cwd=empty)
    ok = rc == 0 and "(6 3)" in out
    return ok, "libdir=%s rc=%d out=%r" % (h.libdir, rc, _short(out))


FUNCTIONAL = [
    ("F1_version_banner", f01_version),
    ("F2_help_output", f02_help),
    ("F3_eval_arithmetic", f03_eval_arithmetic),
    ("F4_eval_data_literals", f04_eval_data),
    ("F5_script_mode", f05_script_mode),
    ("F6_load_then_eval", f06_load_then_eval),
    ("F7_r7rs_base", f07_r7rs_base),
    ("F8_numbers", f08_numbers),
    ("F9_strings_chars", f09_strings_chars),
    ("F10_vectors_bytevectors", f10_vectors_bytevectors),
    ("F11_tail_recursion", f11_tail_recursion),
    ("F12_call_cc", f12_call_cc),
    ("F13_multiple_values", f13_multiple_values),
    ("F14_dynamic_wind", f14_dynamic_wind),
    ("F15_file_ports", f15_file_ports),
    ("F16_error_reporting", f16_error_reporting),
    ("F17_exit_status", f17_exit_status),
    ("F18_program_mode", f18_program_mode),
    ("F19_repl_stdin", f19_repl_stdin),
    ("F20_features", f20_features),
    ("F21_records", f21_records),
]

HARMONYOS = [
    ("H1_ohos_subprocess_spawn", h01_subprocess_spawn),
    ("H2_ohos_sandbox_filesystem", h02_sandbox_filesystem),
    ("H3_ohos_command_line_argv", h03_command_line_argv),
    ("H4_ohos_packaged_srfi_tree", h04_packaged_srfi_tree),
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", required=True, help="packaged bin/skint")
    ap.add_argument("--libdir", required=True,
                    help="packaged share/skint/lib (SRFI external tree)")
    ap.add_argument("--group", choices=["all", "functional", "harmonyos"],
                    default="all")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.binary):
        print("skint functional suite: binary not found: %s" % args.binary)
        print("RESULT: passed=0 failed=1")
        return 1

    workdir = tempfile.mkdtemp(prefix="skint-functional-")
    h = Harness(args.binary, args.libdir, workdir)

    cases = []
    if args.group in ("all", "functional"):
        cases += FUNCTIONAL
    if args.group in ("all", "harmonyos"):
        cases += HARMONYOS

    passed = failed = 0
    for cid, fn in cases:
        try:
            ok, detail = fn(h)
        except Exception as exc:  # noqa: BLE001 - a crash is a failed case
            ok, detail = False, "%s: %s" % (type(exc).__name__, exc)
        print("[%s] %s%s" % ("PASS" if ok else "FAIL", cid,
                             (": " + detail) if detail else ""), flush=True)
        passed += 1 if ok else 0
        failed += 0 if ok else 1

    print("RESULT: passed=%d failed=%d" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
