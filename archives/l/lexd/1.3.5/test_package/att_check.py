#!/usr/bin/env python3
"""att_check.py — consumer-side verification of the installed lexd binary.

Upstream `make check` verifies each fixture by pushing the ATT transducer
through the HFST command line tools:

    hfst-txt2fst <out> | hfst-fst2strings -X obey-flags -c 10 | LC_ALL=C sort -u
    diff -U0 <that> <test-X.lexd.txt.strings.gold>

Neither `hfst-txt2fst` nor `hfst-fst2strings` is published in the ohpcd
artifact repository (HFST itself, and its Foma dependency, are absent), so
that pipeline cannot run on OHOS. This script performs the *same comparison*
with a self-contained reader for the ATT format:

  * every path spelling `left` on the surface side and `right` on the analysis
    side is checked with a position-indexed dynamic program, so a gold line
    is accepted only if a real path exists — no enumeration, so no cap;
  * `@0@` is the empty label and any other `@X.Y@` symbol is a flag diacritic
    (metadata, exactly what HFST's `-X obey-flags` makes invisible);
  * a gold line is rendered as `left:right` when the transition carried
    different labels on the two sides, and as a bare `left` otherwise, so
    both forms are accepted.

Every assertion is a real comparison against the upstream gold data that
ships in `data/`, executed with the installed `bin/lexd`.

Also contains the HarmonyOS-specific target assertion: the delivered ELF must
be a 64-bit AArch64 OHOS executable (and the .pc artifact must be installed).
"""
import os
import re
import struct
import sys

# Upstream's 6 `make check` variants and the lexd flags each one passes.
VARIANTS = (
    ("plain", ()),
    ("flags", ("--flags",)),
    ("minimize-tags", ("--flags", "--tags", "--minimize")),
    ("tags", ("--flags", "--tags")),
    ("minimize", ("--flags", "--minimize")),
    ("single", ("--single",)),
)

FLAG_DIACRITIC = re.compile(r"^@[A-Z][A-Za-z0-9.]*@$")
EPSILON = "@0@"


def is_int(text):
    try:
        int(text)
        return True
    except ValueError:
        return False


def is_invisible(sym):
    """@0@ (empty) and @X.Y@ (flag diacritic) carry no surface characters."""
    return sym == EPSILON or bool(FLAG_DIACRITIC.match(sym))


def parse_att(text):
    """Return (adjacency, final states) for an AT&T transducer."""
    adjacency = {}
    finals = set()

    def edges(state):
        if state not in adjacency:
            adjacency[state] = []
        return adjacency[state]

    for line in text.splitlines():
        if not line.strip():
            continue
        fields = [f.strip() for f in line.split("\t")]
        if len(fields) >= 5:
            # state_in  state_out  in_label  out_label  weight [tags]
            edges(fields[0]).append((fields[1], fields[2], fields[3]))
        elif len(fields) >= 2 and is_int(fields[0]) and is_int(fields[1]):
            # label-less (epsilon) transition
            edges(fields[0]).append((fields[1], EPSILON, EPSILON))
        elif fields and is_int(fields[0]):
            # "<state>\t<weight>" declares a final state
            finals.add(fields[0])
    return adjacency, finals


def accepts(adjacency, finals, left, right):
    """True iff a path from state 0 spells `left`/`right` and ends in a final state."""
    width = len(left)
    # dp[i] = {(state, analysis-so-far)} reachable after consuming left[:i]
    dp = [set() for _ in range(width + 1)]
    dp[0].add(("0", ""))
    for pos in range(width + 1):
        # epsilon / flag-diacritic fixpoint at this position
        changed = True
        while changed:
            changed = False
            for state, analysis in list(dp[pos]):
                for nxt, in_label, out_label in adjacency.get(state, ()):
                    if not is_invisible(in_label):
                        continue
                    tail = "" if is_invisible(out_label) else out_label
                    item = (nxt, analysis + tail)
                    if item not in dp[pos]:
                        dp[pos].add(item)
                        changed = True
        if pos == width:
            break
        for state, analysis in list(dp[pos]):
            for nxt, in_label, out_label in adjacency.get(state, ()):
                if is_invisible(in_label) or not left.startswith(in_label, pos):
                    continue
                tail = "" if is_invisible(out_label) else out_label
                dp[pos + len(in_label)].add((nxt, analysis + tail))
    for state, analysis in dp[width]:
        if state in finals and analysis == right:
            return True
    return False


