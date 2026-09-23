#!/usr/bin/env python3
"""Platform-specific (HarmonyOS) tests for crack 5.0a packaged binaries.

Upstream 5.0a ships no test suite (N=0: no make test/check target exists
anywhere in the Makefile tree), so we exercise the packaged tools on the
target profile:

1. dawg/xdawg roundtrip — pack a wordlist into the DAWG dictionary
   format and unpack it back.
2. cracker functional run — assemble the minimal upstream runtime the
   `Crack` driver would create (conf/dictrun.conf with the pass-through
   rule, a run/dict/1.dwg.gz dictionary built with the packaged dawg,
   scripts/{kickdict,smartcat,crack-sort} on PATH), feed a crypt(3)
   DES ciphertext of the weak password "123456" and assert the cracker
   recovers it.
"""
import os
import shutil
import stat
import subprocess
import sys
import tempfile

# Minimal upstream shell helpers (verbatim from scripts/) needed by the
# cracker dictionary pipeline. smartcat decompresses *.dwg.gz via xdawg;
# crack-sort and kickdict wrappers are thin exec() layers.
SMARTCAT = r'''#!/bin/sh
TMPDIR=${TMPDIR:-/tmp}
PATH="/usr/bin:/bin:$PATH"
PCATF=$TMPDIR/pcat$$.z
if [ "$1" = "" ]
then
	echo "Usage: $0 filename.ext1.ext2.ext3 ..."
	exit 1
elif [ "$1" != "-backend" ]
then
	for file in $*
	do
		$0 -backend $file < $file
	done
	exit 0
fi
shift
file=$1
case $file in
	"")
		echo "$0: error: ran off end of filename" 1>&2
		exit 1 ;;
	*.gz)
		exec gzip -d |
			$0 -backend `basename $file .gz` ;;
	*.dwg)
		exec xdawg |
			$0 -backend `basename $file .dwg` ;;
	*)
		exec cat ;;
esac
'''

CRACK_SORT = '#!/bin/sh\nexec sort $*\n'

WORKDIR = None


def run(cmd, cwd, stdin_data=None, timeout=600):
    if isinstance(stdin_data, str):
        stdin_data = stdin_data.encode()
    proc = subprocess.run(
        cmd, cwd=cwd, input=stdin_data, capture_output=True,
        timeout=timeout,
    )
    proc.stdout = proc.stdout.decode(errors="replace")
    proc.stderr = proc.stderr.decode(errors="replace")
    return proc


def write_script(path, content):
    with open(path, "w") as fh:
        fh.write(content)
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)


def test_dawg_roundtrip(bindir):
    """DAWG pack/unpack roundtrip on a known wordlist."""
    words = ["apple", "banana", "orange", "grape", "password",
             "123456", "qwerty", "silva"]
    src = os.path.join(WORKDIR, "roundtrip-words.txt")
    packed = src + ".dwg"
    with open(src, "w") as fh:
        fh.write("\n".join(words) + "\n")

    r = run([os.path.join(bindir, "dawg"), src], WORKDIR)
    if r.returncode != 0:
        print("dawg pack failed:", r.stdout, r.stderr, file=sys.stderr)
        return False
    if not os.path.exists(packed):
        print("dawg did not create", packed, file=sys.stderr)
        return False

    with open(packed, "rb") as fh:
        blob = fh.read()
    r = run([os.path.join(bindir, "xdawg")], WORKDIR, stdin_data=blob)
    if r.returncode != 0:
        print("xdawg unpack failed:", r.stdout, r.stderr, file=sys.stderr)
        return False
    recovered = [l for l in r.stdout.splitlines() if l.strip()]
    missing = [w for w in words if w not in recovered]
    if missing:
        print("roundtrip missing words:", missing, file=sys.stderr)
        return False
    print(f"dawg/xdawg roundtrip OK ({len(recovered)} words recovered)")
    return True


