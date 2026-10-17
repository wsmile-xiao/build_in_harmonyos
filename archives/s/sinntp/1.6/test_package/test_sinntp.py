#!/usr/bin/env python3
"""Consumer test for the packaged sinntp 1.6 scripts and Python modules.

Covers the installed payload from the consumer perspective (10 checks):
split_host variants, join_lines variants, plugin helpers, and the
installed sinntp entry point (--version/--help).
"""

import email.message
import os
import subprocess
import sys


def _package_roots():
    roots = []
    for var in ("SINNTP_PACKAGE_ROOT", "PYTHONPATH"):
        value = os.environ.get(var, "")
        for entry in value.split(os.pathsep):
            if entry:
                roots.append(entry)
    roots.append(os.path.join(os.path.dirname(__file__)))
    return roots


for root in _package_roots():
    if root and root not in sys.path:
        sys.path.insert(0, root)

import plugins
import utils

checks = []


def check(name, actual, expected):
    assert actual == expected, "%s: got %r want %r" % (name, actual, expected)
    print("check %s ... ok" % name)
    checks.append(name)


# 1-4: host parsing (core of --server handling)
check("split_host/domain", utils.split_host("news.example.com", 119), ("news.example.com", 119))
check("split_host/domain_port", utils.split_host("news.example.com:42", 119), ("news.example.com", 42))
check("split_host/ipv4", utils.split_host("192.0.2.10", 119), ("192.0.2.10", 119))
check("split_host/ipv6_port", utils.split_host("[2001:db8::1]:42", 119), ("2001:db8::1", 42))

# 5-6: mbox body framing used by pull/push
check("join_lines/empty", utils.join_lines([]), b"\n")
check(
    "join_lines/trailing_lf",
    utils.join_lines([b"eggs", b"bacon", b"spam"]),
    b"eggs\nbacon\nspam\n",
)

# 7: plugin pipeline — mimify adds a default Content-Type
msg = email.message.Message()
msg["From"] = "a@example.com"
out = plugins.mimify(message=msg)
assert out["Content-Type"] == "text/plain; charset=US-ASCII", out.items()
print("check plugins/mimify ... ok")
checks.append("plugins/mimify")

# 8: plugin pipeline — strip_headers removes the requested header
msg2 = email.message.Message()
msg2["To"] = "b@example.com"
msg2["Subject"] = "hello"
out2 = plugins.strip_headers(headers="To", message=msg2)
assert "To" not in out2, list(out2.items())
assert out2["Subject"] == "hello"
print("check plugins/strip_headers ... ok")
checks.append("plugins/strip_headers")

# 9-10: installed entry point really runs (version + help)
candidates = []
for var in ("SINNTP_PACKAGE_ROOT",):
    root = os.environ.get(var, "")
    if root:
        candidates.append(os.path.join(os.path.dirname(root), "..", "bin", "sinntp"))
path_env = os.environ.get("PATH", "")
for entry in path_env.split(os.pathsep):
    candidates.append(os.path.join(entry, "sinntp"))
candidates.append(os.path.join(os.path.dirname(__file__), "sinntp"))
sinntp = next((c for c in candidates if c and os.path.isfile(c)), None)
assert sinntp, "installed sinntp entry point not found"
proc_version = subprocess.run(
    [sys.executable, sinntp, "--version"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
assert proc_version.returncode == 0, proc_version.stdout[-1000:]
assert "1.6" in proc_version.stdout, proc_version.stdout[-1000:]
print("check sinntp/--version ... ok")
checks.append("sinntp/--version")

proc_help = subprocess.run(
    [sys.executable, sinntp, "--help"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
assert proc_help.returncode == 0, proc_help.stdout[-1000:]
# Upstream builds help with explicit usage from subcommand docstrings
# (nntp-pull/push/get/list), so the text contains those command names and
# option flags rather than the word "sinntp" itself.
help_lower = proc_help.stdout.lower()
assert "usage" in help_lower, proc_help.stdout[-1000:]
assert "nntp-pull" in help_lower, proc_help.stdout[-1000:]
assert "nntp-push" in help_lower, proc_help.stdout[-1000:]
print("check sinntp/--help ... ok")
checks.append("sinntp/--help")

assert len(checks) == 10, checks
print("sinntp 1.6 consumer: 10/10 PASS")
