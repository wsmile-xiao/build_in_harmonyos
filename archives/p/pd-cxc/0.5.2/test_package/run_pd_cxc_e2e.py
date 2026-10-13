#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pd-cxc 0.5.2 -- end-to-end consumer test driven by the real OHOS ``pd``.

Why this test exists
--------------------
pd-cxc installs nothing but 26 Pure Data externals: no library to link against,
no command line program.  ``pd_cxc_test.c`` covers the load contract and drives
five objects through a minimal Pd runtime shim -- but a shim is not Pd.  The
shim handed the statistics objects a 32-bit-float array, while the platform's
``puredata/0.54.1`` is a **64-bit-float** build in which
``garray_getfloatarray()`` fails outright.  That difference hid a real defect
(see notes.md): ``cxmean``/``cxavgdev``/``cxstddev`` could not read any array at
all, and their "no such table" path segfaulted the pd process (rc=139).

This test therefore runs the *packaged* objects inside the *real* pd binary:

  load      a patch instantiating all 26 delivered classes must load without a
            single "couldn't create"; the same patch is then run with an empty
            search path, where all 26 must fail -- otherwise the check would be
            vacuous;
  stats     the consumer workflow this library exists for: fill a [table]
            buffer, measure it with [cxmean]/[cxavgdev]/[cxstddev] and compare
            all three numbers with an independent Python implementation of the
            algorithms the upstream sources specify;
  hex2dec   [hex2dec hex:%x] and [hex2dec tag-%s] formatting, compared with
            Python's own ``%`` formatting of the same values;
  counter   [cxc_counter] counting and the wrap bang, compared with a Python
            re-implementation of upstream's counter state machine;
  prepend   [cxc_prepend] prefixing and [cxc_split] splitting, compared with a
            Python re-implementation of the upstream C code;
  badtable  a typo'd table name must produce a Pd error and leave pd alive.

Every check prints the input it fed and the value it compared.  A case that
cannot be executed at all (pd does not run on this host) is reported as skipped
and is never counted as a pass.

Usage: run_pd_cxc_e2e.py <pd-cxc package folder> <pd binary> [summary file]
"""
import math
import os
import re
import struct
import subprocess
import sys
import tempfile

SAMPLE_RATE = "44100"
PD_TIMEOUT = 300
# A patch that loops (Pd's own [until] runs away when it gets a bang instead of
# a count) can print unbounded output; keep the parsed log bounded.
PD_LOG_CAP = 4 << 20

CLASSES = ("ENV ascseq ascwave bfilt bfilt2 cxc_counter cxc_prepend cxc_split "
           "cxavgdev cxmean cxstddev delta~ dist_normal hex2dec ixprint mean~ "
           "proc random1 random1~ random_fl random_fl~ random_icg random_icg~ "
           "random_tw reson~ utime").split()

# ── deterministic consumer input ────────────────────────────────────────────
BUF = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]   # one measurement buffer
COUNTER_STEPS = 12                                # bangs into [cxc_counter]
HEX_VALUES = [0.0, 255.0, 4096.0]                 # [hex2dec hex:%x] inputs


def f32(x):
    """Round the way the externals compute: t_float is a 32-bit float."""
    return struct.unpack("f", struct.pack("f", x))[0]


# ── independent reference implementations (from the upstream C sources) ─────
def ref_stats(values):
    """mean~.c: mean = sum(x)/n, avgdev = sum|x-mean|/n,
    stddev = sqrt(sum((x-mean)^2)/(n-1))."""
    n = len(values)
    mean = sum(values) / n
    avgdev = sum(abs(v - mean) for v in values) / n
    stddev = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1)) if n > 1 else 0.0
    return f32(mean), f32(avgdev), f32(stddev)


def ref_counter(steps, low=1, high=10):
    """cxc_counter.c, count-up mode: the counter starts at `high`, every bang
    increments, silently wraps to `low` after the top, and sends one bang on
    outlet 1 when it lands exactly on `high`."""
    out = []
    current = high
    for _ in range(steps):
        current += 1
        if current > high:
            current = low
        out.append((current, current == high))
    return out


def ref_hex2dec(fmt, value):
    """hex2dec.c: sprintf(buf, format, (int)f) for a float, sprintf(buf,
    format, s->s_name) for a symbol."""
    return fmt % (value if isinstance(value, str) else int(value))


def ref_prepend_anything(prefix, atoms):
    """cxc_prepend.c: outlet_anything(prefix, atoms) -- the creation argument
    becomes the outlet selector."""
    return [prefix] + list(atoms)


def ref_split(sym, splitter):
    """cxc_split.c split_anything(): walk the symbol, cut at every occurrence
    of the splitter's first character, turn digits-only pieces into floats and
    everything else into symbols, and always emit the trailing piece."""
    def is_num(text):
        return all(ch in ".0123456789" for ch in text) if text else True

    out, cur = [], ""
    for ch in sym:
        if ch == splitter[0]:
            if cur:
                out.append(float(cur) if is_num(cur) else cur)
                cur = ""
        else:
            cur += ch
    out.append(float(cur) if is_num(cur) else cur)
    return out


# ── patch construction ─────────────────────────────────────────────────────
def canvas(objs, conns, quit_ms=700):
    """Build a Pd patch: `objs` are #X lines, then a loadbang->delay->quit tail."""
    base = len(objs)
    lines = ["#N canvas 0 0 900 900 10;"] + objs + [
        "#X obj 20 830 loadbang;",
        "#X obj 20 860 delay %d;" % quit_ms,
        "#X msg 20 890 \\; pd quit;",
        "#X connect %d 0 %d 0;" % (base, base + 1),
        "#X connect %d 0 %d 0;" % (base + 1, base + 2),
    ]
    return "\n".join(lines + conns) + "\n"


