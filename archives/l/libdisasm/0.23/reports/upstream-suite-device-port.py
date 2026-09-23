#!/usr/bin/env python3
"""Device port of the upstream libdisasm test suite.

Upstream `make check` runs test/run-test.sh, which pipes test/ia32_test_insn.S
through GNU `as --32`, `objdump -h` and `perl` (asmdisasm.pl) -- none of which
exist on the OHOS device. This port keeps the comparison semantics equivalent
to run-test.sh + asmdisasm.pl and only substitutes the environment tools:

    as --32        -> clang --target=i386-linux-gnu -c   (integrated assembler)
    objdump -h     -> llvm-readobj --sections           (.text Offset/Size)
    perl driver    -> this script                       (same regexes/normalization)

Comparison accounting is replicated from run-test.sh:
    INPUT  = expected text extracted from the ORIGINAL .S comments (lines
             without a comment compare against themselves), lowercased, one
             trailing space stripped
    OUTPUT = x86dis att-syntax lines with the "ADDR BB BB " prefix stripped
    BAD    = INPUT-side deletions in a unified diff (unexpected mismatches)
    OKAY   = total - BAD - XFAIL ; exit 1 when BAD > 0

Because the 2003-era test data predates stricter assemblers, clang's
integrated assembler rejects some GNU-as dialect spellings. The script
assembles a canonicalized COPY (dialect shim only -- encodings chosen to
round-trip to exactly the text the old toolchain produced):
    - suffix-less FP memory ops get their 32-bit gas suffix (fadd -> fadds,
      fiadd -> fiaddl, ...); libdisasm prints them suffix-less either way
    - movsx/movzx memory forms use the WORD encoding (movsxw), which is what
      keeps the two upstream XFAIL lines failing for their documented reason
      (libdisasm prints movsxw, expected comment says movsxb)
    - cmpxchg8bq -> cmpxchg8b (libdisasm prints "cmpxchg8bq" for 0F C7 /1)
The INPUT side always reads the original file, so the comparison text
semantics are unchanged.

Usage (on the device):
    python3 upstream-suite-device-port.py <ia32_test_insn.S> <x86dis-binary> \
        [--clang PATH] [--readobj PATH] [--workdir DIR]
"""
import argparse
import difflib
import os
import re
import subprocess
import sys

# 32-bit memory form suffix per ambiguous FP mnemonic (gas dialect)
FP_MEM_SUFFIX = {
    "fadd": "fadds", "fcom": "fcoms", "fcomp": "fcomps", "fdiv": "fdivs",
    "fdivr": "fdivrs", "fmul": "fmuls", "fsub": "fsubs", "fsubr": "fsubrs",
    "fld": "flds", "fst": "fsts", "fstp": "fstps",
    "fiadd": "fiaddl", "ficom": "ficoml", "ficomp": "ficompl",
    "fidiv": "fidivl", "fidivr": "fidivrl", "fimul": "fimull",
    "fisub": "fisubl", "fisubr": "fisubrl",
    "fild": "fildl", "fist": "fistl", "fistp": "fistpl", "fisttp": "fisttpl",
}
# word-encoding forms (AT&T movswl/movzwl = word source, long destination):
# keeps the upstream XFAIL semantics of lines 207/209
MEM_WORD_FORM = {"movsx": "movswl", "movzx": "movzwl"}
# libdisasm prints "cmpxchg8bq"; modern assemblers only accept "cmpxchg8b"
MNEMONIC_ALIAS = {"cmpxchg8bq": "cmpxchg8b"}

def canonicalize(text):
    """Dialect shim for clang's integrated assembler (see module docstring).

    Five self-referential short-branch lines (jcxz 0x0 / loop -1 / loop 0 /
    loopnz 127 / loopz -127) cannot be reproduced: their expected text
    hard-codes 2003-gas rel8 encodings and (for loopz) signed rel8 rendering,
    which are internally inconsistent under any single modern assembler.
    They are left as-is and reported as dialect mismatches."""
    out = []
    for raw in text.splitlines():
        m = re.match(r"^([a-z0-9]+) \(", raw)
        if m:
            mn = m.group(1)
            repl = (FP_MEM_SUFFIX.get(mn) or MEM_WORD_FORM.get(mn)
                    or MNEMONIC_ALIAS.get(mn))
            if repl:
                raw = repl + raw[len(mn):]
        # branch targets above INT32_MAX: old gas wraps, clang rejects the
        # unsigned value -- express the identical address as a negative one
        m = re.match(r"^(j[a-z]+|call) (0x[0-9a-fA-F]+)(\s*#.*)?$", raw)
        if m:
            v = int(m.group(2), 16)
            if v > 0x7FFFFFFF:
                raw = "%s %d%s" % (m.group(1), v - (1 << 32), m.group(3) or "")
        out.append(raw)
    return "\n".join(out) + "\n"