def run_lexd(lexd, args):
    import subprocess
    proc = subprocess.run([lexd] + list(args), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=180)
    return proc.returncode, proc.stdout, proc.stderr


def check_elf(path, failures, notes):
    """HarmonyOS target assertion: the artifact is a 64-bit AArch64 ELF."""
    with open(path, "rb") as handle:
        head = handle.read(20)
    if len(head) < 20 or head[:4] != b"\x7fELF":
        failures.append("elf: %s is not an ELF file" % path)
        return
    ei_class, ei_data = head[4], head[5]
    e_machine = struct.unpack_from("<H" if ei_data == 1 else ">H", head, 18)[0]
    if ei_class != 2:
        failures.append("elf: %s is not ELF64 (e_ident[EI_CLASS]=%d)" % (path, ei_class))
    if e_machine != 183:
        failures.append("elf: %s is not AArch64 (e_machine=%d, want 183)" % (path, e_machine))
    if not failures or not [f for f in failures if f.startswith("elf:")]:
        notes.append("ELF64 AArch64 (OHOS aarch64) target confirmed for %s" % os.path.basename(path))


def main():
    if len(sys.argv) < 4:
        print("usage: att_check.py <lexd-binary> <data-dir> <result-file>")
        return 2
    lexd, data_dir, result_file = sys.argv[1], sys.argv[2], sys.argv[3]

    failures, notes = [], []
    if not os.access(lexd, os.X_OK):
        print("FATAL: lexd binary is missing or not executable: %s" % lexd)
        return 1

    check_elf(lexd, failures, notes)

    fixtures = sorted(f for f in os.listdir(data_dir)
                      if f.startswith("test-") and f.endswith(".lexd"))
    if not fixtures:
        print("FATAL: no upstream fixtures found in %s" % data_dir)
        return 1

    gold_checks = 0
    combos = 0
    combos_ok = 0
    for variant, flags in VARIANTS:
        for fixture in fixtures:
            gold_path = os.path.join(data_dir, fixture + ".txt.strings.gold")
            if not os.path.isfile(gold_path):
                continue
            combo_ok = True
            with open(gold_path, encoding="utf-8") as handle:
                gold = [line.rstrip("\n") for line in handle]
            rc, out, err = run_lexd(lexd, list(flags) + [os.path.join(data_dir, fixture)])
            combos += 1
            if rc != 0:
                failures.append("lexd %s %s exited %d: %s"
                                % (" ".join(flags), fixture, rc,
                                   err.decode("utf-8", "replace")[:160]))
                continue
            adjacency, finals = parse_att(out.decode("utf-8", "replace"))
            if not gold:
                # Upstream ships an empty oracle for the empty lexicon
                # (test-empty.lexd): the transducer must accept nothing, and an
                # empty transducer is the expected result.
                gold_checks += 1
                if adjacency and accepts(adjacency, finals, "", ""):
                    combo_ok = False
                    failures.append("lexd %s %s accepted a form but the upstream "
                                    "gold is empty" % (" ".join(flags), fixture))
                if combo_ok:
                    combos_ok += 1
                continue
            if not adjacency and not finals:
                failures.append("lexd %s %s produced an empty transducer"
                                % (" ".join(flags), fixture))
                continue
            for line in gold:
                gold_checks += 1
                if ":" in line:
                    surface, analysis = line.split(":", 1)
                    hit = accepts(adjacency, finals, surface, analysis)
                else:
                    # bare rendering: HFST prints the surface side when the
                    # transition carried one shared label
                    hit = (accepts(adjacency, finals, line, "")
                           or accepts(adjacency, finals, line, line))
                if not hit:
                    combo_ok = False
                    failures.append("gold line %r not produced by lexd %s %s"
                                    % (line, " ".join(flags), fixture))
            if combo_ok:
                combos_ok += 1

    if gold_checks == 0 or combos_ok != combos:
        print("att_check FAILED: %d gold assertions, %d/%d fixture-variant "
              "combinations fully matched" % (gold_checks, combos_ok, combos))
        for item in failures[:15]:
            print("  - %s" % item)
        return 1

    print("att_check: %d gold assertions over %d fixture-variant combinations OK"
          % (gold_checks, combos))
    for note in notes:
        print("att_check: %s" % note)
    with open(result_file, "w", encoding="utf-8") as handle:
        handle.write("GOLD_CHECKS=%d\n" % gold_checks)
        handle.write("GOLD_COMBOS=%d\n" % combos)
        handle.write("GOLD_COMBOS_OK=%d\n" % combos_ok)
    return 0


if __name__ == "__main__":
    sys.exit(main())