def test_cracker_recovers_weak_password(bindir):
    """Full dictionary run: cracker must recover password 123456.

    Builds the minimal upstream working set (conf/ + run/dict/ + script
    helpers on PATH) exactly as the upstream Crack driver would, using
    the packaged dawg to compress the test dictionary, then feeds the
    SPF stream 'D:ab:ab01FAX.bQRSU:user1:...' (crypt("123456","ab")).
    """
    # crypt(3) DES hash of "123456" with salt "ab" (musl/glibc agree)
    ciphertext = "ab01FAX.bQRSU"
    spf = f"D:ab:{ciphertext}:user1:User One:/bin/sh\n"

    home = os.path.join(WORKDIR, "runhome")
    os.makedirs(os.path.join(home, "conf"), exist_ok=True)
    os.makedirs(os.path.join(home, "run", "dict"), exist_ok=True)
    os.makedirs(os.path.join(home, "scripts"), exist_ok=True)

    # conf/dictrun.conf: dictionary group "1" with rules.fast
    # (pass-through rule ':' first, mirroring upstream ordering)
    with open(os.path.join(home, "conf", "dictrun.conf"), "w") as fh:
        fh.write("1:conf/rules.fast\n")

    # conf/rules.fast with just the pass-through rule
    with open(os.path.join(home, "conf", "rules.fast"), "w") as fh:
        fh.write(":\n")

    # Build the dictionary group with the packaged dawg:
    # words.txt -> sort/uniq -> 1.dwg -> gzip -> run/dict/1.dwg.gz
    words = ["123456", "password", "qwerty", "letmein", "abc123",
             "admin", "root", "silva"]
    raw = os.path.join(home, "words.txt")
    with open(raw, "w") as fh:
        fh.write("\n".join(words) + "\n")
    r = run([os.path.join(bindir, "dawg"), raw], home)
    if r.returncode != 0 or not os.path.exists(raw + ".dwg"):
        print("dawg failed to build test dictionary:", r.stdout, r.stderr,
              file=sys.stderr)
        return False
    shutil.move(raw + ".dwg", os.path.join(home, "run", "dict", "1.dwg"))
    with open(os.path.join(home, "run", "dict", "1.dwg"), "rb") as fin, \
         open(os.path.join(home, "run", "dict", "1.dwg.gz"), "wb") as fout:
        import gzip
        with gzip.GzipFile(fileobj=fout, mode="wb", mtime=0) as gz:
            shutil.copyfileobj(fin, gz)

    # Script helpers (upstream scripts/, trimmed to what this pipeline hits)
    write_script(os.path.join(home, "scripts", "smartcat"), SMARTCAT)
    write_script(os.path.join(home, "scripts", "crack-sort"), CRACK_SORT)

    env = dict(os.environ)
    env["PATH"] = (bindir + ":" + os.path.join(home, "scripts")
                   + ":" + env.get("PATH", ""))
    env["TMPDIR"] = WORKDIR

    cracker = os.path.join(bindir, "cracker")
    r = subprocess.run([cracker], cwd=home, input=spf, capture_output=True,
                       text=True, timeout=600, env=env)
    out = r.stdout
    if "123456" not in out or ciphertext not in out:
        print("cracker did not recover the weak password", file=sys.stderr)
        print("stdout tail:", out[-3000:], file=sys.stderr)
        print("stderr tail:", r.stderr[-2000:], file=sys.stderr)
        return False
    print("cracker recovered weak password 123456 from DES ciphertext OK")
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_crack.py <bindir>", file=sys.stderr)
        return 2
    bindir = sys.argv[1]

    global WORKDIR
    WORKDIR = tempfile.mkdtemp(prefix="crack-test-")
    ok = True
    try:
        ok = test_dawg_roundtrip(bindir) and ok
        ok = test_cracker_recovers_weak_password(bindir) and ok
    finally:
        shutil.rmtree(WORKDIR, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
