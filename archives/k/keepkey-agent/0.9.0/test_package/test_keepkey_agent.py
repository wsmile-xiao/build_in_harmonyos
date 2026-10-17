#!/usr/bin/env python3
"""Conan test_package for keepkey-agent 0.9.0 — R34 consumer verification.

HARD: the packaged `keepkey_agent` shell module + its full Python runtime
closure (libagent / keepkeylib / ed25519 shim + pure25519 / ecdsa / semver /
protobuf 3.15.4 / mnemonic) are present in site-packages and functional.

Substantive checks (all device-independent — real KeepKey USB hardware is
not available in CI):
1. import chain: keepkey_agent -> libagent(.ssh/.gpg/.device.keepkey) ->
   keepkeylib (protobuf protocol layer), KeepKey device class visible
2. `keepkey-agent` console entry script exists in bin/ and its --help
   runs the full argparse chain
3. KeepKey device protocol wire round-trip (protobuf Ping message)
4. NIST256p SSH signature verify closed loop (KeepKey primary curve —
   parse_pubkey -> device-style raw r||s signature -> verifier)
5. ED25519 SSH signature verify closed loop (via the pure-Python
   ed25519 shim backed by pure25519), incl. tampered-signature rejection
"""
import os
import subprocess
import sys

SMOKE_PY = r'''
import struct
import sys

failures = []


def check(name, fn):
    try:
        fn()
        print("PASS:", name)
    except Exception as e:
        failures.append((name, repr(e)))
        print("FAIL:", name, "->", repr(e))


def t_import_chain():
    import keepkey_agent
    import libagent, libagent.ssh, libagent.gpg
    from libagent.device import keepkey as kdev
    from libagent.device.keepkey import KeepKey
    assert callable(keepkey_agent.ssh_agent)
    assert kdev.KeepKey.required_version == ">=1.0.4"


def t_keepkeylib_protocol():
    import keepkeylib.client
    import keepkeylib.messages_pb2 as m
    from keepkeylib.types_pb2 import IdentityType
    from keepkeylib.transport_fake import FakeTransport
    assert callable(FakeTransport)
    ident = IdentityType(proto="ssh", user="u", host="h", index=0)
    assert ident.proto == "ssh"
    msg = m.Ping(message="hello", button_protection=True)
    raw = msg.SerializeToString()
    back = m.Ping()
    back.ParseFromString(raw)
    assert back.message == "hello" and back.button_protection


def t_nist256_sign_verify():
    from libagent import formats
    import ecdsa, ecdsa.util, hashlib

    def frame(b):
        return struct.pack(">I", len(b)) + b

    sk = ecdsa.SigningKey.generate(curve=ecdsa.NIST256p)
    vk = sk.get_verifying_key()
    blob = (frame(formats.SSH_NIST256_KEY_TYPE) +
            frame(formats.SSH_NIST256_CURVE_NAME) +
            frame(formats.SSH_NIST256_DER_OCTET + vk.to_string()))
    r = formats.parse_pubkey(blob)
    assert r["curve"] == formats.CURVE_NIST256
    msg = b"keepkey-agent-consumer-test"
    sig = sk.sign(msg, sigencode=ecdsa.util.sigencode_string,
                  hashfunc=hashlib.sha256)
    ssh_sig = r["verifier"](sig, msg)
    assert len(ssh_sig) == 74


def t_ed25519_sign_verify():
    from libagent import formats
    import ed25519

    def frame(b):
        return struct.pack(">I", len(b)) + b

    seed = bytes(range(32))
    sk = ed25519.SigningKey(seed)
    vk = sk.get_verifying_key()
    blob = frame(formats.SSH_ED25519_KEY_TYPE) + frame(vk.to_bytes())
    r = formats.parse_pubkey(blob)
    assert r["curve"] == formats.CURVE_ED25519
    msg = b"keepkey-agent-consumer-test"
    sig = sk.sign(msg)
    r["verifier"](sig, msg)
    # 篡改签名必须被拒——"接受即失败"的判定移出 try 块
    # （raise 放 try 内会被同一个 except 吞掉，形成永真断言）
    rejected = False
    try:
        r["verifier"](b"\x00" + sig[1:], msg)
    except Exception:
        rejected = True
    assert rejected, "tampered sig accepted"


check("import_chain", t_import_chain)
check("keepkeylib_protocol (protobuf wire round-trip)",
      t_keepkeylib_protocol)
check("nist256_sign_verify (SSH 主曲线闭环)", t_nist256_sign_verify)
check("ed25519_sign_verify (shim+pure25519 闭环)", t_ed25519_sign_verify)

if failures:
    print("TOTAL: %d FAILED" % len(failures))
    sys.exit(1)
print("TOTAL: 4/4 PASSED")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]

    # 1. HARD: 包核心文件存在
    lib_root = os.path.join(pkg, "lib")
    site = None
    for py in os.listdir(lib_root):
        cand = os.path.join(lib_root, py, "site-packages")
        if os.path.isdir(cand) and os.path.isfile(
                os.path.join(cand, "keepkey_agent.py")):
            site = cand
            break
    if not site:
        print(f"FAIL: keepkey_agent module not found under {lib_root}",
              file=sys.stderr)
        return 1

    required = [
        "keepkey_agent.py", "ed25519.py",
        os.path.join("libagent", "__init__.py"),
        os.path.join("libagent", "device", "keepkey.py"),
        os.path.join("keepkeylib", "client.py"),
        os.path.join("keepkeylib", "messages_pb2.py"),
        os.path.join("pure25519", "eddsa.py"),
        os.path.join("ecdsa", "keys.py"),
        os.path.join("semver", "__init__.py"),
        os.path.join("mnemonic", "__init__.py"),
        os.path.join("google", "protobuf", "__init__.py"),
    ]
    missing = [f for f in required
               if not os.path.isfile(os.path.join(site, f))]
    if missing:
        print(f"FAIL: missing files {missing} in {site}", file=sys.stderr)
        return 1

    # 2. HARD: keepkey-agent 入口脚本存在且 --help 可跑（argparse 全链）
    entry = os.path.join(pkg, "bin", "keepkey-agent")
    if not os.path.isfile(entry):
        print(f"FAIL: entry script missing: {entry}", file=sys.stderr)
        return 1
    r = subprocess.run([sys.executable, entry, "--help"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or "identity" not in (r.stdout or ""):
        print(f"FAIL: entry --help rc={r.returncode}", file=sys.stderr)
        print((r.stdout or "")[-500:], file=sys.stderr)
        print((r.stderr or "")[-500:], file=sys.stderr)
        return 1
    print("PASS: keepkey-agent entry --help (argparse full chain)")

    # 3. 功能性闭环（子进程隔离——smoke 脚本写到 $TMPDIR）
    import tempfile
    script = os.path.join(tempfile.gettempdir(),
                          "keepkey-agent-smoke-test.py")
    with open(script, "w") as f:
        f.write(SMOKE_PY)
    r = subprocess.run([sys.executable, script],
                       capture_output=True, text=True, timeout=600,
                       env={**os.environ, "PYTHONPATH": site})
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        print("FAIL: smoke functional test", file=sys.stderr)
        return 1
    print("PASS: keepkey-agent consumer verification (R34)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