LOAD_PATCH = canvas(
    ["#X obj %d %d %s;" % (20 + (i % 6) * 140, 20 + (i // 6) * 40, cls)
     for i, cls in enumerate(CLASSES)], [])

# Consumer workflow: buffer in, three statistics out.  The buffer is filled the
# way a Pd patch fills an array -- a message to the array's name, whose "list"
# selector carries <first-index> <values...> -- and the measurements run 100 ms
# later, so they can never see a half-filled buffer.
STATS_PATCH = canvas(
    ["#X obj 20 20 table buf %d;" % len(BUF),
     "#X obj 20 60 loadbang;",
     "#X obj 20 100 t b b;",
     "#X msg 300 100 \\; buf list 0 " + " ".join("%g" % v for v in BUF) + ";",
     "#X obj 20 220 delay 100;",
     "#X msg 20 260 mean;",
     "#X obj 300 260 cxmean buf;",
     "#X obj 560 260 print MEAN;",
     "#X obj 300 320 cxavgdev buf;",
     "#X obj 560 320 print AVGDEV;",
     "#X obj 300 380 cxstddev buf;",
     "#X obj 560 380 print STDDEV;"],
    ["#X connect 1 0 2 0;",
     "#X connect 2 1 3 0;",
     "#X connect 2 0 4 0;",
     "#X connect 4 0 5 0;",
     "#X connect 5 0 6 0;",
     "#X connect 6 0 7 0;",
     "#X connect 6 0 8 0;",
     "#X connect 8 0 9 0;",
     "#X connect 6 0 10 0;",
     "#X connect 10 0 11 0;"],
    quit_ms=900)


def hex_patch(label, msg, create):
    return canvas(
        ["#X obj 20 20 loadbang;",
         "#X msg 20 60 %s;" % msg,
         "#X obj 200 60 hex2dec %s;" % create,
         "#X obj 420 60 print %s;" % label],
        ["#X connect 0 0 1 0;",
         "#X connect 1 0 2 0;",
         "#X connect 2 0 3 0;"])


HEX_PATCHES = [("HEX%d" % int(v), "%g" % v, "hex:%x", v) for v in HEX_VALUES]
# A symbol input goes through hex2dec's class_addsymbol path, which sprintf's
# the creation format with the symbol's own name.
HEX_PATCHES.append(("HEXTAG", "symbol z", "tag-%s", "z"))

# NB: [until] takes its iteration count from a *float message*, not from a
# creation argument -- "until 12" creates a plain [until] whose bang handler
# loops until its bang2 inlet is hit.  Send it a float.
COUNTER_PATCH = canvas(
    ["#X obj 20 20 loadbang;",
     "#X msg 20 60 %d;" % COUNTER_STEPS,
     "#X obj 20 100 until;",
     "#X obj 20 140 cxc_counter;",
     "#X obj 300 140 print CNT;",
     "#X obj 200 180 print CNTBANG;"],
    ["#X connect 0 0 1 0;",
     "#X connect 1 0 2 0;",
     "#X connect 2 0 3 0;",
     "#X connect 3 0 4 0;",
     "#X connect 3 1 5 0;"],
    quit_ms=1200)

PREPEND_PATCH = canvas(
    ["#X obj 20 20 loadbang;",
     "#X msg 20 60 list foo 1 2;",
     "#X obj 200 60 cxc_prepend pre;",
     "#X obj 420 60 print PREP;"],
    ["#X connect 0 0 1 0;",
     "#X connect 1 0 2 0;",
     "#X connect 2 0 3 0;"])

SPLIT_PATCH = canvas(
    ["#X obj 20 20 loadbang;",
     "#X msg 20 60 symbol ab/cd;",
     "#X obj 200 60 cxc_split /;",
     "#X obj 420 60 print SPLITS;"],
    ["#X connect 0 0 1 0;",
     "#X connect 1 0 2 0;",
     "#X connect 2 0 3 0;"])

BADTABLE_PATCH = canvas(
    ["#X obj 20 20 loadbang;",
     "#X msg 20 60 mean;",
     "#X obj 300 60 cxmean nosuchtable;",
     "#X obj 560 60 print MEAN;"],
    ["#X connect 0 0 1 0;",
     "#X connect 1 0 2 0;",
     "#X connect 2 0 3 0;"],
    quit_ms=600)


# A patch using nothing but Pd's own builtins: if this cannot run, the host
# cannot execute the OHOS `pd` binary at all (wrong libc, no DSP clock, ...)
# and the whole case set is SKIPped instead of being reported as failures.
PROBE_PATCH = canvas(["#X obj 20 20 print PDCXC_PROBE;"],
                     ["#X connect 1 0 0 0;"], quit_ms=200)


# ── running pd ─────────────────────────────────────────────────────────────
def run_pd(pd_binary, patches, paths, timeout=PD_TIMEOUT):
    args = [pd_binary, "-nogui", "-noaudio", "-r", SAMPLE_RATE]
    for path in paths:
        args += ["-path", path]
    for patch in patches:
        args += ["-open", patch]
    def clip(text):
        if len(text) > PD_LOG_CAP:
            print("[pd-cxc-e2e] note: pd printed %d bytes, parsing the first %d"
                  % (len(text), PD_LOG_CAP))
            return text[:PD_LOG_CAP]
        return text
    try:
        proc = subprocess.run(args, timeout=timeout, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        return proc.returncode, clip(proc.stdout.decode("utf-8", "replace"))
    except subprocess.TimeoutExpired as exc:
        return "TIMEOUT", clip((exc.stdout or b"").decode("utf-8", "replace"))
    except OSError as exc:
        return "SPAWN-FAIL", str(exc)


PRINT_RE = re.compile(r"^([A-Z][A-Z0-9_]*): (.*)$", re.M)


def printed(text):
    out = {}
    for label, rest in PRINT_RE.findall(text):
        out.setdefault(label, []).append(rest.strip())
    return out


def parse_float(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def near(got, want):
    return got is not None and abs(got - want) <= 1e-5 * max(1.0, abs(want))


class Report(object):
    def __init__(self):
        self.checks = 0
        self.fails = 0

    def check(self, ok, what, detail=""):
        self.checks += 1
        if ok:
            print("PASS: %s%s" % (what, ("  [%s]" % detail) if detail else ""))
        else:
            self.fails += 1
            print("FAIL: %s%s" % (what, ("  [%s]" % detail) if detail else ""))


def main(argv):
    if len(argv) < 3:
        sys.stderr.write(__doc__)
        return 2
    pkg, pd_binary = argv[1], argv[2]
    summary_path = argv[3] if len(argv) > 3 else None

    ext_dir = os.path.join(pkg, "lib", "pd-externals", "cxc")
    if not os.path.isdir(ext_dir):
        sys.stderr.write("FAIL: packaged externals dir missing: %s\n" % ext_dir)
        return 1
    if not os.path.isfile(pd_binary):
        sys.stderr.write("FAIL: pd binary missing: %s\n" % pd_binary)
        return 1
    delivered = sorted(f for f in os.listdir(ext_dir) if f.endswith(".pd_linux"))
    print("[pd-cxc-e2e] packaged externals: %d" % len(delivered))
    print("[pd-cxc-e2e] pd: %s" % pd_binary)

    work = tempfile.mkdtemp(prefix="pd-cxc-e2e-")
    written = {}

    def write(name, body):
        path = os.path.join(work, "case_%s.pd" % name)
        with open(path, "w") as handle:
            handle.write(body)
        written[name] = path
        return path

    write("load", LOAD_PATCH)
    write("probe", PROBE_PATCH)
    write("stats", STATS_PATCH)
    for label, msg, create, _ in HEX_PATCHES:
        write("hex_%s" % label, hex_patch(label, msg, create))
    write("counter", COUNTER_PATCH)
    write("prepend", PREPEND_PATCH)
    write("split", SPLIT_PATCH)
    write("badtable", BADTABLE_PATCH)

    report = Report()

    # ── can this host run the packaged pd binary at all? ──────────────────
    rc_probe, text_probe = run_pd(pd_binary, [written["probe"]], [ext_dir])
    if rc_probe != 0 or "PDCXC_PROBE: bang" not in text_probe:
        print("[pd-cxc-e2e] SKIP: this host cannot run the OHOS pd binary "
              "(probe rc=%s) -- the end-to-end cases were NOT executed"
              % rc_probe)
        for line in text_probe.splitlines()[:8]:
            print("      | %s" % line)
        print("PD_CXC_E2E executed=0 passed=0 failed=0 skipped=1")
        if summary_path:
            with open(summary_path, "w") as handle:
                handle.write("0 0 0 1\n")
        return 0

    rc, text = run_pd(pd_binary, [written["load"]], [ext_dir])
    if rc == "SPAWN-FAIL":
        print("[pd-cxc-e2e] SKIP: pd could not be spawned (%s)" % text)
        print("PD_CXC_E2E executed=0 passed=0 failed=0 skipped=1")
        if summary_path:
            with open(summary_path, "w") as handle:
                handle.write("0 0 0 1\n")
        return 0

    # ── load ──────────────────────────────────────────────────────────────
    broken = [cls for cls in CLASSES
              if re.search(r"verbose\(0\): %s\s*\nverbose\(1\): \.\.\. couldn't create"
                           % re.escape(cls), text)]
    report.check(not broken,
                 "real pd instantiates all %d delivered classes" % len(CLASSES),
                 "uncreatable: %s" % (", ".join(broken) if broken else "none"))
    report.check("unknown function" not in text, "pd log free of 'unknown function'")

    rc_empty, text_empty = run_pd(pd_binary, [written["load"]], [work])
    uncreatable = len(re.findall(r"couldn't create", text_empty))
    report.check(uncreatable >= len(CLASSES),
                 "the load check can fail (same patch, empty search path)",
                 "%d 'couldn't create' without the package on -path" % uncreatable)

    # ── stats: the consumer workflow ──────────────────────────────────────
    mean_ref, avgdev_ref, stddev_ref = ref_stats(BUF)
    rc, text = run_pd(pd_binary, [written["stats"]], [ext_dir])
    got = printed(text)
    report.check("garray_getfloatarray" not in text,
                 "statistics objects read the [table] buffer (%d samples)"
                 % len(BUF), "no 64-bit garray error in pd's log")
    report.check(near(parse_float((got.get("MEAN") or [""])[0]), mean_ref),
                 "cxmean buf -> mean", "reference %s, pd %s"
                 % (mean_ref, (got.get("MEAN") or ["-"])[0]))
    report.check(near(parse_float((got.get("AVGDEV") or [""])[0]), avgdev_ref),
                 "cxavgdev buf (fed the measured mean) -> average deviation",
                 "reference %s, pd %s" % (avgdev_ref, (got.get("AVGDEV") or ["-"])[0]))
    report.check(near(parse_float((got.get("STDDEV") or [""])[0]), stddev_ref),
                 "cxstddev buf (fed the measured mean) -> standard deviation",
                 "reference %s, pd %s" % (stddev_ref, (got.get("STDDEV") or ["-"])[0]))

    # ── hex2dec ───────────────────────────────────────────────────────────
    patches = [written["hex_%s" % label] for label, _, _, _ in HEX_PATCHES]
    rc, text = run_pd(pd_binary, patches, [ext_dir])
    got = printed(text)
    for label, msg, create, value in HEX_PATCHES:
        want = ref_hex2dec(create, value)
        report.check(got.get(label) == ["symbol %s" % want],
                     "hex2dec %s with %r -> %s" % (create, msg, want),
                     "got %r" % (got.get(label),))

    # ── cxc_counter ───────────────────────────────────────────────────────
    rc, text = run_pd(pd_binary, [written["counter"]], [ext_dir])
    got = printed(text)
    ref = ref_counter(COUNTER_STEPS)
    want_vals = ["%g" % v for v, _ in ref]
    want_bangs = sum(1 for _, bang in ref if bang)
    report.check(got.get("CNT") == want_vals,
                 "cxc_counter after %d bangs -> %s" % (COUNTER_STEPS, want_vals),
                 "got %r" % (got.get("CNT"),))
    report.check(len(got.get("CNTBANG") or []) == want_bangs,
                 "cxc_counter wrap bang fires exactly on the high bound",
                 "reference %d bang(s), pd %d"
                 % (want_bangs, len(got.get("CNTBANG") or [])))

    # ── cxc_prepend / cxc_split ───────────────────────────────────────────
    rc, text = run_pd(pd_binary, [written["prepend"]], [ext_dir])
    got = printed(text)
    want = ref_prepend_anything("pre", ["foo", "1", "2"])
    got_prep = (got.get("PREP") or [""])[0]
    report.check(got_prep.replace("float ", "") == " ".join(want)
                 or got_prep.replace("float ", "") == "pre foo 1 2",
                 "cxc_prepend pre with [list foo 1 2] -> 'pre foo 1 2'",
                 "got %r" % (got_prep,))

    rc, text = run_pd(pd_binary, [written["split"]], [ext_dir])
    got = printed(text)
    parts = ref_split("ab/cd", "/")
    report.check((got.get("SPLITS") or [""])[0] == "list %s %s" % (parts[0], parts[1]),
                 "cxc_split / with symbol ab/cd -> list ab cd",
                 "got %r" % ((got.get("SPLITS") or [None])[0],))

    # ── badtable: a typo must not take pd down ────────────────────────────
    rc, text = run_pd(pd_binary, [written["badtable"]], [ext_dir])
    report.check(rc == 0, "a typo'd table name leaves pd alive",
                 "pd exit code %s (unpatched package: 139/SIGSEGV)" % rc)
    report.check("no such table" in text,
                 "a typo'd table name is reported as a Pd error",
                 "'no such table' present in pd's log")

    print("")
    print("PD_CXC_E2E checks=%d fails=%d" % (report.checks, report.fails))
    if summary_path:
        with open(summary_path, "w") as handle:
            handle.write("%d %d %d 0\n"
                         % (report.checks, report.checks - report.fails, report.fails))
    return 1 if report.fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
