#!/usr/bin/env python3
"""Run meinproc5 on HarmonyOS and verify a real DocBook-to-HTML transform."""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


MARKER = "HARMONYOS_KDOCTOOLS5_DOCBOOK_TRANSFORM_OK"


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_ohos_docbook.py MEINPROC5 PACKAGE_FOLDER")

    system = platform.uname()
    if system.system != "HarmonyOS" and "HongMeng" not in system.version:
        raise RuntimeError(
            "This integration test must execute on a HarmonyOS device; "
            f"reported system={system.system!r}, version={system.version!r}"
        )

    meinproc = Path(sys.argv[1]).resolve()
    package = Path(sys.argv[2]).resolve()
    if not meinproc.is_file():
        raise RuntimeError(f"meinproc5 does not exist: {meinproc}")

    catalogs = [
        path
        for path in package.rglob("catalog.xml")
        if path.parent.name == "customization"
        and path.parent.parent.name == "kdoctools"
    ]
    if not catalogs:
        raise RuntimeError("installed KDocTools catalog.xml was not found")
    kdoctools_data = catalogs[0].parent.parent

    # HarmonyOS PC SSH users may not have permission to write /data/local/tmp.
    # Prefer the caller's TMPDIR, then the writable per-user tmp directory and
    # finally Python's platform-selected temporary directory.
    candidates = [
        Path(os.environ["TMPDIR"]) if os.environ.get("TMPDIR") else None,
        Path.home() / "tmp",
        Path(tempfile.gettempdir()),
    ]
    temp_root = next(
        (
            candidate
            for candidate in candidates
            if candidate is not None
            and candidate.is_dir()
            and os.access(candidate, os.W_OK)
        ),
        None,
    )
    if temp_root is None:
        raise RuntimeError("No writable HarmonyOS temporary directory was found")
    work = Path(tempfile.mkdtemp(prefix="kdoctools5-ohos-", dir=str(temp_root)))

    try:
        fixture_dir = Path(__file__).resolve().parent / "fixtures"
        input_xml = fixture_dir / "article.xml"
        stylesheet = fixture_dir / "identity.xsl"
        output_html = work / "rendered.html"
        env = os.environ.copy()
        env["TMPDIR"] = str(work)
        env["XDG_DATA_HOME"] = str(work / "xdg-data")
        package_data_root = package / "share"
        previous_data_dirs = env.get("XDG_DATA_DIRS", "")
        env["XDG_DATA_DIRS"] = os.pathsep.join(
            part for part in (str(package_data_root), previous_data_dirs) if part
        )

        completed = subprocess.run(
            [
                str(meinproc),
                "--stylesheet",
                str(stylesheet),
                "--srcdir",
                str(kdoctools_data),
                "--output",
                str(output_html),
                str(input_xml),
            ],
            cwd=str(work),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "meinproc5 failed on HarmonyOS (exit {}):\n{}\n{}".format(
                    completed.returncode, completed.stdout, completed.stderr
                )
            )
        if not output_html.is_file() or output_html.stat().st_size == 0:
            raise RuntimeError("meinproc5 did not create a non-empty HTML output")
        rendered = output_html.read_text(encoding="utf-8", errors="replace")
        if MARKER not in rendered:
            raise RuntimeError(
                f"DocBook content did not reach the output; marker {MARKER!r} missing"
            )
        print(
            "HarmonyOS DocBook integration passed: meinproc5 loaded and transformed "
            f"the fixture under {work}"
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
