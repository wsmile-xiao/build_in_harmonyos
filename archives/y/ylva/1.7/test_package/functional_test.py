#!/usr/bin/env python3
"""ylva 1.7 functional suite — 21 independent check items.

Upstream ships no test framework at all (see test_package/MANIFEST.yml for the
audit), so every case below is new.  The suite covers the whole documented CLI
surface: usage/version, password generation, database creation, the active
database pointer, every read path (LIKE search, POSIX regex search, list-all,
list-entry, show-latest, quick search), the interactive add path, QR rendering
and the AES-256-CTR encryption round trip.

Two families live here:

  F1-F21  functional coverage.  F1-F14 run non-interactively.  F15-F21 need a
          real pseudo-terminal because ylva reads every passphrase through
          my_getpass(), which calls tcgetattr() on stdin and therefore fails
          outright when stdin is a pipe (upstream then leaves the caller's
          buffer untouched — deliberately not something this suite pokes at).
  H1-H4   HarmonyOS-specific behaviour (sandbox HOME pointer file, HMDFS file
          mode, SQLite localtime stamps, UTF-8 half-block QR output).

Synchronisation note for the pty driver: ylva prints its prompts with printf()
and no trailing newline.  musl — and therefore the OHOS libc — only flushes a
line-buffered stream when it sees a newline, unlike glibc which also flushes on
line-buffered *input*, so on OHOS the prompt text does not show up before the
read begins.  This driver therefore never waits for a prompt: it sends the
fixed prelude lines in order and then keeps re-sending the passphrase line
until the process exits.  Every my_getpass() starts with tcsetattr(TCSAFLUSH),
which discards only the input pending at that instant, so a re-sent line is
always consumed by the next read.

Upstream option-ordering quirk the suite works around: ylva's main() executes each
option as getopt_long() returns it, while --show-passwords / --show-qrcode /
--auto-encrypt / --force are flag-style long options (they return 0 and only store
the value).  Those flags therefore have to precede the action option, e.g.
``--show-passwords -A``; writing them afterwards silently has no effect.  The
suite uses the working order (verified against a native build before shipping).

Usage: functional_test.py --bindir <pkg>/bin [--verbose]
Summary line: RESULT: passed=N failed=M
Exit code: 0 when failed == 0.
"""
import argparse
import os
import pty
import re
import select
import stat
import subprocess
import sys
import tempfile
import time

PASS = []
FAIL = []
BIN = None