def build_input(src_text, try_xfail=False):
    """run-test.sh: grep -v '^#' | perl -pe 's/^[^#]+#\\s*([^#]*).*$/$1/'
    | tr A-Z a-z | sed -e 's/ $//g'

    With try_xfail, first apply the upstream `perl -pi
    's/^([^#]+)#.*XFAIL.*$/$1/;'` neutralization: XFAIL-marked lines lose
    their expected text and compare against themselves."""
    out = []
    for raw in src_text.splitlines():
        if raw.startswith("#"):
            continue
        if try_xfail:
            m = re.match(r"^([^#]+)#.*XFAIL.*$", raw)
            if m:
                raw = m.group(1)
        m = re.match(r"^([^#]+)#\s*([^#]*).*$", raw)
        if m:
            raw = m.group(2)
        raw = raw.lower()
        if raw.endswith(" "):  # sed strips exactly one trailing space
            raw = raw[:-1]
        out.append(raw)
    return out


def build_output(x86dis_text):
    """asmdisasm.pl normalization, then run-test.sh cut -d'#' -f1 + sed."""
    out = []
    for raw in x86dis_text.splitlines():
        if raw.startswith("#"):
            continue
        line = re.sub(r"\s+", " ", raw)
        line = re.sub(r"\s+$", "", line)
        line = re.sub(r"#.*", "", line)
        line = line.lower()
        m = re.match(r"[0-9][0-9a-f]+\s+((?:[0-9a-f]{2} )+)", line)
        if m:
            line = line[m.end():]
        if line.endswith(" "):
            line = line[:-1]
        out.append(line)
    return out


def text_section(readobj, obj):
    """llvm-readobj --sections: find .text, return (file_offset, size)."""
    sec_name = None
    offset = size = None
    for line in readobj.splitlines():
        s = line.strip()
        if s.startswith("Name:"):
            name = s[len("Name:"):].strip()
            name = name.split("(")[0].strip()
            sec_name = name
        elif sec_name == ".text":
            if s.startswith("Offset:"):
                offset = int(s.split(":", 1)[1].strip(), 0)
            elif s.startswith("Size:"):
                size = int(s.split(":", 1)[1].strip(), 0)
                if offset is not None:
                    return offset, size
    raise RuntimeError("no .text section found in llvm-readobj output")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("insn_file")
    ap.add_argument("x86dis")
    ap.add_argument("--clang", default="/data/service/hnp/bin/clang")
    ap.add_argument("--readobj", default="/data/service/hnp/bin/llvm-readobj")
    ap.add_argument("--workdir", default=".")
    ap.add_argument("--try-xfail", action="store_true",
                    help="neutralize XFAIL lines like upstream run-test.sh")
    args = ap.parse_args()

    os.makedirs(args.workdir, exist_ok=True)
    obj = os.path.join(args.workdir, "ia32_test_insn.o")
    asm = os.path.join(args.workdir, "ia32_test_insn.clang.s")

    env = dict(os.environ)
    env.setdefault("TMPDIR", args.workdir)

    src_text = open(args.insn_file, encoding="utf-8", errors="replace").read()
    open(asm, "w", encoding="utf-8").write(canonicalize(src_text))

    # as --32 -o obj src  ->  clang i386 on the canonicalized copy
    r = subprocess.run(
        [args.clang, "--target=i386-linux-gnu", "-c", asm, "-o", obj],
        capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print("ASSEMBLE FAILED (clang i386):\n" + r.stderr[:4000])
        return 2

    # objdump -h  ->  llvm-readobj --sections
    r = subprocess.run([args.readobj, "--sections", obj],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print("READOBJ FAILED:\n" + r.stderr[:2000])
        return 2
    offset, size = text_section(r.stdout, obj)
    print(".text: offset=%#x size=%d" % (offset, size))

    # x86dis -f obj -s att -r <offset> <size>
    r = subprocess.run(
        [args.x86dis, "-f", obj, "-s", "att", "-r", str(offset), str(size)],
        capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print("X86DIS FAILED:\n" + (r.stdout or "")[:2000] + (r.stderr or "")[:2000])
        return 2

    inp = build_input(src_text, try_xfail=args.try_xfail)
    outp = build_output(r.stdout)
    xfail_lines = [l for l in src_text.splitlines() if "XFAIL" in l]

    diff = list(difflib.unified_diff(inp, outp, lineterm="", n=0))
    report = [l for l in diff if l.startswith("-") and not l.startswith("---")]
    bad = len(report)
    okay = len(inp) - bad - len(xfail_lines)

    print("== Start Instruction Assemble/Disassemble Report ==")
    if xfail_lines:
        print("=== Expected Failures ===")
        for l in xfail_lines:
            print(l)
    if report:
        print("=== Failures ===")
        for l in diff:
            print(l)
    print("=== Test Summary ===")
    if xfail_lines:
        print("XFAIL: %d" % len(xfail_lines))
    print("ok: %d" % okay)
    if bad:
        print("FAILED: %d" % bad)
    print("== End Instruction Assemble/Disassemble Test ==")
    print("(input lines: %d, disassembled lines: %d)" % (len(inp), len(outp)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
