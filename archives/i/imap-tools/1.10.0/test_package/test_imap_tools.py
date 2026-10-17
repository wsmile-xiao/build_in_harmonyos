#!/usr/bin/env python3
"""Conan test_package for imap-tools — verifies module + real offline API.

R34: imap_tools/ module files present in site-packages and a real offline
API call chain works (query builder + MailMessage.from_bytes parsing +
imap_utf7 round trip) — no live IMAP server needed.
"""
import os
import subprocess
import sys

TEST_SCRIPT = r'''
import sys
sys.path.insert(0, "{site}")

import imap_tools
from imap_tools import MailBox, MailBoxTls, MailBoxUnencrypted, MailMessage, A, AND, OR, NOT
from imap_tools.query import H, U
from imap_tools.imap_utf7 import utf7_encode, utf7_decode

# 真实调用 1：查询构建器（Header 需经 A(header=...) 接入搜索条件）
q = AND(AND(A(seen=True), OR(A(flagged=False), A(draft=False))),
        NOT(A(deleted=True)), A(header=H('from', 'test@lisa.com')))
qs = str(q)
assert "SEEN" in qs and "HEADER" in qs and "UNFLAGGED" in qs, qs
print("query builder OK:", qs[:70])

# 真实调用 2：邮件解析（MailMessage.from_bytes 离线解析真实 RFC822）
raw = (b"From: Mikel <test@lindsaar.net>\n"
       b"To: Mikel <raasdnil@gmail.com>\n"
       b"Subject: _append_\n"
       b"Date: Sat, 22 Nov 2008 11:04:59 +1100\n"
       b"Content-Type: text/plain; charset=US-ASCII\n"
       b"\nPlain email.\n")
msg = MailMessage.from_bytes(raw)
assert msg.subject == "_append_", msg.subject
assert msg.from_ == "test@lindsaar.net", msg.from_
assert "Plain email." in msg.text
print("MailMessage.from_bytes OK:", msg.subject, msg.from_)

# 真实调用 3：IMAP UTF-7 编解码往返
enc = utf7_encode("Might & Magic")
dec = utf7_decode(enc)
assert dec == "Might & Magic", (enc, dec)
print("imap_utf7 roundtrip OK:", enc, "->", dec)

# 版本与公开符号
assert imap_tools.__version__ == "1.10.0", imap_tools.__version__
for cls in (MailBox, MailBoxTls, MailBoxUnencrypted):
    assert cls is not None
print("OK: imap-tools", imap_tools.__version__, "import + real offline API works")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    if not os.path.isdir(os.path.join(site, "imap_tools")):
        print(f"FAIL: imap_tools module missing: {site}", file=sys.stderr)
        return 1
    required = ["__init__.py", "consts.py", "errors.py", "folder.py",
                "idle.py", "imap_utf7.py", "mailbox.py", "message.py",
                "query.py", "utils.py", "py.typed"]
    missing = [f for f in required
               if not os.path.isfile(os.path.join(site, "imap_tools", f))]
    if missing:
        print(f"FAIL: imap_tools files missing: {missing}", file=sys.stderr)
        return 1
    r = subprocess.run(
        [sys.executable, "-c", TEST_SCRIPT.replace("{site}", site)],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: import/run: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: imap-tools module + real offline API usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