TIMEOUT = float(os.environ.get("YLVA_TEST_TIMEOUT", "90"))
# crypto.h: sizeof(int) magic + IV_SIZE 16 + SALT_SIZE 64 + HMAC_SHA512_SIZE 64
ENC_OVERHEAD = 148
PASSWORD_CHARSET = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789?)(/%#!?=")
SECRET = "correct horse battery"
DB_MODE_CHECK = 0o007  # nothing for "other"

def record(cid, name, ok, detail=""):
    (PASS if ok else FAIL).append("%s %s" % (cid, name))
    print("  [%s] %s %s%s" % ("PASS" if ok else "FAIL", cid, name,
                              ("  -- " + detail) if detail else ""),
          flush=True)


def base_env(home, tmpdir):
    env = dict(os.environ)
    env["HOME"] = home
    for var in ("TMPDIR", "TMP", "TEMP", "TEMPDIR"):
        env[var] = tmpdir
    env.pop("YLVA_COLOR", None)
    env.pop("YLVA_DEFAULT_USERNAME", None)
    env["LC_ALL"] = "C"
    return env


def run(args, home, tmpdir, timeout=30):
    proc = subprocess.run(
        [BIN] + list(args), env=base_env(home, tmpdir),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=timeout)
    return (proc.returncode,
            proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


def _write(fd, line):
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
    except OSError:
        pass


def _exit_code(status):
    if status is None:
        return None
    if hasattr(os, "waitstatus_to_exitcode"):
        return os.waitstatus_to_exitcode(status)
    if os.WIFSIGNALED(status):
        return -os.WTERMSIG(status)
    return os.WEXITSTATUS(status)


def run_pty(args, home, tmpdir, pre_lines=(), repeat_line=None, timeout=None):
    """Drive one interactive ylva invocation on a real pty.

    Returns (exit_code, output_text).  See the module docstring for why the
    driver re-sends the passphrase instead of waiting for a prompt.
    """
    env = base_env(home, tmpdir)
    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.execve(BIN, [BIN] + list(args), env)
        except Exception:
            os._exit(127)

    out = bytearray()
    status = None
    deadline = time.time() + (timeout or TIMEOUT)
    sent = 0
    next_repeat = time.time() + 0.5
    try:
        while time.time() < deadline:
            if sent < len(pre_lines):
                _write(fd, pre_lines[sent])
                sent += 1
            elif repeat_line is not None and time.time() >= next_repeat:
                _write(fd, repeat_line)
                next_repeat = time.time() + 0.5
            readable, _, _ = select.select([fd], [], [], 0.2)
            if readable:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    chunk = b""
                if not chunk:
                    break
                out += chunk
            try:
                wpid, wstatus = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                wpid, wstatus = pid, None
            if wpid == pid:
                status = wstatus
                break
        # Drain whatever the child wrote before it closed the pty.
        drain_deadline = time.time() + 2.0
        while time.time() < drain_deadline:
            readable, _, _ = select.select([fd], [], [], 0.2)
            if not readable:
                break
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
        if status is None:
            try:
                os.kill(pid, 9)
            except ProcessLookupError:
                pass
            try:
                _, status = os.waitpid(pid, 0)
            except ChildProcessError:
                status = None
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    return _exit_code(status), out.decode("utf-8", "replace")


def main():
    global BIN
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bindir", required=True)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    BIN = os.path.join(args.bindir, "ylva")
    if not os.path.isfile(BIN):
        print("FAIL: %s is missing" % BIN)
        return 1

    tmpdir = tempfile.mkdtemp(prefix="ylva-test-")
    home = os.path.join(tmpdir, "home")
    os.makedirs(home, exist_ok=True)
    empty_home = os.path.join(tmpdir, "empty-home")
    os.makedirs(empty_home, exist_ok=True)
    db = os.path.join(tmpdir, "ylva.db")
    plain = os.path.join(tmpdir, "not-encrypted.bin")
    with open(plain, "wb") as fh:
        fh.write(b"A" * 512)
    holder = os.path.join(home, ".ylva.open_db")

    print("== ylva 1.7 functional suite ==")
    print("   binary=%s\n   workdir=%s\n   HOME=%s" % (BIN, tmpdir, home))

    # ------------------------------------------------------------- F1
    rc, out, err = run(["-v"], home, tmpdir)
    ok = rc == 0 and "Ylva version 1.7" in out
    record("F1", "version flag prints 1.7", ok,
           "rc=%d out=%r" % (rc, out.strip()[:40]))

    # ------------------------------------------------------------- F2
    rc, out, err = run(["-h"], home, tmpdir)
    ok = rc == 0 and "SYNOPSIS" in out and "--gen-password" in out
    record("F2", "help flag prints usage", ok,
           "rc=%d" % rc)

    # ------------------------------------------------------------- F3
    rc, out, err = run([], home, tmpdir)
    ok = rc == 0 and "SYNOPSIS" in out and "OPTIONS" in out
    record("F3", "no arguments prints usage and exits 0", ok, "rc=%d" % rc)

    # ------------------------------------------------------------- F4
    rc, out, err = run(["-g", "24"], home, tmpdir)
    word = out.strip()
    ok = (rc == 0 and len(word) == 24
          and all(ch in PASSWORD_CHARSET for ch in word))
    record("F4", "generate password: exact length and charset", ok,
           "rc=%d len=%d" % (rc, len(word)))

    # ------------------------------------------------------------- F5
    rc, out, err = run(["-g", "0"], home, tmpdir)
    ok = rc == 0 and out == ""
    record("F5", "generate password rejects length < 1", ok,
           "rc=%d out=%r" % (rc, out[:20]))

    # ------------------------------------------------------------- F6
    rc, out, err = run(["-i", db], home, tmpdir)
    head = b""
    size = 0
    if os.path.isfile(db):
        size = os.path.getsize(db)
        with open(db, "rb") as fh:
            head = fh.read(16)
    ok = rc == 0 and os.path.isfile(db) and head == b"SQLite format 3\x00"
    record("F6", "init creates a real SQLite database", ok,
           "rc=%d size=%d" % (rc, size))

    # ------------------------------------------------------------- F7
    rc, out, err = run(["-p"], home, tmpdir)
    ok = rc == 0 and out.strip() == db
    record("F7", "show-db-path reports the active database", ok,
           "rc=%d out=%r" % (rc, out.strip()[:60]))

    # ------------------------------------------------------------- F8
    rc, out, err = run(["-A"], home, tmpdir)
    ok = rc == 0 and "ID: " not in out
    record("F8", "list-all on an empty database", ok, "rc=%d" % rc)

    # ------------------------------------------------------------- F9
    rc, out, err = run(["-l", "1"], home, tmpdir)
    ok = rc == 0 and "Nothing found with id 1" in out
    record("F9", "list-entry on a missing id", ok, "rc=%d" % rc)

    # ------------------------------------------------------------ F10
    rc, out, err = run(["-E"], empty_home, tmpdir)
    ok = rc == 0 and "No decrypted database found" in err
    record("F10", "encrypt refuses when no database is active", ok,
           "rc=%d err=%r" % (rc, err.strip()[:50]))

    # ------------------------------------------------------------ F11
    rc, out, err = run(["-D", plain], empty_home, tmpdir)
    ok = rc == 0 and "File is already decrypted or malformed" in err
    record("F11", "decrypt rejects a plain file", ok,
           "rc=%d err=%r" % (rc, err.strip()[:50]))

    # ------------------------------------------------------------ F12
    rc, out, err = run(["-F", "nothing-matches"], home, tmpdir)
    ok = rc == 0 and "ID: " not in out
    record("F12", "regex search on an empty database", ok, "rc=%d" % rc)

    # ------------------------------------------------------------ F13
    rc, out, err = run(["-t"], home, tmpdir)
    ok = rc == 0 and "ID: " not in out
    record("F13", "show-latest on an empty database", ok, "rc=%d" % rc)

    # ------------------------------------------------------------ F14
    rc, out, err = run(["-q", "nothing-matches"], home, tmpdir)
    ok = rc == 0 and "ID: " not in out
    record("F14", "quick search on an empty database", ok, "rc=%d" % rc)

    # ------------------------------------------------------------ F15
    # Interactive add.  An empty passphrase makes upstream generate a
    # 20-character password internally, so this also exercises the generator
    # through the interactive path.
    rc, text = run_pty(
        ["-a"], home, tmpdir,
        pre_lines=["Bank Account", "alice", "https://bank.example", "test note"],
        repeat_line="")
    ok = (rc == 0 and "Title: " in text
          and "Password (empty to generate new): " in text)
    record("F15", "interactive add stores a new entry", ok,
           "rc=%s prompts=%s" % (rc, "Title: " in text))

    # ------------------------------------------------------------ F16
    rc, out, err = run(["--show-passwords", "-A"], home, tmpdir)
    m = re.search(r"^Password: (\S+)$", out, re.M)
    stored = m.group(1) if m else ""
    ok = (rc == 0 and "ID: 1" in out and "Title: Bank Account" in out
          and "User: alice" in out and "Url: https://bank.example" in out
          and "Notes: test note" in out
          and len(stored) == 20
          and all(ch in PASSWORD_CHARSET for ch in stored))
    record("F16", "list-all shows the entry and its generated password", ok,
           "rc=%d password_len=%d" % (rc, len(stored)))

    # ------------------------------------------------------------ F17
    rc, out, err = run(["-f", "Bank"], home, tmpdir)
    ok = rc == 0 and "Title: Bank Account" in out and "Password: **********" in out
    record("F17", "LIKE search finds the entry (password masked)", ok,
           "rc=%d" % rc)

    # ------------------------------------------------------------ F18
    rc, out, err = run(["-F", "^Bank.*Account$"], home, tmpdir)
    ok = rc == 0 and "Title: Bank Account" in out
    record("F18", "regex search finds the entry", ok, "rc=%d" % rc)

    # ------------------------------------------------------------ F19
    rc, out, err = run(["--show-passwords", "-l", "1"], home, tmpdir)
    ok = (rc == 0 and "ID: 1" in out and "Title: Bank Account" in out
          and "User: alice" in out and "Url: https://bank.example" in out
          and "Notes: test note" in out
          and re.search(r"^Modified: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
                        out, re.M) is not None)
    record("F19", "list-entry shows every stored field", ok, "rc=%d" % rc)

    # ------------------------------------------------------------ F20
    rc, out, err = run(["-q", "Bank"], home, tmpdir)
    ok = rc == 0 and "Password: %s" % stored in out and "*" * 10 not in out
    record("F20", "quick search prints the stored password", ok, "rc=%d" % rc)

    # ------------------------------------------------------------ F21
    # Encryption round trip: -E then -D must preserve both the plaintext size
    # (exactly ENC_OVERHEAD bytes larger while encrypted) and the entry data.
    size_before = os.path.getsize(db)
    rc, text = run_pty(["-E"], home, tmpdir, repeat_line=SECRET)
    encrypted_size = os.path.getsize(db)
    rc_p, out_p, err_p = run(["-p"], home, tmpdir)
    enc_ok = (rc == 0 and "Password again: " in text
              and encrypted_size == size_before + ENC_OVERHEAD
              and "No decrypted database exist" in err_p)
    # A wrong passphrase must be rejected by the HMAC-SHA512 check without
    # touching the ciphertext.
    rc_w, text_w = run_pty(["-D", db], home, tmpdir,
                           repeat_line="not the passphrase")
    wrong_ok = (rc_w == 0 and "Invalid password or tampered data" in text_w
                and os.path.getsize(db) == encrypted_size
                and "No decrypted database exist" in run(["-p"], home, tmpdir)[2])
    rc_d, text_d = run_pty(["-D", db], home, tmpdir, repeat_line=SECRET)
    rc_a, out_a, _ = run(["--show-passwords", "-A"], home, tmpdir)
    dec_ok = (rc_d == 0 and os.path.getsize(db) == size_before
              and "Title: Bank Account" in out_a
              and "Password: %s" % stored in out_a)
    record("F21", "encrypt/decrypt round trip preserves the entry",
           enc_ok and wrong_ok and dec_ok,
           "enc=%s wrong_pw=%s dec=%s size=%d->%d->%d"
           % (enc_ok, wrong_ok, dec_ok, size_before, encrypted_size,
              os.path.getsize(db)))

    # ------------------------------------------------------------ H1
    # HarmonyOS sandbox: the "active database" pointer must live in $HOME.
    content = ""
    if os.path.isfile(holder):
        with open(holder, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    ok = os.path.isfile(holder) and content.strip() == db
    record("H1", "sandbox HOME holds the active-database pointer", ok,
           "$HOME/.ylva.open_db content=%r" % content.strip()[:60])

    # ------------------------------------------------------------ H2
    # HMDFS permission normalisation: the database must stay unreadable for
    # "other" even after the platform normalises the 0600 that
    # set_file_owner_rw() asks for.
    mode = stat.S_IMODE(os.stat(db).st_mode)
    ok = (mode & 0o600) == 0o600 and (mode & DB_MODE_CHECK) == 0
    record("H2", "database mode is owner-rw and closed to other", ok,
           "mode=0o%o" % mode)

    # ------------------------------------------------------------ H3
    # SQLite datetime('now','localtime') must resolve on OHOS: the stamp has
    # to be a real local timestamp close to today, not 1970 or an empty value.
    m = re.search(r"^Modified: (\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$",
                  out_a, re.M)
    stamp_ok = False
    if m:
        y, mo, d = (int(m.group(i)) for i in (1, 2, 3))
        today = time.gmtime()
        try:
            delta = abs((time.mktime((y, mo, d, 0, 0, 0, 0, 0, 0))
                         - time.mktime((today.tm_year, today.tm_mon,
                                        today.tm_mday, 0, 0, 0, 0, 0, 0))))
        except (OverflowError, ValueError):
            delta = 10 ** 9
        stamp_ok = delta <= 2 * 86400
    record("H3", "SQLite localtime stamps resolve on OHOS", stamp_ok,
           "stamp=%r" % (m.group(0) if m else None))

    # ------------------------------------------------------------ H4
    # QR rendering: qr.c prints U+2585 (UTF-8 e2 96 85) half blocks, so the
    # output proves both the libqrcodegen link and correct UTF-8 handling.
    rc, out_q, err_q = run(["--show-qrcode", "-l", "1"], home, tmpdir)
    blocks = out_q.count("\u2585\u2585")
    ok = (rc == 0 and blocks >= 100
          and "Unable to generate QR code" not in out_q + err_q)
    record("H4", "entry renders as a UTF-8 half-block QR code", ok,
           "rc=%d blocks=%d" % (rc, blocks))

    print("\nRESULT: passed=%d failed=%d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("failed items:")
        for item in FAIL:
            print("  - %s" % item)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
