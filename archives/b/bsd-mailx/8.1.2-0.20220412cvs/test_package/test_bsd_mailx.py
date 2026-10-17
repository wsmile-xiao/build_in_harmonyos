#!/usr/bin/env python3
"""Functional tests for the bsd-mailx command line tool.

Exercises the installed bsd-mailx binary end-to-end:
  1. usage text is printed for an unknown option
  2. reading an empty mailbox prints "No mail for ..."
  3. reading a crafted mailbox file lists and prints messages
  4. version banner is emitted when reading a mailbox
"""
import os
import subprocess
import sys
import tempfile

executable = sys.argv[1]


def run(args, input_text=None, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [executable] + args,
        input=input_text,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


asserts = 0


def check(cond, msg):
    global asserts
    assert cond, msg
    asserts += 1


# --- test 1: usage text on unknown option ------------------------------------
r = run(["--help"])
usage = r.stderr + r.stdout
check("usage:" in usage, f"usage text missing: {usage}")
check("-s subject" in usage, f"send mode options missing: {usage}")

# --- test 2: empty mailbox ---------------------------------------------------
r = run(["-n"], env_extra={"MAIL": "/dev/null"})
check("No mail for" in (r.stdout + r.stderr), f"empty mailbox msg missing: {r.stdout}{r.stderr}")

# --- test 3+4: crafted mailbox read/list/print -------------------------------
with tempfile.TemporaryDirectory() as td:
    mbox = os.path.join(td, "inbox")
    with open(mbox, "w") as f:
        f.write(
            "From alice@example.com Thu Jan  1 00:00:00 2026\n"
            "Subject: Hello World\n"
            "Date: Thu, 1 Jan 2026 00:00:00 +0000\n"
            "From: Alice <alice@example.com>\n"
            "To: bob@example.com\n"
            "\n"
            "This is the message body.\n"
            "Line two.\n"
        )
    r = run(["-n", "-f", mbox], input_text="h\np\nq\n")
    out = r.stdout + r.stderr
    check(r.returncode == 0, f"read mailbox rc={r.returncode}: {out}")
    check("Mail version 8.1.2" in out, f"version banner missing: {out}")
    check("1 message" in out, f"message count missing: {out}")
    check("Hello World" in out, f"subject missing from list: {out}")
    check("This is the message body." in out, f"message body missing: {out}")
    check("complete" in out, f"clean exit missing: {out}")

print(f"bsd-mailx functional tests passed ({asserts} assertions)")
