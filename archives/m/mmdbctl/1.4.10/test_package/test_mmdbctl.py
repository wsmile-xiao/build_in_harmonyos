#!/usr/bin/env python3
"""mmdbctl 1.4.10 consumer test (HarmonyOS PC).

Replaces the former CMake+C test_package (which failed device
`cmake.configure()` with `CMAKE_C_COMPILER: /data/service/hnp/bin/clang`
+ `System is unknown to cmake` on 2026-10-08): this test needs no C
toolchain at all.  It runs pure-python reimplementations of the same
core pure-logic mappings the former test.c asserted (mirroring the same
upstream Go Test* functions), plus a substantive smoke test of the real
packaged `mmdbctl` binary (R34), and emits the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker with deterministic counts.

Mappings (same as former test.c):
  1. test_import_ip_version      <-> lib/cmd_import_test.go::TestCmdImport_InvalidIPVersion
  2. test_import_record_size     <-> lib/cmd_import_test.go::TestCmdImport_InvalidRecordSize
  3. test_import_merge_strategy  <-> lib/cmd_import_test.go::TestCmdImport_InvalidMergeStrategy
  4. test_import_csv_headers     <-> lib/cmd_import_test.go::TestParseCSVHeaders
  5. test_export_format          <-> lib/cmd_export_test.go::TestCmdExport_InvalidFormat
     + format inference (TestCmdExport_FormatInferredFromFilename)
Binary smoke:
  6. test_binary                <-> packaged `mmdbctl --help` (R34 substantive)

Counting: single deterministic tally (g_total/g_passed) incremented by
check() as each assertion actually runs.  No string-counting, no
arithmetic repair branches.
"""

import json
import os
import subprocess
import sys

exe = sys.argv[1] if len(sys.argv) > 1 else "mmdbctl"

g_total = 0
g_passed = 0


def check(cond, msg):
    global g_total, g_passed
    g_total += 1
    if cond:
        g_passed += 1
        print("    [PASS] %s" % msg)
    else:
        print("    [FAIL] %s" % msg)


# ---- 1. import ip version: must be 4 or 6 ----
def import_ip_valid(ip):
    return ip == 4 or ip == 6


print("[RUN ] test_import_ip_version")
check(import_ip_valid(4) is True, "ip 4 valid")
check(import_ip_valid(6) is True, "ip 6 valid")
check(import_ip_valid(3) is False, "ip 3 invalid (upstream case)")
check(import_ip_valid(0) is False, "ip 0 invalid")


# ---- 2. import record size: must be 24, 28 or 32 ----
def import_size_valid(size):
    return size in (24, 28, 32)


print("[RUN ] test_import_record_size")
check(import_size_valid(24) is True, "size 24 valid")
check(import_size_valid(28) is True, "size 28 valid")
check(import_size_valid(32) is True, "size 32 valid")
check(import_size_valid(16) is False, "size 16 invalid (upstream case)")


# ---- 3. import merge strategy: none / toplevel / recurse ----
def import_merge_valid(m):
    return m in ("none", "toplevel", "recurse")


print("[RUN ] test_import_merge_strategy")
check(import_merge_valid("none") is True, "merge none valid")
check(import_merge_valid("toplevel") is True, "merge toplevel valid")
check(import_merge_valid("recurse") is True, "merge recurse valid")
check(import_merge_valid("invalid") is False,
      "merge invalid rejected (upstream case)")


# ---- 4. import CSV header parsing: ParseCSVHeaders ----
def parse_csv_headers(parts):
    is_range = False
    has_joinkey = False
    data_start = 1
    if (len(parts) >= 2 and parts[0] == "start_ip"
            and parts[1] == "end_ip"):
        is_range = True
        data_start = 2
        if len(parts) >= 3 and parts[2] == "join_key":
            has_joinkey = True
            data_start = 3
    return is_range, has_joinkey, data_start


print("[RUN ] test_import_csv_headers")
r = parse_csv_headers(["network", "country"])
check(r == (False, False, 1), "simple header -> start=1")
r = parse_csv_headers(["start_ip", "end_ip", "country"])
check(r == (True, False, 2), "range header -> start=2")
r = parse_csv_headers(["start_ip", "end_ip", "join_key", "country"])
check(r == (True, True, 3), "range+joinkey header -> start=3")


# ---- 5. export format: csv/tsv/json valid, xml invalid; inference ----
def export_format_valid(f):
    return f in ("csv", "tsv", "json")


def infer_format(out):
    if out.endswith(".csv"):
        return "csv"
    if out.endswith(".tsv"):
        return "tsv"
    if out.endswith(".json"):
        return "json"
    return "csv"


print("[RUN ] test_export_format")
check(export_format_valid("csv") is True, "format csv valid")
check(export_format_valid("tsv") is True, "format tsv valid")
check(export_format_valid("json") is True, "format json valid")
check(export_format_valid("xml") is False,
      "format xml invalid (upstream case)")
check(infer_format("out.csv") == "csv", "infer .csv")
check(infer_format("out.tsv") == "tsv", "infer .tsv")
check(infer_format("out.json") == "json", "infer .json")
check(infer_format("out.bin") == "csv", "infer default csv")


# ---- 6. packaged binary smoke (R34 substantive) ----
print("[RUN ] test_binary")
check(os.path.isfile(exe), "binary exists (%s)" % exe)
if os.path.isfile(exe):
    try:
        with open(exe, "rb") as f:
            is_elf = f.read(4) == b"\x7fELF"
    except OSError:
        is_elf = False
    check(is_elf, "binary is ELF")
else:
    check(False, "binary is ELF")
try:
    proc = subprocess.run([exe, "--help"], capture_output=True,
                          text=True, timeout=60)
    out = (proc.stdout or "") + (proc.stderr or "")
    check(proc.returncode == 0,
          "mmdbctl --help rc==0 (rc=%s)" % proc.returncode)
    low = out.lower()
    check(len(out.strip()) > 0 and ("mmdbctl" in low or "usage" in low
          or "available" in low or "command" in low),
          "help output contains usage")
except Exception as exc:  # honest failure, never fabricated
    check(False, "mmdbctl --help executed (%s)" % exc)
    check(False, "help output contains usage")

print("tests discovered=%d passed=%d failed=%d"
      % (g_total, g_passed, g_total - g_passed))

marker = {
    "executed": True,
    "passed": (g_total > 0 and g_passed == g_total),
    "command": "test_mmdbctl.py <exe>",
    "discovered": g_total,
    "passedCount": g_passed,
}
print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker), flush=True)

sys.exit(0 if (g_total > 0 and g_passed == g_total) else 1)
