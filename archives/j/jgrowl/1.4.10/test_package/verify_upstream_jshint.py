#!/usr/bin/env python3
"""Run the upstream Grunt JSHint test using Node.js and the pinned JS files."""
import hashlib
import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCES = {
    # Hash canonical LF content so Windows core.autocrlf and Unix checkouts agree.
    "Gruntfile.js": "775fe85f16b29508fbf11f9a314300554155d232d02c6ab96221e7f8356cb59e",
    "jquery.jgrowl.js": "06f5081b0919158aff193eaaa8f7d52614390af31ef529c4dac28cea8cf69c2a",
}


def main():
    upstream = os.path.join(ROOT, "upstream")
    for filename, expected_hash in SOURCES.items():
        path = os.path.join(upstream, filename)
        with open(path, "rb") as stream:
            source = stream.read()
        canonical_source = source.replace(b"\r\n", b"\n")
        actual_hash = hashlib.sha256(canonical_source).hexdigest()
        if actual_hash != expected_hash:
            raise AssertionError(
                "upstream test fixture differs from jGrowl 1.4.10: " + filename
            )
    node = shutil.which("node") or shutil.which("nodejs")
    engine = os.path.join(ROOT, "vendor-final", "jshint", "dist", "jshint.js")
    if not node:
        raise SystemExit("Node.js is required to execute the upstream JSHint test")

    harness = os.path.join(ROOT, "run_upstream_jshint.js")
    inputs = [os.path.join(upstream, filename) for filename in SOURCES]
    result = subprocess.run(
        [node, harness, engine, *inputs],
        check=False,
        text=True,
    )
    if result.returncode:
        raise SystemExit(result.returncode)

    print("[PASS] upstream grunt test JSHint target: Gruntfile.js + jquery.jgrowl.js")
    print("Upstream test cases: 1/1")


if __name__ == "__main__":
    main()
