#!/usr/bin/env python3
"""smu 1.5 functional regression tests; Python standard library only.

Expected HTML is fixed below from the release's documentation and smu.c,
not generated from the executable under test or compared with a second run.
The upstream testdoc contains sample input, but no expected output or runner.

Usage: python3 functional.py /absolute/path/to/smu --report-dir ./smu-report

Raw subprocess output is always retained. Only when this runner itself runs
on Windows are CRLF output bytes normalized to LF for comparison, because
Windows C stdio translates newlines. OHOS/POSIX output is compared byte for
byte without newline normalization. This host policy is recorded in JSON.
Reusing --report-dir replaces the latest report. summary.json is atomically
marked running before executing anything, then passed or failed at completion;
an interrupted run must never be accepted as a completed passing report.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile


VERSION = "1.5"
ARGV0 = "smu"


def utf8(value):
    return value.encode("utf-8")


def make_cases():
    """Define small, readable assertions for supported syntax and CLI paths."""
    cases = []

    def add(name, markdown=b"", html=b"", args=(), filename=None,
            stderr=b"", exit_rule="zero"):
        cases.append({
            "name": name,
            "input": utf8(markdown) if isinstance(markdown, str) else markdown,
            "stdout": utf8(html) if isinstance(html, str) else html,
            "stderr": utf8(stderr) if isinstance(stderr, str) else stderr,
            "args": list(args),
            "filename": filename,
            "exit_rule": exit_rule,
        })

    basic_input = "# Heading\n\nA *small* **test** and `a < b`.\n"
    basic_output = (
        "<h1>Heading</h1>\n"
        "<p>A <em>small</em> <strong>test</strong> and <code>a &lt; b</code>.</p>\n"
    )
    add("markdown_stdin", basic_input, basic_output)
    add("markdown_file", basic_input, basic_output,
        args=("sample file.md",), filename="sample file.md")
    add("heading_levels", "# One\n\n## Two\n\n### Three\n\n"
        "#### Four\n\n##### Five\n\n###### Six\n",
        "<h1>One</h1>\n<h2>Two</h2>\n<h3>Three</h3>\n"
        "<h4>Four</h4>\n<h5>Five</h5>\n<h6>Six</h6>\n")
    add("setext_headings", "Heading\n=======\n\nTopic\n-----\n",
        "<h1>Heading</h1>\n<h2>Topic</h2>\n")
    add("emphasis", "_one_ __two__ ___three___ and ***four***.\n",
        "<p><em>one</em> <strong>two</strong> "
        "<strong><em>three</em></strong> and <strong><em>four</em></strong>.</p>\n")
    add("inline_code_escaping", '`<a & "b">` and ``a ` b``.\n',
        '<p><code>&lt;a &amp; &quot;b&quot;&gt;</code> and <code>a ` b</code>.</p>\n')
    add("paragraphs", "first\ncontinued\n\nsecond\n",
        "<p>first\ncontinued</p>\n<p>second</p>\n")
    add("unordered_list", "* one\n* two\n",
        "<ul>\n<li>one</li>\n<li>two</li>\n</ul>\n")
    add("ordered_list", "1. one\n2. two\n",
        "<ol>\n<li>one</li>\n<li>two</li>\n</ol>\n")
    add("blockquote", "> quoted\n> text\n",
        "<blockquote><p>quoted\ntext</p>\n</blockquote>\n")
    add("indented_code", '   a < b && "x"\n',
        '<pre><code>a &lt; b &amp;&amp; &quot;x&quot;\n</code></pre>\n')
    add("links_images", '[site](https://example.org/ "Title") '
        '![alt](https://example.org/p.png "Picture")\n',
        '<p><a href="https://example.org/" title="Title">site</a> '
        '<img src="https://example.org/p.png" alt="alt" title="Picture" /></p>\n')
    add("autolink", "<https://example.org/>\n",
        '<p><a href="https://example.org/">https://example.org/</a></p>\n')
    # doreplace inserts <br /> without consuming the two spaces/newline.
    add("hard_break", "first  \nsecond\n", "<p>first<br />  \nsecond</p>\n")
    add("horizontal_rule", "- - -\n", "<hr />\n")
    add("escaped_markup", r"\*literal\* and \_plain\_." + "\n",
        "<p>*literal* and _plain_.</p>\n")
    html_input = '<b>raw</b> &amp; "text"\n'
    add("raw_html_default", html_input, '<p><b>raw</b> &amp; "text"</p>\n')
    strict_output = (
        '<p>&lt;b&gt;raw&lt;/b&gt; &amp;amp; &quot;text&quot;</p>\n'
    )
    add("strict_html_stdin", html_input, strict_output, args=("-n",))
    add("strict_html_file", html_input, strict_output,
        args=("-n", "strict.md"), filename="strict.md")
    add("utf8_content", "# 鸿蒙\n\n中文 café — 😀 **正常**\n",
        "<h1>鸿蒙</h1>\n<p>中文 café — 😀 <strong>正常</strong></p>\n")
    add("empty_stdin")
    add("empty_file", args=("empty.md",), filename="empty.md")
    add("blank_lines", "\n\n\n", "")
    add("no_final_newline", "plain text", "<p>plain text</p>\n")
    # More than sixteen 8192-byte buffers, also larger than Windows BUFSIZ.
    large_text = "buffer-boundary-" * 8193
    add("large_input", large_text + "\n", "<p>" + large_text + "</p>\n")
    add("double_dash_stdin", basic_input, basic_output, args=("--",))
    add("dash_filename", basic_input, basic_output,
        args=("--", "-sample.md"), filename="-sample.md")
    add("version", args=("-v",),
        stderr="simple markup 1.5 (C) Enno Boland\n", exit_rule="nonzero")
    usage = "Usage {} [-n] [file]\n -n escape html strictly\n".format(ARGV0)
    for name, argument in (("help", "-h"), ("unknown_option", "--unknown"),
                           ("dash_filename_without_separator", "-sample.md")):
        add(name, args=(argument,), stderr=usage, exit_rule="nonzero")
    add("missing_file", args=("not-present.md",),
        stderr="Cannot open file `not-present.md`\n", exit_rule="nonzero")
    return cases


def compared(data):
    return data.replace(b"\r\n", b"\n") if os.name == "nt" else data


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path, help="path to the smu 1.5 executable")
    parser.add_argument("--report-dir", type=Path, default=Path("smu-functional-report"))
    parser.add_argument("--timeout", type=float, default=10.0,
                        help="seconds allowed for each case (default: 10)")
    options = parser.parse_args()
    executable = options.executable.expanduser().resolve()
    report = options.report_dir.expanduser().resolve()
    report.mkdir(parents=True, exist_ok=True)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    initial = {
        "schema_version": 1, "suite": "smu-1.5-functional", "status": "running",
        "started_at_utc": started, "executable": str(executable), "results": [],
    }
    write_json(report / "summary.json", initial)
    for error in (
        "executable is not a file: {}".format(executable) if not executable.is_file() else None,
        "--timeout must be positive" if options.timeout <= 0 else None,
    ):
        if error:
            initial.update(status="failed", error=error)
            write_json(report / "summary.json", initial)
            parser.error(error)
    cases = make_cases()
    results = []
    # A private directory ensures missing-file tests cannot hit unrelated files.
    with tempfile.TemporaryDirectory(prefix="smu-fixtures-", dir=str(report)) as temporary:
        working = Path(temporary)
        for case in cases:
            name = case["name"]
            if case["filename"] is not None:
                (working / case["filename"]).write_bytes(case["input"])
            command = [str(executable)] + case["args"]
            # A fixed ASCII argv[0] avoids Windows ANSI conversion of a
            # non-ASCII installation path in usage text. The executable path
            # stays explicit; no shell or PATH lookup is involved.
            argv = [ARGV0] + case["args"]
            error = None
            returncode = None
            try:
                completed = subprocess.run(
                    argv, executable=str(executable),
                    input=case["input"] if case["filename"] is None else b"",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    cwd=str(working), timeout=options.timeout, check=False,
                )
                stdout, stderr = completed.stdout, completed.stderr
                returncode = completed.returncode
            except subprocess.TimeoutExpired as exception:
                stdout, stderr = exception.stdout or b"", exception.stderr or b""
                error = "timeout after {} seconds".format(options.timeout)
            except OSError as exception:
                stdout, stderr = b"", b""
                error = "{}: {}".format(type(exception).__name__, exception)
            evidence = {
                "input": name + ".input",
                "stdout": name + ".stdout",
                "stderr": name + ".stderr",
                "expected_stdout": name + ".expected.stdout",
                "expected_stderr": name + ".expected.stderr",
            }
            for key, data in (("input", case["input"]), ("stdout", stdout),
                              ("stderr", stderr), ("expected_stdout", case["stdout"]),
                              ("expected_stderr", case["stderr"])):
                (report / evidence[key]).write_bytes(data)
            # Negative return codes indicate signals on POSIX and are never
            # accepted as a successful diagnostic/usage error.
            exit_matches = (returncode == 0 if case["exit_rule"] == "zero"
                            else returncode is not None and returncode > 0)
            stdout_matches = compared(stdout) == case["stdout"]
            stderr_matches = compared(stderr) == case["stderr"]
            passed = error is None and exit_matches and stdout_matches and stderr_matches
            result = {
                "name": name, "passed": passed, "command": command, "argv": argv,
                "input_mode": "file" if case["filename"] is not None else "stdin",
                "fixture_filename": case["filename"],
                "returncode": returncode, "expected_exit": case["exit_rule"],
                "exit_matches": exit_matches, "stdout_matches": stdout_matches,
                "stderr_matches": stderr_matches, "error": error,
                "evidence": evidence,
            }
            write_json(report / (name + ".json"), result)
            results.append(result)
            print("{} {} (exit={})".format("PASS" if passed else "FAIL", name, returncode))
    failed = sum(not result["passed"] for result in results)
    summary = {
        "schema_version": 1,
        "suite": "smu-1.5-functional",
        "status": "failed" if failed else "passed",
        "started_at_utc": started,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "expected_smu_version": VERSION,
        "executable": str(executable), "executable_sha256": sha256_file(executable),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "host": {"system": platform.system(), "release": platform.release(),
                 "machine": platform.machine(), "python": sys.version},
        "comparison_policy": ("Windows host only: normalize CRLF to LF; raw bytes retained"
                              if os.name == "nt" else "Exact bytes; no newline normalization"),
        "total": len(results), "passed": len(results) - failed, "failed": failed,
        "results": results,
    }
    write_json(report / "summary.json", summary)
    print("{} passed, {} failed; report: {}".format(len(results) - failed, failed, report))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
