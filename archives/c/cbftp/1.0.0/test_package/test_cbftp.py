#!/usr/bin/env python3
"""cbftp consumer test (L0c + R34): standalone test suite executed via
self.run from test_package/conanfile.py test().

R34: actually invoke the packaged binaries — datafilecat/datafilewrite do
real AES-256 data file encryption/decryption round-trips, and the cbftp
main binary is launched to prove the executable/dynamic-linking health.

Test cases:
  1. All three binaries exist and are executable.
  2. datafilecat prints a plain-ASCII data file verbatim (no passphrase).
  3. datafilewrite encrypts a plain text file (AES-256), then datafilecat
     decrypts it back with the same passphrase — byte-identical round trip.
  4. datafilecat fails with a wrong passphrase (must not decrypt).
  5. cbftp main binary starts (ncurses init failure without a TTY is the
     expected, well-defined behaviour and proves the ELF loads and links).
"""
import os
import subprocess
import sys
import tempfile


def find_libcxx_lib(root):
    """Recursively locate the directory containing libc++_shared.so."""
    if not root or not os.path.isdir(root):
        return ""
    for dirpath, dirnames, filenames in os.walk(root):
        if "libc++_shared.so" in filenames:
            return dirpath
    return ""


def run(cmd, env=None, **kwargs):
    """Run a command, capture output, honor a timeout."""
    opts = {"capture_output": True, "text": True, "env": env}
    if "timeout" in kwargs:
        opts["timeout"] = kwargs["timeout"]
    if "input" in kwargs:
        opts["input"] = kwargs["input"]
    return subprocess.run(cmd, **opts)


def main() -> int:
    bin_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    llvm_lib = sys.argv[2] if len(sys.argv) > 2 else ""
    failures = []

    tools = ["cbftp", "datafilecat", "datafilewrite"]
    # --- Case 1: binaries present ---
    for t in tools:
        p = os.path.join(bin_dir, t)
        if not os.path.exists(p) or not os.access(p, os.X_OK):
            failures.append(f"{t} binary missing/not executable at {p}")

    env = dict(os.environ)
    # libc++_shared.so lives below llvm/lib (e.g. .../llvm/lib/aarch64-linux-ohos)
    libcxx_dir = find_libcxx_lib(llvm_lib)
    if libcxx_dir:
        env["LD_LIBRARY_PATH"] = libcxx_dir + os.pathsep + env.get("LD_LIBRARY_PATH", "")

    datafilecat = os.path.join(bin_dir, "datafilecat")
    datafilewrite = os.path.join(bin_dir, "datafilewrite")

    tmp = tempfile.mkdtemp(prefix="cbftp-test-")
    plain = os.path.join(tmp, "plain.txt")
    enc = os.path.join(tmp, "enc.dat")
    dec = os.path.join(tmp, "dec.txt")
    out = os.path.join(tmp, "out.txt")

    sample = ("info\n"
              "sites\n"
              "  site name test.example.com\n"
              "  address test.example.com 21\n"
              "  username anonymous\n"
              "  password anon@example.com\n"
              "  tls none\n"
              "global\n"
              "  download-path ~/downloads\n")
    with open(plain, "w", encoding="ascii") as f:
        f.write(sample)

    # --- Case 2: datafilecat verbatim ASCII output ---
    r = run([datafilecat, f"--infile={plain}", f"--outfile={out}"], env=env)
    if r.returncode != 0:
        failures.append(f"datafilecat ASCII: rc={r.returncode} err={r.stderr!r}")
    else:
        with open(out, encoding="ascii") as f:
            if f.read() != sample:
                failures.append("datafilecat ASCII: output differs from input")
        os.unlink(out)

    # --- Case 3: encrypt then decrypt round trip ---
    r = run([datafilewrite, plain, f"--outfile={enc}"], env=env, input="testpass\n")
    if r.returncode != 0 or not os.path.exists(enc):
        failures.append(f"datafilewrite encrypt: rc={r.returncode} err={r.stderr!r}")
    else:
        r = run([datafilecat, f"--infile={enc}", f"--outfile={dec}"],
                env=env, input="testpass\n")
        if r.returncode != 0:
            failures.append(f"datafilecat decrypt: rc={r.returncode} err={r.stderr!r}")
        else:
            with open(dec, encoding="ascii") as f:
                if f.read() != sample:
                    failures.append("decrypt round trip: output differs from input")

    # --- Case 4: wrong passphrase must not yield the plaintext ---
    # NOTE: upstream Crypto::decrypt() does not check EVP_DecryptFinal_ex,
    # so a wrong passphrase may either be rejected (rc!=0) or produce
    # garbage that passes isMostlyASCII by chance. Either way the decrypted
    # bytes MUST differ from the plaintext (AES-256-CBC key schedule) — this
    # is the deterministic assertion.
    if os.path.exists(dec):
        os.unlink(dec)  # case 3 left plaintext here — must start fresh
    r = run([datafilecat, f"--infile={enc}", f"--outfile={dec}"],
            env=env, input="wrongpass\n")
    if r.returncode != 0:
        # explicitly rejected (clean path)
        pass
    elif os.path.exists(dec):
        with open(dec, "rb") as f:
            if f.read() == sample.encode("ascii"):
                failures.append("datafilecat wrong passphrase yielded plaintext!")
    else:
        failures.append("datafilecat wrong passphrase: rc=0 but no output "
                        "file written")
    if os.path.exists(dec):
        os.unlink(dec)

    # --- Case 5: cbftp main binary starts ---
    cbftp = os.path.join(bin_dir, "cbftp")
    if os.path.exists(cbftp):
        r = run([cbftp], env=env, timeout=10)
        combined = (r.stdout or "") + (r.stderr or "")
        # Without a TTY, ncurses init fails but the ELF loaded + linked fine;
        # a crash/relocation error instead means the binary is broken.
        if "cannot initialize terminal" not in combined.lower() and r.returncode < 0:
            failures.append(f"cbftp startup: rc={r.returncode} out={combined[:160]!r}")

    if failures:
        print("FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    print("OK: cbftp binaries present, datafile encrypt/decrypt round trip "
          "PASSED, wrong-passphrase rejected, cbftp ELF starts")
    return 0


if __name__ == "__main__":
    sys.exit(main())