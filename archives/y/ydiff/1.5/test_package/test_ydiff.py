import os
import subprocess
import sys


DIFF_INPUT = """diff --git a/example.txt b/example.txt
index 3b18e13..7bc31cd 100644
--- a/example.txt
+++ b/example.txt
@@ -1 +1 @@
-hello
+hello harmony
"""


def run(executable, *arguments):
    return subprocess.run(
        [sys.executable, executable, *arguments],
        input=DIFF_INPUT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def main():
    executable = sys.argv[1]

    version = subprocess.run(
        [sys.executable, executable, "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    expected_version = f"{os.path.basename(executable)} 1.5"
    if version.returncode != 0 or version.stdout.strip() != expected_version:
        raise RuntimeError(f"version check failed: {version.stdout}{version.stderr}")

    unified = run(executable, "--unified", "--color=never", "--pager=cat")
    if unified.returncode != 0:
        raise RuntimeError(f"unified diff failed: {unified.stderr}")
    if "-hello" not in unified.stdout or "+hello harmony" not in unified.stdout:
        raise RuntimeError(f"unified diff output mismatch: {unified.stdout}")

    side_by_side = run(
        executable,
        "--width=80",
        "--no-wrap",
        "--color=never",
        "--pager=cat",
    )
    if side_by_side.returncode != 0:
        raise RuntimeError(f"side-by-side diff failed: {side_by_side.stderr}")
    if "hello" not in side_by_side.stdout or "hello harmony" not in side_by_side.stdout:
        raise RuntimeError(f"side-by-side diff output mismatch: {side_by_side.stdout}")


if __name__ == "__main__":
    main()
