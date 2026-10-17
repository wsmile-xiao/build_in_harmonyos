#!/usr/bin/env python3
"""Functional consumer test for the overdrive 2.4.1 package (OHOS aarch64).

Upstream ships no test suite (the 2.4.1 archive contains only README.md and
overdrive.sh), so the executable entries below are taken from the script's own
behaviour contract plus the test declared by the Homebrew core formula:

  * ``overdrive --version``                       -> "2.4.1"
  * ``overdrive``                                 -> usage, exit 1
  * ``overdrive download fake_file.odm``          -> "Specified media file does
                                                    not exist", exit 2
                                                    (assertion of brew's test)
  * ``overdrive info|metadata book.odm``          -> xmllint + sed + awk path
  * licence hash pipeline (overdrive.sh:145)      -> iconv | openssl | base64

Usage: test_overdrive.py <package_folder>
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

SAMPLE_ODM = """<?xml version="1.0" encoding="UTF-8"?>
<OverDriveMedia id="4295342">
  <License>
    <AcquisitionUrl>https://example.invalid/acquisition</AcquisitionUrl>
  </License>
  <Protocol method="download" baseurl="https://example.invalid/files">
    <Part filename="4295342-a6e3-Part01.mp3" duration="12:34" size="1"/>
    <Part filename="4295342-a6e3-Part02.mp3" duration="03:26" size="1"/>
  </Protocol>
  <EarlyReturnURL>https://example.invalid/return</EarlyReturnURL>
<![CDATA[<?xml version="1.0" encoding="UTF-8"?><Metadata><Title>Snow Crash, A Novel</Title><Creator role="Author and narrator">Neal Stephenson</Creator><CoverUrl>https://example.invalid/cover.jpg</CoverUrl></Metadata>]]>
</OverDriveMedia>
"""

RESULTS = []


def record(name, ok, detail):
    RESULTS.append((name, ok, detail))
    print(f"CASE {name}: {'PASS' if ok else 'FAIL'}\n    {detail}")


def run(cmd, timeout=60):
    # No explicit cwd: on OHOS/HMDFS, spawning a child with a cwd argument makes
    # bash's shell-init print "getcwd: cannot access parent directories", which
    # is pure noise here. Every path passed to the script below is absolute.
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def main():
    if len(sys.argv) != 2:
        print("usage: test_overdrive.py <package_folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    script = os.path.join(pkg, "bin", "overdrive")
    bash = shutil.which("bash")
    # No hard-coded fallback path: if bash is absent the two bash-driven cases
    # must report a clean FAIL (with the reason) instead of raising
    # FileNotFoundError out of subprocess and escaping as a traceback.

    # --- case 1/2: packaging layout and executable bit -----------------------
    record("pkg_layout_bin_overdrive", os.path.isfile(script),
           f"expected installed script at {script}")
    record("pkg_executable_bit", os.access(script, os.X_OK),
           f"{script} must keep mode +x (shebang #!/usr/bin/env bash is the "
           f"entry point)")

    # --- case 3: bash syntax check of the packaged script --------------------
    if bash is None:
        record("bash_syntax_check", False,
               "no bash on PATH — the packaged script's shebang "
               "'#!/usr/bin/env bash' cannot be satisfied on this host")
    else:
        r = run([bash, "-n", script])
        record("bash_syntax_check", r.returncode == 0,
               f"{bash} -n -> rc={r.returncode} {r.stderr.strip()[:200]}")

    # --- case 4: --version (script prints VERSION to stderr, overdrive.sh:46)
    r = run([script, "--version"])
    out = r.stdout + r.stderr
    record("version_output_2_4_1",
           r.returncode == 0 and "2.4.1" in out,
           f"{script} --version -> rc={r.returncode} out={out.strip()[:120]!r}")

    # --- case 5: usage / exit 1 with no arguments (overdrive.sh:79-85) ------
    r = run([script])
    out = r.stdout + r.stderr
    record("usage_no_arguments_exit1",
           r.returncode == 1 and "You must supply at least one command." in out,
           f"{script} -> rc={r.returncode}")

    with tempfile.TemporaryDirectory(prefix="od-test-") as work:
        # --- case 6: the entry asserted by Homebrew's formula test block -----
        #     Absolute path to a loan file that cannot exist, so the check does
        #     not depend on the working directory (overdrive.sh:62-65).
        fake_odm = os.path.join(work, "fake_file.odm")
        r = run([script, "download", fake_odm])
        out = r.stdout + r.stderr
        record("enoent_download_exit2",
               r.returncode == 2
               and "Specified media file does not exist" in out,
               f"{script} download fake_file.odm -> rc={r.returncode} "
               f"out={out.strip()[:120]!r}")

        # --- case 7: the six runtime executables of overdrive.sh:87 --------
        missing = [c for c in ("curl", "uuidgen", "xmllint", "iconv",
                               "openssl", "base64") if shutil.which(c) is None]
        record("runtime_prereqs_on_path", not missing,
               f"required executables missing from PATH: {missing or 'none'}")

        odm = os.path.join(work, "Novel.odm")
        with open(odm, "w", encoding="utf-8") as f:
            f.write(SAMPLE_ODM)

        # --- case 8: metadata extraction (xmllint --noblanks + sed CDATA) ---
        r = run([script, "metadata", odm])
        out = r.stdout + r.stderr
        record("metadata_cdata_extraction",
               r.returncode == 0 and "<Title>" in out
               and "Neal Stephenson" in out,
               f"{script} metadata Novel.odm -> rc={r.returncode}")

        # --- case 9: info aggregation (author, sanitised title, awk sum) ---
        #             12:34 + 03:26 -> 754 + 206 = 960 seconds
        r = run([script, "info", odm])
        fields = r.stdout.strip().split("\n")[-1].split("\t") if r.stdout.strip() else []
        ok = (r.returncode == 0 and len(fields) == 3
              and fields[0] == "Neal Stephenson"
              and fields[1].startswith("Snow Crash")
              and fields[2] == "960")
        record("info_author_title_duration", ok,
               f"{script} info Novel.odm -> rc={r.returncode} "
               f"fields={fields!r} (expect Neal Stephenson / Snow Crash* / 960)")

        # --- case 10: sidecar metadata file written next to the loan -------
        record("metadata_sidecar_written",
               os.path.isfile(os.path.join(work, "Novel.odm.metadata")),
               "extract_metadata() must write <odm>.metadata next to the loan")

    # --- case 11: licence hash pipeline, overdrive.sh:145 (offline) ---------
    hash_cmd = (f"printf %s 'CLIENTID|1.2.0|10.11.6|ELOSNOC*AIDEM*EVIRDREVO' "
                f"| iconv -f ASCII -t UTF-16LE | openssl dgst -binary -sha1 "
                f"| base64")
    if bash is None:
        record("license_hash_pipeline", False,
               "no bash on PATH — cannot exercise overdrive.sh:145 pipeline")
    else:
        r = run([bash, "-c", hash_cmd])
        digest = r.stdout.strip()
        record("license_hash_pipeline",
               r.returncode == 0
               and re.fullmatch(r"[A-Za-z0-9+/]{27}=", digest) is not None,
               f"iconv|openssl dgst -sha1|base64 -> rc={r.returncode} "
               f"digest={digest!r} (28 chars base64 of a 20-byte SHA-1)")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    print(f"\noverdrive {pkg}: {len(RESULTS)} cases, {passed} passed, "
          f"{failed} failed, 0 skipped")
    if failed:
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"FAILED CASE {name}: {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
